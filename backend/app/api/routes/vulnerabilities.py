from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.core.security import RoleName, require_roles
from app.models import Vulnerability
from app.schemas.vulnerabilities import VulnerabilityListResponse, VulnerabilitySummary

router = APIRouter(prefix="/vulnerabilities", tags=["vulnerabilities"])


@router.get("", response_model=VulnerabilityListResponse)
def list_vulnerabilities(
    _user: object = Depends(
        require_roles(RoleName.admin, RoleName.analyst, RoleName.viewer, RoleName.auditor)
    ),
    db: Session = Depends(get_db_session),
) -> VulnerabilityListResponse:
    try:
        statement = (
            select(Vulnerability)
            .order_by(Vulnerability.epss_probability.desc().nullslast(), Vulnerability.cvss_score.desc().nullslast())
            .limit(250)
        )
        vulnerabilities = db.scalars(statement).all()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Vulnerability database unavailable") from exc

    return VulnerabilityListResponse(
        vulnerabilities=[
            VulnerabilitySummary(
                id=vulnerability.id,
                cve_id=vulnerability.cve_id,
                title=vulnerability.title,
                cvss_score=float(vulnerability.cvss_score) if vulnerability.cvss_score is not None else None,
                epss_probability=float(vulnerability.epss_probability) if vulnerability.epss_probability is not None else None,
                severity=vulnerability.severity,
            )
            for vulnerability in vulnerabilities
        ]
    )

