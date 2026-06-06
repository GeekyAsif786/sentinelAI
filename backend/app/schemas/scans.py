from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class ScanStatus(StrEnum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
    partial = "partial"


class ScanTargetType(StrEnum):
    ip = "ip"
    cidr = "cidr"
    hostname = "hostname"
    segment = "segment"


class ScanRequest(BaseModel):
    policy_id: UUID
    scanner_profile_id: UUID
    engagement_id: UUID | None = None
    provider: str = Field(pattern=r"^[a-z0-9_-]+$", max_length=40)
    scan_type: str = Field(default="discovery", max_length=80)
    targets: list[str] = Field(min_length=1, max_length=1024)


class ScanCreateResponse(BaseModel):
    scan_id: UUID
    status: ScanStatus
    message: str


class ScanDetail(BaseModel):
    scan_id: UUID
    status: ScanStatus
    provider: str
    targets: list[str]
    graph_projection_status: str
    error_message: str | None = None
