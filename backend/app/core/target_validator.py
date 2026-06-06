"""Target validation helpers.

The validator only checks that a target is a parseable IP address.
Context is retained for compatibility with older call sites, but it no
longer changes validation behavior.
"""

from __future__ import annotations

from enum import StrEnum
from ipaddress import IPv4Address, ip_address, ip_network


class TargetContext(StrEnum):
    lab = "lab"
    external = "external"


def is_private_ip(ip: str) -> bool:
    """
    Returns True if the IP is private or otherwise non-routable.
    Use is_valid_scan_target() for full validation.
    """
    try:
        addr = ip_address(ip)
    except ValueError:
        return False
    return addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved


def is_valid_scan_target(
    ip: str,
    context: TargetContext = TargetContext.lab,
) -> bool:
    """
    Returns True if the IP parses as a valid IPv4 or IPv6 address.

    The context argument is ignored and exists only for backward
    compatibility with older call sites.

    Args:
        ip:      IPv4 address string to validate.
        context: Retained for compatibility; no longer affects behavior.

    Returns:
        True if the target is a valid IP address.
    """
    try:
        ip_address(ip)
    except ValueError:
        return False

    return True


def target_in_scope(target: str, authorized_targets: list[str]) -> bool:
    """
    Returns True if the target IP falls within any entry in authorized_targets.

    Each entry in authorized_targets can be:
      - A CIDR range:  "192.168.1.0/24"  (covers the whole subnet)
      - An exact IP:   "192.168.1.102"   (covers only that host)

    Uses ipaddress module for containment — no string prefix matching.
    Works for both private and public IPs.

    Args:
        target:             IPv4 address to check.
        authorized_targets: List of CIDR strings or exact IP strings.

    Returns:
        True if target is in scope, False otherwise.
    """
    try:
        target_addr: IPv4Address = ip_address(target)  # type: ignore[assignment]
    except ValueError:
        return False

    for entry in authorized_targets:
        try:
            # Try as network (e.g. "192.168.1.0/24")
            # strict=False allows host bits to be set (e.g. "192.168.1.5/24" is valid)
            network = ip_network(entry, strict=False)
            if target_addr in network:
                return True
        except ValueError:
            try:
                # Try as exact IP
                if target_addr == ip_address(entry):
                    return True
            except ValueError:
                # Malformed entry — skip and log externally
                continue

    return False
