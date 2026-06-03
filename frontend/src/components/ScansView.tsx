import { Play, Radar, RefreshCw, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { mockScans, ScanRecord } from "../lib/mockData";
import { ScanModal } from "./ScanModal";

export function ScansView(): JSX.Element {
  const [scans, setScans] = useState<ScanRecord[]>([]);
  const [scanModalOpen, setScanModalOpen] = useState(false);

  useEffect(() => {
    // In a real app this would call an API like fetchScans()
    setScans(mockScans);
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed": return <div className="scan-card-icon completed"><Radar size={20} /></div>;
      case "running": return <div className="scan-card-icon running"><RefreshCw size={20} className="spin" /></div>;
      case "failed": return <div className="scan-card-icon failed"><XCircle size={20} /></div>;
      case "queued": return <div className="scan-card-icon queued"><Play size={20} /></div>;
      case "partial": return <div className="scan-card-icon partial"><AlertTriangle size={20} /></div>;
      default: return <div className="scan-card-icon cancelled"><XCircle size={20} /></div>;
    }
  };

  const formatTarget = (targets: string[]) => {
    if (targets.length === 1) return targets[0];
    return `${targets[0]} (+${targets.length - 1} more)`;
  };

  return (
    <>
      <header className="page-header">
        <div className="page-header-info">
          <h1>Scan Operations & Timeline</h1>
          <p>Scan history, active discoveries, and background job status.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setScanModalOpen(true)}>
          <Radar size={16} /> New Scan
        </button>
      </header>

      <div className="panel">
        <div className="panel-body no-pad">
          <div style={{ display: "flex", flexDirection: "column" }}>
            {scans.map(scan => (
              <div className="scan-card" key={scan.id}>
                {getStatusIcon(scan.status)}
                
                <div className="scan-card-info">
                  <div className="scan-card-title">
                    {scan.scan_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </div>
                  <div className="scan-card-meta">
                    Target: <span className="text-cyan">{formatTarget(scan.targets)}</span> • 
                    Started: {new Date(scan.started_at).toLocaleString()} • 
                    By: {scan.requested_by}
                  </div>
                  <div style={{ marginTop: "6px" }}>
                    <span className={`badge badge-${scan.status}`}>{scan.status.toUpperCase()}</span>
                    <span className="badge badge-info" style={{ marginLeft: "6px", background: "transparent", border: "1px solid var(--border-subtle)", color: "var(--text-muted)" }}>
                      {scan.provider.toUpperCase()}
                    </span>
                  </div>
                </div>

                <div className="scan-card-stats">
                  <div className="scan-stat">
                    <span className="scan-stat-value">{scan.hosts_discovered}</span>
                    <span className="scan-stat-label">Hosts</span>
                  </div>
                  <div className="scan-stat">
                    <span className="scan-stat-value">{scan.services_found}</span>
                    <span className="scan-stat-label">Services</span>
                  </div>
                  <div className="scan-stat">
                    <span className="scan-stat-value" style={{ color: scan.vulnerabilities_found > 0 ? "var(--severity-high)" : "inherit" }}>
                      {scan.vulnerabilities_found}
                    </span>
                    <span className="scan-stat-label">Vulns</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {scanModalOpen && <ScanModal onClose={() => setScanModalOpen(false)} />}
    </>
  );
}

// Ensure AlertTriangle is imported for the partial state icon
import { AlertTriangle } from "lucide-react";
