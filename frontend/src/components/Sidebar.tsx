import {
  Activity,
  Bot,
  Database,
  GitBranch,
  LayoutDashboard,
  LogOut,
  Network,
  Radar,
  Shield,
  ShieldAlert,
} from "lucide-react";

export type TabId =
  | "dashboard"
  | "assets"
  | "graph"
  | "attack-paths"
  | "risk"
  | "scans"
  | "ai-analyst";

interface SidebarProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
  onLogout?: () => void;
}


interface NavItem {
  id: TabId;
  label: string;
  icon: React.ReactNode;
}

const navItems: NavItem[] = [
  { id: "dashboard", label: "Overview", icon: <LayoutDashboard size={20} /> },
  { id: "assets", label: "Assets", icon: <Database size={20} /> },
  { id: "graph", label: "Graph", icon: <Network size={20} /> },
  { id: "attack-paths", label: "Paths", icon: <GitBranch size={20} /> },
  { id: "risk", label: "Risk", icon: <ShieldAlert size={20} /> },
  { id: "scans", label: "Scans", icon: <Radar size={20} /> },
  { id: "ai-analyst", label: "AI", icon: <Bot size={20} /> },
];

export function Sidebar({ activeTab, onTabChange, onLogout }: SidebarProps): JSX.Element {
  return (
    <aside className="sidebar" aria-label="Primary navigation">
      <div className="sidebar-brand">
        <Shield size={26} />
        <span>Sentinel AI</span>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <button
            key={item.id}
            className={`nav-btn${activeTab === item.id ? " active" : ""}`}
            onClick={() => onTabChange(item.id)}
            title={item.label}
            type="button"
          >
            {item.icon}
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-footer" style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        <button className="nav-btn" title="System status" type="button">
          <Activity size={18} />
          <span>Status</span>
        </button>
        {onLogout && (
          <button className="nav-btn" title="Logout" type="button" onClick={onLogout}>
            <LogOut size={18} />
            <span>Logout</span>
          </button>
        )}
      </div>
    </aside>
  );
}
