"use client";

interface FeatureContribution {
  raw_score: number;
  weight: number;
  contribution: number;
  percentage: number;
}

interface ScoreDecompositionProps {
  siteName: string;
  siteCode: string;
  score: number;
  decomposition: Record<string, FeatureContribution>;
  isCustomWeights?: boolean;
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

export default function ScoreDecomposition({
  siteName,
  siteCode,
  score,
  decomposition,
  isCustomWeights,
}: ScoreDecompositionProps) {
  if (!decomposition || Object.keys(decomposition).length === 0) return null;

  // Max contribution for scaling bars
  const maxContrib = Math.max(...Object.values(decomposition).map(d => d.contribution));

  // Verify determinism: sum of contributions should equal score
  const contribSum = Object.values(decomposition).reduce((a, d) => a + d.contribution, 0);
  const checksOut = Math.abs(contribSum - score) < 0.15;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between"
      }}>
        <div style={{ fontSize: 13, fontWeight: 500, color: "#aaa", display: "flex", alignItems: "center", gap: 6 }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: "#666" }}>
            <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/>
          </svg>
          Score decomposition — {siteCode}
          {isCustomWeights && (
            <span style={{
              fontSize: 10, padding: "1px 5px", borderRadius: 4,
              background: "#1c1600", border: "1px solid #4a3800", color: "#f59e0b"
            }}>
              custom weights
            </span>
          )}
        </div>
        <div style={{
          fontSize: 14, fontWeight: 600, color: "#e0e0e0",
          fontVariantNumeric: "tabular-nums"
        }}>
          {score}
          <span style={{ fontSize: 11, color: "#888", fontWeight: 400 }}>/100</span>
        </div>
      </div>

      {FEATURES.filter(f => decomposition[f]).map(feat => {
        const d = decomposition[feat];
        const barWidth = maxContrib > 0 ? (d.contribution / maxContrib) * 100 : 0;
        return (
          <div key={feat} style={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 11, color: "#888", width: 92, flexShrink: 0 }}>
                {FEATURE_LABELS[feat]}
              </span>
              {/* Contribution bar */}
              <div style={{ flex: 1, height: 14, background: "#1a1a1a", borderRadius: 3, overflow: "hidden", position: "relative" }}>
                <div style={{
                  width: `${barWidth}%`, height: "100%",
                  background: FEATURE_COLORS[feat],
                  borderRadius: 3,
                  opacity: 0.85,
                  transition: "width 0.3s ease",
                  display: "flex", alignItems: "center", justifyContent: "flex-end", paddingRight: 4,
                }} />
              </div>
              {/* Contribution value */}
              <span style={{
                fontSize: 11, color: "#e0e0e0", width: 34, textAlign: "right",
                fontWeight: 500, fontVariantNumeric: "tabular-nums"
              }}>
                {d.contribution.toFixed(1)}
              </span>
            </div>
            {/* Detail row */}
            <div style={{
              display: "flex", gap: 4, paddingLeft: 100, fontSize: 10, color: "#555"
            }}>
              <span>{d.raw_score}/100</span>
              <span style={{ color: "#444" }}>×</span>
              <span>{(d.weight * 100).toFixed(0)}% weight</span>
              <span style={{ color: "#444" }}>=</span>
              <span style={{ color: "#666" }}>{d.contribution.toFixed(2)} pts</span>
              <span style={{ color: "#444", marginLeft: 4 }}>({d.percentage.toFixed(1)}%)</span>
            </div>
          </div>
        );
      })}

      {/* Determinism check */}
      <div style={{
        display: "flex", alignItems: "center", gap: 6, marginTop: 2,
        fontSize: 10, color: checksOut ? "#4ade80" : "#e74c3c"
      }}>
        <span style={{
          width: 6, height: 6, borderRadius: "50%",
          background: checksOut ? "#4ade80" : "#e74c3c",
          display: "inline-block", flexShrink: 0
        }} />
        Sum of contributions: {contribSum.toFixed(2)} ≈ {score} (
        {checksOut ? "✓ deterministic" : "⚠ rounding delta"})
      </div>
    </div>
  );
}
