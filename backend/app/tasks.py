from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from ipaddress import ip_address

import celery.exceptions
import structlog

from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.discovery.nmap import NmapDiscoveryProvider, NmapXmlParseError, SCAN_PROFILES, ScanProfile
from app.discovery.provider import DiscoveryResult, DiscoveredHost, DiscoveredService
from app.graph.projection import InventoryGraphProjection
from app.models import Finding, GraphProjectionJob, Host, ScanRun, Service
from app.schemas.scans import ScanStatus
from app.services.cve import NvdCveClient, CveData
from app.services.epss import EpssClient, EpssData
from app.services.recon import PassiveReconService, PassiveReconResult
from app.worker import celery_app

logger = structlog.get_logger()


@celery_app.task(name="execute_scan_from_queue", bind=True, max_retries=3)
def execute_scan_from_queue(self) -> dict[str, object]:
    """Dequeue next queued scan and execute it.

    Returns:
        Dictionary with execution results and metrics
    """
    session = SessionLocal()
    try:
        scan_run = session.scalar(
            select(ScanRun)
            .where(and_(ScanRun.status == ScanStatus.queued.value, ScanRun.provider == "nmap"))
            .order_by(ScanRun.created_at)
            .options(
                selectinload(ScanRun.scanner_profile),
                selectinload(ScanRun.targets),
                selectinload(ScanRun.engagement),
            )
        )

        if scan_run is None:
            return {"status": "no_queue", "message": "No queued scans available"}

        return _execute_nmap_scan(session, scan_run, self.request.hostname)

    except celery.exceptions.Retry:
        raise
    except Exception as exc:
        self.retry(exc=exc, countdown=60)
        return {"status": "error", "message": str(exc)}
    finally:
        session.close()


def _execute_nmap_scan(session, scan_run: ScanRun, worker_node_id: str | None = None) -> dict[str, object]:
    """Execute nmap scan for a ScanRun.

    Args:
        session: SQLAlchemy session
        scan_run: The ScanRun to execute
        worker_node_id: Identifier of executing worker

    Returns:
        Dictionary with execution results
    """
    started_at = datetime.now(UTC)
    scan_run.status = ScanStatus.running.value
    scan_run.started_at = started_at
    scan_run.worker_node_id = worker_node_id
    session.commit()

    try:
        _persist_scan_targets(session, scan_run)
        _validate_scan_targets_for_execution(scan_run)

        targets = [target.target_value for target in scan_run.targets]
        scan_profile = _resolve_scan_profile(scan_run)

        provider = NmapDiscoveryProvider()
        discovery_result, recon_result = _prepare_discovery_run(provider, scan_run, targets, scan_profile)

        if recon_result is not None:
            scan_run.recon_data = recon_result.to_dict()
            logger.info(
                "Passive recon results available",
                scan_id=str(scan_run.id),
                target=targets[0],
                open_ports=recon_result.open_ports,
                hostnames=recon_result.hostnames,
                org=recon_result.org,
                isp=recon_result.isp,
                country=recon_result.country,
                vulns=recon_result.vulns,
            )
            session.commit()

        _persist_discovery_result(session, scan_run, discovery_result)

        _enrich_findings_with_cve_data(session, scan_run)

        scan_run.status = ScanStatus.completed.value
        scan_run.completed_at = datetime.now(UTC)
        scan_run.provider_version = discovery_result.provider_version
        scan_run.configuration = {
            **(scan_run.configuration or {}),
            "hosts_discovered": len(discovery_result.hosts),
            "open_ports": sum(len(host.services) for host in discovery_result.hosts),
        }
        session.commit()

        _trigger_graph_projection(session, scan_run)

        return {
            "status": "completed",
            "scan_id": str(scan_run.id),
            "hosts_discovered": len(discovery_result.hosts),
            "duration_seconds": (datetime.now(UTC) - started_at).total_seconds(),
        }

    except NmapXmlParseError as exc:
        return _handle_scan_error(session, scan_run, "PARSE_ERROR", f"Failed to parse nmap XML: {exc}")
    except TimeoutError as exc:
        return _handle_scan_error(session, scan_run, "TIMEOUT", f"Nmap execution timeout: {exc}")
    except PermissionError as exc:
        return _handle_scan_error(session, scan_run, "PERMISSION_ERROR", f"Nmap execution permission error: {exc}")
    except ValueError as exc:
        return _handle_scan_error(session, scan_run, "TARGET_VALIDATION_ERROR", f"Target validation failed: {exc}")
    except RuntimeError as exc:
        return _handle_scan_error(session, scan_run, "EXECUTION_ERROR", f"Nmap execution failed: {exc}")
    except Exception as exc:
        return _handle_scan_error(session, scan_run, "UNKNOWN_ERROR", f"Unexpected error: {exc}")


def _prepare_discovery_run(
    provider: NmapDiscoveryProvider,
    scan_run: ScanRun,
    targets: list[str],
    scan_profile: ScanProfile,
) -> tuple[DiscoveryResult, PassiveReconResult | None]:
    recon_result = _maybe_run_passive_recon(scan_run, targets)
    scan_config = SCAN_PROFILES.get(scan_profile)
    if scan_config is None or not scan_config.port_range:
        discovery_result = provider.execute_nmap(targets, scan_profile)
        return discovery_result, recon_result

    if recon_result is None or not recon_result.open_ports:
        discovery_result = provider.execute_nmap(targets, scan_profile)
        return discovery_result, recon_result

    seed_port_range = ",".join(str(port) for port in sorted(set(recon_result.open_ports)))
    if not seed_port_range:
        discovery_result = provider.execute_nmap(targets, scan_profile)
        return discovery_result, recon_result

    seeded_result = provider.execute_nmap(targets, scan_profile, port_range_override=seed_port_range)
    full_result = provider.execute_nmap(targets, scan_profile)
    return _merge_discovery_results(seeded_result, full_result), recon_result


def _maybe_run_passive_recon(scan_run: ScanRun, targets: list[str]) -> PassiveReconResult | None:
    if len(targets) != 1:
        return None

    target = targets[0]
    try:
        ip_address(target)
    except ValueError:
        return None

    if scan_run.engagement_id is None:
        return None

    settings = get_settings()
    recon_service = PassiveReconService(settings.shodan_api_key)

    logger.info("Running passive recon before active scan", scan_id=str(scan_run.id), target=target)
    return asyncio.run(recon_service.lookup_ip(target))


def _persist_scan_targets(session, scan_run: ScanRun) -> None:
    """Ensure IP scan targets exist in inventory even if discovery finds nothing."""
    now = datetime.now(UTC)

    for scan_target in scan_run.targets:
        if scan_target.target_type != "ip":
            continue

        existing_host = session.scalar(select(Host).where(Host.primary_ip == scan_target.target_value))
        if existing_host is not None:
            existing_host.last_seen_at = now
            continue

        session.add(
            Host(
                primary_ip=scan_target.target_value,
                hostname=None,
                mac_address=None,
                os_name=None,
                os_version=None,
                os_confidence=None,
                asset_criticality=3,
                source=scan_run.provider,
                first_seen_at=now,
                last_seen_at=now,
            )
        )

    session.commit()


def _resolve_scan_profile(scan_run: ScanRun) -> ScanProfile:
    configuration = scan_run.scanner_profile.configuration or {}
    raw_profile = configuration.get("scan_profile")
    if isinstance(raw_profile, str):
        try:
            return ScanProfile(raw_profile)
        except ValueError:
            logger.warning(
                "Unknown scanner profile configured, falling back to local discovery",
                scan_profile=raw_profile,
                scan_run_id=str(scan_run.id),
            )
    return ScanProfile.local_discovery


def _validate_scan_targets_for_execution(scan_run: ScanRun) -> None:
    if scan_run.engagement_id is None:
        return

    engagement = scan_run.engagement
    if engagement is None:
        raise ValueError(f"Engagement {scan_run.engagement_id} could not be loaded for validation")
    return


def _persist_discovery_result(session, scan_run: ScanRun, discovery_result) -> None:
    """Persist discovered hosts and services to database (upsert).

    Args:
        session: SQLAlchemy session
        scan_run: The ScanRun being processed
        discovery_result: DiscoveryResult from provider
    """
    now = datetime.now(UTC)

    for discovered_host in discovery_result.hosts:
        primary_ip = discovered_host.primary_ip

        existing_host = session.scalar(select(Host).where(Host.primary_ip == primary_ip))
        if existing_host:
            existing_host.hostname = discovered_host.hostname or existing_host.hostname
            existing_host.mac_address = discovered_host.mac_address or existing_host.mac_address
            existing_host.os_name = discovered_host.os_name or existing_host.os_name
            existing_host.os_confidence = discovered_host.os_confidence or existing_host.os_confidence
            existing_host.last_seen_at = now
        else:
            existing_host = Host(
                primary_ip=primary_ip,
                hostname=discovered_host.hostname,
                mac_address=discovered_host.mac_address,
                os_name=discovered_host.os_name,
                os_confidence=discovered_host.os_confidence,
                source=scan_run.provider,
                first_seen_at=now,
                last_seen_at=now,
            )
            session.add(existing_host)
            session.flush()

        for discovered_service in discovered_host.services:
            port = discovered_service.port
            protocol = discovered_service.protocol

            existing_service = session.scalar(
                select(Service).where(
                    and_(
                        Service.host_id == existing_host.id,
                        Service.port == port,
                        Service.protocol == protocol,
                    )
                )
            )

            if existing_service:
                existing_service.state = discovered_service.state
                existing_service.service_name = discovered_service.service_name or existing_service.service_name
                existing_service.product = discovered_service.product or existing_service.product
                existing_service.version = discovered_service.version or existing_service.version
                existing_service.last_seen_at = now
            else:
                new_service = Service(
                    host_id=existing_host.id,
                    port=port,
                    protocol=protocol,
                    state=discovered_service.state,
                    service_name=discovered_service.service_name,
                    product=discovered_service.product,
                    version=discovered_service.version,
                    exposure="external" if _is_external_service(discovered_service) else "internal",
                    first_seen_at=now,
                    last_seen_at=now,
                )
                session.add(new_service)

    session.commit()


def _merge_discovery_results(seed_result: DiscoveryResult, full_result: DiscoveryResult) -> DiscoveryResult:
    hosts_by_ip: dict[str, DiscoveredHost] = {}

    for host in (*seed_result.hosts, *full_result.hosts):
        existing_host = hosts_by_ip.get(host.primary_ip)
        if existing_host is None:
            hosts_by_ip[host.primary_ip] = host
            continue

        merged_services = _merge_services(existing_host.services, host.services)
        hosts_by_ip[host.primary_ip] = DiscoveredHost(
            primary_ip=host.primary_ip,
            hostname=host.hostname or existing_host.hostname,
            mac_address=host.mac_address or existing_host.mac_address,
            os_name=host.os_name or existing_host.os_name,
            os_confidence=host.os_confidence if host.os_confidence is not None else existing_host.os_confidence,
            services=merged_services,
        )

    return DiscoveryResult(
        provider=full_result.provider,
        hosts=tuple(hosts_by_ip.values()),
        raw_artifact_sha256=full_result.raw_artifact_sha256 or seed_result.raw_artifact_sha256,
        provider_version=full_result.provider_version or seed_result.provider_version,
    )


def _merge_services(
    seed_services: tuple[DiscoveredService, ...],
    full_services: tuple[DiscoveredService, ...],
) -> tuple[DiscoveredService, ...]:
    services_by_key: dict[tuple[int, str], DiscoveredService] = {}
    for service in (*seed_services, *full_services):
        key = (service.port, service.protocol)
        existing_service = services_by_key.get(key)
        if existing_service is None:
            services_by_key[key] = service
            continue

        services_by_key[key] = DiscoveredService(
            port=service.port,
            protocol=service.protocol,
            state=service.state or existing_service.state,
            service_name=service.service_name or existing_service.service_name,
            product=service.product or existing_service.product,
            version=service.version or existing_service.version,
        )

    return tuple(sorted(services_by_key.values(), key=lambda service: (service.port, service.protocol)))


EXTERNAL_PORTS: set[int] = {
    21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 3306, 3389, 5432, 6379, 8080, 8443, 27017
}


def _is_external_service(service) -> bool:
    """Heuristic to determine if service is externally exposed.

    Args:
        service: DiscoveredService object

    Returns:
        True if service appears externally exposed
    """
    return service.port in EXTERNAL_PORTS


def _trigger_graph_projection(session, scan_run: ScanRun) -> None:
    """Queue a graph projection job for this scan run.

    Args:
        session: SQLAlchemy session
        scan_run: The ScanRun that completed
    """
    projection_job = GraphProjectionJob(scan_run_id=scan_run.id)
    session.add(projection_job)
    session.commit()

    project_inventory_graph.delay(scan_run_id=str(scan_run.id))


def _handle_scan_error(session, scan_run: ScanRun, error_code: str, error_message: str) -> dict[str, object]:
    """Handle scan execution error and update status.

    Args:
        session: SQLAlchemy session
        scan_run: The ScanRun that failed
        error_code: Error classification code
        error_message: Human-readable error message

    Returns:
        Dictionary with error details
    """
    scan_run.status = ScanStatus.failed.value
    scan_run.completed_at = datetime.now(UTC)
    scan_run.error_code = error_code
    scan_run.error_message = error_message[:500]
    session.commit()

    return {
        "status": "failed",
        "scan_id": str(scan_run.id),
        "error_code": error_code,
        "error_message": error_message,
    }


@celery_app.task(name="project_inventory_graph")
def project_inventory_graph(scan_run_id: str | None = None) -> dict[str, object]:
    """Project inventory to Neo4j graph, with optional scan_run context.

    Args:
        scan_run_id: Optional UUID of scan_run that triggered projection

    Returns:
        Dictionary with projection results
    """
    session = SessionLocal()
    try:
        hosts = session.scalars(
            select(Host).options(selectinload(Host.services)).order_by(Host.last_seen_at.desc())
        ).all()

        projection = InventoryGraphProjection()
        neo4j_projected = projection.project_to_neo4j(hosts)
        graph_slice = projection.build_slice(hosts, max_nodes=250, max_depth=2)

        if scan_run_id:
            projection_job = session.scalar(
                select(GraphProjectionJob).where(GraphProjectionJob.scan_run_id == scan_run_id)
            )
            if projection_job:
                projection_job.status = "completed"
                projection_job.completed_at = datetime.now(UTC)
                projection_job.projection_stats = {
                    "host_count": len(hosts),
                    "node_count": len(graph_slice.nodes),
                    "edge_count": len(graph_slice.edges),
                }
                session.commit()

        return {
            "host_count": len(hosts),
            "node_count": len(graph_slice.nodes),
            "edge_count": len(graph_slice.edges),
            "neo4j_projected": neo4j_projected,
            "freshness_status": graph_slice.freshness_status,
        }

    except Exception as exc:
        if scan_run_id:
            projection_job = session.scalar(
                select(GraphProjectionJob).where(GraphProjectionJob.scan_run_id == scan_run_id)
            )
            if projection_job:
                projection_job.status = "failed"
                projection_job.completed_at = datetime.now(UTC)
                projection_job.error_message = str(exc)[:500]
                session.commit()
        return {
            "status": "failed",
            "error": str(exc),
        }
    finally:
        session.close()


async def _fetch_enrichment_data(
    cve_ids: list[str],
) -> tuple[dict[str, CveData], dict[str, EpssData]]:
    settings = get_settings()
    cve_client = NvdCveClient(api_key=settings.nvd_api_key)
    epss_client = EpssClient()

    # Run fetch_cves and fetch_epss in parallel
    cve_task = cve_client.fetch_cves(cve_ids)
    epss_task = epss_client.fetch_epss(cve_ids)

    return await asyncio.gather(cve_task, epss_task)


def _enrich_findings_with_cve_data(session: Any, scan_run: ScanRun) -> None:
    """Enrich scan run findings with CVE data (CVSS and EPSS scores)."""
    findings = session.scalars(
        select(Finding).where(Finding.scan_run_id == scan_run.id)
    ).all()

    if not findings:
        return

    cve_ids = list({f.cve_id for f in findings if f.cve_id})
    if not cve_ids:
        return

    try:
        cve_results, epss_results = asyncio.run(_fetch_enrichment_data(cve_ids))
    except Exception as e:
        logger.exception("Failed to fetch enrichment data in parallel", error=str(e))
        return

    for finding in findings:
        if finding.cve_id:
            cve_info = cve_results.get(finding.cve_id)
            if cve_info:
                finding.cvss_score = cve_info.cvss_score

            epss_info = epss_results.get(finding.cve_id)
            if epss_info:
                finding.epss_probability = epss_info.epss_probability
