from app.graph.attack_path import DefensiveAttackPathEngine, GraphRelationship


def test_bfs_returns_no_path_for_disconnected_graph() -> None:
    engine = DefensiveAttackPathEngine(
        [GraphRelationship("a", "b", "CONNECTS_TO", weight=1.0, confidence=0.9)]
    )

    assert engine.shortest_path_bfs("a", "z") is None


def test_lowest_cost_path_chooses_lower_weight_route() -> None:
    engine = DefensiveAttackPathEngine(
        [
            GraphRelationship("a", "b", "CONNECTS_TO", weight=10.0, confidence=0.9),
            GraphRelationship("a", "c", "CONNECTS_TO", weight=1.0, confidence=0.8),
            GraphRelationship("c", "b", "CONNECTS_TO", weight=1.0, confidence=0.7),
        ]
    )

    result = engine.lowest_cost_path("a", "b")

    assert result is not None
    assert result.path == ("a", "c", "b")
    assert result.total_weight == 2.0
    assert result.confidence == 0.7


def test_depth_first_search_does_not_loop_on_cycles() -> None:
    engine = DefensiveAttackPathEngine(
        [
            GraphRelationship("a", "b", "CONNECTS_TO", weight=1.0, confidence=0.9),
            GraphRelationship("b", "a", "CONNECTS_TO", weight=1.0, confidence=0.9),
        ]
    )

    paths = engine.bounded_depth_first_search("a", max_depth=3)

    assert paths == [("a",), ("a", "b")]

