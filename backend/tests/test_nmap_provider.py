from unittest.mock import MagicMock, patch

import pytest

from app.discovery.nmap import NmapDiscoveryProvider, NmapXmlParseError, ScanProfile


NMAP_XML = """<?xml version="1.0"?>
<nmaprun scanner="nmap" version="7.95">
  <host>
    <status state="up"/>
    <address addr="192.168.1.10" addrtype="ipv4"/>
    <address addr="AA:BB:CC:DD:EE:FF" addrtype="mac"/>
    <hostnames><hostname name="fileserver.local"/></hostnames>
    <ports>
      <port protocol="tcp" portid="22">
        <state state="open"/>
        <service name="ssh" product="OpenSSH" version="9.6"/>
      </port>
      <port protocol="tcp" portid="80">
        <state state="closed"/>
        <service name="http"/>
      </port>
    </ports>
    <os><osmatch name="Linux 6.x" accuracy="97"/></os>
  </host>
</nmaprun>
"""


def test_parse_nmap_xml_normalizes_up_hosts_and_open_services() -> None:
    provider = NmapDiscoveryProvider()

    result = provider.parse_artifact(NMAP_XML)

    assert result.provider == "nmap"
    assert result.provider_version == "7.95"
    assert len(result.hosts) == 1
    host = result.hosts[0]
    assert host.primary_ip == "192.168.1.10"
    assert host.hostname == "fileserver.local"
    assert host.mac_address == "AA:BB:CC:DD:EE:FF"
    assert host.os_name == "Linux 6.x"
    assert host.os_confidence == 97.0
    assert len(host.services) == 1
    assert host.services[0].port == 22
    assert host.services[0].service_name == "ssh"


def test_parse_empty_artifact_returns_empty_result() -> None:
    provider = NmapDiscoveryProvider()

    result = provider.parse_artifact(" \n ")

    assert result.hosts == tuple()
    assert result.raw_artifact_sha256 is None


def test_parse_rejects_non_nmap_xml() -> None:
    provider = NmapDiscoveryProvider()

    with pytest.raises(NmapXmlParseError):
        provider.parse_artifact("<root />")


def test_execute_nmap_builds_preset_command_and_parses_xml() -> None:
    provider = NmapDiscoveryProvider()

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = NMAP_XML
    mock_result.stderr = ""

    with patch("shutil.which", return_value="/usr/bin/nmap"), patch("os.geteuid", return_value=0), patch(
        "subprocess.run",
        return_value=mock_result,
    ) as mock_run:
        result = provider.execute_nmap(["8.8.8.8"], ScanProfile.external_full)

    assert len(result.hosts) == 1
    command = mock_run.call_args.args[0]
    assert command[0] == "/usr/bin/nmap"
    assert "-sS" in command
    assert "-sV" in command
    assert "--open" in command
    assert "-T3" in command
    assert "--max-rate" in command
    assert "500" in command
    assert "-p" in command
    assert "1-65535" in command
    assert "-oX" in command
    assert "-" in command
    assert "8.8.8.8" in command


def test_execute_nmap_rejects_external_profile_without_root() -> None:
    provider = NmapDiscoveryProvider()

    with patch("shutil.which", return_value="/usr/bin/nmap"), patch("os.geteuid", return_value=1000):
        with pytest.raises(PermissionError):
            provider.execute_nmap(["8.8.8.8"], ScanProfile.external_stealth)
