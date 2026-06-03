# Attack Path Engine

The attack-path engine models defensive paths through exposure, trust, and vulnerability relationships. It never executes attacks or generates offensive instructions.

## Algorithms

- BFS: shortest unweighted path.
- DFS: bounded exploration.
- Dijkstra-style traversal: lowest-cost path.
- Choke point detection: nodes with multiple inbound and outbound relationships.
- Critical node detection: high-connectivity nodes inside a path.

## Output

```json
{
  "path": ["host:a", "service:b", "host:c"],
  "risk_score": 87,
  "critical_nodes": ["service:b"],
  "confidence": 0.72
}
```

## Failure Handling

- Empty graphs return no path.
- Disconnected graphs return no path.
- Cycles are bounded and do not cause infinite traversal.
- Stale graph projections must be visible to callers.
- Low-confidence relationships must be visible in path output.

