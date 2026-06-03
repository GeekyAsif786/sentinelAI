import { Bot, ChevronDown, ChevronRight, Info } from "lucide-react";
import { useEffect, useState } from "react";
import { mockAIAnalyses, AIAnalysis } from "../lib/mockData";

export function AIAnalystView(): JSX.Element {
  const [analyses, setAnalyses] = useState<AIAnalysis[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    // In a real app we'd fetch this from the backend or generate on demand
    setAnalyses(mockAIAnalyses);
  }, []);

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  const getSubjectBadge = (type: string) => {
    switch (type) {
      case "finding": return <span className="badge badge-high">Finding</span>;
      case "attack_path": return <span className="badge badge-critical">Attack Path</span>;
      case "risk_score": return <span className="badge badge-medium">Risk Score</span>;
      case "asset": return <span className="badge badge-info">Asset</span>;
      default: return <span className="badge badge-info">{type}</span>;
    }
  };

  return (
    <>
      <header className="page-header">
        <div className="page-header-info">
          <h1>AI Security Analyst</h1>
          <p>Automated explanations and remediation guidance for complex security context.</p>
        </div>
      </header>

      <div className="ai-disclaimer">
        <Info size={20} />
        <div>
          <strong>AI features are currently operating in deterministic fallback mode.</strong> Connect an OpenAI-compatible endpoint or Ollama instance in the backend configuration to enable generative analysis.
        </div>
      </div>

      <div className="content-grid" style={{ gridTemplateColumns: "1fr" }}>
        {analyses.map(analysis => (
          <div 
            className={`ai-analysis-card ${expandedId === analysis.id ? "expanded" : ""}`}
            key={analysis.id}
          >
            <div 
              className="ai-analysis-header" 
              onClick={() => toggleExpand(analysis.id)}
              style={{ cursor: "pointer" }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <button className="btn-ghost" style={{ padding: "4px" }}>
                  {expandedId === analysis.id ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                </button>
                <Bot size={20} style={{ color: "var(--cyan-500)" }} />
                <div>
                  <div className="ai-analysis-title">{analysis.subject_label}</div>
                  <div className="ai-analysis-meta" style={{ marginTop: "4px" }}>
                    {getSubjectBadge(analysis.subject_type)}
                    <span style={{ marginLeft: "8px" }}>Generated: {new Date(analysis.created_at).toLocaleString()}</span>
                  </div>
                </div>
              </div>
              <div className="ai-analysis-meta" style={{ textAlign: "right" }}>
                <div>Model: <span className="text-cyan">{analysis.model}</span></div>
                <div>Provider: {analysis.provider}</div>
              </div>
            </div>

            {expandedId === analysis.id && (
              <div className="ai-analysis-body">
                <div className="ai-analysis-text">
                  {analysis.generated_text}
                </div>
                
                <div className="ai-evidence-grid">
                  {Object.entries(analysis.source_evidence).map(([key, value]) => (
                    <div className="ai-evidence-item" key={key}>
                      <span className="ai-evidence-key">{key.replace(/_/g, " ")}</span>
                      <span className="ai-evidence-value">{String(value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}

        {analyses.length === 0 && (
          <div className="empty-state panel">
            <Bot size={48} />
            <h3>No analyses generated</h3>
            <p>Request AI analysis from any asset, vulnerability, or attack path detail view.</p>
          </div>
        )}
      </div>
    </>
  );
}
