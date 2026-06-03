import {
  Activity,
  AlertTriangle,
  Bot,
  Database,
  GitBranch,
  Network,
  Radar,
  ShieldCheck
} from "lucide-react";
import { useEffect, useState } from "react";

import { GraphPanel } from "./components/GraphPanel";
import {
  AssetListResponse,
  HealthResponse,
  VulnerabilityListResponse,
  fetchAssets,
  fetchHealth,
  fetchVulnerabilities
} from "./lib/api";

function App(): JSX.Element {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [assetData, setAssetData] = useState<AssetListResponse | null>(null);
  const [vulnerabilityData, setVulnerabilityData] = useState<VulnerabilityListResponse | null>(null);
  const [inventoryError, setInventoryError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    fetchHealth()
      .then((response) => {
        if (isMounted) {
          setHealth(response);
        }
      })
      .catch((error: unknown) => {
        if (isMounted) {
          const message = error instanceof Error ? error.message : "Unknown health check failure";
          setHealthError(message);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    let isMounted = true;

    Promise.all([fetchAssets(), fetchVulnerabilities()])
      .then(([assetsResponse, vulnerabilitiesResponse]) => {
        if (isMounted) {
          setAssetData(assetsResponse);
          setVulnerabilityData(vulnerabilitiesResponse);
        }
      })
      .catch((error: unknown) => {
        if (isMounted) {
          const message = error instanceof Error ? error.message : "Unknown inventory load failure";
          setInventoryError(message);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const assets = assetData?.assets ?? [];
  const risks = (vulnerabilityData?.vulnerabilities ?? []).map((vulnerability) => ({
    title: vulnerability.title,
    tactic: vulnerability.severity,
    score:
      vulnerability.cvss_score !== null
        ? Math.round(vulnerability.cvss_score * 10)
        : vulnerability.epss_probability !== null
          ? Math.round(vulnerability.epss_probability * 100)
          : 0
  }));

  const averageRisk = assets.length === 0 ? 0 : Math.round(assets.reduce((sum, asset) => sum + asset.risk_score, 0) / assets.length);

  return (
    <main className="workspace">
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand">
          <ShieldCheck aria-hidden="true" />
          <span>AI Network Mapper</span>
        </div>
        <nav className="nav-stack">
          <button className="nav-button active" type="button" title="Assets">
            <Database aria-hidden="true" />
          </button>
          <button className="nav-button" type="button" title="Graph">
            <Network aria-hidden="true" />
          </button>
          <button className="nav-button" type="button" title="Attack paths">
            <GitBranch aria-hidden="true" />
          </button>
          <button className="nav-button" type="button" title="AI explanations">
            <Bot aria-hidden="true" />
          </button>
        </nav>
      </aside>

      <section className="content">
        <header className="topbar">
          <div>
            <h1>Security Operations</h1>
            <p>Inventory, risk, graph freshness, and defensive attack-path context.</p>
          </div>
          <div className={`status-pill ${health?.status ?? "degraded"}`}>
            <Activity aria-hidden="true" />
            <span>{health?.detail ?? healthError ?? "Checking API health"}</span>
          </div>
        </header>

        <section className="metrics" aria-label="Operational metrics">
          <article>
            <Radar aria-hidden="true" />
            <strong>{assets.length}</strong>
            <span>Tracked assets</span>
          </article>
          <article>
            <AlertTriangle aria-hidden="true" />
            <strong>{averageRisk}</strong>
            <span>Average risk</span>
          </article>
          <article>
            <GitBranch aria-hidden="true" />
            <strong>1</strong>
            <span>Modeled path</span>
          </article>
          <article>
            <Bot aria-hidden="true" />
            <strong>Off</strong>
            <span>AI analyst</span>
          </article>
        </section>

        <section className="main-grid">
          <div className="asset-band">
            <div className="section-header">
              <h2>Assets</h2>
              <button type="button">Queue Scan</button>
            </div>
            {inventoryError === null ? null : (
              <p className="panel-note">Inventory data is unavailable: {inventoryError}</p>
            )}
            <div className="asset-table" role="table" aria-label="Asset inventory">
              <div className="asset-row table-head" role="row">
                <span>Host</span>
                <span>Services</span>
                <span>Risk</span>
                <span>Last Seen</span>
              </div>
              {assets.map((asset) => (
                <div className="asset-row" role="row" key={asset.id}>
                  <span>
                    <strong>{asset.hostname ?? asset.primary_ip}</strong>
                    <small>{asset.primary_ip}</small>
                  </span>
                  <span>{asset.services.length}</span>
                  <span className="risk-value">{asset.risk_score}</span>
                  <span>{new Date(asset.last_seen_at).toLocaleString()}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="graph-band">
            <div className="section-header">
              <h2>Graph Slice</h2>
              <span>Depth 2 · bounded</span>
            </div>
            <GraphPanel />
          </div>

          <div className="risk-band">
            <div className="section-header">
              <h2>Top Risks</h2>
              <span>Composite v1</span>
            </div>
            <div className="risk-list">
              {risks.slice(0, 3).map((risk) => (
                <article className="risk-item" key={`${risk.title}-${risk.score}`}>
                  <div>
                    <strong>{risk.title}</strong>
                    <span>{risk.tactic}</span>
                  </div>
                  <b>{risk.score}</b>
                </article>
              ))}
              {risks.length === 0 ? <p className="panel-note">No vulnerability records were returned by the API.</p> : null}
            </div>
          </div>

          <div className="timeline-band">
            <div className="section-header">
              <h2>Timeline</h2>
              <span>Scan history</span>
            </div>
            <ol>
              <li>Health checks confirm backend service availability</li>
              <li>Inventory and vulnerability cards reflect live API results</li>
              <li>Graph view remains bounded until a projection is available</li>
            </ol>
          </div>
        </section>
      </section>
    </main>
  );
}

export default App;

