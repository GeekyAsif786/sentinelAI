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
  description?: string;
}

export interface VulnerabilityListResponse {
  vulnerabilities: VulnerabilitySummary[];
}

export interface ScanRequest {
  policy_id: string;
  scanner_profile_id: string;
  provider: string;
  scan_type: string;
  targets: string[];
}

export interface ScanCreateResponse {
  scan_id: string;
  status: string;
  message: string;
}

export interface AttackPathResponse {
  path: string[];
  risk_score: number;
  critical_nodes: string[];
  confidence: number;
  message: string;
}

export interface AnalysisRequest {
  subject_type: string;
  subject_id: string;
  evidence: Record<string, string | number | boolean | null>;
}

export interface AnalysisResponse {
  provider: string;
  model: string;
  prompt_version: string;
  generated_text: string;
  is_ai_generated: boolean;
  source_evidence: Record<string, string | number | boolean | null>;
}

// ─── Mock data imports ──────────────────────────────────────────────

import {
  mockHealth,
  mockAssetListResponse,
  mockVulnerabilityListResponse,
  mockGraphSlice,
} from "./mockData";

// ─── API Configuration ─────────────────────────────────────────────

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
export const AUTH_TOKEN_KEY = "sentinel_auth_token";
export const USER_INFO_KEY = "sentinel_user_info";
const USE_MOCK_FALLBACK = true; // Fallback to mock data if backend is unavailable

export interface UserSession {
  email: string;
  display_name: string;
  roles: string[];
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  email: string;
  display_name: string;
  roles: string[];
}

export async function registerUser(email: string, password: string, displayName: string): Promise<AuthResponse> {
  const response = await fetch(`${apiBaseUrl}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, display_name: displayName }),
  });
  if (!response.ok) {
    let message = "Registration failed";
    try {
      const err = await response.json() as { detail?: string };
      if (err.detail) message = err.detail;
    } catch {}
    throw new Error(message);
  }
  const data = (await response.json()) as AuthResponse;
  localStorage.setItem(AUTH_TOKEN_KEY, data.access_token);
  localStorage.setItem(
    USER_INFO_KEY,
    JSON.stringify({ email: data.email, display_name: data.display_name, roles: data.roles })
  );
  return data;
}

export async function loginUser(email: string, password: string): Promise<AuthResponse> {
  const response = await fetch(`${apiBaseUrl}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    let message = "Login failed";
    try {
      const err = await response.json() as { detail?: string };
      if (err.detail) message = err.detail;
    } catch {}
    throw new Error(message);
  }
  const data = (await response.json()) as AuthResponse;
  localStorage.setItem(AUTH_TOKEN_KEY, data.access_token);
  localStorage.setItem(
    USER_INFO_KEY,
    JSON.stringify({ email: data.email, display_name: data.display_name, roles: data.roles })
  );
  return data;
}

export function logoutUser(): void {
  localStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(USER_INFO_KEY);
  sessionStorage.removeItem("sentinel_dev_token_v2");
}

async function getDevToken(): Promise<string> {
  // Check user-authenticated token first
  const userToken = localStorage.getItem(AUTH_TOKEN_KEY);
  if (userToken) return userToken;

  // Fallback to dev token
  const cachedDev = sessionStorage.getItem("sentinel_dev_token_v2");
  if (cachedDev) return cachedDev;

  const response = await fetch(`${apiBaseUrl}/auth/dev-token`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(`Failed to obtain dev token: ${response.status}`);
  }
  const data = (await response.json()) as { access_token: string };
  sessionStorage.setItem("sentinel_dev_token_v2", data.access_token);
  return data.access_token;
}

// ─── API Functions with Mock Fallback ───────────────────────────────

export async function fetchHealth(): Promise<HealthResponse> {
  try {
    const response = await fetch(`${apiBaseUrl}/health`);
    if (!response.ok) {
      throw new Error(`Health request failed with ${response.status}`);
    }
    return (await response.json()) as HealthResponse;
  } catch {
    if (USE_MOCK_FALLBACK) return { ...mockHealth, detail: "Mock mode — backend unavailable" };
    throw new Error("Health check failed");
  }
}

export async function fetchGraphSlice(maxDepth = 2, maxNodes = 100): Promise<GraphSliceResponse> {
  try {
    const token = await getDevToken();
    const searchParams = new URLSearchParams({
      max_depth: String(maxDepth),
      max_nodes: String(maxNodes)
    });
    const response = await fetch(`${apiBaseUrl}/graph?${searchParams.toString()}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (!response.ok) {
      throw new Error(`Graph request failed with ${response.status}`);
    }
    return (await response.json()) as GraphSliceResponse;
  } catch {
    if (USE_MOCK_FALLBACK) return mockGraphSlice;
    throw new Error("Graph fetch failed");
  }
}

export async function fetchAssets(limit = 50, offset = 0): Promise<AssetListResponse> {
  try {
    const token = await getDevToken();
    const searchParams = new URLSearchParams({
      limit: String(limit),
      offset: String(offset)
    });
    const response = await fetch(`${apiBaseUrl}/assets?${searchParams.toString()}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (!response.ok) {
      throw new Error(`Assets request failed with ${response.status}`);
    }
    return (await response.json()) as AssetListResponse;
  } catch {
    if (USE_MOCK_FALLBACK) return mockAssetListResponse;
    throw new Error("Assets fetch failed");
  }
}

export async function fetchVulnerabilities(): Promise<VulnerabilityListResponse> {
  try {
    const token = await getDevToken();
    const response = await fetch(`${apiBaseUrl}/vulnerabilities`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (!response.ok) {
      throw new Error(`Vulnerability request failed with ${response.status}`);
    }
    return (await response.json()) as VulnerabilityListResponse;
  } catch {
    if (USE_MOCK_FALLBACK) return mockVulnerabilityListResponse;
    throw new Error("Vulnerability fetch failed");
  }
}

export async function fetchAttackPaths(
  source = "host:internet",
  target = "host:192.168.1.10"
): Promise<AttackPathResponse> {
  try {
    const token = await getDevToken();
    const searchParams = new URLSearchParams({ source, target });
    const response = await fetch(`${apiBaseUrl}/attack-paths?${searchParams.toString()}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (!response.ok) {
      throw new Error(`Attack paths request failed with ${response.status}`);
    }
    return (await response.json()) as AttackPathResponse;
  } catch {
    if (USE_MOCK_FALLBACK) {
      return {
        path: ["internet", "fw-perimeter", "web-frontend-01", "api-gateway", "dc-primary"],
        risk_score: 92,
        critical_nodes: ["api-gateway", "dc-primary"],
        confidence: 0.85,
        message: "Mock attack path — backend unavailable",
      };
    }
    throw new Error("Attack paths fetch failed");
  }
}

export async function submitAnalysis(request: AnalysisRequest): Promise<AnalysisResponse> {
  try {
    const token = await getDevToken();
    const response = await fetch(`${apiBaseUrl}/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(request),
    });
    if (!response.ok) {
      throw new Error(`Analysis request failed with ${response.status}`);
    }
    return (await response.json()) as AnalysisResponse;
  } catch {
    if (USE_MOCK_FALLBACK) {
      return {
        provider: "disabled",
        model: "deterministic-v1",
        prompt_version: "1.0.0",
        generated_text: "AI analyst is currently disabled. This is a deterministic analysis based on available evidence data. Enable an AI provider (Ollama or OpenAI-compatible) for enhanced explanations.",
        is_ai_generated: false,
        source_evidence: request.evidence,
      };
    }
    throw new Error("Analysis submit failed");
  }
}

export async function queueScan(request: ScanRequest): Promise<ScanCreateResponse> {
  const token = await getDevToken();
  const response = await fetch(`${apiBaseUrl}/scan`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    let detail = `Scan request failed with ${response.status}`;
    try {
      const err = (await response.json()) as { detail?: string };
      if (err.detail) detail = err.detail;
    } catch {
      // ignore parse error
    }
    throw new Error(detail);
  }
  return (await response.json()) as ScanCreateResponse;
}
