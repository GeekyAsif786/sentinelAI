from app.core.target_validator import is_private_ip, is_valid_scan_target, target_in_scope


def test_is_private_ip_rejects_rfc1918_and_loopback_ranges() -> None:
    assert is_private_ip("10.0.0.1") is True
    assert is_private_ip("127.0.0.1") is True
    assert is_private_ip("169.254.10.10") is True
    assert is_private_ip("8.8.8.8") is False


def test_is_valid_scan_target_accepts_any_parseable_ip() -> None:
    assert is_valid_scan_target("8.8.8.8") is True
    assert is_valid_scan_target("10.0.0.1") is True
    assert is_valid_scan_target("255.255.255.255") is True
    assert is_valid_scan_target("192.168.1.102") is True
    assert is_valid_scan_target("not-an-ip") is False


def test_target_in_scope_matches_ips_and_cidrs() -> None:
    authorized_targets = ["8.8.8.8", "1.1.1.0/24"]
    assert target_in_scope("8.8.8.8", authorized_targets) is True
    assert target_in_scope("1.1.1.10", authorized_targets) is True
    assert target_in_scope("9.9.9.9", authorized_targets) is False
