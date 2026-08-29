"use client";

import { useMemo } from "react";
import ScoreDecomposition from "./ScoreDecomposition";
import MissionWeightEditor from "./MissionWeightEditor";

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

interface Props {
  sites: Site[];
  rankings: Ranking[];
  selectedSite: Site | null;
  mission: string;
  defaultWeights: Record<string, number>;
  isCustomWeights: boolean;
  rankingExplanation: RankingExplanation | null;
  onSelectSite: (site: Site) => void;
  onWeightsChange: (weights: Record<string, number> | null) => void;
}

const ATTR_LABELS: Record<string, string> = {
  terrain: "Terrain safety",
  water: "Water access",
  solar: "Solar potential",
  science: "Science value",
  edl: "EDL safety",
};

const ATTR_COLORS: Record<string, string> = {
  terrain: "#3b82f6",
  water: "#06b6d4",
  solar: "#22c55e",
  science: "#a855f7",
  edl: "#6b7280",
};

const MISSION_NAMES: Record<string, string> = {
  settlement: "Human settlement",
  science: "Scientific discovery",
  resource: "Resource extraction",
};

export default function SiteDashboard({
  sites,
  rankings,
  selectedSite,
  mission,
  defaultWeights,
  isCustomWeights,
  rankingExplanation,
  onSelectSite,
  onWeightsChange,
}: Props) {
  const sortedSites = useMemo(() => {
    const rankMap = new Map(rankings.map(r => [r.site_id, r]));
    return [...sites]
      .map(s => ({ ...s, rankInfo: rankMap.get(s.id) }))
      .sort((a, b) => (b.rankInfo?.score || 0) - (a.rankInfo?.score || 0));
  }, [sites, rankings]);

  const radarPoints = useMemo(() => {
    if (!selectedSite) return "";
    const attrs = ["terrain", "water", "solar", "science", "edl"];
    const n = attrs.length;
    const cx = 100, cy = 100, r = 70;
    return attrs.map((attr, i) => {
      const a = (Math.PI * 2 * i / n) - Math.PI / 2;
      const rr = r * (selectedSite.features[attr as keyof Site["features"]] / 100);
      return `${cx + rr * Math.cos(a)},${cy + rr * Math.sin(a)}`;
    }).join(" ");
  }, [selectedSite]);

  const selectedRanking = useMemo(
    () => rankings.find(r => r.site_id === selectedSite?.id),
    [rankings, selectedSite]
  );

  if (!selectedSite) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12, minHeight: 0, overflowY: "auto" }}>

      {/* What-if Weight Editor */}
      <div style={{ border: "1px solid #333", borderRadius: 12, padding: 14, display: "flex", flexDirection: "column", gap: 10 }}>
        <MissionWeightEditor
          mission={mission}
          defaultWeights={defaultWeights}
          onWeightsChange={onWeightsChange}
          isCustom={isCustomWeights}
        />
      </div>

      {/* Ranking Explanation */}
      {rankingExplanation && (
        <div style={{
          border: "1px solid #2a2a2a", borderRadius: 10, padding: 12,
          background: "#0d0d0d", display: "flex", flexDirection: "column", gap: 6
        }}>
          <div style={{ fontSize: 11, color: "#555", fontWeight: 500, display: "flex", alignItems: "center", gap: 5 }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#4ade80", display: "inline-block" }} />
            RANKING ANALYSIS
            {isCustomWeights && (
              <span style={{ fontSize: 10, color: "#f59e0b" }}>· custom weights</span>
            )}
          </div>
          <div style={{ fontSize: 12, color: "#aaa", lineHeight: 1.55 }}>
            {rankingExplanation.text}
          </div>
        </div>
      )}

      {/* Candidate Sites */}
      <div style={{ border: "1px solid #333", borderRadius: 12, padding: 14, display: "flex", flexDirection: "column", gap: 10 }}>
        <div style={{ fontSize: 14, fontWeight: 500, color: "#aaa", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={{ color: "#666" }}>
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>
            </svg>
            Candidate sites
          </span>
          <span style={{ fontSize: 12, color: "#666", fontWeight: 400 }}>
            {MISSION_NAMES[mission] || mission}
            {isCustomWeights && <span style={{ color: "#f59e0b" }}> · modified</span>}
          </span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
          {sortedSites.map((s, idx) => {
            const isSel = s.id === selectedSite.id;
            const rankColors = ["#4ade80", "#facc15", "#888"];
            const rankColor = idx < 3 ? rankColors[idx] : "#555";
            return (
              <div
                key={s.id}
                onClick={() => onSelectSite(s)}
                style={{
                  padding: "8px 10px", borderRadius: 8,
                  border: `1px solid ${isSel ? "#e0e0e0" : "#333"}`,
                  background: isSel ? "#1a1a1a" : "transparent",
                  cursor: "pointer", display: "flex", alignItems: "center", gap: 10,
                  transition: "all 0.15s ease"
                }}
              >
                <span style={{
                  width: 20, height: 20, borderRadius: "50%", background: rankColor,
                  color: "#0a0a0a", display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 10, fontWeight: 600, flexShrink: 0
                }}>{idx + 1}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 500, color: "#e0e0e0", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{s.name}</div>
                  <div style={{ fontSize: 11, color: "#666" }}>{s.code}</div>
                </div>
                <div style={{ fontSize: 16, fontWeight: 500, color: isSel ? "#e0e0e0" : "#aaa", fontVariantNumeric: "tabular-nums" }}>
                  {s.rankInfo?.score ?? "—"}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Score Decomposition */}
      {selectedRanking?.decomposition && (
        <div style={{ border: "1px solid #333", borderRadius: 12, padding: 14 }}>
          <ScoreDecomposition
            siteName={selectedSite.name}
            siteCode={selectedSite.code}
            score={selectedRanking.score}
            decomposition={selectedRanking.decomposition}
            isCustomWeights={isCustomWeights}
          />
        </div>
      )}

      {/* Radar Chart */}
      <div style={{ border: "1px solid #333", borderRadius: 12, padding: 14, display: "flex", flexDirection: "column", gap: 8, minHeight: 200 }}>
        <div style={{ fontSize: 13, fontWeight: 500, color: "#aaa", display: "flex", alignItems: "center", gap: 6 }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={{ color: "#666" }}>
            <polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 12 22 17"/><polyline points="2 12 12 17 22 12"/>
          </svg>
          Feature profile — {selectedSite.code}
        </div>
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", minHeight: 160 }}>
          <svg width="180" height="180" viewBox="0 0 200 200">
            {/* Grid */}
            {[20, 40, 60, 80, 100].map(level => {
              const pts = ["terrain", "water", "solar", "science", "edl"].map((_, i) => {
                const a = (Math.PI * 2 * i / 5) - Math.PI / 2;
                const rr = 70 * level / 100;
                return `${100 + rr * Math.cos(a)},${100 + rr * Math.sin(a)}`;
              }).join(" ");
              return <polygon key={level} points={pts} fill="none" stroke="#333" strokeWidth="0.5" />;
            })}
            {/* Axes */}
            {[0, 1, 2, 3, 4].map(i => {
              const a = (Math.PI * 2 * i / 5) - Math.PI / 2;
              return <line key={i} x1="100" y1="100" x2={100 + 70 * Math.cos(a)} y2={100 + 70 * Math.sin(a)} stroke="#333" strokeWidth="0.5" />;
            })}
            {/* Labels */}
            {["terrain", "water", "solar", "science", "edl"].map((attr, i) => {
              const a = (Math.PI * 2 * i / 5) - Math.PI / 2;
              const lx = 100 + 86 * Math.cos(a);
              const ly = 100 + 86 * Math.sin(a);
              return <text key={attr} x={lx} y={ly} textAnchor="middle" dominantBaseline="middle" fontSize="10" fill="#666" fontFamily="sans-serif">{ATTR_LABELS[attr].split(" ")[0]}</text>;
            })}
            {/* Data */}
            <polygon points={radarPoints} fill="rgba(59, 130, 246, 0.15)" stroke="#3b82f6" strokeWidth="1.5" />
            {selectedSite && ["terrain", "water", "solar", "science", "edl"].map((attr, i) => {
              const a = (Math.PI * 2 * i / 5) - Math.PI / 2;
              const rr = 70 * (selectedSite.features[attr as keyof Site["features"]] / 100);
              return <circle key={attr} cx={100 + rr * Math.cos(a)} cy={100 + rr * Math.sin(a)} r="3" fill="#3b82f6" />;
            })}
          </svg>
        </div>
      </div>
    </div>
  );
}
