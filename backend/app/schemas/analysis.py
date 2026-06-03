from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    subject_type: str = Field(pattern=r"^(finding|attack_path|risk_score|asset)$")
    subject_id: str = Field(min_length=1, max_length=120)
    evidence: dict[str, str | int | float | bool | None]


class AnalysisResponse(BaseModel):
    provider: str
    model: str
    prompt_version: str
    generated_text: str
    is_ai_generated: bool
    source_evidence: dict[str, str | int | float | bool | None]

