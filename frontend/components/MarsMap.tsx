"use client";

import { useRef, useEffect, useCallback, useState } from "react";

interface Site {
  id: string;
  name: string;
  code: string;
  x: number;
  y: number;
  features: { terrain: number; water: number; solar: number; science: number; edl: number };
}

interface Ranking {
  site_id: string;
  score: number;
  rank: number;
}

interface Props {
  sites: Site[];
  rankings: Ranking[];
  activeLayer: string;
  selectedSite: Site | null;
  onSelectSite: (site: Site) => void;
  onLayerChange: (layer: string) => void;
}

const LAYERS = [
  { key: "elevation", label: "Elevation" },
  { key: "ice", label: "Ice" },
  { key: "slope", label: "Slope" },
  { key: "solar", label: "Solar" },
  { key: "science", label: "Science" },
];

const LAYER_COLORS: Record<string, Record<string, string>> = {
  elevation: { arc: "#4a90d9", val: "#e74c3c", gal: "#f39c12", uto: "#27ae60", hel: "#9b59b6" },
  ice: { arc: "#3498db", val: "#95a5a6", gal: "#bdc3c7", uto: "#2980b9", hel: "#7f8c8d" },
  slope: { arc: "#2ecc71", val: "#e74c3c", gal: "#f1c40f", uto: "#2ecc71", hel: "#e67e22" },
  solar: { arc: "#f1c40f", val: "#f39c12", gal: "#f1c40f", uto: "#e67e22", hel: "#f39c12" },
  science: { arc: "#95a5a6", val: "#e74c3c", gal: "#c0392b", uto: "#7f8c8d", hel: "#d35400" },
};

export default function MarsMap({ sites, rankings, activeLayer, selectedSite, onSelectSite, onLayerChange }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; site: Site } | null>(null);
  const [canvasSize, setCanvasSize] = useState({ w: 0, h: 0 });

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d")!;
    const w = canvasSize.w;
    const h = canvasSize.h;
    const cx = w / 2;
    const cy = h / 2;
    const r = Math.min(cx, cy) * 0.85;

    ctx.clearRect(0, 0, w, h);

    // Mars body
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fillStyle = "#c25e28";
    ctx.fill();
    ctx.strokeStyle = "#444";
    ctx.lineWidth = 1;
    ctx.stroke();

    // Surface features
    ctx.save();
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.clip();
    ctx.fillStyle = "rgba(0,0,0,0.15)";
    ctx.beginPath(); ctx.ellipse(cx - r * 0.2, cy - r * 0.1, r * 0.35, r * 0.2, 0.3, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.ellipse(cx + r * 0.3, cy + r * 0.2, r * 0.25, r * 0.15, -0.2, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = "rgba(255,255,255,0.08)";
    ctx.beginPath(); ctx.ellipse(cx - r * 0.1, cy - r * 0.35, r * 0.2, r * 0.15, 0, 0, Math.PI * 2); ctx.fill();
    ctx.restore();

    // Grid
    ctx.strokeStyle = "rgba(255,255,255,0.08)";
    ctx.lineWidth = 0.5;
    for (let i = 1; i < 4; i++) {
      ctx.beginPath(); ctx.arc(cx, cy, r * i / 4, 0, Math.PI * 2); ctx.stroke();
    }
    for (let a = 0; a < Math.PI * 2; a += Math.PI / 4) {
      ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r); ctx.stroke();
    }

    // Layer heat blobs
    const lc = LAYER_COLORS[activeLayer] || LAYER_COLORS.elevation;
    sites.forEach(s => {
      const sx = cx + (s.x - 0.5) * r * 1.6;
      const sy = cy + (s.y - 0.5) * r * 1.6;
      const val = s.features[activeLayer as keyof Site["features"]] || 50;
      const rad = r * 0.18 * (val / 100);
      const grad = ctx.createRadialGradient(sx, sy, 0, sx, sy, rad);
      const base = lc[s.id] || "#888";
      grad.addColorStop(0, base + "88");
      grad.addColorStop(1, base + "00");
      ctx.fillStyle = grad;
      ctx.beginPath(); ctx.arc(sx, sy, rad, 0, Math.PI * 2); ctx.fill();
    });

    // Site markers
    sites.forEach(s => {
      const sx = cx + (s.x - 0.5) * r * 1.6;
      const sy = cy + (s.y - 0.5) * r * 1.6;
      const isSel = s.id === selectedSite?.id;
      const rank = rankings.find(r => r.site_id === s.id)?.rank;

      if (isSel) {
        ctx.fillStyle = "rgba(255,255,255,0.15)";
        ctx.beginPath(); ctx.arc(sx, sy, 14, 0, Math.PI * 2); ctx.fill();
      }

      ctx.beginPath(); ctx.arc(sx, sy, isSel ? 6 : 4, 0, Math.PI * 2);
      ctx.fillStyle = isSel ? "#e0e0e0" : "#1a1a1a";
      ctx.fill();
      ctx.strokeStyle = isSel ? "#e0e0e0" : (rank === 1 ? "#4ade80" : "#888");
      ctx.lineWidth = isSel ? 2 : 1.5;
      ctx.stroke();

      if (rank && rank <= 3) {
        const colors = ["#4ade80", "#facc15", "#888"];
        ctx.fillStyle = colors[rank - 1];
        ctx.beginPath(); ctx.arc(sx + 10, sy - 10, 7, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = "#0a0a0a";
        ctx.font = "9px sans-serif";
        ctx.textAlign = "center"; ctx.textBaseline = "middle";
        ctx.fillText(String(rank), sx + 10, sy - 10);
      }

      ctx.fillStyle = isSel ? "#e0e0e0" : "#aaa";
      ctx.font = (isSel ? "500 11px" : "400 10px") + " sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(s.code, sx, sy + (isSel ? 18 : 14));
    });
  }, [sites, rankings, activeLayer, selectedSite, canvasSize]);

  useEffect(() => {
    const resize = () => {
      const parent = canvasRef.current?.parentElement;
      if (!parent) return;
      const rect = parent.getBoundingClientRect();
      setCanvasSize({ w: rect.width, h: rect.height });
    };
    resize();
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
  }, []);

  useEffect(() => {
    draw();
  }, [draw]);

  const handleMouseMove = (e: React.MouseEvent) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const cx = canvasSize.w / 2;
    const cy = canvasSize.h / 2;
    const r = Math.min(cx, cy) * 0.85;

    let hit: Site | null = null;
    sites.forEach(s => {
      const sx = cx + (s.x - 0.5) * r * 1.6;
      const sy = cy + (s.y - 0.5) * r * 1.6;
      if (Math.hypot(mx - sx, my - sy) < 14) hit = s;
    });

    if (hit) {
      setTooltip({ x: mx + 12, y: my - 8, site: hit });
    } else {
      setTooltip(null);
    }
  };

  const handleClick = (e: React.MouseEvent) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const cx = canvasSize.w / 2;
    const cy = canvasSize.h / 2;
    const r = Math.min(cx, cy) * 0.85;

    sites.forEach(s => {
      const sx = cx + (s.x - 0.5) * r * 1.6;
      const sy = cy + (s.y - 0.5) * r * 1.6;
      if (Math.hypot(mx - sx, my - sy) < 14) onSelectSite(s);
    });
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12, minHeight: 0 }}>
      <div style={{ fontSize: 14, fontWeight: 500, color: "#aaa", display: "flex", alignItems: "center", gap: 6 }}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={{ color: "#666" }}>
          <circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/>
        </svg>
        Planetary overview
      </div>
      <div style={{ position: "relative", flex: 1, borderRadius: 12, border: "1px solid #333", overflow: "hidden", background: "#111", minHeight: 320 }}>
        <canvas
          ref={canvasRef}
          width={canvasSize.w * 2}
          height={canvasSize.h * 2}
          style={{ width: "100%", height: "100%", display: "block" }}
          onMouseMove={handleMouseMove}
          onClick={handleClick}
          onMouseLeave={() => setTooltip(null)}
        />
        {tooltip && (
          <div style={{
            position: "absolute", left: tooltip.x, top: tooltip.y,
            background: "#1a1a1a", border: "1px solid #444", borderRadius: 8,
            padding: "8px 12px", fontSize: 12, color: "#e0e0e0", pointerEvents: "none",
            boxShadow: "0 2px 8px rgba(0,0,0,0.5)", zIndex: 10, maxWidth: 180
          }}>
            <div style={{ fontWeight: 500, marginBottom: 2 }}>{tooltip.site.name}</div>
            <div style={{ color: "#888" }}>
              Score: {rankings.find(r => r.site_id === tooltip.site.id)?.score || "—"}/100
            </div>
          </div>
        )}
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        {LAYERS.map(layer => (
          <button
            key={layer.key}
            onClick={() => onLayerChange(layer.key)}
            style={{
              fontSize: 12, padding: "5px 10px", borderRadius: 6,
              border: "1px solid #444",
              background: activeLayer === layer.key ? "#2a2a2a" : "transparent",
              color: activeLayer === layer.key ? "#e0e0e0" : "#888",
              cursor: "pointer", fontWeight: 500
            }}
          >
            {layer.label}
          </button>
        ))}
      </div>
    </div>
  );
}
