import { useState } from "react";
import { Sidebar, TabId } from "./components/Sidebar";
import { AuthView } from "./components/AuthView";
import { AUTH_TOKEN_KEY, USER_INFO_KEY, logoutUser, UserSession } from "./lib/api";

// Import Views
import { DashboardView } from "./components/DashboardView";
import { AssetsView } from "./components/AssetsView";
import { GraphView } from "./components/GraphView";
import { AttackPathsView } from "./components/AttackPathsView";
import { RiskView } from "./components/RiskView";
import { ScansView } from "./components/ScansView";
import { AIAnalystView } from "./components/AIAnalystView";

function App(): JSX.Element {
  const [activeTab, setActiveTab] = useState<TabId>("dashboard");
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(AUTH_TOKEN_KEY));
  const [user, setUser] = useState<UserSession | null>(() => {
    const raw = localStorage.getItem(USER_INFO_KEY);
    try {
      return raw ? (JSON.parse(raw) as UserSession) : null;
    } catch {
      return null;
    }
  });
  const [bypassAuth, setBypassAuth] = useState(false);

  // Navigation handler to pass to views that need to cross-navigate
  const handleNavigate = (tabId: TabId) => {
    setActiveTab(tabId);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleAuthSuccess = (newToken: string, userInfo: UserSession) => {
    setToken(newToken);
    setUser(userInfo);
    setBypassAuth(false);
  };

  const handleLogout = () => {
    logoutUser();
    setToken(null);
    setUser(null);
    setBypassAuth(false);
  };

  const renderActiveView = () => {
    switch (activeTab) {
      case "dashboard":
        return <DashboardView onNavigate={handleNavigate} />;
      case "assets":
        return <AssetsView />;
      case "graph":
        return <GraphView />;
      case "attack-paths":
        return <AttackPathsView />;
      case "risk":
        return <RiskView />;
      case "scans":
        return <ScansView />;
      case "ai-analyst":
        return <AIAnalystView />;
      default:
        return <DashboardView onNavigate={handleNavigate} />;
    }
  };

  // If not authenticated and not bypassed, render the AuthView
  if (!token && !bypassAuth) {
    return <AuthView onAuthSuccess={handleAuthSuccess} onBypass={() => setBypassAuth(true)} />;
  }

  return (
    <div className="app-shell">
      <Sidebar
        activeTab={activeTab}
        onTabChange={handleNavigate}
        onLogout={token ? handleLogout : () => setBypassAuth(false)}
      />
      <main className="main-content">
        {/* Render User status banner at top right */}
        {user && (
          <div className="user-status-bar" style={{
            display: "flex",
            justifyContent: "flex-end",
            alignItems: "center",
            padding: "8px 24px",
            fontSize: "12px",
            color: "var(--text-secondary)",
            background: "rgba(15, 23, 42, 0.4)",
            borderBottom: "1px solid var(--border-subtle)",
            marginBottom: "16px",
            borderRadius: "var(--radius-md)"
          }}>
            <span style={{ marginRight: "8px", width: "8px", height: "8px", borderRadius: "50%", background: "var(--status-ok)", display: "inline-block" }}></span>
            <span>Signed in as: <strong>{user.display_name}</strong> ({user.email})</span>
          </div>
        )}
        {renderActiveView()}
      </main>
    </div>
  );
}

export default App;
