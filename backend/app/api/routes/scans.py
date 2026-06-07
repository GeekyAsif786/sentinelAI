from __future__ import annotations

from datetime import UTC, datetime
from ipaddress import IPv4Network, IPv6Network, ip_address, ip_network
import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.core.security import AuthenticatedUser, RoleName, require_roles
from app.core.target_validator import (
    ScanContext,
    classify_ip,
    is_valid_scan_target,
    target_in_scope,
)
from app.models import Engagement, ScanPolicy, ScanRun, ScanTarget, ScannerProfile
from app.schemas.scans import ScanCreateResponse, ScanDetail, ScanRequest, ScanStatus, ScanTargetType
from app.tasks import execute_scan_from_queue

router = APIRouter(prefix="/scans", tags=["scans"])
legacy_router = APIRouter(prefix="/scan", tags=["scans"])
HOSTNAME_PATTERN = re.compile(r"^(?=.{1,253}$)(?!-)[A-Za-z0-9.-]+(?<!-)$")


@router.post("", response_model=ScanCreateResponse)
@legacy_router.post("", response_model=ScanCreateResponse)
def create_scan(
    scan_request: ScanRequest,
    request: Request,
    user: AuthenticatedUser = Depends(require_roles(RoleName.admin, RoleName.analyst)),
    db: Session = Depends(get_db_session),
) -> ScanCreateResponse:
    policy = db.get(ScanPolicy, scan_request.policy_id)
    if policy is None or not policy.is_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan policy is unavailable")

    profile = db.get(ScannerProfile, scan_request.scanner_profile_id)
    if profile is None or not profile.is_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scanner profile is unavailable")

    if profile.provider != scan_request.provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scanner profile provider does not match the requested provider",
        )

    engagement = None
    if scan_request.engagement_id is not None:
        engagement = db.get(Engagement, scan_request.engagement_id)
        if engagement is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Engagement not found")

    # Context rules:
    # - XML import:     ScanContext.xml_import    (no live IP validation)
    # - With engagement: ScanContext.external     (public IPs only, scope enforced)
    # - No engagement:  ScanContext.institutional (RFC1918 + VPC + public allowed)
    if getattr(scan_request, "is_xml_import", False):
        scan_context = ScanContext.xml_import
    elif scan_request.engagement_id is not None:
        scan_context = ScanContext.external
    else:
        scan_context = ScanContext.institutional

    if len(scan_request.targets) > policy.max_targets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target count exceeds the enabled scan policy",
        )

    validated_targets = [_validate_target(target, context=scan_context) for target in scan_request.targets]
    if engagement is not None:
        authorized_targets = list(engagement.authorized_targets or [])
        for validated in validated_targets:
            target_type = validated.get("type")
            if isinstance(target_type, str) and target_type in (
                ScanTargetType.ip.value,
                ScanTargetType.cidr.value,
            ):
                target_value = validated.get("value")
                if not isinstance(target_value, str) or not _target_is_authorized(
                    target_value,
                    target_type,
                    authorized_targets,
                ):
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            f"Target '{target_value}' is outside "
                            f"authorized scope for engagement {engagement.id}. "
                            f"Authorized: {engagement.authorized_targets}"
                        ),
                    )

    requested_by_user_id = _parse_user_id(user.user_id)

    scan_run = ScanRun(
        requested_by_user_id=requested_by_user_id,
        scan_policy_id=policy.id,
        scanner_profile_id=profile.id,
        engagement_id=scan_request.engagement_id,
        provider=scan_request.provider,
        status=ScanStatus.queued.value,
        scan_type=scan_request.scan_type,
        scan_source_ip=request.client.host if request.client else None,
        started_at=datetime.now(UTC),
        configuration={
            "target_count": len(validated_targets),
            "scanner_profile": profile.name,
            "provider": scan_request.provider,
        },
    )
    db.add(scan_run)
    db.flush()

    for target in validated_targets:
        db.add(
            ScanTarget(
                scan_run_id=scan_run.id,
                target_value=target["value"],
                target_type=target["type"],
                validation_status=target["status"],
                validation_message=target["message"],
            )
        )

    db.commit()

    execute_scan_from_queue.delay()

    engagement_note = ""
    if engagement is not None:
        engagement_note = f" Engagement {engagement.id} was attached to the scan."

    return ScanCreateResponse(
        scan_id=scan_run.id,
        status=ScanStatus.queued,
        message=(
            f"Scan accepted for policy {scan_request.policy_id} by {user.email}. "
            f"{len(validated_targets)} target(s) were validated and queued.{engagement_note}"
        ),
    )


@router.post("/import", response_model=ScanCreateResponse)
async def import_nmap_xml(
    request: Request,
    label: str = Query(
        default="xml-import",
        description="Human-readable label for this import",
    ),
    user: AuthenticatedUser = Depends(
        require_roles(RoleName.admin, RoleName.analyst)
    ),
    db: Session = Depends(get_db_session),
) -> ScanCreateResponse:
    """
    Import a pre-captured Nmap XML artifact.

    Use this when:
    - You ran nmap manually from a different machine or ISP
    - You have an existing scan result to feed into sentinelAI
    - Live scanning is not possible (firewall, ISP filtering, etc.)

    The XML is parsed, hosts and services are extracted, and the
    full risk scoring + graph projection pipeline runs normally.
    No live network probes are sent.
    """
    from app.discovery.nmap import NmapDiscoveryProvider, NmapXmlParseError

    content = (await request.body()).decode("utf-8", errors="replace")
    if not content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    provider = NmapDiscoveryProvider()
    try:
        discovery_result = provider.parse_artifact(content)
    except NmapXmlParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid Nmap XML: {exc}",
        ) from exc

    if not discovery_result.hosts:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No live hosts found in the uploaded Nmap XML.",
        )

    requested_by_user_id = _parse_user_id(user.user_id)

    scan_run = ScanRun(
        requested_by_user_id=requested_by_user_id,
        scan_policy_id=None,
        scanner_profile_id=None,
        engagement_id=None,
        provider="nmap",
        status=ScanStatus.queued.value,
        scan_type="xml_import",
        scan_source_ip=request.client.host if request.client else None,
        started_at=datetime.now(UTC),
        configuration={
            "import_label": label,
            "source": "xml_upload",
            "hosts_in_artifact": len(discovery_result.hosts),
            "artifact_sha256": discovery_result.raw_artifact_sha256,
        },
    )
    db.add(scan_run)
    db.flush()

    for host in discovery_result.hosts:
        db.add(
            ScanTarget(
                scan_run_id=scan_run.id,
                target_value=host.primary_ip,
                target_type="ip",
                validation_status="xml_import",
                validation_message="Target extracted from uploaded Nmap XML artifact.",
            )
        )

    db.commit()

    from app.tasks import process_xml_import
    process_xml_import.delay(
        scan_run_id=str(scan_run.id),
        xml_content=content,
    )

    return ScanCreateResponse(
        scan_id=scan_run.id,
        status=ScanStatus.queued,
        message=(
            f"XML import accepted. "
            f"{len(discovery_result.hosts)} host(s) found in artifact. "
            f"Risk scoring and graph projection queued."
        ),
    )


@router.get("/{scan_id}", response_model=ScanDetail)
@legacy_router.get("/{scan_id}", response_model=ScanDetail)
def get_scan(
    scan_id: UUID,
    user: AuthenticatedUser = Depends(
        require_roles(RoleName.admin, RoleName.analyst, RoleName.viewer, RoleName.auditor)
    ),
    db: Session = Depends(get_db_session),
) -> ScanDetail:
    scan_run = db.get(ScanRun, scan_id)
    if scan_run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

    return ScanDetail(
        scan_id=scan_id,
        status=ScanStatus(scan_run.status),
        provider=scan_run.provider,
        targets=[target.target_value for target in scan_run.targets],
        graph_projection_status=_graph_projection_status(scan_run.status),
        error_message=scan_run.error_message,
    )


def _parse_user_id(raw_user_id: str) -> UUID:
    try:
        return UUID(raw_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user id") from exc


def _validate_target(
    target: str,
    context: ScanContext = ScanContext.institutional,
) -> dict[str, str | None]:
    normalized_target = target.strip()
    if not normalized_target:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target values cannot be empty")

    if "/" in normalized_target:
        try:
            network = ip_network(normalized_target, strict=False)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid CIDR target: {target}") from exc
        _validate_network_target(network, context)
        return {
            "value": str(network),
            "type": ScanTargetType.cidr.value,
            "status": "validated",
            "message": None,
        }

    try:
        address = ip_address(normalized_target)
    except ValueError:
        if not HOSTNAME_PATTERN.match(normalized_target):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid target: {target}")
        return {
            "value": normalized_target,
            "type": ScanTargetType.hostname.value,
            "status": "validated",
            "message": "Hostname accepted for resolution during worker execution",
        }

    if not is_valid_scan_target(str(address), context=context):
        ip_class = classify_ip(str(address))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Target '{address}' cannot be scanned in "
                f"{context} context. "
                f"Classification: {ip_class}. "
                f"Blocked ranges: CGNAT (100.64.0.0/10), loopback, "
                f"multicast, link-local, documentation, and benchmarking "
                f"ranges are never scannable. Use institutional context "
                f"for RFC1918/VPC targets (no engagement_id required)."
            ),
        )

    return {
        "value": str(address),
        "type": ScanTargetType.ip.value,
        "status": "validated",
        "message": None,
    }


def _validate_network_target(network: IPv4Network | IPv6Network, context: ScanContext) -> None:
    if context == ScanContext.xml_import:
        return

    network_address = getattr(network, "network_address")
    broadcast_address = getattr(network, "broadcast_address")
    for address in (network_address, broadcast_address):
        if not is_valid_scan_target(str(address), context=context):
            ip_class = classify_ip(str(address))
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Target '{network}' cannot be scanned in "
                    f"{context} context. "
                    f"Classification: {ip_class}. "
                    f"Blocked ranges: CGNAT (100.64.0.0/10), loopback, "
                    f"multicast, link-local, documentation, and benchmarking "
                    f"ranges are never scannable. Use institutional context "
                    f"for RFC1918/VPC targets (no engagement_id required)."
                ),
            )


def _target_is_authorized(
    target_value: str,
    target_type: str,
    authorized_targets: list[str],
) -> bool:
    if target_type == ScanTargetType.ip.value:
        return bool(target_in_scope(target_value, authorized_targets))

    try:
        target_network = ip_network(target_value, strict=False)
    except ValueError:
        return False

    for authorized_target in authorized_targets:
        try:
            authorized_network = ip_network(authorized_target, strict=False)
        except ValueError:
            try:
                authorized_ip = ip_address(authorized_target)
            except ValueError:
                continue
            if target_network.num_addresses == 1 and target_network.network_address == authorized_ip:
                return True
            continue

        if isinstance(target_network, IPv4Network) and isinstance(authorized_network, IPv4Network):
            if target_network.subnet_of(authorized_network):
                return True
            continue

        if isinstance(target_network, IPv6Network) and isinstance(authorized_network, IPv6Network):
            if target_network.subnet_of(authorized_network):
                return True
            continue

    return False


def _graph_projection_status(scan_status: str) -> str:
    if scan_status == ScanStatus.completed.value:
        return "projected"
    if scan_status == ScanStatus.partial.value:
        return "partial"
    if scan_status == ScanStatus.failed.value:
        return "failed"
    return "queued"
