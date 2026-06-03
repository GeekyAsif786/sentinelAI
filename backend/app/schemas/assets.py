from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ServiceSummary(BaseModel):
    id: UUID
    port: int = Field(ge=0, le=65535)
    protocol: str
    service_name: str | None = None
    product: str | None = None
    version: str | None = None
    state: str
    exposure: str


class HostSummary(BaseModel):
    id: UUID
    primary_ip: str
    hostname: str | None = None
    os_name: str | None = None
    asset_criticality: int = Field(ge=1, le=5)
    risk_score: float = Field(ge=0, le=100)
    last_seen_at: datetime
    services: list[ServiceSummary] = Field(default_factory=list)


class AssetListResponse(BaseModel):
    assets: list[HostSummary]
    limit: int
    offset: int
    total: int
