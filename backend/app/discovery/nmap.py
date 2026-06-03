from hashlib import sha256
from xml.etree import ElementTree

from app.discovery.provider import (
    DiscoveredHost,
    DiscoveredService,
    DiscoveryProvider,
    DiscoveryProviderName,
    DiscoveryResult,
)

ADDRESS_TYPE_IPV4 = "ipv4"
ADDRESS_TYPE_IPV6 = "ipv6"
ADDRESS_TYPE_MAC = "mac"
HOST_STATUS_UP = "up"
SERVICE_STATE_OPEN = "open"


class NmapXmlParseError(ValueError):
    pass


class NmapDiscoveryProvider(DiscoveryProvider):
    provider_name = DiscoveryProviderName.nmap

    def parse_artifact(self, artifact: str) -> DiscoveryResult:
        if not artifact.strip():
            return DiscoveryResult(provider=self.provider_name, hosts=tuple(), raw_artifact_sha256=None)

        try:
            root = ElementTree.fromstring(artifact)
        except ElementTree.ParseError as exc:
            raise NmapXmlParseError("Invalid Nmap XML artifact") from exc

        scanner = root.attrib.get("scanner")
        if scanner != "nmap":
            raise NmapXmlParseError("XML artifact is not an Nmap result")

        hosts: list[DiscoveredHost] = []
        for host_element in root.findall("host"):
            status_element = host_element.find("status")
            if status_element is not None and status_element.attrib.get("state") != HOST_STATUS_UP:
                continue

            primary_ip = self._extract_primary_ip(host_element)
            if primary_ip is None:
                continue

            hosts.append(
                DiscoveredHost(
                    primary_ip=primary_ip,
                    hostname=self._extract_hostname(host_element),
                    mac_address=self._extract_mac_address(host_element),
                    os_name=self._extract_os_name(host_element),
                    os_confidence=self._extract_os_confidence(host_element),
                    services=tuple(self._extract_services(host_element)),
                )
            )

        return DiscoveryResult(
            provider=self.provider_name,
            hosts=tuple(hosts),
            raw_artifact_sha256=sha256(artifact.encode("utf-8")).hexdigest(),
            provider_version=root.attrib.get("version"),
        )

    def _extract_primary_ip(self, host_element: ElementTree.Element) -> str | None:
        fallback_ip: str | None = None
        for address_element in host_element.findall("address"):
            address_type = address_element.attrib.get("addrtype")
            address_value = address_element.attrib.get("addr")
            if address_type == ADDRESS_TYPE_IPV4 and address_value:
                return address_value
            if address_type == ADDRESS_TYPE_IPV6 and address_value:
                fallback_ip = address_value
        return fallback_ip

    def _extract_mac_address(self, host_element: ElementTree.Element) -> str | None:
        for address_element in host_element.findall("address"):
            if address_element.attrib.get("addrtype") == ADDRESS_TYPE_MAC:
                return address_element.attrib.get("addr")
        return None

    def _extract_hostname(self, host_element: ElementTree.Element) -> str | None:
        hostname_element = host_element.find("hostnames/hostname")
        if hostname_element is None:
            return None
        hostname = hostname_element.attrib.get("name")
        return hostname if hostname else None

    def _extract_os_name(self, host_element: ElementTree.Element) -> str | None:
        os_match = host_element.find("os/osmatch")
        if os_match is None:
            return None
        os_name = os_match.attrib.get("name")
        return os_name if os_name else None

    def _extract_os_confidence(self, host_element: ElementTree.Element) -> float | None:
        os_match = host_element.find("os/osmatch")
        if os_match is None:
            return None
        accuracy = os_match.attrib.get("accuracy")
        if accuracy is None:
            return None
        try:
            return float(accuracy)
        except ValueError:
            return None

    def _extract_services(self, host_element: ElementTree.Element) -> list[DiscoveredService]:
        services: list[DiscoveredService] = []
        for port_element in host_element.findall("ports/port"):
            protocol = port_element.attrib.get("protocol", "tcp")
            port_number = self._parse_port(port_element.attrib.get("portid"))
            if port_number is None:
                continue

            state_element = port_element.find("state")
            state = state_element.attrib.get("state", "unknown") if state_element is not None else "unknown"
            if state != SERVICE_STATE_OPEN:
                continue

            service_element = port_element.find("service")
            services.append(
                DiscoveredService(
                    port=port_number,
                    protocol=protocol,
                    state=state,
                    service_name=self._service_attr(service_element, "name"),
                    product=self._service_attr(service_element, "product"),
                    version=self._service_attr(service_element, "version"),
                )
            )
        return services

    def _parse_port(self, raw_port: str | None) -> int | None:
        if raw_port is None:
            return None
        try:
            port = int(raw_port)
        except ValueError:
            return None
        if port < 0 or port > 65535:
            return None
        return port

    def _service_attr(self, service_element: ElementTree.Element | None, key: str) -> str | None:
        if service_element is None:
            return None
        value = service_element.attrib.get(key)
        return value if value else None

    def execute_nmap(self, targets: list[str], profile_config: dict[str, object], timeout: int = 300) -> DiscoveryResult:
        """Execute nmap scanner against targets and parse XML output.

        Args:
            targets: List of target addresses (IPs, CIDRs, or hostnames)
            profile_config: Scanner profile configuration with nmap options
            timeout: Subprocess timeout in seconds

        Returns:
            DiscoveryResult with parsed hosts and services

        Raises:
            NmapXmlParseError: If XML output cannot be parsed
            TimeoutError: If scan execution exceeds timeout
            RuntimeError: If nmap binary is not found or execution fails
        """
        import subprocess
        import shutil

        nmap_binary = shutil.which("nmap")
        if nmap_binary is None:
            raise RuntimeError("nmap binary not found in PATH")

        cmd = self._build_nmap_command(nmap_binary, targets, profile_config)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(f"nmap execution exceeded {timeout}s timeout") from exc
        except Exception as exc:
            raise RuntimeError(f"nmap execution failed: {exc}") from exc

        if result.returncode not in (0, 1):
            stderr = result.stderr.strip() if result.stderr else "unknown error"
            raise RuntimeError(f"nmap failed with return code {result.returncode}: {stderr}")

        if not result.stdout.strip():
            return DiscoveryResult(provider=self.provider_name, hosts=tuple())

        return self.parse_artifact(result.stdout)

    def _build_nmap_command(self, nmap_binary: str, targets: list[str], profile_config: dict[str, object]) -> list[str]:
        """Build nmap command with options from profile configuration.

        Args:
            nmap_binary: Path to nmap executable
            targets: List of target addresses
            profile_config: Scanner profile configuration dict

        Returns:
            Command list for subprocess
        """
        cmd = [nmap_binary]

        extra_args = profile_config.get("extra_args", [])
        if isinstance(extra_args, list):
            cmd.extend(extra_args)

        cmd.extend(["-oX", "-"])

        cmd.extend(targets)

        return cmd

