from app.services.risk import CompositeRiskScore, ExposureLevel, RiskInputs, RiskSeverity


def test_composite_risk_score_uses_all_components() -> None:
    scorer = CompositeRiskScore()

    score = scorer.calculate(
        RiskInputs(
            cvss_score=9.8,
            epss_probability=0.91,
            exposure=ExposureLevel.external,
            asset_criticality=5,
        )
    )

    assert score.score >= 85
    assert score.severity == RiskSeverity.critical
    assert score.cvss_component == 98.0
    assert score.epss_component == 91.0
    assert score.exposure_component == 100.0
    assert score.asset_criticality_component == 100.0


def test_composite_risk_score_handles_missing_vulnerability_intelligence() -> None:
    scorer = CompositeRiskScore()

    score = scorer.calculate(
        RiskInputs(
            cvss_score=None,
            epss_probability=None,
            exposure=ExposureLevel.internal,
            asset_criticality=1,
        )
    )

    assert score.score > 0
    assert score.severity in {RiskSeverity.low, RiskSeverity.informational}
    assert score.cvss_component == 0
    assert score.epss_component == 0

