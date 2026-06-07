from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.inventory import TimestampMixin

if TYPE_CHECKING:
    from app.models.inventory import ScanRun


class Engagement(Base, TimestampMixin):
    __tablename__ = "engagements"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), index=True)
    authorization_ref: Mapped[str] = mapped_column(String(160), index=True)
    authorized_targets: Mapped[list[str]] = mapped_column(JSONB)
    authorized_by: Mapped[str] = mapped_column(String(200), index=True)
    authorized_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(40), index=True, default="active")

    scan_runs: Mapped[list["ScanRun"]] = relationship(back_populates="engagement")
