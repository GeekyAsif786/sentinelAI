from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class HealthStatus(StrEnum):
    ok = "ok"
    degraded = "degraded"
    failed = "failed"


class HealthResponse(BaseModel):
    service: str
    status: HealthStatus
    checked_at: datetime
    detail: str


class Page(BaseModel):
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class ResourceId(BaseModel):
    id: UUID


class DevTokenResponse(BaseModel):
    access_token: str
    token_type: str

