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


def test_bfs_linear_graph() -> None:
    engine = DefensiveAttackPathEngine([
        GraphRelationship("a", "b", "CONNECTS_TO", weight=1.0, confidence=0.9),
        GraphRelationship("b", "c", "CONNECTS_TO", weight=1.0, confidence=0.8),
        GraphRelationship("c", "d", "CONNECTS_TO", weight=1.0, confidence=0.7),
    ])
    result = engine.shortest_path_bfs("a", "d")
    assert result is not None
    assert result.path == ("a", "b", "c", "d")
    assert result.total_weight == 3.0
    assert result.confidence == 0.7


def test_critical_nodes_ignores_global_hubs() -> None:
    # 'hub' is connected to everything, but the path is ('a', 'b', 'c', 'd')
    engine = DefensiveAttackPathEngine([
        GraphRelationship("a", "b", "CONNECTS_TO", weight=1.0, confidence=0.9),
        GraphRelationship("b", "c", "CONNECTS_TO", weight=1.0, confidence=0.9),
        GraphRelationship("c", "d", "CONNECTS_TO", weight=1.0, confidence=0.9),
        GraphRelationship("hub", "a", "CONNECTS_TO", weight=1.0, confidence=0.9),
        GraphRelationship("hub", "b", "CONNECTS_TO", weight=1.0, confidence=0.9),
        GraphRelationship("hub", "c", "CONNECTS_TO", weight=1.0, confidence=0.9),
        GraphRelationship("hub", "d", "CONNECTS_TO", weight=1.0, confidence=0.9),
    ])
    result = engine.critical_nodes(("a", "b", "c", "d"))
    assert "hub" not in result
    assert result == ("b", "c")


def test_choke_points_in_diamond_graph() -> None:
    # a -> b -> x -> d -> e
    # a -> c -> x -> f -> e
    engine = DefensiveAttackPathEngine([
        GraphRelationship("a", "b", "CONNECTS_TO", weight=1.0, confidence=0.9),
        GraphRelationship("a", "c", "CONNECTS_TO", weight=1.0, confidence=0.9),
        GraphRelationship("b", "x", "CONNECTS_TO", weight=1.0, confidence=0.9),
        GraphRelationship("c", "x", "CONNECTS_TO", weight=1.0, confidence=0.9),
        GraphRelationship("x", "d", "CONNECTS_TO", weight=1.0, confidence=0.9),
        GraphRelationship("x", "f", "CONNECTS_TO", weight=1.0, confidence=0.9),
        GraphRelationship("d", "e", "CONNECTS_TO", weight=1.0, confidence=0.9),
        GraphRelationship("f", "e", "CONNECTS_TO", weight=1.0, confidence=0.9),
    ])
    result = engine.choke_points()
    assert result == ("x",)


