from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.core.security import RoleName, require_roles
from app.models import Engagement
from app.schemas.engagements import (
    EngagementCreateRequest,
    EngagementDetail,
    EngagementScanRunSummary,
    EngagementStatus,
    EngagementSummary,
    EngagementUpdateRequest,
)
from app.schemas.scans import ScanStatus
from app.services.report import EngagementReportGenerator

router = APIRouter(prefix="/engagements", tags=["engagements"])


@router.post("", response_model=EngagementSummary)
def create_engagement(
    request: EngagementCreateRequest,
    _user: object = Depends(require_roles(RoleName.admin)),
    db: Session = Depends(get_db_session),
) -> EngagementSummary:
    engagement = Engagement(
        name=request.name,
        authorization_ref=request.authorization_ref,
        authorized_targets=request.authorized_targets,
        authorized_by=request.authorized_by,
        authorized_at=request.authorized_at,
        notes=request.notes,
        status=EngagementStatus.active.value,
    )
    db.add(engagement)
    db.commit()
    db.refresh(engagement)
    return _to_summary(engagement)


@router.get("", response_model=list[EngagementSummary])
def list_engagements(
    _user: object = Depends(require_roles(RoleName.admin, RoleName.analyst, RoleName.viewer, RoleName.auditor)),
    db: Session = Depends(get_db_session),
) -> list[EngagementSummary]:
    engagements = db.query(Engagement).order_by(Engagement.created_at.desc()).all()
    return [_to_summary(engagement) for engagement in engagements]


@router.get("/{engagement_id}", response_model=EngagementDetail)
def get_engagement(
    engagement_id: UUID,
    _user: object = Depends(require_roles(RoleName.admin, RoleName.analyst, RoleName.viewer, RoleName.auditor)),
    db: Session = Depends(get_db_session),
) -> EngagementDetail:
    engagement = db.get(Engagement, engagement_id)
    if engagement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Engagement not found")
    return _to_detail(engagement)


@router.patch("/{engagement_id}", response_model=EngagementSummary)
def update_engagement(
    engagement_id: UUID,
    request: EngagementUpdateRequest,
    _user: object = Depends(require_roles(RoleName.admin)),
    db: Session = Depends(get_db_session),
) -> EngagementSummary:
    engagement = db.get(Engagement, engagement_id)
    if engagement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Engagement not found")

    if request.status is None and request.notes is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No engagement fields were provided")

    if request.status is not None:
        engagement.status = request.status.value
    if request.notes is not None:
        engagement.notes = request.notes

    db.commit()
    db.refresh(engagement)
    return _to_summary(engagement)


@router.get("/{engagement_id}/report")
def get_engagement_report(
    engagement_id: UUID,
    _user: object = Depends(require_roles(RoleName.admin, RoleName.analyst, RoleName.viewer, RoleName.auditor)),
    db: Session = Depends(get_db_session),
) -> dict[str, object]:
    engagement = db.get(Engagement, engagement_id)
    if engagement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Engagement not found")

    if engagement.status != EngagementStatus.completed.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Engagement is not completed")

    running_scan_exists = any(
        scan_run.status in {ScanStatus.queued.value, ScanStatus.running.value}
        for scan_run in engagement.scan_runs
    )
    if running_scan_exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Engagement still has running scan jobs",
        )

    report = EngagementReportGenerator().generate(db, engagement)
    return jsonable_encoder(report.to_dict())


def _to_summary(engagement: Engagement) -> EngagementSummary:
    return EngagementSummary(
        id=engagement.id,
        name=engagement.name,
        authorization_ref=engagement.authorization_ref,
        authorized_targets=list(engagement.authorized_targets or []),
        authorized_by=engagement.authorized_by,
        authorized_at=engagement.authorized_at,
        notes=engagement.notes,
        created_at=engagement.created_at,
        status=EngagementStatus(engagement.status),
    )


def _to_detail(engagement: Engagement) -> EngagementDetail:
    return EngagementDetail(
        **_to_summary(engagement).model_dump(),
        scan_runs=[
            EngagementScanRunSummary(
                id=scan_run.id,
                provider=scan_run.provider,
                status=scan_run.status,
                scan_type=scan_run.scan_type,
                targets=[target.target_value for target in scan_run.targets],
                started_at=scan_run.started_at,
                completed_at=scan_run.completed_at,
            )
            for scan_run in engagement.scan_runs
        ],
    )
