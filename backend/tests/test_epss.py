from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.services.epss import EpssClient


@pytest.mark.anyio
async def test_epss_client_success() -> None:
    client = EpssClient()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "OK",
        "data": [
            {
                "cve": "CVE-2021-44228",
                "epss": "0.974530000",
                "percentile": "0.99942",
            }
        ]
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        results = await client.fetch_epss(["CVE-2021-44228"])

        assert "CVE-2021-44228" in results
        assert results["CVE-2021-44228"].epss_probability == 0.97453
        mock_get.assert_called_once()
        _, kwargs = mock_get.call_args
        assert kwargs["params"] == {"cve": "CVE-2021-44228"}


@pytest.mark.anyio
async def test_epss_client_comma_separated_batching() -> None:
    client = EpssClient()
    cves = [f"CVE-2021-{i:04d}" for i in range(105)]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "OK",
        "data": [],
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        await client.fetch_epss(cves)
        assert mock_get.call_count == 2
        # Check first call params has 100 comma-separated CVEs
        _, first_call_kwargs = mock_get.call_args_list[0]
        cves_param = first_call_kwargs["params"]["cve"]
        assert len(cves_param.split(",")) == 100
        # Check second call params has 5 comma-separated CVEs
        _, second_call_kwargs = mock_get.call_args_list[1]
        cves_param_2 = second_call_kwargs["params"]["cve"]
        assert len(cves_param_2.split(",")) == 5


@pytest.mark.anyio
async def test_epss_client_error_handling() -> None:
    client = EpssClient()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = Exception("Connection failed")
        results = await client.fetch_epss(["CVE-2021-44228"])
        assert results == {}
