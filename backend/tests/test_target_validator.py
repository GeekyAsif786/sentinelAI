"""
target_validator.py unit tests.
These tests are the specification. Do not modify them.
If a test fails, fix the validator.
"""
import pytest
from app.core.target_validator import (
    ScanContext,
    classify_ip,
    is_always_blocked,
    is_cgnat,
    is_rfc1918,
    is_valid_scan_target,
    target_in_scope,
)


# ── classify_ip ───────────────────────────────────────────────────────────────

class TestClassifyIp:
    def test_cgnat(self) -> None:
        assert classify_ip("100.97.128.160") == "cgnat"

    def test_cgnat_start(self) -> None:
        assert classify_ip("100.64.0.1") == "cgnat"

    def test_cgnat_end(self) -> None:
        assert classify_ip("100.127.255.255") == "cgnat"

    def test_loopback(self) -> None:
        assert classify_ip("127.0.0.1") == "loopback"

    def test_link_local(self) -> None:
        assert classify_ip("169.254.1.1") == "link-local"

    def test_multicast(self) -> None:
        assert classify_ip("224.0.0.1") == "multicast"

    def test_reserved(self) -> None:
        assert classify_ip("240.0.0.1") == "reserved"

    def test_broadcast(self) -> None:
        assert classify_ip("255.255.255.255") == "reserved"

    def test_testnet_1(self) -> None:
        assert classify_ip("192.0.2.1") == "documentation"

    def test_testnet_2(self) -> None:
        assert classify_ip("198.51.100.1") == "documentation"

    def test_testnet_3(self) -> None:
        assert classify_ip("203.0.113.1") == "documentation"

    def test_benchmarking(self) -> None:
        assert classify_ip("198.18.0.1") == "benchmarking"

    def test_aws_default_vpc(self) -> None:
        assert classify_ip("172.31.5.10") == "cloud-vpc"

    def test_gcp_default_subnet(self) -> None:
        assert classify_ip("10.128.0.5") == "cloud-vpc"

    def test_rfc1918_192(self) -> None:
        assert classify_ip("192.168.1.102") == "rfc1918-private"

    def test_rfc1918_10(self) -> None:
        assert classify_ip("10.0.0.1") == "rfc1918-private"

    def test_rfc1918_172(self) -> None:
        assert classify_ip("172.16.5.1") == "rfc1918-private"

    def test_public_google(self) -> None:
        assert classify_ip("8.8.8.8") == "public"

    def test_public_jio(self) -> None:
        assert classify_ip("223.185.34.216") == "public"

    def test_public_bsnl(self) -> None:
        assert classify_ip("110.224.103.114") == "public"

    def test_public_airtel(self) -> None:
        assert classify_ip("106.202.80.160") == "public"

    def test_invalid_string(self) -> None:
        assert classify_ip("not-an-ip") == "invalid"


# ── is_always_blocked ─────────────────────────────────────────────────────────

class TestAlwaysBlocked:
    def test_cgnat_always_blocked(self) -> None:
        assert is_always_blocked("100.97.128.160") is True

    def test_loopback_always_blocked(self) -> None:
        assert is_always_blocked("127.0.0.1") is True

    def test_multicast_always_blocked(self) -> None:
        assert is_always_blocked("224.0.0.1") is True

    def test_testnet_always_blocked(self) -> None:
        assert is_always_blocked("192.0.2.1") is True
        assert is_always_blocked("198.51.100.1") is True
        assert is_always_blocked("203.0.113.1") is True

    def test_benchmarking_always_blocked(self) -> None:
        assert is_always_blocked("198.18.5.1") is True

    def test_rfc1918_not_always_blocked(self) -> None:
        # RFC1918 is context-dependent, NOT always blocked
        assert is_always_blocked("192.168.1.1") is False

    def test_public_not_always_blocked(self) -> None:
        assert is_always_blocked("8.8.8.8") is False

    def test_invalid_string_is_blocked(self) -> None:
        assert is_always_blocked("not-an-ip") is True


# ── is_cgnat ──────────────────────────────────────────────────────────────────

class TestIsCgnat:
    def test_100_97_is_cgnat(self) -> None:
        assert is_cgnat("100.97.128.160") is True

    def test_range_start(self) -> None:
        assert is_cgnat("100.64.0.1") is True

    def test_range_end(self) -> None:
        assert is_cgnat("100.127.255.255") is True

    def test_just_outside_range(self) -> None:
        assert is_cgnat("100.128.0.1") is False

    def test_public_not_cgnat(self) -> None:
        assert is_cgnat("8.8.8.8") is False

    def test_rfc1918_not_cgnat(self) -> None:
        assert is_cgnat("192.168.1.1") is False


# ── institutional context (default) ──────────────────────────────────────────

class TestInstitutionalContext:
    def test_phone_on_home_wifi(self) -> None:
        assert is_valid_scan_target("192.168.1.102") is True

    def test_rfc1918_10(self) -> None:
        assert is_valid_scan_target("10.0.0.50") is True

    def test_rfc1918_172(self) -> None:
        assert is_valid_scan_target("172.16.5.1") is True

    def test_aws_default_vpc(self) -> None:
        assert is_valid_scan_target("172.31.0.5") is True

    def test_gcp_subnet(self) -> None:
        assert is_valid_scan_target("10.128.0.10") is True

    def test_azure_vnet(self) -> None:
        assert is_valid_scan_target("10.0.1.5") is True

    def test_public_ip_allowed(self) -> None:
        assert is_valid_scan_target("8.8.8.8") is True

    def test_cgnat_blocked(self) -> None:
        assert is_valid_scan_target("100.97.128.160") is False

    def test_loopback_blocked(self) -> None:
        assert is_valid_scan_target("127.0.0.1") is False

    def test_link_local_blocked(self) -> None:
        assert is_valid_scan_target("169.254.1.1") is False

    def test_multicast_blocked(self) -> None:
        assert is_valid_scan_target("224.0.0.1") is False

    def test_testnet_blocked(self) -> None:
        assert is_valid_scan_target("192.0.2.1") is False
        assert is_valid_scan_target("198.51.100.1") is False
        assert is_valid_scan_target("203.0.113.1") is False

    def test_benchmarking_blocked(self) -> None:
        assert is_valid_scan_target("198.18.0.1") is False

    def test_default_context_is_institutional(self) -> None:
        # calling with no context should allow RFC1918
        assert is_valid_scan_target("192.168.1.1") is True

    def test_invalid_string(self) -> None:
        assert is_valid_scan_target("not-an-ip") is False


# ── external context ──────────────────────────────────────────────────────────

class TestExternalContext:
    def test_rfc1918_blocked(self) -> None:
        assert is_valid_scan_target(
            "192.168.1.102", ScanContext.external
        ) is False

    def test_10_range_blocked(self) -> None:
        assert is_valid_scan_target(
            "10.0.0.1", ScanContext.external
        ) is False

    def test_aws_vpc_blocked(self) -> None:
        assert is_valid_scan_target(
            "172.31.0.5", ScanContext.external
        ) is False

    def test_cgnat_blocked(self) -> None:
        assert is_valid_scan_target(
            "100.97.128.160", ScanContext.external
        ) is False

    def test_public_allowed(self) -> None:
        assert is_valid_scan_target(
            "8.8.8.8", ScanContext.external
        ) is True

    def test_jio_ip_allowed(self) -> None:
        assert is_valid_scan_target(
            "223.185.34.216", ScanContext.external
        ) is True

    def test_bsnl_ip_allowed(self) -> None:
        assert is_valid_scan_target(
            "110.224.103.114", ScanContext.external
        ) is True

    def test_airtel_ip_allowed(self) -> None:
        assert is_valid_scan_target(
            "106.202.80.160", ScanContext.external
        ) is True


# ── xml_import context ────────────────────────────────────────────────────────

class TestXmlImportContext:
    def test_rfc1918_allowed(self) -> None:
        assert is_valid_scan_target(
            "192.168.1.1", ScanContext.xml_import
        ) is True

    def test_cgnat_allowed(self) -> None:
        # xml_import skips all IP validation — artifact is pre-captured
        assert is_valid_scan_target(
            "100.97.128.160", ScanContext.xml_import
        ) is True

    def test_loopback_allowed(self) -> None:
        assert is_valid_scan_target(
            "127.0.0.1", ScanContext.xml_import
        ) is True

    def test_public_allowed(self) -> None:
        assert is_valid_scan_target(
            "8.8.8.8", ScanContext.xml_import
        ) is True

    def test_invalid_string_still_rejected(self) -> None:
        assert is_valid_scan_target(
            "not-an-ip", ScanContext.xml_import
        ) is False


# ── target_in_scope ───────────────────────────────────────────────────────────

class TestTargetInScope:
    def test_ip_in_cidr(self) -> None:
        assert target_in_scope(
            "192.168.1.102", ["192.168.1.0/24"]
        ) is True

    def test_ip_outside_cidr(self) -> None:
        assert target_in_scope(
            "192.168.2.1", ["192.168.1.0/24"]
        ) is False

    def test_exact_match(self) -> None:
        assert target_in_scope("10.0.0.5", ["10.0.0.5"]) is True

    def test_aws_vpc_in_scope(self) -> None:
        assert target_in_scope(
            "172.31.5.10", ["172.31.0.0/16"]
        ) is True

    def test_gcp_vpc_in_scope(self) -> None:
        assert target_in_scope(
            "10.128.0.5", ["10.128.0.0/9"]
        ) is True

    def test_multiple_ranges_second_matches(self) -> None:
        assert target_in_scope(
            "10.0.0.5", ["192.168.1.0/24", "10.0.0.0/8"]
        ) is True

    def test_empty_scope_rejects(self) -> None:
        assert target_in_scope("192.168.1.1", []) is False

    def test_malformed_entry_skipped(self) -> None:
        assert target_in_scope(
            "192.168.1.1", ["bad-entry", "192.168.1.0/24"]
        ) is True

    def test_public_ip_in_scope(self) -> None:
        assert target_in_scope(
            "8.8.8.8", ["8.8.8.0/24"]
        ) is True

    def test_public_ip_out_of_scope(self) -> None:
        assert target_in_scope(
            "1.1.1.1", ["8.8.8.0/24"]
        ) is False
