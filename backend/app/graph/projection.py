from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from neo4j import GraphDatabase

from app.core.config import get_settings
from app.models import Host
from app.schemas.graph import GraphEdge, GraphNode, GraphSliceResponse
from app.services.risk import CompositeRiskScore, ExposureLevel, RiskInputs


@dataclass(frozen=True)
class ProjectedGraphRecord:
    host_id: str
    service_id: str
    host_node_id: str
    service_node_id: str
    service_protocol: str


class InventoryGraphProjection:
    def __init__(self) -> None:
        self._risk_scorer = CompositeRiskScore()

    def build_slice(self, hosts: Sequence[Host], max_nodes: int, max_depth: int) -> GraphSliceResponse:
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []

        if max_nodes <= 0:
            return GraphSliceResponse(
                nodes=nodes,
                edges=edges,
                freshness_status="empty",
                max_depth=max_depth,
                max_nodes=max_nodes,
            )

        for host in hosts:
            host_node_id = f"host:{host.primary_ip}"
            host_risk = self._host_risk(host)
            if self._append_node(nodes, host_node_id, host.hostname or str(host.primary_ip), "Host", host_risk, max_nodes):
                break

            for service in sorted(host.services, key=lambda service: service.port):
                service_node_id = f"service:{host.primary_ip}:{service.port}:{service.protocol}"
                service_label = f"{service.service_name or service.protocol} {service.port}/{service.protocol}"
                service_risk = self._service_risk(host_risk, service.exposure)
                if self._append_node(nodes, service_node_id, service_label, "Service", service_risk, max_nodes):
                    return self._response(nodes, edges, max_depth, max_nodes, "partial")

                edges.append(
                    GraphEdge(
                        id=f"runs:{host.primary_ip}:{service.port}:{service.protocol}",
                        source=host_node_id,
                        target=service_node_id,
                        relationship="RUNS",
                        confidence=0.95 if service.exposure == ExposureLevel.external.value else 0.9,
                        weight=1.0,
                    )
                )

        freshness_status = "empty" if not nodes else "inventory_projected"
        return self._response(nodes, edges, max_depth, max_nodes, freshness_status)

    def project_to_neo4j(self, hosts: Sequence[Host]) -> bool:
        settings = get_settings()
        try:
            driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_username, settings.neo4j_password),
            )
        except Exception:
            return False

        records = self._project_records(hosts)
        if not records:
            driver.close()
            return True

        try:
            with driver.session() as session:
                for record in records:
                    session.run(
                        """
                        MERGE (host:Host {id: $host_node_id})
                        SET host.primary_ip = $primary_ip,
                            host.label = $host_label,
                            host.kind = 'Host'
                        MERGE (service:Service {id: $service_node_id})
                        SET service.label = $service_label,
                            service.kind = 'Service',
                            service.port = $service_port,
                            service.protocol = $service_protocol
                        MERGE (host)-[:RUNS]->(service)
                        """,
                        host_node_id=record.host_node_id,
                        primary_ip=record.host_id,
                        host_label=record.host_id,
                        service_node_id=record.service_node_id,
                        service_label=record.service_node_id,
                        service_port=record.service_id,
                        service_protocol=record.service_protocol,
                    )
        except Exception:
            driver.close()
            return False

        driver.close()
        return True

    def _project_records(self, hosts: Sequence[Host]) -> list[ProjectedGraphRecord]:
        records: list[ProjectedGraphRecord] = []
        for host in hosts:
            host_node_id = f"host:{host.primary_ip}"
            for service in host.services:
                records.append(
                    ProjectedGraphRecord(
                        host_id=str(host.primary_ip),
                        service_id=f"{service.port}/{service.protocol}",
                        host_node_id=host_node_id,
                        service_node_id=f"service:{host.primary_ip}:{service.port}:{service.protocol}",
                        service_protocol=service.protocol,
                    )
                )
        return records

    def _response(
        self,
        nodes: list[GraphNode],
        edges: list[GraphEdge],
        max_depth: int,
        max_nodes: int,
        freshness_status: str,
    ) -> GraphSliceResponse:
        return GraphSliceResponse(
            nodes=nodes,
            edges=edges,
            freshness_status=freshness_status,
            max_depth=max_depth,
            max_nodes=max_nodes,
        )

    def _append_node(
        self,
        nodes: list[GraphNode],
        node_id: str,
        label: str,
        kind: str,
        risk_score: float,
        max_nodes: int,
    ) -> bool:
        if len(nodes) >= max_nodes:
            return True
        nodes.append(
            GraphNode(
                id=node_id,
                label=label,
                kind=kind,
                risk_score=round(min(max(risk_score, 0.0), 100.0), 2),
            )
        )
        return False

    def _host_risk(self, host: Host) -> float:
        exposure = ExposureLevel.external if any(
            service.exposure == ExposureLevel.external.value for service in host.services
        ) else ExposureLevel.internal if host.services else ExposureLevel.unknown
        score = self._risk_scorer.calculate(
            RiskInputs(
                cvss_score=None,
                epss_probability=None,
                exposure=exposure,
                asset_criticality=host.asset_criticality,
            )
        )
        return score.score

    def _service_risk(self, host_risk: float, exposure: str) -> float:
        bonus = 6.0 if exposure == ExposureLevel.external.value else 2.5 if exposure == ExposureLevel.internal.value else 0.0
        return min(100.0, host_risk + bonus)