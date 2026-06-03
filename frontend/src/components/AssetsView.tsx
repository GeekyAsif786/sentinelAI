import {
  ChevronDown,
  ChevronRight,
  Database,
  Search,
  Server,
  Shield,
  ShieldAlert,
} from "lucide-react";
import { useEffect, useState } from "react";
import { AssetListResponse, fetchAssets, HostSummary } from "../lib/api";

export function AssetsView(): JSX.Element {
  const [assetData, setAssetData] = useState<AssetListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [expandedAssetId, setExpandedAssetId] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    fetchAssets()
      .then((res) => {
        if (isMounted) {
          setAssetData(res);
          setLoading(false);
        }
      })
      .catch((err) => {
        console.error("Error loading assets:", err);
        setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const toggleExpand = (id: string) => {
    setExpandedAssetId(expandedAssetId === id ? null : id);
  };

  const getRiskBadge = (score: number) => {
    if (score >= 80) return <span className="badge badge-critical">Critical ({score})</span>;
    if (score >= 60) return <span className="badge badge-high">High ({score})</span>;
    if (score >= 40) return <span className="badge badge-medium">Medium ({score})</span>;
    return <span className="badge badge-low">Low ({score})</span>;
  };

  const filteredAssets = (assetData?.assets ?? []).filter(asset => {
    const term = searchTerm.toLowerCase();
    return (
      (asset.hostname?.toLowerCase().includes(term)) ||
      (asset.primary_ip.includes(term)) ||
      (asset.os_name?.toLowerCase().includes(term))
    );
  });

  return (
    <>
      <header className="page-header">
        <div className="page-header-info">
          <h1>Asset Inventory</h1>
          <p>Discovered hosts, operating systems, and exposed services.</p>
        </div>
        <div className="toolbar">
          <div className="search-box">
            <Search size={16} />
            <input 
              type="text" 
              className="input" 
              placeholder="Search assets..." 
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <button className="btn btn-secondary">
            <Server size={16} /> Filter
          </button>
        </div>
      </header>

      <div className="panel">
        <div className="panel-body no-pad">
          {loading ? (
            <div className="empty-state">
              <Database className="spin" size={32} />
              <p>Loading asset inventory...</p>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ width: "40px" }}></th>
                  <th>Asset</th>
                  <th>IP Address</th>
                  <th>OS</th>
                  <th>Services</th>
                  <th>Risk Score</th>
                  <th>Last Seen</th>
                </tr>
              </thead>
              <tbody>
                {filteredAssets.length === 0 ? (
                  <tr>
                    <td colSpan={7}>
                      <div className="empty-state">
                        <Shield size={32} />
                        <h3>No assets found</h3>
                        <p>No assets match your search criteria.</p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  filteredAssets.map((asset) => (
                    <React.Fragment key={asset.id}>
                      <tr 
                        style={{ cursor: "pointer" }} 
                        onClick={() => toggleExpand(asset.id)}
                      >
                        <td>
                          <button className="btn-ghost">
                            {expandedAssetId === asset.id ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                          </button>
                        </td>
                        <td>
                          <div className="cell-primary">{asset.hostname ?? "Unknown Host"}</div>
                        </td>
                        <td className="cell-ip">{asset.primary_ip}</td>
                        <td>{asset.os_name ?? "Unknown"}</td>
                        <td>
                          <span className="badge badge-info">{asset.services.length} services</span>
                        </td>
                        <td>{getRiskBadge(asset.risk_score)}</td>
                        <td>{new Date(asset.last_seen_at).toLocaleDateString()}</td>
                      </tr>
                      {expandedAssetId === asset.id && (
                        <tr className="asset-detail-row">
                          <td colSpan={7}>
                            <div className="asset-detail-inner">
                              <h4 style={{ fontSize: "12px", color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "12px" }}>
                                Discovered Services
                              </h4>
                              {asset.services.length === 0 ? (
                                <p className="text-muted text-sm">No services discovered for this host.</p>
                              ) : (
                                <div className="asset-services-grid">
                                  {asset.services.map(svc => (
                                    <div className="service-chip" key={svc.id}>
                                      <span className="port">{svc.port}/{svc.protocol}</span>
                                      <span className="name">{svc.service_name || "unknown"}</span>
                                      {svc.product && <span className="product">{svc.product}</span>}
                                      {svc.exposure === "external" && <span title="Externally Exposed"><ShieldAlert size={14} style={{ color: "var(--severity-high)" }} /></span>}
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  );
}

// Need to import React to use React.Fragment
import React from 'react';
