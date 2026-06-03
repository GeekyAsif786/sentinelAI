from datetime import UTC, datetime
from ipaddress import ip_network

from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload

from app.core.database import SessionLocal
from app.discovery.nmap import NmapDiscoveryProvider, NmapXmlParseError
from app.graph.projection import InventoryGraphProjection
from app.models import Finding, GraphProjectionJob, Host, ScanRun, Service
from app.schemas.scans import ScanStatus
from app.worker import celery_app


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
            .options(selectinload(ScanRun.scanner_profile), selectinload(ScanRun.targets))
        )

        if scan_run is None:
            return {"status": "no_queue", "message": "No queued scans available"}

        return _execute_nmap_scan(session, scan_run, self.request.hostname)

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
        targets = [target.target_value for target in scan_run.targets]
        profile_config = scan_run.scanner_profile.configuration or {}

        provider = NmapDiscoveryProvider()
        discovery_result = provider.execute_nmap(targets, profile_config)

        _persist_discovery_result(session, scan_run, discovery_result)

        scan_run.status = ScanStatus.completed.value
        scan_run.completed_at = datetime.now(UTC)
        scan_run.provider_version = discovery_result.provider_version
        scan_run.configuration["hosts_discovered"] = len(discovery_result.hosts)
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
    except RuntimeError as exc:
        return _handle_scan_error(session, scan_run, "EXECUTION_ERROR", f"Nmap execution failed: {exc}")
    except Exception as exc:
        return _handle_scan_error(session, scan_run, "UNKNOWN_ERROR", f"Unexpected error: {exc}")


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


def _is_external_service(service) -> bool:
    """Heuristic to determine if service is externally exposed.

    Args:
        service: DiscoveredService object

    Returns:
        True if service appears externally exposed
    """
    external_ports = {22, 80, 443, 3306, 5432, 6379, 8080, 8443}
    return service.port in external_ports or service.port >= 8000


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