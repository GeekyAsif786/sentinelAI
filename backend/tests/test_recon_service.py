from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.recon import PassiveReconService


@pytest.mark.anyio
async def test_lookup_ip_parses_shodan_payload() -> None:
    service = PassiveReconService(shodan_api_key="test-key")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "ip_str": "8.8.8.8",
        "ports": [53, 443, 53],
        "hostnames": ["dns.google", {"name": "dns.google"}],
        "org": "Google LLC",
        "isp": "Google",
        "country_name": "United States",
        "vulns": {"CVE-2023-1234": {}},
        "data": [
            {
                "port": 53,
                "data": "BANNER",
                "timestamp": "2024-06-03T10:00:00Z",
            }
        ],
        "last_update": "2024-06-03T11:00:00Z",
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await service.lookup_ip("8.8.8.8")

    assert result is not None
    assert result.ip == "8.8.8.8"
    assert result.open_ports == [53, 443]
    assert result.hostnames == ["dns.google"]
    assert result.org == "Google LLC"
    assert result.isp == "Google"
    assert result.country == "United States"
    assert result.vulns == ["CVE-2023-1234"]
    assert result.banners[53] == "BANNER"
    assert result.last_seen is not None


@pytest.mark.anyio
async def test_lookup_crtsh_returns_unique_hostnames() -> None:
    service = PassiveReconService(shodan_api_key="test-key")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"name_value": "*.example.com\nwww.example.com"},
        {"name_value": "api.example.com"},
    ]

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await service.lookup_crtsh("example.com")

    assert result == ["api.example.com", "example.com", "www.example.com"]
