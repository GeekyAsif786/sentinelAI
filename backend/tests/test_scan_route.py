from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.routes.scans import create_scan, get_scan
from app.core.security import AuthenticatedUser, RoleName
from app.models import ScanPolicy, ScanRun, ScanTarget, ScannerProfile
from app.schemas.scans import ScanRequest, ScanStatus


class FakeSession:
    def __init__(self, policy: ScanPolicy, profile: ScannerProfile, scan_run: ScanRun | None = None) -> None:
        self.policy = policy
        self.profile = profile
        self.scan_run = scan_run
        self.added: list[object] = []

    def get(self, model: type[object], primary_key: object) -> object | None:
        if model is ScanPolicy and primary_key == self.policy.id:
            return self.policy
        if model is ScannerProfile and primary_key == self.profile.id:
            return self.profile
        if model is ScanRun and self.scan_run is not None and primary_key == self.scan_run.id:
            return self.scan_run
        return None

    def add(self, instance: object) -> None:
        self.added.append(instance)

    def flush(self) -> None:
        for instance in self.added:
            if isinstance(instance, ScanRun) and instance.id is None:
                instance.id = uuid4()

    def commit(self) -> None:
        return None


def _user() -> AuthenticatedUser:
    return AuthenticatedUser(user_id=str(uuid4()), email="analyst@example.com", roles={RoleName.analyst})


def _policy() -> ScanPolicy:
    return ScanPolicy(
        id=uuid4(),
        name="internal",
        description="Internal scanning",
        allowed_cidrs=["10.0.0.0/8"],
        blocked_cidrs=[],
        max_targets=5,
        max_scan_rate=100,
        provider_restrictions={},
        is_enabled=True,
    )


def _profile() -> ScannerProfile:
    return ScannerProfile(
        id=uuid4(),
        name="safe-nmap",
        provider="nmap",
        description="Safe internal discovery",
        configuration={},
        is_enabled=True,
    )


def test_create_scan_persists_scan_and_targets() -> None:
    policy = _policy()
    profile = _profile()
    session = FakeSession(policy=policy, profile=profile)
    request = ScanRequest(
        policy_id=policy.id,
        scanner_profile_id=profile.id,
        provider="nmap",
        scan_type="discovery",
        targets=["10.0.1.10", "scanner.local"],
    )

    response = create_scan(request, _user(), session)

    assert response.status == ScanStatus.queued
    assert response.scan_id is not None
    assert len(session.added) == 3
    assert isinstance(session.added[0], ScanRun)
    assert all(isinstance(item, (ScanRun, ScanTarget)) for item in session.added)


def test_create_scan_rejects_out_of_scope_targets() -> None:
    policy = _policy()
    policy.blocked_cidrs = ["10.0.1.0/24"]
    profile = _profile()
    session = FakeSession(policy=policy, profile=profile)
    request = ScanRequest(
        policy_id=policy.id,
        scanner_profile_id=profile.id,
        provider="nmap",
        scan_type="discovery",
        targets=["10.0.1.10"],
    )

    with pytest.raises(HTTPException) as exc_info:
        create_scan(request, _user(), session)

    assert exc_info.value.status_code == 400


def test_get_scan_returns_persisted_targets() -> None:
    policy = _policy()
    profile = _profile()
    scan_run = ScanRun(
        id=uuid4(),
        requested_by_user_id=uuid4(),
        scan_policy_id=policy.id,
        scanner_profile_id=profile.id,
        provider="nmap",
        status=ScanStatus.completed.value,
        scan_type="discovery",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        configuration={},
    )
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
    session = FakeSession(policy=policy, profile=profile, scan_run=scan_run)

    response = get_scan(scan_run.id, _user(), session)

    assert response.status == ScanStatus.completed
    assert response.targets == ["10.0.1.10"]
    assert response.graph_projection_status == "projected"