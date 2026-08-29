"use client";

import { useState, useEffect, useCallback } from "react";

interface WeightEditorProps {
  mission: string;
  defaultWeights: Record<string, number>;
  onWeightsChange: (weights: Record<string, number> | null) => void;
  isCustom: boolean;
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

/** Normalize a weight map so values sum exactly to 1.0 */
function normalize(weights: Record<string, number>): Record<string, number> {
  const total = Object.values(weights).reduce((a, b) => a + b, 0);
  if (total <= 0) return weights;
  return Object.fromEntries(Object.entries(weights).map(([k, v]) => [k, v / total]));
}

export default function MissionWeightEditor({
  mission,
  defaultWeights,
  onWeightsChange,
  isCustom,
}: WeightEditorProps) {
  // Internal slider state (0–100 raw, will be normalized before sending)
  const [sliders, setSliders] = useState<Record<string, number>>(() =>
    Object.fromEntries(FEATURES.map(f => [f, Math.round((defaultWeights[f] ?? 0.2) * 100)]))
  );

  // When mission changes, reset sliders to new defaults
  useEffect(() => {
    setSliders(
      Object.fromEntries(FEATURES.map(f => [f, Math.round((defaultWeights[f] ?? 0.2) * 100)]))
    );
  }, [mission, defaultWeights]);

  const handleSliderChange = useCallback(
    (feature: string, rawValue: number) => {
      const updated = { ...sliders, [feature]: rawValue };
      setSliders(updated);

      // Normalize and send upstream (as fractions summing to 1)
      const rawFractions = Object.fromEntries(
        Object.entries(updated).map(([k, v]) => [k, v / 100])
      );
      const normalized = normalize(rawFractions);
      onWeightsChange(normalized);
    },
    [sliders, onWeightsChange]
  );

  const handleReset = useCallback(() => {
    setSliders(
      Object.fromEntries(FEATURES.map(f => [f, Math.round((defaultWeights[f] ?? 0.2) * 100)]))
    );
    onWeightsChange(null); // null = revert to default
  }, [defaultWeights, onWeightsChange]);

  // Compute normalized display weights for live percentage labels
  const rawFractions = Object.fromEntries(
    Object.entries(sliders).map(([k, v]) => [k, v / 100])
  );
  const displayWeights = normalize(rawFractions);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8
      }}>
        <div style={{ fontSize: 13, fontWeight: 500, color: "#aaa", display: "flex", alignItems: "center", gap: 6 }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: "#666" }}>
            <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
          </svg>
          What-if weights
          {isCustom && (
            <span style={{
              fontSize: 10, padding: "1px 5px", borderRadius: 4,
              background: "#1c1600", border: "1px solid #4a3800", color: "#f59e0b"
            }}>
              MODIFIED
            </span>
          )}
        </div>
        {isCustom && (
          <button
            onClick={handleReset}
            title="Reset to default mission weights"
            style={{
              fontSize: 11, padding: "2px 7px", borderRadius: 4,
              border: "1px solid #444", background: "transparent",
              color: "#888", cursor: "pointer"
            }}
          >
            Reset
          </button>
        )}
      </div>

      {FEATURES.map(feat => (
        <div key={feat} style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 11, color: "#888", width: 92, flexShrink: 0 }}>
            {FEATURE_LABELS[feat]}
          </span>
          <input
            type="range"
            min={0}
            max={100}
            value={sliders[feat]}
            onChange={e => handleSliderChange(feat, Number(e.target.value))}
            style={{
              flex: 1,
              accentColor: FEATURE_COLORS[feat],
              cursor: "pointer",
              height: 4,
            }}
          />
          <span style={{
            fontSize: 11, color: isCustom && Math.abs(displayWeights[feat] - (defaultWeights[feat] ?? 0)) > 0.005
              ? "#f59e0b"
              : "#aaa",
            width: 36, textAlign: "right", fontWeight: 500, fontVariantNumeric: "tabular-nums"
          }}>
            {Math.round(displayWeights[feat] * 100)}%
          </span>
        </div>
      ))}

      {/* Sum indicator — always 100% when normalized */}
      <div style={{ display: "flex", gap: 4, marginTop: 2 }}>
        {FEATURES.map(feat => (
          <div
            key={feat}
            title={`${FEATURE_LABELS[feat]}: ${Math.round(displayWeights[feat] * 100)}%`}
            style={{
              flex: displayWeights[feat],
              height: 3,
              background: FEATURE_COLORS[feat],
              borderRadius: 2,
              transition: "flex 0.2s ease",
            }}
          />
        ))}
      </div>
    </div>
  );
}
