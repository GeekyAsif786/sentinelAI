// ─── Mock Data Layer ────────────────────────────────────────────────
// Provides realistic data for all SentinelAI views so the frontend
// is fully functional even without a live backend connection.

import type {
  HealthResponse,
  GraphNode,
  GraphEdge,
  GraphSliceResponse,
  HostSummary,
  AssetListResponse,
  VulnerabilitySummary,
  VulnerabilityListResponse,
} from "./api";

// ─── Helpers ────────────────────────────────────────────────────────

function uuid(): string {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}

function hoursAgo(h: number): string {
  return new Date(Date.now() - h * 3600000).toISOString();
}

// ─── Mock Health ────────────────────────────────────────────────────

export const mockHealth: HealthResponse = {
  service: "ai-network-mapper",
  status: "ok",
  checked_at: new Date().toISOString(),
  detail: "All systems operational",
};

// ─── Mock Hosts / Assets ────────────────────────────────────────────

export const mockAssets: HostSummary[] = [
  {
    id: uuid(),
    primary_ip: "10.0.1.5",
    hostname: "dc-primary.corp.local",
    os_name: "Windows Server 2022",
    asset_criticality: 95,
    risk_score: 87,
    last_seen_at: hoursAgo(0.5),
    services: [
      { id: uuid(), port: 53, protocol: "tcp", service_name: "dns", product: "Microsoft DNS", version: "10.0", state: "open", exposure: "internal" },
      { id: uuid(), port: 88, protocol: "tcp", service_name: "kerberos", product: "Microsoft Kerberos", version: null, state: "open", exposure: "internal" },
      { id: uuid(), port: 389, protocol: "tcp", service_name: "ldap", product: "Active Directory LDAP", version: null, state: "open", exposure: "internal" },
      { id: uuid(), port: 445, protocol: "tcp", service_name: "microsoft-ds", product: "Windows SMB", version: "3.1.1", state: "open", exposure: "internal" },
      { id: uuid(), port: 3389, protocol: "tcp", service_name: "ms-wbt-server", product: "Microsoft RDP", version: null, state: "open", exposure: "internal" },
    ],
  },
  {
    id: uuid(),
    primary_ip: "10.0.1.10",
    hostname: "web-frontend-01.corp.local",
    os_name: "Ubuntu 22.04 LTS",
    asset_criticality: 80,
    risk_score: 72,
    last_seen_at: hoursAgo(1),
    services: [
      { id: uuid(), port: 80, protocol: "tcp", service_name: "http", product: "nginx", version: "1.24.0", state: "open", exposure: "external" },
      { id: uuid(), port: 443, protocol: "tcp", service_name: "https", product: "nginx", version: "1.24.0", state: "open", exposure: "external" },
      { id: uuid(), port: 22, protocol: "tcp", service_name: "ssh", product: "OpenSSH", version: "9.3", state: "open", exposure: "internal" },
    ],
  },
  {
    id: uuid(),
    primary_ip: "10.0.2.20",
    hostname: "db-postgres-01.corp.local",
    os_name: "Debian 12",
    asset_criticality: 90,
    risk_score: 65,
    last_seen_at: hoursAgo(0.2),
    services: [
      { id: uuid(), port: 5432, protocol: "tcp", service_name: "postgresql", product: "PostgreSQL", version: "16.1", state: "open", exposure: "internal" },
      { id: uuid(), port: 22, protocol: "tcp", service_name: "ssh", product: "OpenSSH", version: "9.6", state: "open", exposure: "internal" },
    ],
  },
  {
    id: uuid(),
    primary_ip: "10.0.2.25",
    hostname: "redis-cache-01.corp.local",
    os_name: "Alpine Linux 3.19",
    asset_criticality: 60,
    risk_score: 42,
    last_seen_at: hoursAgo(2),
    services: [
      { id: uuid(), port: 6379, protocol: "tcp", service_name: "redis", product: "Redis", version: "7.2.4", state: "open", exposure: "internal" },
    ],
  },
  {
    id: uuid(),
    primary_ip: "10.0.3.50",
    hostname: "api-gateway.corp.local",
    os_name: "Ubuntu 22.04 LTS",
    asset_criticality: 85,
    risk_score: 78,
    last_seen_at: hoursAgo(0.1),
    services: [
      { id: uuid(), port: 443, protocol: "tcp", service_name: "https", product: "Envoy", version: "1.28", state: "open", exposure: "external" },
      { id: uuid(), port: 8443, protocol: "tcp", service_name: "https-alt", product: "gRPC", version: null, state: "open", exposure: "internal" },
      { id: uuid(), port: 9090, protocol: "tcp", service_name: "prometheus", product: "Prometheus", version: "2.48", state: "open", exposure: "internal" },
    ],
  },
  {
    id: uuid(),
    primary_ip: "10.0.1.100",
    hostname: "mail-server.corp.local",
    os_name: "CentOS Stream 9",
    asset_criticality: 70,
    risk_score: 58,
    last_seen_at: hoursAgo(3),
    services: [
      { id: uuid(), port: 25, protocol: "tcp", service_name: "smtp", product: "Postfix", version: "3.8", state: "open", exposure: "external" },
      { id: uuid(), port: 993, protocol: "tcp", service_name: "imaps", product: "Dovecot", version: "2.3", state: "open", exposure: "external" },
      { id: uuid(), port: 587, protocol: "tcp", service_name: "submission", product: "Postfix", version: "3.8", state: "open", exposure: "external" },
    ],
  },
  {
    id: uuid(),
    primary_ip: "10.0.4.15",
    hostname: "jenkins-ci.corp.local",
    os_name: "Ubuntu 20.04 LTS",
    asset_criticality: 75,
    risk_score: 81,
    last_seen_at: hoursAgo(1.5),
    services: [
      { id: uuid(), port: 8080, protocol: "tcp", service_name: "http-proxy", product: "Jenkins", version: "2.426", state: "open", exposure: "internal" },
      { id: uuid(), port: 50000, protocol: "tcp", service_name: "jenkins-agent", product: "Jenkins Agent", version: null, state: "open", exposure: "internal" },
      { id: uuid(), port: 22, protocol: "tcp", service_name: "ssh", product: "OpenSSH", version: "8.9", state: "open", exposure: "internal" },
    ],
  },
  {
    id: uuid(),
    primary_ip: "10.0.5.5",
    hostname: "k8s-master-01.corp.local",
    os_name: "Ubuntu 22.04 LTS",
    asset_criticality: 92,
    risk_score: 69,
    last_seen_at: hoursAgo(0.3),
    services: [
      { id: uuid(), port: 6443, protocol: "tcp", service_name: "kube-api", product: "Kubernetes API", version: "1.28", state: "open", exposure: "internal" },
      { id: uuid(), port: 2379, protocol: "tcp", service_name: "etcd", product: "etcd", version: "3.5", state: "open", exposure: "internal" },
      { id: uuid(), port: 10250, protocol: "tcp", service_name: "kubelet", product: "kubelet", version: null, state: "open", exposure: "internal" },
    ],
  },
  {
    id: uuid(),
    primary_ip: "10.0.3.80",
    hostname: "monitoring.corp.local",
    os_name: "Debian 12",
    asset_criticality: 55,
    risk_score: 35,
    last_seen_at: hoursAgo(4),
    services: [
      { id: uuid(), port: 3000, protocol: "tcp", service_name: "grafana", product: "Grafana", version: "10.2", state: "open", exposure: "internal" },
      { id: uuid(), port: 9090, protocol: "tcp", service_name: "prometheus", product: "Prometheus", version: "2.48", state: "open", exposure: "internal" },
    ],
  },
  {
    id: uuid(),
    primary_ip: "10.0.6.10",
    hostname: "file-server.corp.local",
    os_name: "Windows Server 2019",
    asset_criticality: 65,
    risk_score: 53,
    last_seen_at: hoursAgo(6),
    services: [
      { id: uuid(), port: 445, protocol: "tcp", service_name: "microsoft-ds", product: "Windows SMB", version: "3.0", state: "open", exposure: "internal" },
      { id: uuid(), port: 139, protocol: "tcp", service_name: "netbios-ssn", product: "Windows NetBIOS", version: null, state: "open", exposure: "internal" },
      { id: uuid(), port: 3389, protocol: "tcp", service_name: "ms-wbt-server", product: "Microsoft RDP", version: null, state: "open", exposure: "internal" },
    ],
  },
  {
    id: uuid(),
    primary_ip: "192.168.1.1",
    hostname: "fw-perimeter.corp.local",
    os_name: "pfSense 2.7",
    asset_criticality: 98,
    risk_score: 45,
    last_seen_at: hoursAgo(0.1),
    services: [
      { id: uuid(), port: 443, protocol: "tcp", service_name: "https", product: "pfSense WebGUI", version: "2.7", state: "open", exposure: "external" },
      { id: uuid(), port: 500, protocol: "udp", service_name: "isakmp", product: "strongSwan", version: "5.9", state: "open", exposure: "external" },
    ],
  },
  {
    id: uuid(),
    primary_ip: "10.0.7.30",
    hostname: "dev-workstation-01",
    os_name: "macOS 14.2",
    asset_criticality: 40,
    risk_score: 28,
    last_seen_at: hoursAgo(8),
    services: [
      { id: uuid(), port: 22, protocol: "tcp", service_name: "ssh", product: "OpenSSH", version: "9.4", state: "open", exposure: "internal" },
    ],
  },
];

export const mockAssetListResponse: AssetListResponse = {
  assets: mockAssets,
  limit: 50,
  offset: 0,
  total: mockAssets.length,
};

// ─── Mock Vulnerabilities ───────────────────────────────────────────

export const mockVulnerabilities: VulnerabilitySummary[] = [
  { id: uuid(), cve_id: "CVE-2024-21762", title: "Fortinet FortiOS Out-of-Bound Write", cvss_score: 9.8, epss_probability: 0.97, severity: "critical" },
  { id: uuid(), cve_id: "CVE-2024-3400", title: "Palo Alto PAN-OS Command Injection", cvss_score: 10.0, epss_probability: 0.95, severity: "critical" },
  { id: uuid(), cve_id: "CVE-2023-44228", title: "Apache Log4j Remote Code Execution", cvss_score: 10.0, epss_probability: 0.98, severity: "critical" },
  { id: uuid(), cve_id: "CVE-2024-1709", title: "ConnectWise ScreenConnect Auth Bypass", cvss_score: 10.0, epss_probability: 0.94, severity: "critical" },
  { id: uuid(), cve_id: "CVE-2023-46747", title: "F5 BIG-IP Authentication Bypass", cvss_score: 9.8, epss_probability: 0.89, severity: "critical" },
  { id: uuid(), cve_id: "CVE-2024-0012", title: "Palo Alto PAN-OS Auth Bypass", cvss_score: 9.1, epss_probability: 0.82, severity: "critical" },
  { id: uuid(), cve_id: "CVE-2023-20198", title: "Cisco IOS XE Web UI Privilege Escalation", cvss_score: 10.0, epss_probability: 0.96, severity: "critical" },
  { id: uuid(), cve_id: "CVE-2024-27198", title: "JetBrains TeamCity Auth Bypass", cvss_score: 9.8, epss_probability: 0.91, severity: "critical" },
  { id: uuid(), cve_id: "CVE-2023-4966", title: "Citrix NetScaler Information Disclosure", cvss_score: 7.5, epss_probability: 0.72, severity: "high" },
  { id: uuid(), cve_id: "CVE-2024-21887", title: "Ivanti Connect Secure Command Injection", cvss_score: 9.1, epss_probability: 0.88, severity: "critical" },
  { id: uuid(), cve_id: "CVE-2023-38545", title: "curl SOCKS5 Heap Buffer Overflow", cvss_score: 7.5, epss_probability: 0.45, severity: "high" },
  { id: uuid(), cve_id: "CVE-2024-23897", title: "Jenkins Arbitrary File Read", cvss_score: 7.5, epss_probability: 0.68, severity: "high" },
  { id: uuid(), cve_id: "CVE-2023-36884", title: "Microsoft Office RCE via HTML", cvss_score: 7.5, epss_probability: 0.55, severity: "high" },
  { id: uuid(), cve_id: "CVE-2024-6387", title: "OpenSSH regreSSHion RCE", cvss_score: 8.1, epss_probability: 0.62, severity: "high" },
  { id: uuid(), cve_id: "CVE-2023-32784", title: "KeePass Memory Dump Master Key", cvss_score: 5.5, epss_probability: 0.35, severity: "medium" },
  { id: uuid(), cve_id: "CVE-2024-0204", title: "GoAnywhere MFT Auth Bypass", cvss_score: 9.8, epss_probability: 0.87, severity: "critical" },
];

export const mockVulnerabilityListResponse: VulnerabilityListResponse = {
  vulnerabilities: mockVulnerabilities,
};

// ─── Mock Graph Data ────────────────────────────────────────────────

const graphNodes: GraphNode[] = [
  { id: "internet", label: "Internet", kind: "external", risk_score: 0 },
  { id: "fw-perimeter", label: "fw-perimeter", kind: "firewall", risk_score: 45 },
  { id: "dmz-web-01", label: "web-frontend-01", kind: "host", risk_score: 72 },
  { id: "api-gw", label: "api-gateway", kind: "host", risk_score: 78 },
  { id: "mail-srv", label: "mail-server", kind: "host", risk_score: 58 },
  { id: "dc-primary", label: "dc-primary", kind: "host", risk_score: 87 },
  { id: "db-postgres", label: "db-postgres-01", kind: "database", risk_score: 65 },
  { id: "redis-cache", label: "redis-cache-01", kind: "cache", risk_score: 42 },
  { id: "jenkins-ci", label: "jenkins-ci", kind: "host", risk_score: 81 },
  { id: "k8s-master", label: "k8s-master-01", kind: "host", risk_score: 69 },
  { id: "monitoring", label: "monitoring", kind: "host", risk_score: 35 },
  { id: "file-server", label: "file-server", kind: "host", risk_score: 53 },
  { id: "dev-ws-01", label: "dev-workstation", kind: "endpoint", risk_score: 28 },
];

const graphEdges: GraphEdge[] = [
  { id: "e1", source: "internet", target: "fw-perimeter", relationship: "CONNECTS_TO", confidence: 1.0, weight: 1.0 },
  { id: "e2", source: "fw-perimeter", target: "dmz-web-01", relationship: "ALLOWS", confidence: 0.95, weight: 0.5 },
  { id: "e3", source: "fw-perimeter", target: "api-gw", relationship: "ALLOWS", confidence: 0.95, weight: 0.5 },
  { id: "e4", source: "fw-perimeter", target: "mail-srv", relationship: "ALLOWS", confidence: 0.90, weight: 0.7 },
  { id: "e5", source: "dmz-web-01", target: "api-gw", relationship: "ROUTES_TO", confidence: 0.92, weight: 0.4 },
  { id: "e6", source: "api-gw", target: "db-postgres", relationship: "QUERIES", confidence: 0.95, weight: 0.3 },
  { id: "e7", source: "api-gw", target: "redis-cache", relationship: "CACHES_WITH", confidence: 0.88, weight: 0.2 },
  { id: "e8", source: "api-gw", target: "k8s-master", relationship: "ORCHESTRATED_BY", confidence: 0.90, weight: 0.5 },
  { id: "e9", source: "dc-primary", target: "db-postgres", relationship: "AUTHENTICATES", confidence: 0.85, weight: 0.6 },
  { id: "e10", source: "dc-primary", target: "file-server", relationship: "MANAGES", confidence: 0.92, weight: 0.4 },
  { id: "e11", source: "dc-primary", target: "jenkins-ci", relationship: "AUTHENTICATES", confidence: 0.80, weight: 0.7 },
  { id: "e12", source: "jenkins-ci", target: "k8s-master", relationship: "DEPLOYS_TO", confidence: 0.85, weight: 0.5 },
  { id: "e13", source: "jenkins-ci", target: "db-postgres", relationship: "READS_CONFIG", confidence: 0.70, weight: 0.8 },
  { id: "e14", source: "k8s-master", target: "monitoring", relationship: "MONITORED_BY", confidence: 0.95, weight: 0.2 },
  { id: "e15", source: "db-postgres", target: "monitoring", relationship: "MONITORED_BY", confidence: 0.90, weight: 0.2 },
  { id: "e16", source: "dev-ws-01", target: "jenkins-ci", relationship: "PUSHES_TO", confidence: 0.75, weight: 0.6 },
  { id: "e17", source: "dev-ws-01", target: "dc-primary", relationship: "AUTHENTICATES_VIA", confidence: 0.85, weight: 0.5 },
  { id: "e18", source: "file-server", target: "dc-primary", relationship: "TRUSTS", confidence: 0.88, weight: 0.4 },
  { id: "e19", source: "mail-srv", target: "dc-primary", relationship: "AUTHENTICATES_VIA", confidence: 0.82, weight: 0.6 },
  { id: "e20", source: "dmz-web-01", target: "redis-cache", relationship: "SESSION_STORE", confidence: 0.78, weight: 0.3 },
];

export const mockGraphSlice: GraphSliceResponse = {
  nodes: graphNodes,
  edges: graphEdges,
  freshness_status: "fresh",
  max_depth: 3,
  max_nodes: 100,
};

// ─── Mock Attack Paths ──────────────────────────────────────────────

export interface AttackPath {
  id: string;
  name: string;
  source: string;
  target: string;
  path: string[];
  risk_score: number;
  confidence: number;
  critical_nodes: string[];
  mitre_techniques: { id: string; name: string; tactic: string }[];
  description: string;
  recommendations: string[];
}

export const mockAttackPaths: AttackPath[] = [
  {
    id: uuid(),
    name: "Internet → Domain Controller via Web App",
    source: "Internet",
    target: "dc-primary.corp.local",
    path: ["Internet", "fw-perimeter", "web-frontend-01", "api-gateway", "dc-primary"],
    risk_score: 92,
    confidence: 0.85,
    critical_nodes: ["api-gateway", "dc-primary"],
    mitre_techniques: [
      { id: "T1190", name: "Exploit Public-Facing Application", tactic: "Initial Access" },
      { id: "T1078", name: "Valid Accounts", tactic: "Persistence" },
      { id: "T1021", name: "Remote Services", tactic: "Lateral Movement" },
    ],
    description: "An attacker exploits a vulnerability in the public web frontend, pivots through the API gateway, and uses stolen credentials to access the domain controller.",
    recommendations: [
      "Patch web-frontend-01 to latest nginx version",
      "Implement network segmentation between DMZ and internal zones",
      "Enable MFA on all domain controller access",
      "Deploy WAF rules for known exploit patterns",
    ],
  },
  {
    id: uuid(),
    name: "Internet → Database via Mail Server",
    source: "Internet",
    target: "db-postgres-01.corp.local",
    path: ["Internet", "fw-perimeter", "mail-server", "dc-primary", "db-postgres-01"],
    risk_score: 78,
    confidence: 0.72,
    critical_nodes: ["mail-server", "dc-primary"],
    mitre_techniques: [
      { id: "T1566", name: "Phishing", tactic: "Initial Access" },
      { id: "T1003", name: "OS Credential Dumping", tactic: "Credential Access" },
      { id: "T1210", name: "Exploitation of Remote Services", tactic: "Lateral Movement" },
    ],
    description: "Phishing attack targets mail server, harvested credentials are used to authenticate to the domain controller, which has trust to the database.",
    recommendations: [
      "Deploy email security gateway with advanced threat protection",
      "Restrict database access to application service accounts only",
      "Implement credential rotation policy",
    ],
  },
  {
    id: uuid(),
    name: "CI/CD Pipeline Compromise",
    source: "dev-workstation-01",
    target: "k8s-master-01.corp.local",
    path: ["dev-workstation-01", "jenkins-ci", "k8s-master-01"],
    risk_score: 85,
    confidence: 0.80,
    critical_nodes: ["jenkins-ci"],
    mitre_techniques: [
      { id: "T1195", name: "Supply Chain Compromise", tactic: "Initial Access" },
      { id: "T1059", name: "Command and Scripting Interpreter", tactic: "Execution" },
      { id: "T1609", name: "Container Administration Command", tactic: "Execution" },
    ],
    description: "Compromised developer workstation pushes malicious code through Jenkins, which deploys to the Kubernetes cluster.",
    recommendations: [
      "Enforce code review and signing requirements",
      "Implement Jenkins pipeline approval gates",
      "Restrict kubectl access to authorized CI/CD service accounts",
      "Enable admission controllers in Kubernetes",
    ],
  },
  {
    id: uuid(),
    name: "Lateral Movement via SMB",
    source: "file-server.corp.local",
    target: "dc-primary.corp.local",
    path: ["file-server", "dc-primary"],
    risk_score: 68,
    confidence: 0.75,
    critical_nodes: ["dc-primary"],
    mitre_techniques: [
      { id: "T1021.002", name: "SMB/Windows Admin Shares", tactic: "Lateral Movement" },
      { id: "T1558", name: "Steal or Forge Kerberos Tickets", tactic: "Credential Access" },
    ],
    description: "File server has a trust relationship with the domain controller. SMB exploitation allows lateral movement to the DC.",
    recommendations: [
      "Disable SMBv1 on all hosts",
      "Restrict administrative shares",
      "Implement Kerberos constrained delegation",
    ],
  },
  {
    id: uuid(),
    name: "Data Exfiltration via Redis",
    source: "Internet",
    target: "redis-cache-01.corp.local",
    path: ["Internet", "fw-perimeter", "web-frontend-01", "redis-cache-01"],
    risk_score: 55,
    confidence: 0.65,
    critical_nodes: ["redis-cache-01"],
    mitre_techniques: [
      { id: "T1190", name: "Exploit Public-Facing Application", tactic: "Initial Access" },
      { id: "T1005", name: "Data from Local System", tactic: "Collection" },
      { id: "T1041", name: "Exfiltration Over C2 Channel", tactic: "Exfiltration" },
    ],
    description: "Web frontend compromise provides access to session data and cached credentials in Redis.",
    recommendations: [
      "Enable Redis AUTH with strong password",
      "Encrypt sensitive cache data at rest",
      "Restrict Redis network access to application servers only",
    ],
  },
  {
    id: uuid(),
    name: "API Gateway → Full Infrastructure",
    source: "Internet",
    target: "monitoring.corp.local",
    path: ["Internet", "fw-perimeter", "api-gateway", "k8s-master-01", "monitoring"],
    risk_score: 62,
    confidence: 0.70,
    critical_nodes: ["api-gateway", "k8s-master-01"],
    mitre_techniques: [
      { id: "T1190", name: "Exploit Public-Facing Application", tactic: "Initial Access" },
      { id: "T1610", name: "Deploy Container", tactic: "Execution" },
      { id: "T1046", name: "Network Service Discovery", tactic: "Discovery" },
    ],
    description: "API gateway exploitation leads to Kubernetes cluster access, providing visibility into the entire monitoring infrastructure.",
    recommendations: [
      "Implement API rate limiting and input validation",
      "Use network policies to isolate Kubernetes namespaces",
      "Restrict monitoring dashboard access with RBAC",
    ],
  },
];

// ─── Mock Scan History ──────────────────────────────────────────────

export interface ScanRecord {
  id: string;
  status: "queued" | "running" | "completed" | "failed" | "partial" | "cancelled";
  provider: string;
  scan_type: string;
  targets: string[];
  started_at: string;
  completed_at: string | null;
  hosts_discovered: number;
  services_found: number;
  vulnerabilities_found: number;
  requested_by: string;
}

export const mockScans: ScanRecord[] = [
  {
    id: uuid(), status: "completed", provider: "nmap", scan_type: "full_inventory",
    targets: ["10.0.0.0/16"], started_at: hoursAgo(2), completed_at: hoursAgo(1.5),
    hosts_discovered: 12, services_found: 38, vulnerabilities_found: 16, requested_by: "admin@corp.local",
  },
  {
    id: uuid(), status: "completed", provider: "nmap", scan_type: "discovery",
    targets: ["10.0.1.0/24"], started_at: hoursAgo(6), completed_at: hoursAgo(5.8),
    hosts_discovered: 4, services_found: 14, vulnerabilities_found: 7, requested_by: "analyst@corp.local",
  },
  {
    id: uuid(), status: "running", provider: "nmap", scan_type: "service_detection",
    targets: ["10.0.2.0/24", "10.0.3.0/24"], started_at: hoursAgo(0.5), completed_at: null,
    hosts_discovered: 3, services_found: 8, vulnerabilities_found: 0, requested_by: "analyst@corp.local",
  },
  {
    id: uuid(), status: "completed", provider: "nmap", scan_type: "discovery",
    targets: ["192.168.1.0/24"], started_at: hoursAgo(24), completed_at: hoursAgo(23.5),
    hosts_discovered: 1, services_found: 2, vulnerabilities_found: 0, requested_by: "admin@corp.local",
  },
  {
    id: uuid(), status: "failed", provider: "nmap", scan_type: "full_inventory",
    targets: ["10.0.4.0/24"], started_at: hoursAgo(12), completed_at: hoursAgo(11.9),
    hosts_discovered: 0, services_found: 0, vulnerabilities_found: 0, requested_by: "admin@corp.local",
  },
  {
    id: uuid(), status: "completed", provider: "nmap", scan_type: "discovery",
    targets: ["10.0.5.0/24"], started_at: hoursAgo(48), completed_at: hoursAgo(47.5),
    hosts_discovered: 2, services_found: 6, vulnerabilities_found: 3, requested_by: "analyst@corp.local",
  },
  {
    id: uuid(), status: "queued", provider: "nmap", scan_type: "full_inventory",
    targets: ["10.0.6.0/24", "10.0.7.0/24"], started_at: hoursAgo(0.1), completed_at: null,
    hosts_discovered: 0, services_found: 0, vulnerabilities_found: 0, requested_by: "admin@corp.local",
  },
  {
    id: uuid(), status: "partial", provider: "nmap", scan_type: "service_detection",
    targets: ["10.0.1.0/24"], started_at: hoursAgo(18), completed_at: hoursAgo(17),
    hosts_discovered: 3, services_found: 10, vulnerabilities_found: 4, requested_by: "analyst@corp.local",
  },
  {
    id: uuid(), status: "completed", provider: "nmap", scan_type: "discovery",
    targets: ["10.0.3.0/24"], started_at: hoursAgo(72), completed_at: hoursAgo(71),
    hosts_discovered: 3, services_found: 9, vulnerabilities_found: 5, requested_by: "admin@corp.local",
  },
  {
    id: uuid(), status: "cancelled", provider: "nmap", scan_type: "full_inventory",
    targets: ["10.0.0.0/8"], started_at: hoursAgo(96), completed_at: hoursAgo(95),
    hosts_discovered: 0, services_found: 0, vulnerabilities_found: 0, requested_by: "admin@corp.local",
  },
];

// ─── Mock AI Analyses ───────────────────────────────────────────────

export interface AIAnalysis {
  id: string;
  subject_type: "finding" | "attack_path" | "risk_score" | "asset";
  subject_id: string;
  subject_label: string;
  provider: string;
  model: string;
  prompt_version: string;
  generated_text: string;
  is_ai_generated: boolean;
  source_evidence: Record<string, string | number | boolean | null>;
  created_at: string;
}

export const mockAIAnalyses: AIAnalysis[] = [
  {
    id: uuid(),
    subject_type: "finding",
    subject_id: "CVE-2024-21762",
    subject_label: "Fortinet FortiOS Out-of-Bound Write",
    provider: "disabled",
    model: "deterministic-v1",
    prompt_version: "1.0.0",
    generated_text: "This vulnerability (CVE-2024-21762) in Fortinet FortiOS allows unauthenticated remote code execution through an out-of-bound write in the SSL VPN component. With a CVSS score of 9.8 and EPSS probability of 97%, this vulnerability is actively exploited in the wild.\n\n**Risk Assessment**: CRITICAL — This vulnerability provides direct initial access from the internet and has been observed in nation-state campaigns.\n\n**Recommended Actions**:\n1. Immediately patch FortiOS to version 7.4.3 or later\n2. If patching is not immediately possible, disable SSL VPN as a workaround\n3. Review VPN access logs for indicators of compromise\n4. Enable IPS signatures for CVE-2024-21762 detection",
    is_ai_generated: false,
    source_evidence: {
      cve_id: "CVE-2024-21762",
      cvss_score: 9.8,
      epss_probability: 0.97,
      severity: "critical",
      affected_product: "FortiOS",
      exploit_available: true,
    },
    created_at: hoursAgo(1),
  },
  {
    id: uuid(),
    subject_type: "attack_path",
    subject_id: "path-web-to-dc",
    subject_label: "Internet → Domain Controller via Web App",
    provider: "disabled",
    model: "deterministic-v1",
    prompt_version: "1.0.0",
    generated_text: "This attack path represents a high-risk chain from the internet to the domain controller through the web application tier. The path traverses 4 network hops and exploits trust relationships between the DMZ and internal network.\n\n**Chain Analysis**:\n- **Step 1**: Exploit public-facing web application (T1190)\n- **Step 2**: Pivot through API gateway using captured session tokens\n- **Step 3**: Leverage service account credentials to reach Active Directory\n- **Step 4**: Escalate privileges on the domain controller\n\n**Key Risk Factors**:\n- The API gateway has direct network connectivity to the domain controller\n- Service account credentials are stored in application configuration\n- No network segmentation between application and directory tiers",
    is_ai_generated: false,
    source_evidence: {
      path_length: 4,
      risk_score: 92,
      critical_nodes: "api-gateway, dc-primary",
      mitre_tactics: "Initial Access, Lateral Movement, Privilege Escalation",
    },
    created_at: hoursAgo(2),
  },
  {
    id: uuid(),
    subject_type: "risk_score",
    subject_id: "dc-primary",
    subject_label: "dc-primary.corp.local Risk Assessment",
    provider: "disabled",
    model: "deterministic-v1",
    prompt_version: "1.0.0",
    generated_text: "The domain controller (dc-primary.corp.local) has the highest composite risk score in the environment at 87/100.\n\n**Score Breakdown**:\n- Asset criticality: 95/100 (domain controller — foundational infrastructure)\n- Exposure: Internal only (reduces external attack surface)\n- Service count: 5 services including Kerberos, LDAP, SMB, DNS, RDP\n- Vulnerability context: Multiple services with known CVEs\n\n**Key Concerns**:\n- RDP (3389) is enabled, increasing lateral movement risk\n- SMB services may be vulnerable to relay attacks\n- Single point of failure for authentication infrastructure\n\n**Remediation Priority**: HIGH — This asset's compromise would enable domain-wide access.",
    is_ai_generated: false,
    source_evidence: {
      hostname: "dc-primary.corp.local",
      risk_score: 87,
      asset_criticality: 95,
      service_count: 5,
      os: "Windows Server 2022",
    },
    created_at: hoursAgo(3),
  },
  {
    id: uuid(),
    subject_type: "asset",
    subject_id: "jenkins-ci",
    subject_label: "jenkins-ci.corp.local Security Review",
    provider: "disabled",
    model: "deterministic-v1",
    prompt_version: "1.0.0",
    generated_text: "Jenkins CI server (jenkins-ci.corp.local) presents a significant security risk due to its role in the CI/CD pipeline and its connectivity to production infrastructure.\n\n**Findings**:\n- Jenkins version 2.426 has known vulnerability CVE-2024-23897 (Arbitrary File Read)\n- Agent port 50000 is accessible from the internal network\n- SSH access enabled with potentially weak key rotation\n\n**Supply Chain Risk**:\nThis server directly deploys to the Kubernetes cluster. Compromise could result in malicious container deployments across the production environment.\n\n**Recommendations**:\n1. Update Jenkins to latest LTS version\n2. Restrict agent port access to known agent IPs\n3. Implement pipeline-level RBAC\n4. Enable audit logging for all pipeline executions",
    is_ai_generated: false,
    source_evidence: {
      hostname: "jenkins-ci.corp.local",
      risk_score: 81,
      service_count: 3,
      deploys_to: "k8s-master-01",
      known_cve: "CVE-2024-23897",
    },
    created_at: hoursAgo(5),
  },
];

// ─── Mock Timeline Events ───────────────────────────────────────────

export interface TimelineEvent {
  id: string;
  type: "scan_complete" | "vulnerability_found" | "host_discovered" | "risk_change" | "alert" | "graph_projected";
  title: string;
  description: string;
  timestamp: string;
  severity: "info" | "warning" | "critical" | "success";
}

export const mockTimelineEvents: TimelineEvent[] = [
  { id: uuid(), type: "scan_complete", title: "Full inventory scan completed", description: "Discovered 12 hosts, 38 services, 16 vulnerabilities in 10.0.0.0/16", timestamp: hoursAgo(1.5), severity: "success" },
  { id: uuid(), type: "vulnerability_found", title: "Critical CVE detected", description: "CVE-2024-3400 (CVSS 10.0) found on api-gateway.corp.local", timestamp: hoursAgo(1.5), severity: "critical" },
  { id: uuid(), type: "risk_change", title: "Risk score increased", description: "dc-primary.corp.local risk increased from 72 to 87 after new vulnerability mapping", timestamp: hoursAgo(2), severity: "warning" },
  { id: uuid(), type: "host_discovered", title: "New host discovered", description: "dev-workstation-01 (10.0.7.30) first seen on network scan", timestamp: hoursAgo(3), severity: "info" },
  { id: uuid(), type: "graph_projected", title: "Graph projection updated", description: "Neo4j graph refreshed with 13 nodes and 20 relationships", timestamp: hoursAgo(4), severity: "success" },
  { id: uuid(), type: "alert", title: "External exposure detected", description: "mail-server.corp.local SMTP port 25 is externally accessible", timestamp: hoursAgo(5), severity: "warning" },
  { id: uuid(), type: "vulnerability_found", title: "High severity CVE mapped", description: "CVE-2024-6387 (OpenSSH regreSSHion) mapped to 3 hosts", timestamp: hoursAgo(6), severity: "warning" },
  { id: uuid(), type: "scan_complete", title: "Discovery scan completed", description: "Scanned 10.0.1.0/24: 4 hosts, 14 services found", timestamp: hoursAgo(6), severity: "success" },
  { id: uuid(), type: "risk_change", title: "Risk model recalculated", description: "Composite risk model v1 recalculated across all 12 assets", timestamp: hoursAgo(8), severity: "info" },
  { id: uuid(), type: "alert", title: "Jenkins vulnerability confirmed", description: "CVE-2024-23897 arbitrary file read confirmed on jenkins-ci.corp.local", timestamp: hoursAgo(12), severity: "critical" },
];
