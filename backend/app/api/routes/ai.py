from fastapi import APIRouter, Depends

from app.ai.provider import DisabledAISecurityAnalyst, SecurityAnalysisRequest
from app.core.security import RoleName, require_roles
from app.schemas.analysis import AnalysisRequest, AnalysisResponse

router = APIRouter(prefix="/analyze", tags=["analysis"])


@router.post("", response_model=AnalysisResponse)
def analyze(
    request: AnalysisRequest,
    _user: object = Depends(require_roles(RoleName.admin, RoleName.analyst)),
) -> AnalysisResponse:
    analyst = DisabledAISecurityAnalyst()
    response = analyst.explain(
        SecurityAnalysisRequest(
            subject_type=request.subject_type,
            subject_id=request.subject_id,
            evidence=request.evidence,
        )
    )
    return AnalysisResponse(
        provider=response.provider,
        model=response.model,
        prompt_version=response.prompt_version,
        generated_text=response.generated_text,
        is_ai_generated=response.is_ai_generated,
        source_evidence=response.source_evidence,
    )

