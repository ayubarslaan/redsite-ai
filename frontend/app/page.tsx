"use client";

import { useState, useEffect } from "react";
import MarsMap from "../components/MarsMap";
import SiteDashboard from "../components/SiteDashboard";
import AnalystChat from "../components/AnalystChat";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Site {
  id: string;
  name: string;
  code: string;
  coordinates: { lat: number; lon: number };
  features: { terrain: number; water: number; solar: number; science: number; edl: number };
  description: string;
}

interface Ranking {
  site_id: string;
  score: number;
  rank: number;
}

export default function Home() {
  const [sites, setSites] = useState<Site[]>([]);
  const [rankings, setRankings] = useState<Ranking[]>([]);
  const [selectedSite, setSelectedSite] = useState<Site | null>(null);
  const [mission, setMission] = useState("settlement");
  const [activeLayer, setActiveLayer] = useState("elevation");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/api/sites`)
      .then(r => r.json())
      .then(data => {
        setSites(data.sites);
        setSelectedSite(data.sites[0]);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to fetch sites:", err);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (sites.length === 0) return;
    fetch(`${API_BASE}/api/score`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mission }),
    })
      .then(r => r.json())
      .then(data => setRankings(data.rankings))
      .catch(err => console.error("Failed to score:", err));
  }, [mission, sites]);

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", color: "#666" }}>
        Initializing RedSite AI...
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", background: "#0a0a0a", color: "#e0e0e0" }}>
      {/* Header */}
      <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 20px", borderBottom: "1px solid #333" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: "#e0e0e0", color: "#0a0a0a", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 600, fontSize: 14 }}>RS</div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 500 }}>RedSite AI</div>
            <div style={{ fontSize: 12, color: "#888" }}>Mars site intelligence & decision engine</div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <select
            value={mission}
            onChange={e => setMission(e.target.value)}
            style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid #444", background: "#1a1a1a", color: "#e0e0e0", fontSize: 13 }}
          >
            <option value="settlement">Human settlement</option>
            <option value="science">Scientific discovery</option>
            <option value="resource">Resource extraction</option>
          </select>
          <span style={{ fontSize: 12, color: "#4ade80", display: "flex", alignItems: "center", gap: 4 }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#4ade80", display: "inline-block" }} />
            Systems nominal
          </span>
        </div>
      </header>

      {/* Main content */}
      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr 1fr", gap: 16, padding: 16, flex: 1, minHeight: 0 }}>
        <MarsMap
          sites={sites}
          rankings={rankings}
          activeLayer={activeLayer}
          selectedSite={selectedSite}
          onSelectSite={setSelectedSite}
          onLayerChange={setActiveLayer}
        />
        <SiteDashboard
          sites={sites}
          rankings={rankings}
          selectedSite={selectedSite}
          mission={mission}
          onSelectSite={setSelectedSite}
        />
        <AnalystChat
          selectedSite={selectedSite}
          mission={mission}
          apiBase={API_BASE}
        />
      </div>
    </div>
  );
}
