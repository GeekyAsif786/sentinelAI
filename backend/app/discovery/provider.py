from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum


class DiscoveryProviderName(StrEnum):
    nmap = "nmap"


@dataclass(frozen=True)
class DiscoveredService:
    port: int
    protocol: str
    state: str
    service_name: str | None = None
    product: str | None = None
    version: str | None = None


@dataclass(frozen=True)
class DiscoveredHost:
    primary_ip: str
    hostname: str | None = None
    mac_address: str | None = None
    os_name: str | None = None
    os_confidence: float | None = None
    services: tuple[DiscoveredService, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class DiscoveryResult:
    provider: DiscoveryProviderName
    hosts: tuple[DiscoveredHost, ...]
    raw_artifact_sha256: str | None = None
    provider_version: str | None = None


class DiscoveryProvider(ABC):
    provider_name: DiscoveryProviderName

    @abstractmethod
    def parse_artifact(self, artifact: str) -> DiscoveryResult:
        raise NotImplementedError

