from abc import ABC, abstractmethod
from dataclasses import dataclass


PROMPT_VERSION = "defensive-explanation-v1"
DISABLED_PROVIDER_NAME = "disabled"
DISABLED_MODEL_NAME = "deterministic-template"


@dataclass(frozen=True)
class SecurityAnalysisRequest:
    subject_type: str
    subject_id: str
    evidence: dict[str, str | int | float | bool | None]


@dataclass(frozen=True)
class SecurityAnalysisResponse:
    provider: str
    model: str
    prompt_version: str
    generated_text: str
    is_ai_generated: bool
    source_evidence: dict[str, str | int | float | bool | None]


class AISecurityAnalyst(ABC):
    @abstractmethod
    def explain(self, request: SecurityAnalysisRequest) -> SecurityAnalysisResponse:
        raise NotImplementedError


class DisabledAISecurityAnalyst(AISecurityAnalyst):
    def explain(self, request: SecurityAnalysisRequest) -> SecurityAnalysisResponse:
        evidence_keys = ", ".join(sorted(request.evidence.keys())) or "no evidence fields"
        generated_text = (
            f"AI analysis is disabled. Deterministic evidence for {request.subject_type} "
            f"{request.subject_id} includes: {evidence_keys}. Review risk score, asset exposure, "
            "and MITRE mappings before making security decisions."
        )
        return SecurityAnalysisResponse(
            provider=DISABLED_PROVIDER_NAME,
            model=DISABLED_MODEL_NAME,
            prompt_version=PROMPT_VERSION,
            generated_text=generated_text,
            is_ai_generated=False,
            source_evidence=request.evidence,
        )

