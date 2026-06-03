from dataclasses import dataclass
from enum import StrEnum


class ExposureLevel(StrEnum):
    internal = "internal"
    external = "external"
    unknown = "unknown"


class RiskSeverity(StrEnum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    informational = "informational"


@dataclass(frozen=True)
class RiskInputs:
    cvss_score: float | None
    epss_probability: float | None
    exposure: ExposureLevel
    asset_criticality: int


@dataclass(frozen=True)
class RiskScore:
    score: float
    severity: RiskSeverity
    scoring_version: str
    cvss_component: float
    epss_component: float
    exposure_component: float
    asset_criticality_component: float
    explanation: str


class CompositeRiskScore:
    version = "1.0.0"
    name = "Composite Risk Score v1"

    CVSS_WEIGHT = 0.45
    EPSS_WEIGHT = 0.25
    EXPOSURE_WEIGHT = 0.20
    ASSET_CRITICALITY_WEIGHT = 0.10
    MAX_CVSS = 10.0
    MAX_CRITICALITY = 5

    def calculate(self, inputs: RiskInputs) -> RiskScore:
        cvss_component = self._bounded(inputs.cvss_score, 0.0, self.MAX_CVSS) / self.MAX_CVSS
        epss_component = self._bounded(inputs.epss_probability, 0.0, 1.0)
        exposure_component = self._exposure_component(inputs.exposure)
        asset_criticality_component = self._bounded(
            float(inputs.asset_criticality),
            1.0,
            float(self.MAX_CRITICALITY),
        ) / float(self.MAX_CRITICALITY)

        score = round(
            100
            * (
                cvss_component * self.CVSS_WEIGHT
                + epss_component * self.EPSS_WEIGHT
                + exposure_component * self.EXPOSURE_WEIGHT
                + asset_criticality_component * self.ASSET_CRITICALITY_WEIGHT
            ),
            2,
        )

        severity = self._severity(score)
        explanation = (
            f"Composite score {score:.2f} uses CVSS, EPSS, service exposure, and asset "
            f"criticality with risk model {self.version}. Missing CVSS or EPSS values are "
            "treated as zero contribution instead of blocking deterministic scoring."
        )
        return RiskScore(
            score=score,
            severity=severity,
            scoring_version=self.version,
            cvss_component=round(cvss_component * 100, 2),
            epss_component=round(epss_component * 100, 2),
            exposure_component=round(exposure_component * 100, 2),
            asset_criticality_component=round(asset_criticality_component * 100, 2),
            explanation=explanation,
        )

    def _bounded(self, value: float | None, minimum: float, maximum: float) -> float:
        if value is None:
            return minimum
        return min(max(value, minimum), maximum)

    def _exposure_component(self, exposure: ExposureLevel) -> float:
        if exposure == ExposureLevel.external:
            return 1.0
        if exposure == ExposureLevel.internal:
            return 0.45
        return 0.25

    def _severity(self, score: float) -> RiskSeverity:
        if score >= 85:
            return RiskSeverity.critical
        if score >= 70:
            return RiskSeverity.high
        if score >= 40:
            return RiskSeverity.medium
        if score >= 10:
            return RiskSeverity.low
        return RiskSeverity.informational

