from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.services.cve import NvdCveClient


@pytest.mark.anyio
async def test_nvd_cve_client_success() -> None:
    client = NvdCveClient(api_key="test-key")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "vulnerabilities": [
            {
                "cve": {
                    "id": "CVE-2021-44228",
                    "metrics": {
                        "cvssMetricV31": [
                            {
                                "type": "Primary",
                                "cvssData": {
                                    "baseScore": 10.0,
                                },
                            }
                        ]
                    },
                }
            }
        ]
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        results = await client.fetch_cves(["CVE-2021-44228"])

        assert "CVE-2021-44228" in results
        assert results["CVE-2021-44228"].cvss_score == 10.0
        mock_get.assert_called_once()


@pytest.mark.anyio
async def test_nvd_cve_client_fallback_logic() -> None:
    client = NvdCveClient()

    # 1. Fallback from v3.1 to v3.0
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "vulnerabilities": [
            {
                "cve": {
                    "id": "CVE-2021-44228",
                    "metrics": {
                        "cvssMetricV30": [
                            {
                                "type": "Primary",
                                "cvssData": {
                                    "baseScore": 9.8,
                                },
                            }
                        ]
                    },
                }
            }
        ]
    }
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        results = await client.fetch_cves(["CVE-2021-44228"])
        assert results["CVE-2021-44228"].cvss_score == 9.8

    # 2. Fallback to v2.0
    mock_response.json.return_value = {
        "vulnerabilities": [
            {
                "cve": {
                    "id": "CVE-2021-44228",
                    "metrics": {
                        "cvssMetricV2": [
                            {
                                "type": "Primary",
                                "cvssData": {
                                    "baseScore": 7.5,
                                },
                            }
                        ]
                    },
                }
            }
        ]
    }
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        results = await client.fetch_cves(["CVE-2021-44228"])
        assert results["CVE-2021-44228"].cvss_score == 7.5


@pytest.mark.anyio
async def test_nvd_cve_client_timeout_and_error_handling() -> None:
    client = NvdCveClient()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = Exception("Timeout occurred")
        results = await client.fetch_cves(["CVE-2021-44228"])
        assert results == {}


@pytest.mark.anyio
async def test_nvd_cve_client_batching() -> None:
    client = NvdCveClient()
    cves = [f"CVE-2021-{i:04d}" for i in range(15)]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"vulnerabilities": []}

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        with patch("asyncio.sleep", return_value=None) as mock_sleep:
            await client.fetch_cves(cves)
            assert mock_get.call_count == 2
            mock_sleep.assert_called_once_with(6.0)
