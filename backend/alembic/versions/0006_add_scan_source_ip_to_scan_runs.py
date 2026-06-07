"""Add scan source IP to scan runs.

Revision ID: 0006_scan_source_ip
Revises: 0005_public_lab_scope
Create Date: 2026-06-07
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0006_scan_source_ip"
down_revision: str | None = "0005_public_lab_scope"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scan_runs",
        sa.Column(
            "scan_source_ip",
            sa.String(),
            nullable=True,
            comment="IP address of the machine that submitted the scan request",
        ),
    )
    op.alter_column(
        "scan_runs",
        "scan_policy_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.alter_column(
        "scan_runs",
        "scanner_profile_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "scan_runs",
        "scanner_profile_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.alter_column(
        "scan_runs",
        "scan_policy_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_column("scan_runs", "scan_source_ip")
