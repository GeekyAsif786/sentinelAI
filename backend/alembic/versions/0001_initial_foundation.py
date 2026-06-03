"""Initial foundation schema.

Revision ID: 0001_foundation
Revises:
Create Date: 2026-06-03
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_is_active", "users", ["is_active"])

    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_roles_name", "roles", ["name"], unique=True)

    op.create_table(
        "user_roles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "scan_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("allowed_cidrs", postgresql.ARRAY(postgresql.CIDR()), nullable=False),
        sa.Column("blocked_cidrs", postgresql.ARRAY(postgresql.CIDR()), nullable=False),
        sa.Column("max_targets", sa.Integer(), nullable=False),
        sa.Column("max_scan_rate", sa.Integer(), nullable=False),
        sa.Column("provider_restrictions", postgresql.JSONB(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_scan_policies_name", "scan_policies", ["name"], unique=True)
    op.create_index("ix_scan_policies_is_enabled", "scan_policies", ["is_enabled"])

    op.create_table(
        "scanner_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("configuration", postgresql.JSONB(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("provider", "name", name="uq_scanner_profiles_provider_name"),
    )
    op.create_index("ix_scanner_profiles_name", "scanner_profiles", ["name"])
    op.create_index("ix_scanner_profiles_provider", "scanner_profiles", ["provider"])
    op.create_index("ix_scanner_profiles_is_enabled", "scanner_profiles", ["is_enabled"])

    op.create_table(
        "scan_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("scan_policy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scan_policies.id"), nullable=False),
        sa.Column("scanner_profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scanner_profiles.id"), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("scan_type", sa.String(length=80), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=120), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("provider_version", sa.String(length=80), nullable=True),
        sa.Column("configuration", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_scan_runs_requested_by_user_id", "scan_runs", ["requested_by_user_id"])
    op.create_index("ix_scan_runs_scan_policy_id", "scan_runs", ["scan_policy_id"])
    op.create_index("ix_scan_runs_scanner_profile_id", "scan_runs", ["scanner_profile_id"])
    op.create_index("ix_scan_runs_provider", "scan_runs", ["provider"])
    op.create_index("ix_scan_runs_status", "scan_runs", ["status"])

    op.create_table(
        "scan_targets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scan_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scan_runs.id"), nullable=False),
        sa.Column("target_value", sa.Text(), nullable=False),
        sa.Column("target_type", sa.String(length=40), nullable=False),
        sa.Column("validation_status", sa.String(length=40), nullable=False),
        sa.Column("validation_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_scan_targets_scan_run_id", "scan_targets", ["scan_run_id"])
    op.create_index("ix_scan_targets_target_type", "scan_targets", ["target_type"])

    op.create_table(
        "hosts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("primary_ip", postgresql.INET(), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column("mac_address", sa.String(length=64), nullable=True),
        sa.Column("os_name", sa.String(length=255), nullable=True),
        sa.Column("os_version", sa.String(length=120), nullable=True),
        sa.Column("os_confidence", sa.Numeric(), nullable=True),
        sa.Column("asset_criticality", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_hosts_primary_ip", "hosts", ["primary_ip"], unique=True)
    op.create_index("ix_hosts_hostname", "hosts", ["hostname"])
    op.create_index("ix_hosts_mac_address", "hosts", ["mac_address"])
    op.create_index("ix_hosts_asset_criticality", "hosts", ["asset_criticality"])
    op.create_index("ix_hosts_last_seen_at", "hosts", ["last_seen_at"])

    op.create_table(
        "services",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("host_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hosts.id"), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("protocol", sa.String(length=20), nullable=False),
        sa.Column("service_name", sa.String(length=120), nullable=True),
        sa.Column("product", sa.String(length=255), nullable=True),
        sa.Column("version", sa.String(length=120), nullable=True),
        sa.Column("banner", sa.Text(), nullable=True),
        sa.Column("state", sa.String(length=40), nullable=False),
        sa.Column("exposure", sa.String(length=40), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("host_id", "port", "protocol", name="uq_services_host_port_protocol"),
    )
    op.create_index("ix_services_host_id", "services", ["host_id"])
    op.create_index("ix_services_service_name", "services", ["service_name"])
    op.create_index("ix_services_product", "services", ["product"])
    op.create_index("ix_services_state", "services", ["state"])
    op.create_index("ix_services_exposure", "services", ["exposure"])
    op.create_index("ix_services_last_seen_at", "services", ["last_seen_at"])

    op.create_table(
        "asset_tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_asset_tags_name", "asset_tags", ["name"], unique=True)

    op.create_table(
        "vulnerabilities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cve_id", sa.String(length=40), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("cvss_score", sa.Numeric(), nullable=True),
        sa.Column("cvss_vector", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(length=40), nullable=False),
        sa.Column("epss_probability", sa.Numeric(), nullable=True),
        sa.Column("epss_percentile", sa.Numeric(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_vulnerabilities_cve_id", "vulnerabilities", ["cve_id"], unique=True)
    op.create_index("ix_vulnerabilities_severity", "vulnerabilities", ["severity"])
    op.create_index("ix_vulnerabilities_cvss_score", "vulnerabilities", ["cvss_score"])
    op.create_index("ix_vulnerabilities_epss_probability", "vulnerabilities", ["epss_probability"])
    op.create_index("ix_vulnerabilities_published_at", "vulnerabilities", ["published_at"])

    op.create_table(
        "findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scan_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scan_runs.id"), nullable=False),
        sa.Column("host_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hosts.id"), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("services.id"), nullable=True),
        sa.Column("vulnerability_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vulnerabilities.id"), nullable=True),
        sa.Column("finding_type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_findings_scan_run_id", "findings", ["scan_run_id"])
    op.create_index("ix_findings_host_id", "findings", ["host_id"])
    op.create_index("ix_findings_service_id", "findings", ["service_id"])
    op.create_index("ix_findings_vulnerability_id", "findings", ["vulnerability_id"])
    op.create_index("ix_findings_finding_type", "findings", ["finding_type"])
    op.create_index("ix_findings_status", "findings", ["status"])
    op.create_index("ix_findings_last_seen_at", "findings", ["last_seen_at"])

    op.create_table(
        "risk_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("formula_summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_risk_models_version", "risk_models", ["version"], unique=True)

    op.create_table(
        "risk_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("finding_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("findings.id"), nullable=True),
        sa.Column("attack_path_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("risk_model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("risk_models.id"), nullable=False),
        sa.Column("score", sa.Numeric(), nullable=False),
        sa.Column("severity", sa.String(length=40), nullable=False),
        sa.Column("scoring_version", sa.String(length=80), nullable=False),
        sa.Column("cvss_component", sa.Numeric(), nullable=True),
        sa.Column("epss_component", sa.Numeric(), nullable=True),
        sa.Column("exposure_component", sa.Numeric(), nullable=True),
        sa.Column("asset_criticality_component", sa.Numeric(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "(finding_id IS NOT NULL AND attack_path_id IS NULL) OR "
            "(finding_id IS NULL AND attack_path_id IS NOT NULL)",
            name="ck_risk_scores_one_scored_entity",
        ),
    )
    op.create_index("ix_risk_scores_finding_id", "risk_scores", ["finding_id"])
    op.create_index("ix_risk_scores_attack_path_id", "risk_scores", ["attack_path_id"])
    op.create_index("ix_risk_scores_risk_model_id", "risk_scores", ["risk_model_id"])
    op.create_index("ix_risk_scores_score", "risk_scores", ["score"])


def downgrade() -> None:
    op.drop_table("risk_scores")
    op.drop_table("risk_models")
    op.drop_table("findings")
    op.drop_table("vulnerabilities")
    op.drop_table("asset_tags")
    op.drop_table("services")
    op.drop_table("hosts")
    op.drop_table("scan_targets")
    op.drop_table("scan_runs")
    op.drop_table("scanner_profiles")
    op.drop_table("scan_policies")
    op.drop_table("user_roles")
    op.drop_table("roles")
    op.drop_table("users")
