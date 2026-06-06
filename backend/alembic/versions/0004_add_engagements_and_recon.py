"""Add engagements and scan recon data.

Revision ID: 0004_add_engagements_and_recon
Revises: 0003_add_finding_cve_fields
Create Date: 2026-06-04
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004_add_engagements_and_recon"
down_revision: str | None = "0003_add_finding_cve_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "engagements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("authorization_ref", sa.String(length=160), nullable=False),
        sa.Column("authorized_targets", postgresql.JSONB(), nullable=False),
        sa.Column("authorized_by", sa.String(length=200), nullable=False),
        sa.Column("authorized_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_engagements_name", "engagements", ["name"])
    op.create_index("ix_engagements_authorization_ref", "engagements", ["authorization_ref"])
    op.create_index("ix_engagements_authorized_by", "engagements", ["authorized_by"])
    op.create_index("ix_engagements_status", "engagements", ["status"])

    op.add_column(
        "scan_runs",
        sa.Column("engagement_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_scan_runs_engagement_id", "scan_runs", ["engagement_id"])
    op.create_foreign_key("fk_scan_runs_engagement_id", "scan_runs", "engagements", ["engagement_id"], ["id"])

    op.add_column(
        "scan_runs",
        sa.Column("recon_data", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scan_runs", "recon_data")
    op.drop_constraint("fk_scan_runs_engagement_id", "scan_runs", type_="foreignkey")
    op.drop_index("ix_scan_runs_engagement_id", table_name="scan_runs")
    op.drop_column("scan_runs", "engagement_id")

    op.drop_index("ix_engagements_status", table_name="engagements")
    op.drop_index("ix_engagements_authorized_by", table_name="engagements")
    op.drop_index("ix_engagements_authorization_ref", table_name="engagements")
    op.drop_index("ix_engagements_name", table_name="engagements")
    op.drop_table("engagements")
