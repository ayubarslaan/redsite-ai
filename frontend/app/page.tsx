"use client";

import { useState, useEffect, useCallback } from "react";
import MarsMap from "../components/MarsMap";
import SiteDashboard from "../components/SiteDashboard";
import AnalystChat from "../components/AnalystChat";
import ComparisonView from "../components/ComparisonView";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Site {
  id: string;
  name: string;
  code: string;
  coordinates: { lat: number; lon: number };
  features: { terrain: number; water: number; solar: number; science: number; edl: number };
  description: string;
}

interface FeatureContribution {
  raw_score: number;
  weight: number;
  contribution: number;
  percentage: number;
}

interface Ranking {
  site_id: string;
  score: number;
  rank: number;
  decomposition?: Record<string, FeatureContribution>;
}

interface RankingExplanation {
  text: string;
  rank1_site_id: string;
  rank1_site_name: string;
  key_advantage_feature: string;
  key_advantage_contribution_delta: number;
}

/** Default profile weights fetched from the backend */
interface ProfileWeights {
  [key: string]: Record<string, number>;
}

export default function Home() {
  const [sites, setSites] = useState<Site[]>([]);
  const [rankings, setRankings] = useState<Ranking[]>([]);
  const [selectedSite, setSelectedSite] = useState<Site | null>(null);
  const [mission, setMission] = useState("settlement");
  const [activeLayer, setActiveLayer] = useState("elevation");
  const [loading, setLoading] = useState(true);
  const [analystMode, setAnalystMode] = useState<string>("rule-based");
  const [error, setError] = useState<string | null>(null);

  // What-if weights: null means use default profile weights
  const [customWeights, setCustomWeights] = useState<Record<string, number> | null>(null);
  const [isCustomWeights, setIsCustomWeights] = useState(false);

  // Default profile weights (fetched from /api/mission/profiles)
  const [profileWeights, setProfileWeights] = useState<ProfileWeights>({
    settlement: { terrain: 0.25, water: 0.35, solar: 0.20, science: 0.10, edl: 0.10 },
    science: { terrain: 0.20, water: 0.15, solar: 0.15, science: 0.40, edl: 0.10 },
    resource: { terrain: 0.20, water: 0.30, solar: 0.15, science: 0.25, edl: 0.10 },
  });

  // Ranking explanation from the backend
  const [rankingExplanation, setRankingExplanation] = useState<RankingExplanation | null>(null);

  // Comparison view toggle and refresh key
  const [showComparison, setShowComparison] = useState(false);
  const [compareRefreshKey, setCompareRefreshKey] = useState(0);

  // Load sites once on mount
  useEffect(() => {
    fetch(`${API_BASE}/api/sites`)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(data => {
        setSites(data.sites);
        if (data.sites.length > 0) setSelectedSite(data.sites[0]);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to fetch sites:", err);
        setError("Cannot connect to the RedSite AI backend. Make sure the server is running on port 8000.");
        setLoading(false);
      });

    // Fetch analyst mode from health endpoint
    fetch(`${API_BASE}/api/health`)
      .then(r => r.json())
      .then(data => {
        setAnalystMode(data.features?.analyst_mode ?? "rule-based");
      })
      .catch(() => {});

    // Fetch mission profiles so weight editor starts with accurate defaults
    fetch(`${API_BASE}/api/mission/profiles`)
      .then(r => r.json())
      .then((data: Array<{ key: string; weights: Record<string, number> }>) => {
        const pw: ProfileWeights = {};
        data.forEach(p => { pw[p.key] = p.weights; });
        setProfileWeights(pw);
      })
      .catch(() => {});
  }, []);

  // Re-score whenever mission, sites, or custom weights change
  useEffect(() => {
    if (sites.length === 0) return;

    const body: Record<string, unknown> = { mission };
    if (customWeights) body.weights = customWeights;

    fetch(`${API_BASE}/api/score`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(data => {
        setRankings(data.rankings);
        setIsCustomWeights(data.is_custom_weights ?? false);
        setRankingExplanation(data.explanation ?? null);
        // Trigger comparison refresh whenever scores change
        setCompareRefreshKey(k => k + 1);
      })
      .catch(err => console.error("Failed to score:", err));
  }, [mission, sites, customWeights]);

  // Reset custom weights when mission changes
  const handleMissionChange = useCallback((newMission: string) => {
    setMission(newMission);
    setCustomWeights(null);
    setIsCustomWeights(false);
  }, []);

  // Handle weight changes from MissionWeightEditor (null = revert to default)
  const handleWeightsChange = useCallback(
    (weights: Record<string, number> | null) => {
      setCustomWeights(weights);
    },
    []
  );

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", color: "#666", background: "#0a0a0a" }}>
        Initializing RedSite AI…
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100vh", color: "#888", background: "#0a0a0a", gap: 12, padding: 32 }}>
        <div style={{ fontSize: 18, color: "#e0e0e0" }}>RedSite AI</div>
        <div style={{ fontSize: 14, color: "#e74c3c", maxWidth: 480, textAlign: "center" }}>{error}</div>
        <button
          onClick={() => window.location.reload()}
          style={{ marginTop: 8, padding: "8px 16px", borderRadius: 8, border: "1px solid #444", background: "#1a1a1a", color: "#e0e0e0", cursor: "pointer", fontSize: 13 }}
        >
          Retry
        </button>
      </div>
    );
  }

  const currentDefaultWeights = profileWeights[mission] ?? profileWeights["settlement"];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", background: "#0a0a0a", color: "#e0e0e0" }}>
      {/* Header */}
      <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 20px", borderBottom: "1px solid #333", flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ width: 30, height: 30, borderRadius: 8, background: "#e0e0e0", color: "#0a0a0a", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 600, fontSize: 13 }}>RS</div>
          <div>
            <div style={{ fontSize: 15, fontWeight: 500 }}>RedSite AI</div>
            <div style={{ fontSize: 11, color: "#888" }}>Mars site intelligence · Explainable decision engine</div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {/* Mission selector */}
          <select
            value={mission}
            onChange={e => handleMissionChange(e.target.value)}
            style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid #444", background: "#1a1a1a", color: "#e0e0e0", fontSize: 13 }}
          >
            <option value="settlement">Human settlement</option>
            <option value="science">Scientific discovery</option>
            <option value="resource">Resource extraction</option>
          </select>

          {/* Custom weights indicator */}
          {isCustomWeights && (
            <span style={{ fontSize: 12, color: "#f59e0b", display: "flex", alignItems: "center", gap: 4 }}>
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#f59e0b", display: "inline-block" }} />
              Custom weights
            </span>
          )}

          {/* Compare button */}
          <button
            onClick={() => setShowComparison(v => !v)}
            style={{
              padding: "6px 12px", borderRadius: 6, border: "1px solid #444",
              background: showComparison ? "#2a2a2a" : "transparent",
              color: showComparison ? "#e0e0e0" : "#888", fontSize: 12, cursor: "pointer",
              display: "flex", alignItems: "center", gap: 5
            }}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="2" y="3" width="8" height="18" rx="1"/><rect x="14" y="3" width="8" height="18" rx="1"/>
            </svg>
            Compare top-2
          </button>

          <span style={{ fontSize: 12, color: "#4ade80", display: "flex", alignItems: "center", gap: 4 }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#4ade80", display: "inline-block" }} />
            Systems nominal
          </span>
        </div>
      </header>

      {/* Main content */}
      <div style={{
        display: "grid",
        gridTemplateColumns: showComparison ? "1.1fr 0.9fr 1fr 0.95fr" : "1.2fr 1fr 1fr",
        gap: 14,
        padding: 14,
        flex: 1,
        minHeight: 0,
        overflowY: "auto",
      }}>
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
          defaultWeights={currentDefaultWeights}
          isCustomWeights={isCustomWeights}
          rankingExplanation={rankingExplanation}
          onSelectSite={setSelectedSite}
          onWeightsChange={handleWeightsChange}
        />
        {showComparison && (
          <div style={{ minHeight: 0, overflowY: "auto" }}>
            <ComparisonView
              mission={mission}
              customWeights={customWeights}
              apiBase={API_BASE}
              refreshKey={compareRefreshKey}
              onClose={() => setShowComparison(false)}
            />
          </div>
        )}
        <AnalystChat
          selectedSite={selectedSite}
          mission={mission}
          apiBase={API_BASE}
          sites={sites}
          rankings={rankings}
          analystMode={analystMode}
          customWeights={customWeights}
          isCustomWeights={isCustomWeights}
        />
      </div>
    </div>
  );
}
