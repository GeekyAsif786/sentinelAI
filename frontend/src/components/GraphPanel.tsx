import cytoscape, { Core } from "cytoscape";
import { useEffect, useRef, useState } from "react";

import { GraphSliceResponse, fetchGraphSlice } from "../lib/api";

export function GraphPanel(): JSX.Element {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const graphRef = useRef<Core | null>(null);
  const [graphSlice, setGraphSlice] = useState<GraphSliceResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    fetchGraphSlice()
      .then((response) => {
        if (active) {
          setGraphSlice(response);
        }
      })
      .catch((fetchError: unknown) => {
        if (active) {
          const message = fetchError instanceof Error ? fetchError.message : "Failed to load graph";
          setError(message);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (containerRef.current === null) {
      return undefined;
    }

    graphRef.current?.destroy();

    if (graphSlice === null || graphSlice.nodes.length === 0) {
      graphRef.current = null;
      return undefined;
    }

    const graph: Core = cytoscape({
      container: containerRef.current,
      elements: [
        ...graphSlice.nodes.map((node) => ({
          data: {
            id: node.id,
            label: node.label,
            kind: node.kind,
            riskScore: node.risk_score
          }
        })),
        ...graphSlice.edges.map((edge) => ({
          data: {
            id: edge.id,
            source: edge.source,
            target: edge.target,
            label: edge.relationship,
            confidence: edge.confidence,
            weight: edge.weight
          }
        }))
      ],
      layout: {
        name: "breadthfirst",
        directed: true,
        padding: 16
      },
      style: [
        {
          selector: "node",
          style: {
            "background-color": "#146c5f",
            "border-color": "#f0b429",
            "border-width": 2,
            color: "#13201d",
            "font-size": 12,
            label: "data(label)",
            "text-background-color": "#f7fbf8",
            "text-background-opacity": 0.92,
            "text-background-padding": "3",
            "text-margin-y": -10,
            width: "mapData(riskScore, 0, 100, 34, 62)",
            height: "mapData(riskScore, 0, 100, 34, 62)"
          }
        },
        {
          selector: "edge",
          style: {
            "curve-style": "bezier",
            "target-arrow-shape": "triangle",
            "line-color": "#5f6f73",
            "target-arrow-color": "#5f6f73",
            label: "data(label)",
            "font-size": 9,
            "text-background-color": "#ffffff",
            "text-background-opacity": 0.86,
            "text-background-padding": "2"
          }
        }
      ]
    });

    graphRef.current = graph;

    return () => {
      graph.destroy();
      graphRef.current = null;
    };
  }, [graphSlice]);

  if (error !== null) {
    return (
      <div className="graph-panel graph-panel-empty" aria-label="Network graph visualization">
        <strong>Graph unavailable</strong>
        <span>{error}</span>
      </div>
    );
  }

  if (graphSlice === null || graphSlice.nodes.length === 0) {
    return (
      <div className="graph-panel graph-panel-empty" aria-label="Network graph visualization">
        <strong>Graph not projected yet</strong>
        <span>Neo4j projection is empty until a scan populates the topology.</span>
      </div>
    );
  }

  return <div className="graph-panel" ref={containerRef} aria-label="Network graph visualization" />;
}

