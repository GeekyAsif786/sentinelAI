import { X } from "lucide-react";
import { VulnerabilitySummary } from "../lib/api";

interface RiskModalProps {
  vulnerability: VulnerabilitySummary;
  onClose: () => void;
}

export function RiskModal({ vulnerability, onClose }: RiskModalProps): JSX.Element {
  const cvssScore = vulnerability.cvss_score ?? "N/A";
  const epssProbability = vulnerability.epss_probability 
    ? (vulnerability.epss_probability * 100).toFixed(2) + "%" 
    : "N/A";

  return (
    <div className="modal-overlay">
      <div className="modal-content" role="dialog" aria-modal="true" aria-labelledby="risk-modal-title">
        <header className="modal-header">
          <h2 id="risk-modal-title">Risk Details: {vulnerability.title}</h2>
          <button type="button" className="close-btn" onClick={onClose} aria-label="Close modal">
            <X aria-hidden="true" size={20} />
          </button>
        </header>
        
        <div className="modal-body">
          <div className="form-group">
            <label>Severity</label>
            <div className="static-value">{vulnerability.severity.toUpperCase()}</div>
          </div>
          
          <div className="form-group">
            <label>CVSS Score</label>
            <div className="static-value">{cvssScore}</div>
          </div>

          <div className="form-group">
            <label>EPSS Probability (Exploitability)</label>
            <div className="static-value">{epssProbability}</div>
          </div>
          
          <div className="form-group" style={{ gridColumn: "1 / -1" }}>
            <label>Description</label>
            <div className="static-value" style={{ whiteSpace: "pre-wrap", minHeight: "80px" }}>
              {vulnerability.description || "No description provided."}
            </div>
          </div>
        </div>

        <footer className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose}>Close</button>
        </footer>
      </div>
    </div>
  );
}
