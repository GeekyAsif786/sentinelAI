import {
  Activity,
  AlertTriangle,
  Bot,
  GitBranch,
  Network,
  Radar,
  ShieldAlert,
} from "lucide-react";
import { useEffect, useState } from "react";

import { ScanModal } from "./ScanModal";
import {
  AssetListResponse,
  HealthResponse,
  VulnerabilityListResponse,
  fetchAssets,
  fetchHealth,
  fetchVulnerabilities,
  fetchAttackPaths,
  AttackPathResponse,
} from "../lib/api";

interface DashboardViewProps {
  onNavigate: (tabId: "scans" | "assets" | "risk" | "attack-paths") => void;
}

export function DashboardView({ onNavigate }: DashboardViewProps): JSX.Element {
  const [scanModalOpen, setScanModalOpen] = useState<boolean>(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [assetData, setAssetData] = useState<AssetListResponse | null>(null);
  const [vulnerabilityData, setVulnerabilityData] = useState<VulnerabilityListResponse | null>(null);
  const [pathsData, setPathsData] = useState<AttackPathResponse | null>(null);

  useEffect(() => {
    let isMounted = true;

    const loadData = async () => {
      try {
        const [h, a, v, p] = await Promise.all([
          fetchHealth(),
          fetchAssets(),
          fetchVulnerabilities(),
          fetchAttackPaths(),
        ]);
        if (isMounted) {
          setHealth(h);
          setAssetData(a);
          setVulnerabilityData(v);
          setPathsData(p);
        }
      } catch (err) {
        console.error("Dashboard data load error:", err);
      }
    };

    loadData();
    const intervalId = setInterval(loadData, 10000);
    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, []);

  const assets = assetData?.assets ?? [];
  const vulnerabilities = vulnerabilityData?.vulnerabilities ?? [];
  const avgRisk = assets.length ? Math.round(assets.reduce((sum, a) => sum + a.risk_score, 0) / assets.length) : 0;
  
  // Sort assets by risk
  const topRiskyAssets = [...assets].sort((a, b) => b.risk_score - a.risk_score).slice(0, 5);

  return (
    <>
      <header className="page-header">
        <div className="page-header-info">
          <h1>Security Overview</h1>
          <p>Real-time threat landscape, active risks, and structural posture.</p>
        </div>
        <div className={`status-pill ${health?.status ?? "degraded"}`}>
          <Activity size={16} />
          <span>{health?.detail ?? "Connecting to platform..."}</span>
        </div>
      </header>

      {/* KPI Cards */}
      <section className="kpi-grid">
        <article className="kpi-card" onClick={() => onNavigate("assets")} style={{cursor: "pointer"}}>
          <Radar className="kpi-icon" />
          <strong className="kpi-value">{assets.length}</strong>
          <span className="kpi-label">Tracked Assets</span>
        </article>
        <article className="kpi-card" onClick={() => onNavigate("risk")} style={{cursor: "pointer"}}>
          <ShieldAlert className="kpi-icon" style={{color: "var(--severity-high)"}} />
          <strong className="kpi-value">{vulnerabilities.length}</strong>
          <span className="kpi-label">Vulnerabilities</span>
        </article>
        <article className="kpi-card" onClick={() => onNavigate("risk")} style={{cursor: "pointer"}}>
          <AlertTriangle className="kpi-icon" style={{color: avgRisk > 70 ? "var(--severity-critical)" : "var(--severity-medium)"}} />
          <strong className="kpi-value">{avgRisk}</strong>
          <span className="kpi-label">Average Risk</span>
        </article>
        <article className="kpi-card" onClick={() => onNavigate("attack-paths")} style={{cursor: "pointer"}}>
          <GitBranch className="kpi-icon" style={{color: "var(--emerald-400)"}} />
          <strong className="kpi-value">{pathsData ? "6" : "0"}</strong>
          <span className="kpi-label">Modeled Paths</span>
        </article>
        <article className="kpi-card" onClick={() => onNavigate("scans")} style={{cursor: "pointer"}}>
          <Activity className="kpi-icon pulse" />
          <strong className="kpi-value">1</strong>
          <span className="kpi-label">Active Scan</span>
        </article>
        <article className="kpi-card">
          <Bot className="kpi-icon" style={{color: "var(--text-muted)"}} />
          <strong className="kpi-value" style={{color: "var(--text-muted)"}}>Off</strong>
          <span className="kpi-label">AI Analyst</span>
        </article>
      </section>

      {/* Main Content Grid */}
      <section className="content-grid">
        
        {/* Top Assets */}
        <div className="panel">
          <div className="panel-header">
            <h2>Critical Assets</h2>
            <button className="btn btn-primary btn-sm" onClick={() => setScanModalOpen(true)}>
              <Radar size={14} /> Queue Scan
            </button>
          </div>
          <div className="panel-body no-pad">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Hostname / IP</th>
                  <th>Exposure</th>
                  <th>Risk</th>
                </tr>
              </thead>
              <tbody>
                {topRiskyAssets.map(asset => (
                  <tr key={asset.id}>
                    <td>
                      <div className="flex-center gap-sm">
                        <span className="cell-primary">{asset.hostname ?? asset.primary_ip}</span>
                      </div>
                      <span className="cell-mono text-muted">{asset.primary_ip}</span>
                    </td>
                    <td>
                      {asset.services.some(s => s.exposure === "external") ? (
                        <span className="badge badge-critical">External</span>
                      ) : (
                        <span className="badge badge-info">Internal</span>
                      )}
                    </td>
                    <td>
                      <span className={`badge ${asset.risk_score >= 80 ? 'badge-critical' : asset.risk_score >= 60 ? 'badge-high' : 'badge-medium'}`}>
                        {asset.risk_score}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Recent Events feed */}
        <div className="panel">
          <div className="panel-header">
            <h2>Recent Events</h2>
            <button className="btn btn-ghost btn-sm" onClick={() => onNavigate("scans")}>View All</button>
          </div>
          <div className="panel-body">
            <div className="timeline">
              <div className="timeline-event">
                <div className="timeline-dot success"></div>
                <div className="timeline-content">
                  <div className="timeline-title">Full inventory scan completed</div>
                  <div className="timeline-desc">Discovered 12 hosts, 38 services in 10.0.0.0/16</div>
                  <div className="timeline-time">2 hours ago</div>
                </div>
              </div>
              <div className="timeline-event">
                <div className="timeline-dot critical"></div>
                <div className="timeline-content">
                  <div className="timeline-title">Critical CVE detected</div>
                  <div className="timeline-desc">CVE-2024-3400 found on api-gateway.corp.local</div>
                  <div className="timeline-time">2 hours ago</div>
                </div>
              </div>
              <div className="timeline-event">
                <div className="timeline-dot warning"></div>
                <div className="timeline-content">
                  <div className="timeline-title">Risk score increased</div>
                  <div className="timeline-desc">dc-primary.corp.local risk increased from 72 to 87</div>
                  <div className="timeline-time">3 hours ago</div>
                </div>
              </div>
              <div className="timeline-event">
                <div className="timeline-dot info"></div>
                <div className="timeline-content">
                  <div className="timeline-title">New host discovered</div>
                  <div className="timeline-desc">dev-workstation-01 first seen on network</div>
                  <div className="timeline-time">4 hours ago</div>
                </div>
              </div>
            </div>
          </div>
        </div>

      </section>

      {scanModalOpen && <ScanModal onClose={() => setScanModalOpen(false)} />}
    </>
  );
}
