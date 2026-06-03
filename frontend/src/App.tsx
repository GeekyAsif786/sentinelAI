import { useState } from "react";
import { Sidebar, TabId } from "./components/Sidebar";

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

  // Navigation handler to pass to views that need to cross-navigate
  const handleNavigate = (tabId: TabId) => {
    setActiveTab(tabId);
    window.scrollTo({ top: 0, behavior: "smooth" });
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

  return (
    <div className="app-shell">
      <Sidebar activeTab={activeTab} onTabChange={handleNavigate} />
      <main className="main-content">
        {renderActiveView()}
      </main>
    </div>
  );
}

export default App;
