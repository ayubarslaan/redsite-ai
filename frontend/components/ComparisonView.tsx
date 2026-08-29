"use client";

import { useEffect, useState, useCallback } from "react";

interface FeatureContribution {
  raw_score: number;
  weight: number;
  contribution: number;
  percentage: number;
}

interface CompareEntry {
  site_id: string;
  site_name: string;
  site_code: string;
  rank: number;
  score: number;
  decomposition: Record<string, FeatureContribution>;
  strengths: string[];
  weaknesses: string[];
}

interface CompareResponse {
  mission: string;
  weights_used: Record<string, number>;
  sites: CompareEntry[];
  narrative: string;
}

interface ComparisonViewProps {
  mission: string;
  customWeights: Record<string, number> | null;
  apiBase: string;
  /** Trigger to re-fetch when this changes */
  refreshKey?: number;
  onClose?: () => void;
}

const FEATURE_LABELS: Record<string, string> = {
  terrain: "Terrain safety",
  water: "Water access",
  solar: "Solar potential",
  science: "Science value",
  edl: "EDL safety",
};

const FEATURE_COLORS: Record<string, string> = {
  terrain: "#3b82f6",
  water: "#06b6d4",
  solar: "#22c55e",
  science: "#a855f7",
  edl: "#6b7280",
};

const FEATURES = ["terrain", "water", "solar", "science", "edl"];

export default function ComparisonView({
  mission,
  customWeights,
  apiBase,
  refreshKey,
  onClose,
}: ComparisonViewProps) {
  const [data, setData] = useState<CompareResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchComparison = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const body: Record<string, unknown> = { mission };
      if (customWeights) body.weights = customWeights;

      const res = await fetch(`${apiBase}/api/compare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json: CompareResponse = await res.json();
      setData(json);
    } catch (e: unknown) {
      setError((e as Error).message ?? "Failed to load comparison.");
    } finally {
      setLoading(false);
    }
  }, [mission, customWeights, apiBase]);

  useEffect(() => {
    fetchComparison();
  }, [fetchComparison, refreshKey]);

  const container: React.CSSProperties = {
    border: "1px solid #333", borderRadius: 12, padding: 16,
    display: "flex", flexDirection: "column", gap: 14,
    background: "#111",
  };

  const heading: React.CSSProperties = {
    display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8,
  };

  if (loading) {
    return (
      <div style={container}>
        <div style={heading}>
          <span style={{ fontSize: 13, fontWeight: 500, color: "#aaa" }}>Site comparison</span>
        </div>
        <div style={{ fontSize: 12, color: "#666" }}>Loading…</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={container}>
        <div style={heading}>
          <span style={{ fontSize: 13, fontWeight: 500, color: "#aaa" }}>Site comparison</span>
          {onClose && (
            <button onClick={onClose} style={{ background: "none", border: "none", color: "#666", cursor: "pointer", fontSize: 16, lineHeight: 1 }}>×</button>
          )}
        </div>
        <div style={{ fontSize: 12, color: "#e74c3c" }}>{error ?? "No data"}</div>
      </div>
    );
  }

  const [s1, s2] = data.sites;
  if (!s1 || !s2) return null;

  // Max raw score across both sites for each feature — for bar scaling
  const maxRaw: Record<string, number> = {};
  FEATURES.forEach(f => {
    maxRaw[f] = Math.max(
      s1.decomposition[f]?.raw_score ?? 0,
      s2.decomposition[f]?.raw_score ?? 0
    );
  });
  const maxContrib1 = Math.max(...FEATURES.map(f => s1.decomposition[f]?.contribution ?? 0));
  const maxContrib2 = Math.max(...FEATURES.map(f => s2.decomposition[f]?.contribution ?? 0));
  const maxContrib = Math.max(maxContrib1, maxContrib2);

  const rankColors = ["#4ade80", "#facc15"];

  return (
    <div style={container}>
      {/* Header */}
      <div style={heading}>
        <div style={{ fontSize: 13, fontWeight: 500, color: "#aaa", display: "flex", alignItems: "center", gap: 6 }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: "#666" }}>
            <rect x="2" y="3" width="8" height="18" rx="1"/><rect x="14" y="3" width="8" height="18" rx="1"/>
          </svg>
          Top-2 comparison — {data.mission}
        </div>
        {onClose && (
          <button onClick={onClose} style={{ background: "none", border: "none", color: "#666", cursor: "pointer", fontSize: 16, lineHeight: 1 }}>×</button>
        )}
      </div>

      {/* Side-by-side score header */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        {data.sites.map((s, i) => (
          <div key={s.site_id} style={{
            padding: "8px 10px", borderRadius: 8,
            border: `1px solid ${rankColors[i]}44`,
            background: `${rankColors[i]}11`,
            display: "flex", flexDirection: "column", gap: 2
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{
                width: 18, height: 18, borderRadius: "50%", background: rankColors[i],
                color: "#0a0a0a", display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 9, fontWeight: 600, flexShrink: 0
              }}>{i + 1}</span>
              <span style={{ fontSize: 12, fontWeight: 500, color: "#e0e0e0" }}>{s.site_name}</span>
            </div>
            <div style={{ fontSize: 20, fontWeight: 600, color: rankColors[i], paddingLeft: 24 }}>
              {s.score}
              <span style={{ fontSize: 11, color: "#888", fontWeight: 400 }}>/100</span>
            </div>
          </div>
        ))}
      </div>

      {/* Feature-by-feature comparison */}
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <div style={{ fontSize: 11, color: "#555", fontWeight: 500 }}>WEIGHTED CONTRIBUTIONS</div>
        {FEATURES.filter(f => s1.decomposition[f] || s2.decomposition[f]).map(feat => {
          const d1 = s1.decomposition[feat];
          const d2 = s2.decomposition[feat];
          if (!d1 || !d2) return null;

          const bar1 = maxContrib > 0 ? (d1.contribution / maxContrib) * 100 : 0;
          const bar2 = maxContrib > 0 ? (d2.contribution / maxContrib) * 100 : 0;
          const leader = d1.contribution >= d2.contribution ? 0 : 1;

          return (
            <div key={feat}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                <span style={{ fontSize: 11, color: "#888", flex: 1 }}>{FEATURE_LABELS[feat]}</span>
                <span style={{ fontSize: 10, color: FEATURE_COLORS[feat] }}>
                  weight {(d1.weight * 100).toFixed(0)}%
                </span>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4 }}>
                {[{ entry: s1, d: d1, bar: bar1, idx: 0 }, { entry: s2, d: d2, bar: bar2, idx: 1 }].map(
                  ({ entry, d, bar, idx }) => (
                    <div key={entry.site_id} style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                      <div style={{ height: 12, background: "#1a1a1a", borderRadius: 3, overflow: "hidden" }}>
                        <div style={{
                          width: `${bar}%`, height: "100%",
                          background: FEATURE_COLORS[feat],
                          opacity: leader === idx ? 0.9 : 0.45,
                          borderRadius: 3, transition: "width 0.3s ease",
                        }} />
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10 }}>
                        <span style={{ color: "#666" }}>{d.raw_score}/100</span>
                        <span style={{
                          color: leader === idx ? rankColors[idx] : "#666",
                          fontWeight: leader === idx ? 600 : 400
                        }}>
                          {d.contribution.toFixed(1)} pts
                        </span>
                      </div>
                    </div>
                  )
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Strengths and weaknesses */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        {data.sites.map((s, i) => (
          <div key={s.site_id} style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <div style={{ fontSize: 11, color: "#555", fontWeight: 500 }}>{s.site_name.toUpperCase()}</div>
            {s.strengths.length > 0 && (
              <div>
                <div style={{ fontSize: 10, color: "#4ade80", marginBottom: 2 }}>▲ Strengths</div>
                {s.strengths.map(str => (
                  <div key={str} style={{ fontSize: 11, color: "#888", paddingLeft: 8 }}>• {str}</div>
                ))}
              </div>
            )}
            {s.weaknesses.length > 0 && (
              <div>
                <div style={{ fontSize: 10, color: "#e74c3c", marginBottom: 2 }}>▼ Weaknesses</div>
                {s.weaknesses.map(wk => (
                  <div key={wk} style={{ fontSize: 11, color: "#888", paddingLeft: 8 }}>• {wk}</div>
                ))}
              </div>
            )}
            {s.strengths.length === 0 && s.weaknesses.length === 0 && (
              <div style={{ fontSize: 11, color: "#555" }}>Similar profile</div>
            )}
          </div>
        ))}
      </div>

      {/* Narrative */}
      <div style={{
        padding: "10px 12px", borderRadius: 8, border: "1px solid #2a2a2a",
        background: "#0d0d0d", fontSize: 12, color: "#aaa", lineHeight: 1.6
      }}>
        <div style={{ fontSize: 10, color: "#555", fontWeight: 500, marginBottom: 4 }}>
          RANKING ANALYSIS (from score engine)
        </div>
        {data.narrative}
      </div>
    </div>
  );
}
