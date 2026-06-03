from datetime import UTC, datetime
from ipaddress import ip_address, ip_network
import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.core.security import AuthenticatedUser, RoleName, require_roles
from app.models import ScanPolicy, ScanRun, ScanTarget, ScannerProfile
from app.schemas.scans import ScanCreateResponse, ScanDetail, ScanRequest, ScanStatus, ScanTargetType

router = APIRouter(prefix="/scan", tags=["scan"])
HOSTNAME_PATTERN = re.compile(r"^(?=.{1,253}$)(?!-)[A-Za-z0-9.-]+(?<!-)$")


@router.post("", response_model=ScanCreateResponse)
def create_scan(
    request: ScanRequest,
    user: AuthenticatedUser = Depends(require_roles(RoleName.admin, RoleName.analyst)),
    db: Session = Depends(get_db_session),
) -> ScanCreateResponse:
    policy = db.get(ScanPolicy, request.policy_id)
    if policy is None or not policy.is_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan policy is unavailable")

    profile = db.get(ScannerProfile, request.scanner_profile_id)
    if profile is None or not profile.is_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scanner profile is unavailable")

    if profile.provider != request.provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scanner profile provider does not match the requested provider",
        )

    if len(request.targets) > policy.max_targets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target count exceeds the enabled scan policy",
        )

    validated_targets = [_validate_target(target, policy) for target in request.targets]
    requested_by_user_id = _parse_user_id(user.user_id)

    scan_run = ScanRun(
        requested_by_user_id=requested_by_user_id,
        scan_policy_id=policy.id,
        scanner_profile_id=profile.id,
        provider=request.provider,
        status=ScanStatus.queued.value,
        scan_type=request.scan_type,
        started_at=datetime.now(UTC),
        configuration={
            "target_count": len(validated_targets),
            "scanner_profile": profile.name,
            "provider": request.provider,
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
    return ScanCreateResponse(
        scan_id=scan_run.id,
        status=ScanStatus.queued,
        message=(
            f"Scan accepted for policy {request.policy_id} by {user.email}. "
            f"{len(validated_targets)} target(s) were validated and queued."
        ),
    )


@router.get("/{scan_id}", response_model=ScanDetail)
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


def _validate_target(target: str, policy: ScanPolicy) -> dict[str, str | None]:
    normalized_target = target.strip()
    if not normalized_target:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target values cannot be empty")

    if "/" in normalized_target:
        try:
            network = ip_network(normalized_target, strict=False)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid CIDR target: {target}") from exc
        _validate_network_scope(network, policy, target)
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

    _validate_address_scope(address, policy, target)
    return {
        "value": str(address),
        "type": ScanTargetType.ip.value,
        "status": "validated",
        "message": None,
    }


def _validate_address_scope(address: object, policy: ScanPolicy, target: str) -> None:
    if not policy.allowed_cidrs:
        return

    for blocked_cidr in policy.blocked_cidrs:
        if ip_address(str(address)) in ip_network(str(blocked_cidr), strict=False):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Target is blocked by policy: {target}")

    if any(ip_address(str(address)) in ip_network(str(allowed_cidr), strict=False) for allowed_cidr in policy.allowed_cidrs):
        return

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Target is outside the policy scope: {target}")


def _validate_network_scope(network: object, policy: ScanPolicy, target: str) -> None:
    if not policy.allowed_cidrs:
        return

    for blocked_cidr in policy.blocked_cidrs:
        if ip_network(str(network), strict=False).overlaps(ip_network(str(blocked_cidr), strict=False)):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Target is blocked by policy: {target}")

    if any(ip_network(str(network), strict=False).subnet_of(ip_network(str(allowed_cidr), strict=False)) for allowed_cidr in policy.allowed_cidrs):
        return

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Target is outside the policy scope: {target}")


def _graph_projection_status(scan_status: str) -> str:
    if scan_status == ScanStatus.completed.value:
        return "projected"
    if scan_status == ScanStatus.partial.value:
        return "partial"
    if scan_status == ScanStatus.failed.value:
        return "failed"
    return "queued"

