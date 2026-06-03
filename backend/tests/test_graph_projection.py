from types import SimpleNamespace

from app.graph.projection import InventoryGraphProjection


def test_build_slice_projects_hosts_and_services() -> None:
    host = SimpleNamespace(
        primary_ip="10.0.0.10",
        hostname="fileserver.local",
        asset_criticality=4,
        services=[
            SimpleNamespace(port=445, protocol="tcp", service_name="smb", exposure="internal"),
            SimpleNamespace(port=22, protocol="tcp", service_name="ssh", exposure="external"),
        ],
    )

    projection = InventoryGraphProjection()
    response = projection.build_slice([host], max_nodes=10, max_depth=2)

    assert response.freshness_status == "inventory_projected"
    assert [node.kind for node in response.nodes] == ["Host", "Service", "Service"]
    assert response.edges[0].relationship == "RUNS"
    assert response.nodes[0].id == "host:10.0.0.10"


def test_build_slice_marks_partial_when_bounded() -> None:
    host = SimpleNamespace(
        primary_ip="10.0.0.10",
        hostname="fileserver.local",
        asset_criticality=4,
        services=[
            SimpleNamespace(port=445, protocol="tcp", service_name="smb", exposure="internal"),
            SimpleNamespace(port=22, protocol="tcp", service_name="ssh", exposure="external"),
        ],
    )

    projection = InventoryGraphProjection()
    response = projection.build_slice([host], max_nodes=2, max_depth=2)

    assert response.freshness_status == "partial"
    assert len(response.nodes) == 2