import asyncio
from dataclasses import dataclass
from typing import Any
import httpx
import structlog

logger = structlog.get_logger()


@dataclass(frozen=True)
class CveData:
    cve_id: str
    cvss_score: float | None


class NvdCveClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://services.nvd.nist.gov/rest/json/cves/2.0",
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url

    async def fetch_cves(self, cve_ids: list[str]) -> dict[str, CveData]:
        """Fetch CVSS scores for a list of CVE IDs.

        Returns:
            Dictionary mapping CVE ID to CveData.
        """
        if not cve_ids:
            return {}

        results: dict[str, CveData] = {}
        chunk_size = 100 if self.api_key else 10
        delay = 0.6 if self.api_key else 6.0

        chunks = [cve_ids[i:i + chunk_size] for i in range(0, len(cve_ids), chunk_size)]
        headers: dict[str, str] = {}
        if self.api_key:
            headers["apiKey"] = self.api_key

        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            for idx, chunk in enumerate(chunks):
                if idx > 0:
                    logger.debug("Rate limiting delay", delay=delay)
                    await asyncio.sleep(delay)

                cve_ids_str = ",".join(chunk)
                params = {"cveIds": cve_ids_str}
                try:
                    logger.info("Fetching CVEs from NVD", count=len(chunk))
                    response = await client.get(self.base_url, params=params)
                    if response.status_code == 200:
                        data = response.json()
                        vulnerabilities = data.get("vulnerabilities", [])
                        for item in vulnerabilities:
                            cve_data = item.get("cve", {})
                            cve_id = cve_data.get("id")
                            if not cve_id or not isinstance(cve_id, str):
                                continue

                            metrics = cve_data.get("metrics", {})
                            cvss_score = self._extract_cvss_score(metrics)
                            results[cve_id] = CveData(cve_id=cve_id, cvss_score=cvss_score)
                    else:
                        logger.error(
                            "NVD API returned error status",
                            status_code=response.status_code,
                            body=response.text[:200],
                        )
                except Exception as e:
                    logger.exception("Failed to fetch CVE data from NVD", error=str(e))

        return results

    def _extract_cvss_score(self, metrics: dict[str, Any]) -> float | None:
        """Extract CVSS score falling back from CVSS v3.1 to v3.0, then v2.0."""
        for version_key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            metric_list = metrics.get(version_key, [])
            if not isinstance(metric_list, list) or not metric_list:
                continue

            primary = next(
                (m for m in metric_list if isinstance(m, dict) and m.get("type") == "Primary"),
                None,
            )
            if not primary and isinstance(metric_list[0], dict):
                primary = metric_list[0]

            if primary:
                cvss_data = primary.get("cvssData", {})
                if isinstance(cvss_data, dict):
                    base_score = cvss_data.get("baseScore")
                    if base_score is not None:
                        try:
                            return float(base_score)
                        except ValueError:
                            pass
        return None
