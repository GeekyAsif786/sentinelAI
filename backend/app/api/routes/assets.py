from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db_session
from app.core.security import RoleName, require_roles
from app.models import Host
from app.schemas.assets import AssetListResponse, HostSummary, ServiceSummary
from app.services.risk import CompositeRiskScore, ExposureLevel, RiskInputs

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=AssetListResponse)
def list_assets(
    limit: int = 50,
    offset: int = 0,
    _user: object = Depends(
        require_roles(RoleName.admin, RoleName.analyst, RoleName.viewer, RoleName.auditor)
    ),
    db: Session = Depends(get_db_session),
) -> AssetListResponse:
    try:
        total = db.scalar(select(func.count()).select_from(Host)) or 0
        statement = (
            select(Host)
            .options(selectinload(Host.services))
            .order_by(Host.last_seen_at.desc())
            .limit(limit)
            .offset(offset)
        )
        hosts = db.scalars(statement).all()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Inventory database unavailable") from exc

    risk_scorer = CompositeRiskScore()
    assets = [
        _serialize_host(host, risk_scorer)
        for host in hosts
    ]
    return AssetListResponse(assets=assets, limit=limit, offset=offset, total=total)


def _serialize_host(host: Host, risk_scorer: CompositeRiskScore) -> HostSummary:
    services = sorted(host.services, key=lambda service: service.port)
    exposure = _host_exposure(services)
    risk_score = risk_scorer.calculate(
        RiskInputs(
            cvss_score=None,
            epss_probability=None,
            exposure=exposure,
            asset_criticality=host.asset_criticality,
        )
    ).score
    return HostSummary(
        id=host.id,
        primary_ip=str(host.primary_ip),
        hostname=host.hostname,
        os_name=host.os_name,
        asset_criticality=host.asset_criticality,
        risk_score=risk_score,
        last_seen_at=host.last_seen_at,
        services=[
            ServiceSummary(
                id=service.id,
                port=service.port,
                protocol=service.protocol,
                service_name=service.service_name,
                product=service.product,
                version=service.version,
                state=service.state,
                exposure=service.exposure,
            )
            for service in services
        ],
    )


def _host_exposure(services: list[object]) -> ExposureLevel:
    for service in services:
        if getattr(service, "exposure", None) == ExposureLevel.external.value:
            return ExposureLevel.external
    if services:
        return ExposureLevel.internal
    return ExposureLevel.unknown

