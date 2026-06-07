from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class EngagementStatus(StrEnum):
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class EngagementCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    authorization_ref: str = Field(min_length=1, max_length=160)
    authorized_targets: list[str] = Field(min_length=1, max_length=1024)
    authorized_by: str = Field(min_length=1, max_length=200)
    authorized_at: datetime
    notes: str | None = Field(default=None, max_length=4000)


class EngagementUpdateRequest(BaseModel):
    status: EngagementStatus | None = None
    notes: str | None = Field(default=None, max_length=4000)


class EngagementScanRunSummary(BaseModel):
    id: UUID
    provider: str
    status: str
    scan_type: str
    targets: list[str]
    started_at: datetime | None = None
    completed_at: datetime | None = None


class EngagementSummary(BaseModel):
    id: UUID
    name: str
    authorization_ref: str
    authorized_targets: list[str]
    authorized_by: str
    authorized_at: datetime
    notes: str | None = None
    created_at: datetime
    status: EngagementStatus


class EngagementDetail(EngagementSummary):
    scan_runs: list[EngagementScanRunSummary] = Field(default_factory=list)
