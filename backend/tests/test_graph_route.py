from app.api.routes.graph import get_graph
from app.api.routes.graph import project_graph


class FakeResult:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return self._rows


class FakeSession:
    def scalars(self, _statement: object) -> FakeResult:
        return FakeResult([])


class FakeAsyncResult:
    id = "task-123"


class FakeTask:
    def delay(self) -> FakeAsyncResult:
        return FakeAsyncResult()


def test_graph_route_returns_empty_uninitialized_projection() -> None:
    response = get_graph(max_depth=3, max_nodes=25, _user=object(), db=FakeSession())

    assert response.nodes == []
    assert response.edges == []
    assert response.freshness_status == "empty"
    assert response.max_depth == 3
    assert response.max_nodes == 25


def test_project_graph_enqueues_job(monkeypatch: object) -> None:
    monkeypatch.setattr("app.api.routes.graph.project_inventory_graph", FakeTask())

    response = project_graph(_user=object())

    assert response.task_id == "task-123"
    assert response.status == "queued"