from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db_session
from app.core.security import RoleName, require_roles
from app.graph.projection import InventoryGraphProjection
from app.models import Host
from app.schemas.graph import GraphProjectionJobResponse, GraphSliceResponse
from app.tasks import project_inventory_graph

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("", response_model=GraphSliceResponse)
def get_graph(
    max_depth: int = 2,
    max_nodes: int = 100,
    _user: object = Depends(
        require_roles(RoleName.admin, RoleName.analyst, RoleName.viewer, RoleName.auditor)
    ),
    db: Session = Depends(get_db_session),
) -> GraphSliceResponse:
    try:
        hosts = db.scalars(
            select(Host)
            .options(selectinload(Host.services))
            .order_by(Host.last_seen_at.desc())
            .limit(max_nodes)
        ).all()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Graph inventory unavailable") from exc

    projection = InventoryGraphProjection()
    return projection.build_slice(hosts, max_nodes=max_nodes, max_depth=max_depth)


@router.post("/project", response_model=GraphProjectionJobResponse)
def project_graph(
    _user: object = Depends(require_roles(RoleName.admin, RoleName.analyst)),
) -> GraphProjectionJobResponse:
    async_result = project_inventory_graph.delay()
    return GraphProjectionJobResponse(
        task_id=async_result.id,
        status="queued",
        message="Graph projection job has been queued for asynchronous execution.",
    )

