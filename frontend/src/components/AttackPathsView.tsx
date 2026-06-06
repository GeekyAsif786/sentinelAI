import { GitBranch, ShieldAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { mockAttackPaths, AttackPath } from "../lib/mockData";
import { fetchAttackPaths } from "../lib/api";

export function AttackPathsView(): JSX.Element {
  const [paths, setPaths] = useState<AttackPath[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    // Try to load real attack-paths from the backend; fall back to mock data.
    (async () => {
      try {
        const resp = await fetchAttackPaths();
        if (!active) return;

        // Backend returns a single path response. Map it to the UI's AttackPath shape.
        if (resp.path && resp.path.length > 0) {
          const mapped: AttackPath = {
            id: String(Date.now()),
            name: `Modeled Path`,
            source: "",
            target: "",
            path: resp.path,
            risk_score: Math.round(resp.risk_score),
            confidence: resp.confidence,
            critical_nodes: resp.critical_nodes,
            mitre_techniques: [],
            description: resp.message || "",
            recommendations: [],
          };
          setPaths([mapped]);
        } else {
          // Empty or no path — use mock list so UX is helpful during demos.
          setPaths(mockAttackPaths.sort((a, b) => b.risk_score - a.risk_score));
        }
      } catch {
        if (!active) return;
        setPaths(mockAttackPaths.sort((a, b) => b.risk_score - a.risk_score));
      }
    })();

    return () => {
      active = false;
    };
  }, []);

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  const getRiskColor = (score: number) => {
    if (score >= 80) return "var(--severity-critical)";
    if (score >= 60) return "var(--severity-high)";
    if (score >= 40) return "var(--severity-medium)";
    return "var(--severity-low)";
  };

  return (
    <>
      <header className="page-header">
        <div className="page-header-info">
          <h1>Modeled Attack Paths</h1>
          <p>Simulated chains an attacker could exploit to reach critical assets.</p>
        </div>
      </header>

      <div className="content-grid" style={{ gridTemplateColumns: "1fr" }}>
        {paths.map(path => (
          <div 
            className={`attack-path-card ${expandedId === path.id ? "expanded" : ""}`}
            key={path.id}
            onClick={() => toggleExpand(path.id)}
          >
            <div className="attack-path-header">
              <div>
                <div className="attack-path-title">{path.name}</div>
                <div className="attack-path-subtitle">
                  Confidence: {Math.round(path.confidence * 100)}% • Path Length: {path.path.length} hops
                </div>
              </div>
              <div 
                className={`risk-score-circle ${
                  path.risk_score >= 80 ? 'risk-critical' : 
                  path.risk_score >= 60 ? 'risk-high' : 
                  path.risk_score >= 40 ? 'risk-medium' : 'risk-low'
                }`}
              >
                {path.risk_score}
              </div>
            </div>

            <div className="attack-path-chain">
              {path.path.map((node, i) => (
                <React.Fragment key={`${node}-${i}`}>
                  <div className={`attack-path-node ${path.critical_nodes.includes(node) ? 'critical' : ''}`}>
                    {node}
                  </div>
                  {i < path.path.length - 1 && (
                    <div className="attack-path-arrow">→</div>
                  )}
                </React.Fragment>
              ))}
            </div>

            <div className="attack-path-tags">
              {path.mitre_techniques.map(tech => (
                <span className="mitre-tag" key={tech.id} title={tech.tactic}>
                  {tech.id}: {tech.name}
                </span>
              ))}
            </div>

            {expandedId === path.id && (
              <div className="attack-path-details" onClick={e => e.stopPropagation()}>
                <p className="attack-path-desc">{path.description}</p>
                <div style={{ marginTop: "16px" }}>
                  <h4 style={{ fontSize: "12px", color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "8px" }}>
                    Remediation Recommendations
                  </h4>
                  <ul className="attack-path-recs">
                    {path.recommendations.map((rec, i) => (
                      <li key={i}>{rec}</li>
                    ))}
                  </ul>
                </div>
                <div style={{ marginTop: "20px", display: "flex", gap: "10px" }}>
                  <button className="btn btn-secondary btn-sm">
                    <ShieldAlert size={14} /> Send to SIEM
                  </button>
                  <button className="btn btn-secondary btn-sm">
                    <GitBranch size={14} /> View in Graph
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}

        {paths.length === 0 && (
          <div className="empty-state panel">
            <GitBranch size={48} />
            <h3>No attack paths modeled</h3>
            <p>Run a network scan to build the topology and generate potential attack paths.</p>
          </div>
        )}
      </div>
    </>
  );
}

import React from 'react';
