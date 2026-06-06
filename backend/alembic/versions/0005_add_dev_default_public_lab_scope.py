"""Add a public lab scan scope to the default development policy.

Revision ID: 0005_public_lab_scope
Revises: 0004_add_engagements_and_recon
Create Date: 2026-06-05
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005_public_lab_scope"
down_revision: str | None = "0004_add_engagements_and_recon"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_POLICY_ID = "c001e000-0000-0000-0000-000000000001"
PUBLIC_LAB_RANGE = "110.224.103.0/24"
PUBLIC_LAB_HOST = "110.224.103.114/32"


def upgrade() -> None:
    op.execute(
        f"""
        UPDATE scan_policies
        SET allowed_cidrs = CASE
            WHEN '{PUBLIC_LAB_RANGE}'::cidr = ANY(allowed_cidrs)
                AND '{PUBLIC_LAB_HOST}'::cidr = ANY(allowed_cidrs)
            THEN allowed_cidrs
            WHEN '{PUBLIC_LAB_RANGE}'::cidr = ANY(allowed_cidrs)
            THEN array_append(allowed_cidrs, '{PUBLIC_LAB_HOST}'::cidr)
            WHEN '{PUBLIC_LAB_HOST}'::cidr = ANY(allowed_cidrs)
            THEN array_append(allowed_cidrs, '{PUBLIC_LAB_RANGE}'::cidr)
            ELSE array_append(
                array_append(allowed_cidrs, '{PUBLIC_LAB_HOST}'::cidr),
                '{PUBLIC_LAB_RANGE}'::cidr
            )
        END
        WHERE id = '{DEFAULT_POLICY_ID}'::uuid
          AND name = 'dev-default'
        """
    )


def downgrade() -> None:
    op.execute(
        f"""
        UPDATE scan_policies
        SET allowed_cidrs = array_remove(
            array_remove(allowed_cidrs, '{PUBLIC_LAB_HOST}'::cidr),
            '{PUBLIC_LAB_RANGE}'::cidr
        )
        WHERE id = '{DEFAULT_POLICY_ID}'::uuid
          AND name = 'dev-default'
        """
    )
