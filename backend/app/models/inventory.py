from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, CIDR, INET, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(Text)
    display_name: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    roles: Mapped[list["UserRole"]] = relationship(back_populates="user")


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list["UserRole"]] = relationship(back_populates="role")


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role_id: Mapped[UUID] = mapped_column(ForeignKey("roles.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="roles")
    role: Mapped[Role] = relationship(back_populates="users")


class ScanPolicy(Base, TimestampMixin):
    __tablename__ = "scan_policies"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text)
    allowed_cidrs: Mapped[list[str]] = mapped_column(ARRAY(CIDR))
    blocked_cidrs: Mapped[list[str]] = mapped_column(ARRAY(CIDR))
    max_targets: Mapped[int] = mapped_column(Integer)
    max_scan_rate: Mapped[int] = mapped_column(Integer)
    provider_restrictions: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class ScannerProfile(Base, TimestampMixin):
    __tablename__ = "scanner_profiles"
    __table_args__ = (UniqueConstraint("provider", "name", name="uq_scanner_profiles_provider_name"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), index=True)
    provider: Mapped[str] = mapped_column(String(80), index=True)
    description: Mapped[str] = mapped_column(Text)
    configuration: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class ScanRun(Base, TimestampMixin):
    __tablename__ = "scan_runs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    requested_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    scan_policy_id: Mapped[UUID] = mapped_column(ForeignKey("scan_policies.id"), index=True)
    scanner_profile_id: Mapped[UUID] = mapped_column(ForeignKey("scanner_profiles.id"), index=True)
    provider: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    scan_type: Mapped[str] = mapped_column(String(80))
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[Optional[str]] = mapped_column(String(120))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    provider_version: Mapped[Optional[str]] = mapped_column(String(80))
    worker_node_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    configuration: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)

    targets: Mapped[list["ScanTarget"]] = relationship(back_populates="scan_run")
    projection_jobs: Mapped[list["GraphProjectionJob"]] = relationship(back_populates="scan_run")
    scanner_profile: Mapped["ScannerProfile"] = relationship()


class ScanTarget(Base):
    __tablename__ = "scan_targets"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    scan_run_id: Mapped[UUID] = mapped_column(ForeignKey("scan_runs.id"), index=True)
    target_value: Mapped[str] = mapped_column(Text)
    target_type: Mapped[str] = mapped_column(String(40), index=True)
    validation_status: Mapped[str] = mapped_column(String(40))
    validation_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    scan_run: Mapped[ScanRun] = relationship(back_populates="targets")


class Host(Base, TimestampMixin):
    __tablename__ = "hosts"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    primary_ip: Mapped[str] = mapped_column(INET, unique=True, index=True)
    hostname: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    mac_address: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    os_name: Mapped[Optional[str]] = mapped_column(String(255))
    os_version: Mapped[Optional[str]] = mapped_column(String(120))
    os_confidence: Mapped[Optional[float]] = mapped_column(Numeric)
    asset_criticality: Mapped[int] = mapped_column(Integer, default=3, index=True)
    source: Mapped[str] = mapped_column(String(80))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    services: Mapped[list["Service"]] = relationship(back_populates="host")


class Service(Base, TimestampMixin):
    __tablename__ = "services"
    __table_args__ = (UniqueConstraint("host_id", "port", "protocol", name="uq_services_host_port_protocol"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    host_id: Mapped[UUID] = mapped_column(ForeignKey("hosts.id"), index=True)
    port: Mapped[int] = mapped_column(Integer)
    protocol: Mapped[str] = mapped_column(String(20))
    service_name: Mapped[Optional[str]] = mapped_column(String(120), index=True)
    product: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    version: Mapped[Optional[str]] = mapped_column(String(120))
    banner: Mapped[Optional[str]] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(40), index=True)
    exposure: Mapped[str] = mapped_column(String(40), index=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    host: Mapped[Host] = relationship(back_populates="services")


class AssetTag(Base):
    __tablename__ = "asset_tags"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Vulnerability(Base, TimestampMixin):
    __tablename__ = "vulnerabilities"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    cve_id: Mapped[Optional[str]] = mapped_column(String(40), unique=True, index=True)
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    cvss_score: Mapped[Optional[float]] = mapped_column(Numeric, index=True)
    cvss_vector: Mapped[Optional[str]] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(40), index=True)
    epss_probability: Mapped[Optional[float]] = mapped_column(Numeric, index=True)
    epss_percentile: Mapped[Optional[float]] = mapped_column(Numeric)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    modified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class Finding(Base, TimestampMixin):
    __tablename__ = "findings"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    scan_run_id: Mapped[UUID] = mapped_column(ForeignKey("scan_runs.id"), index=True)
    host_id: Mapped[UUID] = mapped_column(ForeignKey("hosts.id"), index=True)
    service_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("services.id"), index=True)
    vulnerability_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("vulnerabilities.id"), index=True)
    finding_type: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict[str, object]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(40), index=True)
    cve_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    cvss_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    epss_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class RiskModel(Base):
    __tablename__ = "risk_models"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    version: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    formula_summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RiskScore(Base):
    __tablename__ = "risk_scores"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    finding_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("findings.id"), index=True)
    attack_path_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), index=True)
    risk_model_id: Mapped[UUID] = mapped_column(ForeignKey("risk_models.id"), index=True)
    score: Mapped[float] = mapped_column(Numeric, index=True)
    severity: Mapped[str] = mapped_column(String(40))
    scoring_version: Mapped[str] = mapped_column(String(80))
    cvss_component: Mapped[Optional[float]] = mapped_column(Numeric)
    epss_component: Mapped[Optional[float]] = mapped_column(Numeric)
    exposure_component: Mapped[Optional[float]] = mapped_column(Numeric)
    asset_criticality_component: Mapped[Optional[float]] = mapped_column(Numeric)
    explanation: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GraphProjectionJob(Base, TimestampMixin):
    __tablename__ = "graph_projection_jobs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    scan_run_id: Mapped[UUID] = mapped_column(ForeignKey("scan_runs.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), index=True, default="queued")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    projection_stats: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)

    scan_run: Mapped[ScanRun] = relationship(back_populates="projection_jobs")

