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


def test_composite_risk_score_boundaries_and_thresholds() -> None:
    scorer = CompositeRiskScore()

    # Minimum possible inputs
    min_score = scorer.calculate(
        RiskInputs(
            cvss_score=0.0,
            epss_probability=0.0,
            exposure=ExposureLevel.unknown,
            asset_criticality=1,
        )
    )
    assert min_score.score == 7.0
    assert min_score.severity == RiskSeverity.informational

    # Critical threshold check (score >= 85)
    crit_score = scorer.calculate(
        RiskInputs(
            cvss_score=8.5,
            epss_probability=0.85,
            exposure=ExposureLevel.external,
            asset_criticality=4,
        )
    )
    assert crit_score.score >= 85.0
    assert crit_score.severity == RiskSeverity.critical

    # High threshold check (score >= 70)
    high_score = scorer.calculate(
        RiskInputs(
            cvss_score=7.0,
            epss_probability=0.7,
            exposure=ExposureLevel.external,
            asset_criticality=3,
        )
    )
    assert 70.0 <= high_score.score < 85.0
    assert high_score.severity == RiskSeverity.high

    # Medium threshold check (score >= 40)
    med_score = scorer.calculate(
        RiskInputs(
            cvss_score=5.0,
            epss_probability=0.3,
            exposure=ExposureLevel.internal,
            asset_criticality=2,
        )
    )
    assert 40.0 <= med_score.score < 70.0
    assert med_score.severity == RiskSeverity.medium

    # Low threshold check (score >= 10)
    low_score = scorer.calculate(
        RiskInputs(
            cvss_score=2.0,
            epss_probability=0.1,
            exposure=ExposureLevel.internal,
            asset_criticality=1,
        )
    )
    assert 10.0 <= low_score.score < 40.0
    assert low_score.severity == RiskSeverity.low


