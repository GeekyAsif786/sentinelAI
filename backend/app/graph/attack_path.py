from collections import defaultdict, deque
from dataclasses import dataclass
from heapq import heappop, heappush


@dataclass(frozen=True)
class GraphRelationship:
    source: str
    target: str
    relationship: str
    weight: float
    confidence: float


@dataclass(frozen=True)
class PathResult:
    path: tuple[str, ...]
    total_weight: float
    confidence: float
    critical_nodes: tuple[str, ...]


class DefensiveAttackPathEngine:
    def __init__(self, relationships: list[GraphRelationship]) -> None:
        self._relationships = relationships
        self._adjacency: dict[str, list[GraphRelationship]] = defaultdict(list)
        for relationship in relationships:
            self._adjacency[relationship.source].append(relationship)

    def shortest_path_bfs(self, source: str, target: str) -> PathResult | None:
        if source == target:
            return PathResult(path=(source,), total_weight=0.0, confidence=1.0, critical_nodes=tuple())

        queue: deque[tuple[str, tuple[str, ...], float]] = deque([(source, (source,), 1.0)])
        visited: set[str] = {source}

        while queue:
            node, path, confidence = queue.popleft()
            for relationship in self._adjacency.get(node, []):
                if relationship.target in visited:
                    continue
                next_path = (*path, relationship.target)
                next_confidence = min(confidence, relationship.confidence)
                if relationship.target == target:
                    return PathResult(
                        path=next_path,
                        total_weight=float(len(next_path) - 1),
                        confidence=next_confidence,
                        critical_nodes=self.critical_nodes(next_path),
                    )
                visited.add(relationship.target)
                queue.append((relationship.target, next_path, next_confidence))
        return None

    def bounded_depth_first_search(self, source: str, max_depth: int) -> list[tuple[str, ...]]:
        if max_depth < 0:
            raise ValueError("max_depth must be non-negative")

        paths: list[tuple[str, ...]] = []

        def visit(node: str, path: tuple[str, ...], remaining_depth: int) -> None:
            paths.append(path)
            if remaining_depth == 0:
                return
            for relationship in self._adjacency.get(node, []):
                if relationship.target in path:
                    continue
                visit(relationship.target, (*path, relationship.target), remaining_depth - 1)

        visit(source, (source,), max_depth)
        return paths

    def lowest_cost_path(self, source: str, target: str) -> PathResult | None:
        queue: list[tuple[float, str, tuple[str, ...], float]] = [(0.0, source, (source,), 1.0)]
        best_costs: dict[str, float] = {source: 0.0}

        while queue:
            cost, node, path, confidence = heappop(queue)
            if node == target:
                return PathResult(
                    path=path,
                    total_weight=round(cost, 4),
                    confidence=confidence,
                    critical_nodes=self.critical_nodes(path),
                )

            for relationship in self._adjacency.get(node, []):
                next_cost = cost + relationship.weight
                if next_cost >= best_costs.get(relationship.target, float("inf")):
                    continue
                best_costs[relationship.target] = next_cost
                heappush(
                    queue,
                    (
                        next_cost,
                        relationship.target,
                        (*path, relationship.target),
                        min(confidence, relationship.confidence),
                    ),
                )
        return None

    def critical_nodes(self, path: tuple[str, ...]) -> tuple[str, ...]:
        if len(path) <= 2:
            return tuple()
        edge_counts: dict[str, int] = defaultdict(int)
        for relationship in self._relationships:
            edge_counts[relationship.source] += 1
            edge_counts[relationship.target] += 1
        middle_nodes = path[1:-1]
        return tuple(node for node in middle_nodes if edge_counts[node] >= 3)

    def choke_points(self) -> tuple[str, ...]:
        incoming: dict[str, int] = defaultdict(int)
        outgoing: dict[str, int] = defaultdict(int)
        for relationship in self._relationships:
            outgoing[relationship.source] += 1
            incoming[relationship.target] += 1
        return tuple(
            sorted(
                node
                for node in set(incoming) | set(outgoing)
                if incoming[node] >= 2 and outgoing[node] >= 2
            )
        )

