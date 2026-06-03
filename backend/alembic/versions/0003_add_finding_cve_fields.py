"""Add cve_id, cvss_score, and epss_probability to findings.

Revision ID: 0003_add_finding_cve_fields
Revises: 0002_add_graph_jobs
Create Date: 2026-06-04
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0003_add_finding_cve_fields"
down_revision: str | None = "0002_add_graph_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "findings",
        sa.Column("cve_id", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "findings",
        sa.Column("cvss_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "findings",
        sa.Column("epss_probability", sa.Float(), nullable=True),
    )
    op.create_index("ix_findings_cve_id", "findings", ["cve_id"])


def downgrade() -> None:
    op.drop_index("ix_findings_cve_id", table_name="findings")
    op.drop_column("findings", "epss_probability")
    op.drop_column("findings", "cvss_score")
    op.drop_column("findings", "cve_id")
