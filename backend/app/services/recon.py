from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime

import httpx
import structlog

logger = structlog.get_logger()


@dataclass(frozen=True)
class PassiveReconResult:
    ip: str
    open_ports: list[int]
    hostnames: list[str]
    org: str | None
    isp: str | None
    country: str | None
    vulns: list[str]
    banners: dict[int, str]
    last_seen: datetime | None
    source: str = "shodan"

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        if self.last_seen is not None:
            payload["last_seen"] = self.last_seen.isoformat()
        return payload


class PassiveReconService:
    def __init__(self, shodan_api_key: str | None = None) -> None:
        self.shodan_api_key = shodan_api_key

    async def lookup_ip(self, ip: str) -> PassiveReconResult | None:
        if not self.shodan_api_key:
            logger.warning("Skipping Shodan lookup because no API key is configured", ip=ip)
            return None

        url = f"https://api.shodan.io/shodan/host/{ip}"
        params = {"key": self.shodan_api_key}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)

            if response.status_code != 200:
                logger.error(
                    "Shodan lookup failed",
                    ip=ip,
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                return None

            data = response.json()
            if not isinstance(data, dict):
                logger.error("Shodan lookup returned unexpected payload", ip=ip)
                return None

            return PassiveReconResult(
                ip=str(data.get("ip_str") or ip),
                open_ports=self._extract_open_ports(data),
                hostnames=self._extract_hostnames(data),
                org=self._coerce_optional_string(data.get("org")),
                isp=self._coerce_optional_string(data.get("isp")),
                country=self._coerce_optional_string(data.get("country_name") or data.get("country")),
                vulns=self._extract_vulns(data),
                banners=self._extract_banners(data),
                last_seen=self._extract_last_seen(data),
            )
        except Exception as exc:
            logger.exception("Failed to perform Shodan lookup", ip=ip, error=str(exc))
            return None

    async def lookup_crtsh(self, domain: str) -> list[str]:
        url = "https://crt.sh/"
        params = {"q": domain, "output": "json"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)

            if response.status_code != 200:
                logger.error(
                    "crt.sh lookup failed",
                    domain=domain,
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                return []

            payload = response.json()
            if not isinstance(payload, list):
                return []

            hostnames: set[str] = set()
            for entry in payload:
                if not isinstance(entry, dict):
                    continue
                raw_name = entry.get("name_value")
                if not isinstance(raw_name, str):
                    continue
                for candidate in raw_name.splitlines():
                    hostname = candidate.strip().lower().rstrip(".")
                    if hostname.startswith("*."):
                        hostname = hostname[2:]
                    if hostname:
                        hostnames.add(hostname)

            return sorted(hostnames)
        except Exception as exc:
            logger.exception("Failed to query crt.sh", domain=domain, error=str(exc))
            return []

    def _extract_open_ports(self, data: dict[str, object]) -> list[int]:
        ports = data.get("ports", [])
        if not isinstance(ports, list):
            return []

        open_ports: set[int] = set()
        for raw_port in ports:
            try:
                open_ports.add(int(raw_port))
            except (TypeError, ValueError):
                continue
        return sorted(open_ports)

    def _extract_hostnames(self, data: dict[str, object]) -> list[str]:
        hostnames = data.get("hostnames", [])
        if not isinstance(hostnames, list):
            return []

        results: set[str] = set()
        for item in hostnames:
            if isinstance(item, str):
                hostname = item.strip().lower().rstrip(".")
            elif isinstance(item, dict):
                value = item.get("name")
                hostname = value.strip().lower().rstrip(".") if isinstance(value, str) else ""
            else:
                hostname = ""

            if hostname:
                results.add(hostname)

        return sorted(results)

    def _extract_vulns(self, data: dict[str, object]) -> list[str]:
        vulns = data.get("vulns", {})
        if isinstance(vulns, dict):
            return sorted(key for key in vulns.keys() if isinstance(key, str))
        if isinstance(vulns, list):
            return sorted(vuln for vuln in vulns if isinstance(vuln, str))
        return []

    def _extract_banners(self, data: dict[str, object]) -> dict[int, str]:
        banners: dict[int, str] = {}
        entries = data.get("data", [])
        if not isinstance(entries, list):
            return banners

        for entry in entries:
            if not isinstance(entry, dict):
                continue

            port_value = entry.get("port")
            try:
                port = int(port_value)
            except (TypeError, ValueError):
                continue

            banner = entry.get("data")
            if isinstance(banner, str) and banner.strip():
                banners[port] = banner.strip()
                continue

            product = entry.get("product")
            version = entry.get("version")
            parts = [part for part in (product, version) if isinstance(part, str) and part.strip()]
            if parts:
                banners[port] = " ".join(parts)

        return banners

    def _extract_last_seen(self, data: dict[str, object]) -> datetime | None:
        candidates = [data.get("last_update")]
        entries = data.get("data", [])
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict):
                    candidates.append(entry.get("timestamp"))

        for candidate in candidates:
            parsed = self._parse_datetime(candidate)
            if parsed is not None:
                return parsed
        return None

    def _parse_datetime(self, value: object) -> datetime | None:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value), tz=UTC)
        if not isinstance(value, str):
            return None

        raw_value = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(raw_value)
        except ValueError:
            return None

    def _coerce_optional_string(self, value: object) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None
