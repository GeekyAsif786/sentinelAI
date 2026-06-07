from dataclasses import dataclass
import httpx
import structlog

logger = structlog.get_logger()


@dataclass(frozen=True)
class EpssData:
    cve_id: str
    epss_probability: float | None


class EpssClient:
    def __init__(self, base_url: str = "https://api.first.org/data/v1/epss") -> None:
        self.base_url = base_url

    async def fetch_epss(self, cve_ids: list[str]) -> dict[str, EpssData]:
        """Fetch EPSS scores for a list of CVE IDs.

        Returns:
            Dictionary mapping CVE ID to EpssData.
        """
        if not cve_ids:
            return {}

        results: dict[str, EpssData] = {}
        chunk_size = 100
        chunks = [cve_ids[i:i + chunk_size] for i in range(0, len(cve_ids), chunk_size)]

        async with httpx.AsyncClient(timeout=30.0) as client:
            for chunk in chunks:
                cve_str = ",".join(chunk)
                params = {"cve": cve_str}
                try:
                    logger.info("Fetching EPSS scores from FIRST.org", count=len(chunk))
                    response = await client.get(self.base_url, params=params)
                    if response.status_code == 200:
                        data = response.json()
                        items = data.get("data", [])
                        if isinstance(items, list):
                            for item in items:
                                if not isinstance(item, dict):
                                    continue
                                cve_id = item.get("cve")
                                if not cve_id or not isinstance(cve_id, str):
                                    continue
                                epss_str = item.get("epss")
                                epss_val: float | None = None
                                if epss_str is not None:
                                    try:
                                        epss_val = float(epss_str)
                                    except ValueError:
                                        pass
                                results[cve_id] = EpssData(
                                    cve_id=cve_id,
                                    epss_probability=epss_val,
                                )
                    else:
                        logger.error(
                            "EPSS API returned error status",
                            status_code=response.status_code,
                            body=response.text[:200],
                        )
                except Exception as e:
                    logger.exception("Failed to fetch EPSS data", error=str(e))

        return results
