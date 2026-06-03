import pytest

from app.discovery.nmap import NmapDiscoveryProvider, NmapXmlParseError


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

