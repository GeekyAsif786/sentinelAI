"""
target_validator.py — sentinelAI IP classification and scan gating.

ALLOWED scan targets (by ScanContext):
  institutional : RFC1918, cloud VPC private ranges, public IPs
                  Covers: home labs, corporate VPCs, authorized engagements
  external      : Public IPs only (authorized client pentests)
  xml_import    : No IP validation — artifact already captured offline

ALWAYS BLOCKED regardless of context:
  - CGNAT         100.64.0.0/10   (RFC 6598 — ISP shared space)
  - Loopback      127.0.0.0/8
  - Link-local    169.254.0.0/16
  - Multicast     224.0.0.0/4
  - Reserved      240.0.0.0/4
  - Broadcast     255.255.255.255/32
  - Unspecified   0.0.0.0/8
  - TEST-NETs     192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24
  - Benchmarking  198.18.0.0/15
  - IETF assign.  192.0.0.0/24
"""
from __future__ import annotations

from enum import StrEnum
from ipaddress import IPv4Address, IPv4Network, ip_address, ip_network
from typing import cast


class ScanContext(StrEnum):
    institutional = "institutional"   # RFC1918 + cloud VPC + public
    external      = "external"        # public IPs only
    xml_import    = "xml_import"      # offline artifact, skip validation


# ── Always blocked — no context overrides these ──────────────────────────────

_ALWAYS_BLOCKED: list[IPv4Network] = [
    cast(IPv4Network, ip_network("0.0.0.0/8")),            # unspecified
    cast(IPv4Network, ip_network("100.64.0.0/10")),        # RFC 6598  — CGNAT (NEVER scannable)
    cast(IPv4Network, ip_network("127.0.0.0/8")),          # loopback
    cast(IPv4Network, ip_network("169.254.0.0/16")),       # link-local / APIPA
    cast(IPv4Network, ip_network("192.0.0.0/24")),         # IETF protocol assignments
    cast(IPv4Network, ip_network("192.0.2.0/24")),         # TEST-NET-1 (documentation)
    cast(IPv4Network, ip_network("198.18.0.0/15")),        # RFC 2544 benchmarking
    cast(IPv4Network, ip_network("198.51.100.0/24")),      # TEST-NET-2 (documentation)
    cast(IPv4Network, ip_network("203.0.113.0/24")),       # TEST-NET-3 (documentation)
    cast(IPv4Network, ip_network("224.0.0.0/4")),          # multicast
    cast(IPv4Network, ip_network("240.0.0.0/4")),          # reserved / future use
    cast(IPv4Network, ip_network("255.255.255.255/32")),   # broadcast
]

# ── RFC1918 private ranges ────────────────────────────────────────────────────

_RFC1918: list[IPv4Network] = [
    cast(IPv4Network, ip_network("10.0.0.0/8")),
    cast(IPv4Network, ip_network("172.16.0.0/12")),
    cast(IPv4Network, ip_network("192.168.0.0/16")),
]

# ── Cloud provider VPC / internal ranges ─────────────────────────────────────
# These are the private/internal CIDRs cloud providers use inside VPCs.
# They overlap with RFC1918 but are listed explicitly for clarity and
# so classify_ip() can label them correctly in reports.

_CLOUD_VPC: list[IPv4Network] = [
    # AWS
    cast(IPv4Network, ip_network("172.31.0.0/16")),    # AWS default VPC
    cast(IPv4Network, ip_network("10.0.0.0/8")),       # AWS custom VPCs (subset of RFC1918)
    # GCP
    cast(IPv4Network, ip_network("10.128.0.0/9")),     # GCP default subnet range
    # Azure
    cast(IPv4Network, ip_network("10.0.0.0/8")),       # Azure VNet (subset of RFC1918)
    cast(IPv4Network, ip_network("172.16.0.0/12")),    # Azure VNet alt range
    # Generic cloud-internal (still RFC1918, listed for label accuracy)
    cast(IPv4Network, ip_network("192.168.0.0/16")),
]
# Note: cloud VPC ranges are all subsets of RFC1918.
# _CLOUD_VPC is used only for classification labeling, not for
# additional allow/block logic. Allowing RFC1918 covers all of them.


# ── Public API ────────────────────────────────────────────────────────────────

def classify_ip(ip: str) -> str:
    """
    Returns a human-readable classification for use in error messages,
    audit logs, and scan reports.

    Returns one of:
      "invalid"          — not a parseable IP address
      "cgnat"            — RFC 6598 carrier-grade NAT (100.64.0.0/10)
      "loopback"         — 127.x.x.x
      "link-local"       — 169.254.x.x
      "multicast"        — 224.x.x.x
      "reserved"         — 240.x.x.x, 0.x.x.x, broadcast, etc.
      "documentation"    — TEST-NET ranges (never real hosts)
      "benchmarking"     — RFC 2544 testing range
      "cloud-vpc"        — cloud provider VPC internal range
      "rfc1918-private"  — home/corporate private range
      "public"           — routable internet IP
    """
    try:
        addr = ip_address(ip)
    except ValueError:
        return "invalid"

    if addr in ip_network("100.64.0.0/10"):
        return "cgnat"
    if addr in ip_network("127.0.0.0/8"):
        return "loopback"
    if addr in ip_network("169.254.0.0/16"):
        return "link-local"
    if addr in ip_network("224.0.0.0/4"):
        return "multicast"
    if addr in ip_network("240.0.0.0/4") or addr in ip_network("0.0.0.0/8"):
        return "reserved"
    if addr in ip_network("255.255.255.255/32"):
        return "reserved"
    if (
        addr in ip_network("192.0.2.0/24")
        or addr in ip_network("198.51.100.0/24")
        or addr in ip_network("203.0.113.0/24")
        or addr in ip_network("192.0.0.0/24")
    ):
        return "documentation"
    if addr in ip_network("198.18.0.0/15"):
        return "benchmarking"
    # Cloud VPC check before generic RFC1918 so label is more specific
    if addr in ip_network("172.31.0.0/16") or addr in ip_network("10.128.0.0/9"):
        return "cloud-vpc"
    if any(addr in net for net in _RFC1918):
        return "rfc1918-private"
    return "public"


def is_always_blocked(ip: str) -> bool:
    """
    Returns True if this IP is blocked regardless of scan context.
    CGNAT, loopback, multicast, reserved, documentation, benchmarking.
    No context can override this.
    """
    try:
        addr = ip_address(ip)
    except ValueError:
        return True   # unparseable = blocked
    return any(addr in net for net in _ALWAYS_BLOCKED)


def is_rfc1918(ip: str) -> bool:
    """True if IP is in any RFC1918 private range."""
    try:
        addr = ip_address(ip)
    except ValueError:
        return False
    return any(addr in net for net in _RFC1918)


def is_cgnat(ip: str) -> bool:
    """True if IP is in RFC 6598 CGNAT shared space (100.64.0.0/10)."""
    try:
        addr = ip_address(ip)
    except ValueError:
        return False
    return addr in ip_network("100.64.0.0/10")


def is_valid_scan_target(
    ip: str,
    context: ScanContext = ScanContext.institutional,
) -> bool:
    """
    Returns True if the IP is valid to scan in the given context.

    ScanContext.institutional (default):
        Allows: RFC1918, cloud VPC, public IPs.
        Blocks: CGNAT, loopback, link-local, multicast, reserved,
                documentation, benchmarking.
        Use for: home lab, corporate network, cloud VPC, authorized
                 institutional scanning work.

    ScanContext.external:
        Allows: public IPs only.
        Blocks: everything above PLUS RFC1918 and cloud VPC ranges.
        Use for: internet-facing client pentest engagements.

    ScanContext.xml_import:
        Skips all IP validation — the artifact was already captured
        offline. The IPs inside the XML are recorded as-is.
        Use for: POST /scans/import with an uploaded Nmap XML file.
        Returns True always (except truly unparseable input).

    Args:
        ip:      IPv4 address string.
        context: ScanContext — defaults to institutional.

    Returns:
        True if the IP may be scanned in this context.
    """
    # xml_import bypasses all IP-level validation
    if context == ScanContext.xml_import:
        try:
            ip_address(ip)
            return True
        except ValueError:
            return False

    # Hard blocks — no context overrides
    if is_always_blocked(ip):
        return False

    # External context additionally rejects private/VPC ranges
    if context == ScanContext.external and is_rfc1918(ip):
        return False

    # Institutional context: RFC1918 and public both allowed
    return True


def target_in_scope(
    target: str,
    authorized_targets: list[str],
) -> bool:
    """
    Returns True if target falls within any authorized CIDR or exact IP.

    Each entry in authorized_targets may be:
      "192.168.1.0/24"  — CIDR range
      "10.0.0.5"        — exact IP
      "172.31.0.0/16"   — cloud VPC subnet

    Uses ip_network containment — no string matching.
    Works for RFC1918, cloud VPC, and public ranges.

    Args:
        target:             IPv4 address to check.
        authorized_targets: List of CIDRs or exact IPs in scope.

    Returns:
        True if target is in scope.
    """
    try:
        target_addr: IPv4Address = ip_address(target)  # type: ignore[assignment]
    except ValueError:
        return False

    for entry in authorized_targets:
        try:
            if target_addr in ip_network(entry, strict=False):
                return True
        except ValueError:
            try:
                if target_addr == ip_address(entry):
                    return True
            except ValueError:
                continue

    return False


# Keep TargetContext as an alias so old call sites don't break
# while the codebase migrates to ScanContext.
# TODO: remove after all call sites updated to ScanContext.
TargetContext = ScanContext
