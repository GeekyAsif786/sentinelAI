from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from collections import Counter, defaultdict
from uuid import UUID

from sqlalchemy.orm import Session

from app.graph.attack_path import DefensiveAttackPathEngine, GraphRelationship
from app.models import Engagement, Finding, Host, ScanRun, Service
from app.services.mitre import FindingType, MitreAttackMapper
from app.services.risk import CompositeRiskScore, ExposureLevel, RiskInputs, RiskScore as CalculatedRiskScore


@dataclass(frozen=True)
class AssetReport:
    asset_id: str
    primary_ip: str
    hostname: str | None
    asset_criticality: int
    open_ports: list[int]
    risk_score: float
    services: list[str]


@dataclass(frozen=True)
class AttackPathReport:
    source: str
    target: str
    path: list[str]
    risk_score: float
    confidence: float
    critical_nodes: list[str]
    description: str | None = None


@dataclass(frozen=True)
class FindingReport:
    title: str
    severity: str
    cvss_score: float | None
    epss_probability: float | None
    composite_risk_score: float
    affected_asset: str
    cve_id: str | None
    mitre_techniques: list[str]
    remediation_guidance: str | None


@dataclass(frozen=True)
class ExecutiveSummary:
    total_hosts_discovered: int
    total_open_ports: int
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    highest_risk_asset: str | None
    scan_duration_seconds: float


@dataclass(frozen=True)
class EngagementReport:
    engagement_id: str
    engagement_name: str
    authorization_ref: str
    generated_at: datetime
    executive_summary: ExecutiveSummary
    assets: list[AssetReport]
    findings: list[FindingReport]
    attack_paths: list[AttackPathReport]
    mitre_coverage: dict[str, list[str]]
    risk_distribution: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class EngagementReportGenerator:
    def __init__(self) -> None:
        self._risk_scorer = CompositeRiskScore()
        self._mitre_mapper = MitreAttackMapper()

    def generate(self, session: Session, engagement: Engagement) -> EngagementReport:
        scan_runs = list(engagement.scan_runs)
        scan_run_ids = [scan_run.id for scan_run in scan_runs]

        findings = self._load_findings(session, scan_run_ids)
        hosts = self._load_hosts(session, scan_runs, findings)
        services = self._load_services(session, hosts)

        asset_reports = self._build_asset_reports(hosts, services, findings)
        finding_reports = self._build_finding_reports(findings, hosts, services)
        attack_path_reports = self._build_attack_path_reports(hosts, services)

        executive_summary = self._build_executive_summary(scan_runs, asset_reports, finding_reports)
        mitre_coverage = self._build_mitre_coverage(findings, hosts, services)
        risk_distribution = self._build_risk_distribution(finding_reports)

        return EngagementReport(
            engagement_id=str(engagement.id),
            engagement_name=engagement.name,
            authorization_ref=engagement.authorization_ref,
            generated_at=datetime.now(UTC),
            executive_summary=executive_summary,
            assets=asset_reports,
            findings=finding_reports,
            attack_paths=attack_path_reports,
            mitre_coverage=mitre_coverage,
            risk_distribution=risk_distribution,
        )

    def _load_findings(self, session: Session, scan_run_ids: list[UUID]) -> list[Finding]:
        if not scan_run_ids:
            return []
        return (
            session.query(Finding)
            .filter(Finding.scan_run_id.in_(scan_run_ids))
            .all()
        )

    def _load_hosts(
        self,
        session: Session,
        scan_runs: list[ScanRun],
        findings: list[Finding],
    ) -> dict[str, Host]:
        host_ips: set[str] = set()
        for scan_run in scan_runs:
            for target in scan_run.targets:
                if target.target_type == "ip":
                    host_ips.add(target.target_value)

        host_ids = {finding.host_id for finding in findings}
        if host_ids:
            host_records = session.query(Host).filter(Host.id.in_(host_ids)).all()
            for host_record in host_records:
                host_ips.add(str(host_record.primary_ip))

        if not host_ips:
            return {}

        host_records = session.query(Host).filter(Host.primary_ip.in_(sorted(host_ips))).all()
        return {str(host.primary_ip): host for host in host_records}

    def _load_services(self, session: Session, hosts: dict[str, Host]) -> dict[str, list[Service]]:
        if not hosts:
            return {}

        host_ids = [host.id for host in hosts.values()]
        services = session.query(Service).filter(Service.host_id.in_(host_ids)).all()
        services_by_host_id: dict[str, list[Service]] = defaultdict(list)
        for service in services:
            services_by_host_id[str(service.host_id)].append(service)
        return services_by_host_id

    def _build_asset_reports(
        self,
        hosts: dict[str, Host],
        services_by_host_id: dict[str, list[Service]],
        findings: list[Finding],
    ) -> list[AssetReport]:
        risk_by_host_ip: dict[str, float] = defaultdict(float)
        for finding in findings:
            host = next((host for host in hosts.values() if host.id == finding.host_id), None)
            if host is None:
                continue
            risk = self._calculate_finding_risk(finding, host, self._service_for_finding(finding, services_by_host_id))
            host_ip = str(host.primary_ip)
            risk_by_host_ip[host_ip] = max(risk_by_host_ip[host_ip], risk.score)

        asset_reports: list[AssetReport] = []
        for host_ip, host in sorted(hosts.items(), key=lambda item: item[0]):
            host_services = services_by_host_id.get(str(host.id), [])
            asset_reports.append(
                AssetReport(
                    asset_id=str(host.id),
                    primary_ip=host_ip,
                    hostname=host.hostname,
                    asset_criticality=host.asset_criticality,
                    open_ports=sorted({service.port for service in host_services}),
                    risk_score=round(risk_by_host_ip.get(host_ip, 0.0), 2),
                    services=[
                        f"{service.service_name or service.protocol}:{service.port}/{service.protocol}"
                        for service in sorted(host_services, key=lambda item: item.port)
                    ],
                )
            )

        return sorted(asset_reports, key=lambda asset: asset.risk_score, reverse=True)

    def _build_finding_reports(
        self,
        findings: list[Finding],
        hosts: dict[str, Host],
        services_by_host_id: dict[str, list[Service]],
    ) -> list[FindingReport]:
        reports: list[FindingReport] = []
        for finding in findings:
            host = next((host for host in hosts.values() if host.id == finding.host_id), None)
            if host is None:
                continue

            service = self._service_for_finding(finding, services_by_host_id)
            risk = self._calculate_finding_risk(finding, host, service)
            mitre_mappings = self._mitre_mapper.map_finding(
                self._finding_type(finding.finding_type),
                service.service_name if service else None,
                finding.title,
            )
            mitre_techniques = sorted({mapping.technique_id for mapping in mitre_mappings})

            reports.append(
                FindingReport(
                    title=finding.title,
                    severity=risk.severity.value,
                    cvss_score=finding.cvss_score,
                    epss_probability=finding.epss_probability,
                    composite_risk_score=risk.score,
                    affected_asset=str(host.primary_ip),
                    cve_id=finding.cve_id,
                    mitre_techniques=mitre_techniques,
                    remediation_guidance=self._remediation_guidance(finding, risk.severity.value),
                )
            )

        return sorted(reports, key=lambda report: report.composite_risk_score, reverse=True)

    def _build_attack_path_reports(
        self,
        hosts: dict[str, Host],
        services_by_host_id: dict[str, list[Service]],
    ) -> list[AttackPathReport]:
        relationships: list[GraphRelationship] = []
        service_nodes: dict[str, tuple[str, int]] = {}

        for host_ip, host in hosts.items():
            host_node_id = f"host:{host_ip}"
            host_services = services_by_host_id.get(str(host.id), [])
            for service in host_services:
                if service.exposure != ExposureLevel.external.value:
                    continue

                service_node_id = f"service:{host_ip}:{service.port}:{service.protocol}"
                relationships.append(
                    GraphRelationship(
                        source="internet",
                        target=host_node_id,
                        relationship="EXPOSES",
                        weight=1.0,
                        confidence=0.75,
                    )
                )
                relationships.append(
                    GraphRelationship(
                        source=host_node_id,
                        target=service_node_id,
                        relationship="RUNS",
                        weight=1.0,
                        confidence=0.9,
                    )
                )
                service_nodes[service_node_id] = (host_ip, service.port)

        if not relationships:
            return []

        engine = DefensiveAttackPathEngine(relationships)
        reports: list[AttackPathReport] = []
        seen_targets: set[str] = set()

        for service_node_id, (host_ip, port) in service_nodes.items():
            if service_node_id in seen_targets:
                continue
            seen_targets.add(service_node_id)
            result = engine.lowest_cost_path("internet", service_node_id)
            if result is None:
                continue

            reports.append(
                AttackPathReport(
                    source="internet",
                    target=service_node_id,
                    path=list(result.path),
                    risk_score=max(0.0, 100.0 - result.total_weight * 10.0),
                    confidence=result.confidence,
                    critical_nodes=list(result.critical_nodes),
                    description=f"Externally exposed service on {host_ip}:{port}",
                )
            )

        return reports

    def _build_executive_summary(
        self,
        scan_runs: list[ScanRun],
        asset_reports: list[AssetReport],
        finding_reports: list[FindingReport],
    ) -> ExecutiveSummary:
        severity_counts = Counter(report.severity for report in finding_reports)
        total_hosts_discovered = sum(self._safe_int(scan_run.configuration.get("hosts_discovered")) for scan_run in scan_runs)
        total_open_ports = sum(self._safe_int(scan_run.configuration.get("open_ports")) for scan_run in scan_runs)

        highest_risk_asset = None
        if asset_reports:
            highest_risk_asset = max(asset_reports, key=lambda asset: asset.risk_score).primary_ip

        scan_duration_seconds = 0.0
        for scan_run in scan_runs:
            if scan_run.started_at is None or scan_run.completed_at is None:
                continue
            scan_duration_seconds += (scan_run.completed_at - scan_run.started_at).total_seconds()

        return ExecutiveSummary(
            total_hosts_discovered=total_hosts_discovered,
            total_open_ports=total_open_ports,
            total_findings=len(finding_reports),
            critical_count=severity_counts.get("critical", 0),
            high_count=severity_counts.get("high", 0),
            medium_count=severity_counts.get("medium", 0),
            low_count=severity_counts.get("low", 0),
            highest_risk_asset=highest_risk_asset,
            scan_duration_seconds=round(scan_duration_seconds, 2),
        )

    def _build_mitre_coverage(
        self,
        findings: list[Finding],
        hosts: dict[str, Host],
        services_by_host_id: dict[str, list[Service]],
    ) -> dict[str, list[str]]:
        coverage: dict[str, set[str]] = defaultdict(set)
        for finding in findings:
            host = next((host for host in hosts.values() if host.id == finding.host_id), None)
            if host is None:
                continue

            service = self._service_for_finding(finding, services_by_host_id)
            mappings = self._mitre_mapper.map_finding(
                self._finding_type(finding.finding_type),
                service.service_name if service else None,
                finding.title,
            )
            for mapping in mappings:
                coverage[mapping.tactic].add(mapping.technique_id)
        return {tactic: sorted(techniques) for tactic, techniques in coverage.items()}

    def _build_risk_distribution(self, finding_reports: list[FindingReport]) -> dict[str, int]:
        distribution: Counter[str] = Counter()
        for finding_report in finding_reports:
            distribution[finding_report.severity] += 1
        return dict(sorted(distribution.items()))

    def _calculate_finding_risk(
        self,
        finding: Finding,
        host: Host,
        service: Service | None,
    ) -> CalculatedRiskScore:
        exposure = ExposureLevel.unknown
        if service is not None:
            exposure = ExposureLevel.external if service.exposure == ExposureLevel.external.value else ExposureLevel.internal

        return self._risk_scorer.calculate(
            RiskInputs(
                cvss_score=finding.cvss_score,
                epss_probability=finding.epss_probability,
                exposure=exposure,
                asset_criticality=host.asset_criticality,
            )
        )

    def _service_for_finding(
        self,
        finding: Finding,
        services_by_host_id: dict[str, list[Service]],
    ) -> Service | None:
        if finding.service_id is None:
            return None

        for services in services_by_host_id.values():
            for service in services:
                if service.id == finding.service_id:
                    return service
        return None

    def _finding_type(self, raw_type: str) -> FindingType:
        try:
            return FindingType(raw_type)
        except ValueError:
            return FindingType.informational

    def _remediation_guidance(self, finding: Finding, severity: str) -> str | None:
        if finding.cve_id:
            return f"Review vendor guidance and patch or mitigate {finding.cve_id}."

        if severity in {"critical", "high"}:
            return "Reduce exposure, restrict access, and validate compensating controls."

        if severity in {"medium", "low"}:
            return "Review the exposure and prioritize remediation based on business impact."

        return "Track as informational and validate whether the exposure is expected."

    def _safe_int(self, value: object) -> int:
        try:
            return int(value) if value is not None else 0
        except (TypeError, ValueError):
            return 0
