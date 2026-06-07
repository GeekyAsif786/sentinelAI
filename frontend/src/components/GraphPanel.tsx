import cytoscape, { Core } from "cytoscape";
import { useEffect, useRef, useState } from "react";

import { GraphSliceResponse, fetchGraphSlice } from "../lib/api";

export type GraphLayoutMode = "breadthfirst" | "cose";
export type GraphCommand = "zoom-in" | "zoom-out" | "fit";

interface GraphPanelProps {
  layoutMode: GraphLayoutMode;
  command: { type: GraphCommand; id: number } | null;
}

export function GraphPanel({ layoutMode, command }: GraphPanelProps): JSX.Element {
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
        name: layoutMode,
        directed: layoutMode === "breadthfirst",
        padding: 16
      },
      style: [
        {
          selector: "node",
          style: {
            "background-color": "#22c55e",
            "border-color": "#f7fbf8",
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
          selector: "node[riskScore >= 40]",
          style: {
            "background-color": "#eab308"
          }
        },
        {
          selector: "node[riskScore >= 60]",
          style: {
            "background-color": "#f97316"
          }
        },
        {
          selector: "node[riskScore >= 80]",
          style: {
            "background-color": "#ef4444"
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
  }, [graphSlice, layoutMode]);

  useEffect(() => {
    if (command === null || graphRef.current === null) {
      return;
    }

    const graph = graphRef.current;
    if (command.type === "fit") {
      graph.fit(undefined, 32);
      return;
    }

    const currentZoom = graph.zoom();
    const nextZoom = command.type === "zoom-in" ? currentZoom * 1.2 : currentZoom / 1.2;
    graph.zoom({
      level: Math.max(0.2, Math.min(3, nextZoom)),
      renderedPosition: {
        x: graph.width() / 2,
        y: graph.height() / 2,
      },
    });
  }, [command]);

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
