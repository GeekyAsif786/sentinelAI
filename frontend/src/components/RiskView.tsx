import { Activity, AlertTriangle, ShieldAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { VulnerabilitySummary, fetchVulnerabilities } from "../lib/api";
import { RiskModal } from "./RiskModal";

export function RiskView(): JSX.Element {
  const [vulnerabilities, setVulnerabilities] = useState<VulnerabilitySummary[]>([]);
  const [selectedRisk, setSelectedRisk] = useState<VulnerabilitySummary | null>(null);

  useEffect(() => {
    let isMounted = true;
    fetchVulnerabilities()
      .then(res => {
        if (isMounted) setVulnerabilities(res.vulnerabilities);
      })
      .catch(err => console.error("Error loading vulnerabilities:", err));
    return () => { isMounted = false; };
  }, []);

  const getSeverityCount = (sev: string) => vulnerabilities.filter(v => v.severity.toLowerCase() === sev).length;
  const total = vulnerabilities.length || 1; // avoid div by 0

  return (
    <>
      <header className="page-header">
        <div className="page-header-info">
          <h1>Risk Assessment</h1>
          <p>Composite risk scoring, vulnerability severity, and exposure analysis.</p>
        </div>
      </header>

      <div className="content-grid">
        {/* Risk Distribution */}
        <div className="panel">
          <div className="panel-header">
            <h2>Vulnerability Distribution</h2>
            <span className="panel-header-badge">By Severity</span>
          </div>
          <div className="panel-body">
            <div className="risk-bar-chart">
              {[
                { label: "Critical", count: getSeverityCount("critical"), color: "var(--severity-critical)" },
                { label: "High", count: getSeverityCount("high"), color: "var(--severity-high)" },
                { label: "Medium", count: getSeverityCount("medium"), color: "var(--severity-medium)" },
                { label: "Low", count: getSeverityCount("low"), color: "var(--severity-low)" },
              ].map(sev => (
                <div className="risk-bar-row" key={sev.label}>
                  <div className="risk-bar-label">{sev.label}</div>
                  <div className="risk-bar-track">
                    <div 
                      className="risk-bar-fill" 
                      style={{ width: `${Math.max(5, (sev.count / total) * 100)}%`, background: sev.color }}
                    ></div>
                  </div>
                  <div className="risk-bar-count">{sev.count}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Risk Matrix */}
        <div className="panel">
          <div className="panel-header">
            <h2>Risk Matrix</h2>
            <span className="panel-header-badge">Likelihood × Impact</span>
          </div>
          <div className="panel-body">
            <div className="risk-matrix">
              {/* Empty corner */}
              <div></div>
              {/* X Axis labels */}
              <div className="risk-matrix-label">Low</div>
              <div className="risk-matrix-label">Med</div>
              <div className="risk-matrix-label">High</div>
              <div className="risk-matrix-label">V.High</div>
              <div className="risk-matrix-label">Crit</div>

              {/* Y Axis: Critical Impact */}
              <div className="risk-matrix-label" style={{ writingMode: "vertical-rl", transform: "rotate(180deg)" }}>Critical</div>
              <div className="risk-matrix-cell" style={{ background: "rgba(234,179,8,0.15)", color: "var(--severity-medium)" }}></div>
              <div className="risk-matrix-cell" style={{ background: "rgba(249,115,22,0.15)", color: "var(--severity-high)" }}></div>
              <div className="risk-matrix-cell" style={{ background: "rgba(239,68,68,0.15)", color: "var(--severity-critical)" }}>2</div>
              <div className="risk-matrix-cell" style={{ background: "rgba(239,68,68,0.4)", color: "white" }}>5</div>
              <div className="risk-matrix-cell" style={{ background: "rgba(239,68,68,0.7)", color: "white" }}>3</div>

              {/* Y Axis: High Impact */}
              <div className="risk-matrix-label" style={{ writingMode: "vertical-rl", transform: "rotate(180deg)" }}>High</div>
              <div className="risk-matrix-cell" style={{ background: "rgba(34,197,94,0.15)", color: "var(--severity-low)" }}></div>
              <div className="risk-matrix-cell" style={{ background: "rgba(234,179,8,0.15)", color: "var(--severity-medium)" }}>1</div>
              <div className="risk-matrix-cell" style={{ background: "rgba(249,115,22,0.15)", color: "var(--severity-high)" }}>4</div>
              <div className="risk-matrix-cell" style={{ background: "rgba(239,68,68,0.15)", color: "var(--severity-critical)" }}>1</div>
              <div className="risk-matrix-cell" style={{ background: "rgba(239,68,68,0.4)", color: "white" }}></div>

              {/* Y Axis: Medium Impact */}
              <div className="risk-matrix-label" style={{ writingMode: "vertical-rl", transform: "rotate(180deg)" }}>Medium</div>
              <div className="risk-matrix-cell" style={{ background: "rgba(34,197,94,0.15)", color: "var(--severity-low)" }}></div>
              <div className="risk-matrix-cell" style={{ background: "rgba(34,197,94,0.15)", color: "var(--severity-low)" }}></div>
              <div className="risk-matrix-cell" style={{ background: "rgba(234,179,8,0.15)", color: "var(--severity-medium)" }}></div>
              <div className="risk-matrix-cell" style={{ background: "rgba(249,115,22,0.15)", color: "var(--severity-high)" }}></div>
              <div className="risk-matrix-cell" style={{ background: "rgba(239,68,68,0.15)", color: "var(--severity-critical)" }}></div>
            </div>
            <div style={{ textAlign: "center", fontSize: "10px", color: "var(--text-muted)", marginTop: "8px", textTransform: "uppercase", letterSpacing: "0.04em" }}>
              Likelihood (EPSS / Exposure)
            </div>
          </div>
        </div>

        {/* Top Vulnerabilities Table */}
        <div className="panel span-full">
          <div className="panel-header">
            <h2>Top Vulnerabilities</h2>
          </div>
          <div className="panel-body no-pad">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Vulnerability</th>
                  <th>CVE ID</th>
                  <th>Severity</th>
                  <th>CVSS Score</th>
                  <th>EPSS Probability</th>
                </tr>
              </thead>
              <tbody>
                {vulnerabilities.length === 0 ? (
                  <tr>
                    <td colSpan={5}>
                      <div className="empty-state">
                        <ShieldAlert size={32} />
                        <p>No vulnerabilities identified.</p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  vulnerabilities.slice(0, 10).map((vuln) => (
                    <tr 
                      key={vuln.id} 
                      onClick={() => setSelectedRisk(vuln)}
                      style={{ cursor: "pointer" }}
                    >
                      <td className="cell-primary">{vuln.title}</td>
                      <td className="cell-mono text-cyan">{vuln.cve_id || "N/A"}</td>
                      <td>
                        <span className={`badge badge-${vuln.severity.toLowerCase()}`}>
                          {vuln.severity.toUpperCase()}
                        </span>
                      </td>
                      <td className="cell-mono">
                        {vuln.cvss_score !== null ? vuln.cvss_score.toFixed(1) : "N/A"}
                      </td>
                      <td className="cell-mono">
                        {vuln.epss_probability !== null ? `${(vuln.epss_probability * 100).toFixed(1)}%` : "N/A"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {selectedRisk && <RiskModal vulnerability={selectedRisk} onClose={() => setSelectedRisk(null)} />}
    </>
  );
}
