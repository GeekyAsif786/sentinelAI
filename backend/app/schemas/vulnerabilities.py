from uuid import UUID

from pydantic import BaseModel, Field


class VulnerabilitySummary(BaseModel):
    id: UUID
    cve_id: str | None = None
    title: str
    cvss_score: float | None = Field(default=None, ge=0, le=10)
    epss_probability: float | None = Field(default=None, ge=0, le=1)
    severity: str


class VulnerabilityListResponse(BaseModel):
    vulnerabilities: list[VulnerabilitySummary]