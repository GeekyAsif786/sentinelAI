"""Tests for scan execution tasks."""

from datetime import UTC, datetime
from uuid import uuid4
from unittest.mock import MagicMock, patch

import pytest

from app.discovery.provider import DiscoveredHost, DiscoveredService, DiscoveryResult
from app.discovery.nmap import DiscoveryProviderName
from app.models import GraphProjectionJob, Host, ScanPolicy, ScanRun, ScanTarget, ScannerProfile, Service
from app.schemas.scans import ScanStatus
from app.tasks import (
    _execute_nmap_scan,
    _handle_scan_error,
    _is_external_service,
    _persist_discovery_result,
    _trigger_graph_projection,
)


class FakeTaskRequest:
    def __init__(self, hostname: str = "worker-001"):
        self.hostname = hostname


class FakeSession:
    def __init__(self):
        self.hosts: dict = {}
        self.services: dict = {}
        self.scan_runs: dict = {}
        self.projection_jobs: dict = {}
        self.added: list = []
        self.committed: list = []

    def scalar(self, query):
        return None

    def add(self, instance):
        self.added.append(instance)
        if isinstance(instance, GraphProjectionJob):
            self.projection_jobs[str(instance.id)] = instance

    def flush(self):
        for instance in self.added:
            if isinstance(instance, Host) and instance.id is None:
                instance.id = uuid4()
            if isinstance(instance, Service) and instance.id is None:
                instance.id = uuid4()

    def commit(self):
        self.committed.append("committed")

    def close(self):
        pass


def _create_policy() -> ScanPolicy:
    return ScanPolicy(
        id=uuid4(),
        name="test-policy",
        description="Test policy",
        allowed_cidrs=["10.0.0.0/8"],
        blocked_cidrs=[],
        max_targets=10,
        max_scan_rate=100,
        provider_restrictions={},
        is_enabled=True,
    )


def _create_profile() -> ScannerProfile:
    return ScannerProfile(
        id=uuid4(),
        name="test-profile",
        provider="nmap",
        description="Test profile",
        configuration={"extra_args": ["-sV"]},
        is_enabled=True,
    )


def _create_scan_run(policy: ScanPolicy, profile: ScannerProfile) -> ScanRun:
    scan_run = ScanRun(
        id=uuid4(),
        requested_by_user_id=uuid4(),
        scan_policy_id=policy.id,
        scanner_profile_id=profile.id,
        provider="nmap",
        status=ScanStatus.queued.value,
        scan_type="discovery",
        configuration={},
    )
    scan_run.scanner_profile = profile
    scan_run.targets = [
        ScanTarget(
            id=uuid4(),
            scan_run_id=scan_run.id,
            target_value="10.0.1.10",
            target_type="ip",
            validation_status="validated",
            validation_message=None,
        )
    ]
    return scan_run


def test_persist_discovery_result_creates_new_host() -> None:
    policy = _create_policy()
    profile = _create_profile()
    scan_run = _create_scan_run(policy, profile)
    session = FakeSession()

    discovered_result = DiscoveryResult(
        provider=DiscoveryProviderName.nmap,
        hosts=(
            DiscoveredHost(
                primary_ip="10.0.1.10",
                hostname="web.local",
                services=(
                    DiscoveredService(port=80, protocol="tcp", state="open", service_name="http"),
                    DiscoveredService(port=443, protocol="tcp", state="open", service_name="https"),
                ),
            ),
        ),
    )

    _persist_discovery_result(session, scan_run, discovered_result)

    assert len(session.added) >= 2
    host_added = any(isinstance(item, Host) for item in session.added)
    service_added = any(isinstance(item, Service) for item in session.added)
    assert host_added
    assert service_added


def test_persist_discovery_result_upserts_existing_host() -> None:
    policy = _create_policy()
    profile = _create_profile()
    scan_run = _create_scan_run(policy, profile)
    session = FakeSession()

    existing_host = Host(
        id=uuid4(),
        primary_ip="10.0.1.10",
        hostname="oldname.local",
        mac_address=None,
        os_name=None,
        os_confidence=None,
        asset_criticality=3,
        source="nmap",
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
    )

    def mock_scalar(query):
        # Check if this is a query for hosts table
        query_str = str(query)
        if "hosts" in query_str and "primary_ip" in query_str:
            return existing_host
        return None

    session.scalar = mock_scalar

    discovered_result = DiscoveryResult(
        provider=DiscoveryProviderName.nmap,
        hosts=(
            DiscoveredHost(
                primary_ip="10.0.1.10",
                hostname="newname.local",
                services=(),
            ),
        ),
    )

    _persist_discovery_result(session, scan_run, discovered_result)

    assert existing_host.hostname == "newname.local"


def test_is_external_service_identifies_common_external_ports() -> None:
    service_ssh = MagicMock()
    service_ssh.port = 22
    assert _is_external_service(service_ssh) is True

    service_http = MagicMock()
    service_http.port = 80
    assert _is_external_service(service_http) is True

    service_https = MagicMock()
    service_https.port = 443
    assert _is_external_service(service_https) is True

    service_smtp = MagicMock()
    service_smtp.port = 25
    assert _is_external_service(service_smtp) is True

    service_arbitrary = MagicMock()
    service_arbitrary.port = 12345
    assert _is_external_service(service_arbitrary) is False


def test_is_external_service_identifies_high_port_services() -> None:
    service_high = MagicMock()
    service_high.port = 8000
    assert _is_external_service(service_high) is False

    service_higher = MagicMock()
    service_higher.port = 9999
    assert _is_external_service(service_higher) is False


def test_handle_scan_error_sets_status_and_error() -> None:
    policy = _create_policy()
    profile = _create_profile()
    scan_run = _create_scan_run(policy, profile)
    session = FakeSession()

    result = _handle_scan_error(session, scan_run, "TEST_ERROR", "Test error message")

    assert scan_run.status == ScanStatus.failed.value
    assert scan_run.error_code == "TEST_ERROR"
    assert scan_run.error_message == "Test error message"
    assert result["status"] == "failed"
    assert result["error_code"] == "TEST_ERROR"


def test_handle_scan_error_truncates_long_messages() -> None:
    policy = _create_policy()
    profile = _create_profile()
    scan_run = _create_scan_run(policy, profile)
    session = FakeSession()

    long_message = "x" * 1000

    _handle_scan_error(session, scan_run, "LONG_ERROR", long_message)

    assert len(scan_run.error_message) <= 500


def test_trigger_graph_projection_creates_job() -> None:
    policy = _create_policy()
    profile = _create_profile()
    scan_run = _create_scan_run(policy, profile)
    session = FakeSession()

    with patch("app.tasks.project_inventory_graph") as mock_task:
        mock_task.delay = MagicMock()
        _trigger_graph_projection(session, scan_run)

    assert len(session.added) >= 1
    projection_job = next((item for item in session.added if isinstance(item, GraphProjectionJob)), None)
    assert projection_job is not None
    assert projection_job.scan_run_id == scan_run.id
    mock_task.delay.assert_called_once()
