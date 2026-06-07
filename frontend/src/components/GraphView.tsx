import { Layout, Maximize, ZoomIn, ZoomOut, Network } from "lucide-react";
import { useState } from "react";
import { GraphCommand, GraphLayoutMode, GraphPanel } from "./GraphPanel";

export function GraphView(): JSX.Element {
  const [layoutMode, setLayoutMode] = useState<GraphLayoutMode>("breadthfirst");
  const [command, setCommand] = useState<{ type: GraphCommand; id: number } | null>(null);

  function sendCommand(type: GraphCommand): void {
    setCommand({ type, id: Date.now() });
  }

  return (
    <>
      <header className="page-header">
        <div className="page-header-info">
          <h1>Network Topology</h1>
          <p>Visual exploration of asset relationships, exposures, and trust paths.</p>
        </div>
        <div className="toolbar">
          <div className="toolbar-group">
            <button className="btn-ghost" title="Zoom In" onClick={() => sendCommand("zoom-in")}><ZoomIn size={16} /></button>
            <button className="btn-ghost" title="Zoom Out" onClick={() => sendCommand("zoom-out")}><ZoomOut size={16} /></button>
            <button className="btn-ghost" title="Fit to Screen" onClick={() => sendCommand("fit")}><Maximize size={16} /></button>
          </div>
          <div className="toolbar-group">
            <button
              className={`btn-ghost${layoutMode === "breadthfirst" ? " active" : ""}`}
              title="Breadth-first Layout"
              onClick={() => setLayoutMode("breadthfirst")}
            >
              <Layout size={16} />
            </button>
            <button
              className={`btn-ghost${layoutMode === "cose" ? " active" : ""}`}
              title="Force-directed Layout"
              onClick={() => setLayoutMode("cose")}
            >
              <Network size={16} />
            </button>
          </div>
        </div>
      </header>

      <div className="graph-container">
        <GraphPanel layoutMode={layoutMode} command={command} />
        <div className="graph-legend">
          <div className="graph-legend-item">
            <div className="graph-legend-dot" style={{ background: "var(--severity-critical)" }}></div>
            <span>Critical Risk (80-100)</span>
          </div>
          <div className="graph-legend-item">
            <div className="graph-legend-dot" style={{ background: "var(--severity-high)" }}></div>
            <span>High Risk (60-79)</span>
          </div>
          <div className="graph-legend-item">
            <div className="graph-legend-dot" style={{ background: "var(--severity-medium)" }}></div>
            <span>Medium Risk (40-59)</span>
          </div>
          <div className="graph-legend-item">
            <div className="graph-legend-dot" style={{ background: "var(--severity-low)" }}></div>
            <span>Low Risk (0-39)</span>
          </div>
          <div style={{ borderTop: "1px solid var(--border-subtle)", margin: "4px 0" }}></div>
          <div className="graph-legend-item">
            <svg width="24" height="4" viewBox="0 0 24 4" style={{ flexShrink: 0 }}>
              <path d="M0,2 L20,2" stroke="var(--text-muted)" strokeWidth="1.5" />
              <polygon points="20,0 24,2 20,4" fill="var(--text-muted)" />
            </svg>
            <span>Relationship</span>
          </div>
        </div>
      </div>
    </>
  );
}
