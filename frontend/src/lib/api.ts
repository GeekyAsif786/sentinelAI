export type HealthStatus = "ok" | "degraded" | "failed";

export interface HealthResponse {
  service: string;
  status: HealthStatus;
  checked_at: string;
  detail: string;
}

export interface GraphNode {
  id: string;
  label: string;
  kind: string;
  risk_score: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relationship: string;
  confidence: number;
  weight: number;
}

export interface GraphSliceResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  freshness_status: string;
  max_depth: number;
  max_nodes: number;
}

export interface ServiceSummary {
  id: string;
  port: number;
  protocol: string;
  service_name: string | null;
  product: string | null;
  version: string | null;
  state: string;
  exposure: string;
}

export interface HostSummary {
  id: string;
  primary_ip: string;
  hostname: string | null;
  os_name: string | null;
  asset_criticality: number;
  risk_score: number;
  last_seen_at: string;
  services: ServiceSummary[];
}

export interface AssetListResponse {
  assets: HostSummary[];
  limit: number;
  offset: number;
  total: number;
}

export interface VulnerabilitySummary {
  id: string;
  cve_id: string | null;
  title: string;
  cvss_score: number | null;
  epss_probability: number | null;
  severity: string;
}

export interface VulnerabilityListResponse {
  vulnerabilities: VulnerabilitySummary[];
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${apiBaseUrl}/health`);
  if (!response.ok) {
    throw new Error(`Health request failed with ${response.status}`);
  }
  return (await response.json()) as HealthResponse;
}

export async function fetchGraphSlice(maxDepth = 2, maxNodes = 100): Promise<GraphSliceResponse> {
  const searchParams = new URLSearchParams({
    max_depth: String(maxDepth),
    max_nodes: String(maxNodes)
  });
  const response = await fetch(`${apiBaseUrl}/graph?${searchParams.toString()}`);
  if (!response.ok) {
    throw new Error(`Graph request failed with ${response.status}`);
  }
  return (await response.json()) as GraphSliceResponse;
}

export async function fetchAssets(limit = 50, offset = 0): Promise<AssetListResponse> {
  const searchParams = new URLSearchParams({
    limit: String(limit),
    offset: String(offset)
  });
  const response = await fetch(`${apiBaseUrl}/assets?${searchParams.toString()}`);
  if (!response.ok) {
    throw new Error(`Assets request failed with ${response.status}`);
  }
  return (await response.json()) as AssetListResponse;
}

export async function fetchVulnerabilities(): Promise<VulnerabilityListResponse> {
  const response = await fetch(`${apiBaseUrl}/vulnerabilities`);
  if (!response.ok) {
    throw new Error(`Vulnerability request failed with ${response.status}`);
  }
  return (await response.json()) as VulnerabilityListResponse;
}

