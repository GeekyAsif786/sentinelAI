"""Add graph projection job tracking and scan execution fields.

Revision ID: 0002_add_graph_jobs
Revises: 0001_foundation
Create Date: 2026-06-03
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_add_graph_jobs"
down_revision: str | None = "0001_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scan_runs",
        sa.Column("worker_node_id", sa.String(length=120), nullable=True),
    )

    op.create_table(
        "graph_projection_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scan_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scan_runs.id"), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="queued"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("projection_stats", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_graph_projection_jobs_scan_run_id", "graph_projection_jobs", ["scan_run_id"])
    op.create_index("ix_graph_projection_jobs_status", "graph_projection_jobs", ["status"])
    op.create_index("ix_graph_projection_jobs_created_at", "graph_projection_jobs", ["created_at"])


def downgrade() -> None:
    op.drop_table("graph_projection_jobs")
    op.drop_column("scan_runs", "worker_node_id")
