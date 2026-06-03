from fastapi import APIRouter, Depends

from app.core.security import RoleName, require_roles
from app.graph.attack_path import DefensiveAttackPathEngine, GraphRelationship
from app.schemas.graph import AttackPathResponse

router = APIRouter(prefix="/attack-paths", tags=["attack-paths"])


@router.get("", response_model=AttackPathResponse)
def get_attack_paths(
    source: str = "host:internet",
    target: str = "host:192.168.1.10",
    _user: object = Depends(require_roles(RoleName.admin, RoleName.analyst, RoleName.viewer)),
) -> AttackPathResponse:
    engine = DefensiveAttackPathEngine([])
    result = engine.lowest_cost_path(source, target)
    if result is None:
        return AttackPathResponse(
            path=[],
            risk_score=0,
            critical_nodes=[],
            confidence=0,
            message="No projected graph data is available for the requested nodes.",
        )

    risk_score = max(0.0, min(100.0, 100.0 - result.total_weight * 10.0))
    return AttackPathResponse(
        path=list(result.path),
        risk_score=risk_score,
        critical_nodes=list(result.critical_nodes),
        confidence=result.confidence,
        message="Defensive attack-path model only; no execution steps are generated.",
    )

