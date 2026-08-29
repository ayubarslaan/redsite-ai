"use client";

import { useRef, useEffect, useCallback, useState } from "react";

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
  elevation: { "arc-01": "#4a90d9", "val-02": "#e74c3c", "gal-03": "#f39c12", "uto-04": "#27ae60", "hel-05": "#9b59b6" },
  ice:       { "arc-01": "#3498db", "val-02": "#95a5a6", "gal-03": "#bdc3c7", "uto-04": "#2980b9", "hel-05": "#7f8c8d" },
  slope:     { "arc-01": "#2ecc71", "val-02": "#e74c3c", "gal-03": "#f1c40f", "uto-04": "#2ecc71", "hel-05": "#e67e22" },
  solar:     { "arc-01": "#f1c40f", "val-02": "#f39c12", "gal-03": "#f1c40f", "uto-04": "#e67e22", "hel-05": "#f39c12" },
  science:   { "arc-01": "#95a5a6", "val-02": "#e74c3c", "gal-03": "#c0392b", "uto-04": "#7f8c8d", "hel-05": "#d35400" },
};

/**
 * Convert geographic lat/lon to canvas coordinates on the Mars globe.
 * Uses an equirectangular projection centred on the disc.
 *
 * lat: -90 (south pole) … +90 (north pole)   → mapped to canvas top … bottom
 * lon: -180 … +180 (east)                     → mapped to canvas left … right
 *
 * Returns normalised [0,1] fractions that the draw loop multiplies by the
 * canvas radius so sites appear at their actual planetary positions.
 */
function latLonToXY(lat: number, lon: number): { nx: number; ny: number } {
  // Normalise longitude to [0, 1] left-to-right
  const nx = (lon + 180) / 360;
  // Normalise latitude to [0, 1] top-to-bottom (north = 0, south = 1)
  const ny = (90 - lat) / 180;
  return { nx, ny };
}

export default function MarsMap({ sites, rankings, activeLayer, selectedSite, onSelectSite, onLayerChange }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; site: Site } | null>(null);
  const [canvasSize, setCanvasSize] = useState({ w: 0, h: 0 });

  /** Convert a site's lat/lon to canvas pixel position */
  const siteToCanvas = useCallback((site: Site, cx: number, cy: number, r: number) => {
    const { nx, ny } = latLonToXY(site.coordinates.lat, site.coordinates.lon);
    // Scale to the disc: nx=0.5 lon=0° → cx, ny=0.5 lat=0° → cy
    const sx = cx + (nx - 0.5) * r * 1.8;
    const sy = cy + (ny - 0.5) * r * 1.8;
    return { sx, sy };
  }, []);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d")!;
    const w = canvasSize.w;
    const h = canvasSize.h;
    if (w === 0 || h === 0) return;
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

    // Grid lines (lat/lon reference)
    ctx.strokeStyle = "rgba(255,255,255,0.08)";
    ctx.lineWidth = 0.5;
    // Latitude circles (equator, ±30, ±60)
    [-60, -30, 0, 30, 60].forEach(lat => {
      const ny = (90 - lat) / 180;
      const yPos = cy + (ny - 0.5) * r * 1.8;
      const halfWidth = Math.sqrt(Math.max(0, r * r - (yPos - cy) * (yPos - cy)));
      if (halfWidth > 0) {
        ctx.beginPath(); ctx.ellipse(cx, yPos, halfWidth, halfWidth * 0.3, 0, 0, Math.PI * 2); ctx.stroke();
      }
    });
    // Longitude lines every 60°
    for (let lon = -180; lon < 180; lon += 60) {
      const nx = (lon + 180) / 360;
      const xPos = cx + (nx - 0.5) * r * 1.8;
      ctx.beginPath(); ctx.moveTo(xPos, cy - r * 0.9); ctx.lineTo(xPos, cy + r * 0.9); ctx.stroke();
    }

    const lc = LAYER_COLORS[activeLayer] || LAYER_COLORS.elevation;

    // Layer heat blobs
    sites.forEach(s => {
      const { sx, sy } = siteToCanvas(s, cx, cy, r);
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
      const { sx, sy } = siteToCanvas(s, cx, cy, r);
      const isSel = s.id === selectedSite?.id;
      const rank = rankings.find(rk => rk.site_id === s.id)?.rank;

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
  }, [sites, rankings, activeLayer, selectedSite, canvasSize, siteToCanvas]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    // Set pixel dimensions from logical size (handle devicePixelRatio)
    const dpr = window.devicePixelRatio || 1;
    canvas.width = canvasSize.w * dpr;
    canvas.height = canvasSize.h * dpr;
    const ctx = canvas.getContext("2d");
    if (ctx) ctx.scale(dpr, dpr);
    draw();
  }, [canvasSize, draw]);

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

  const getMouseSite = (e: React.MouseEvent): Site | null => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const cx = canvasSize.w / 2;
    const cy = canvasSize.h / 2;
    const r = Math.min(cx, cy) * 0.85;

    let hit: Site | null = null;
    sites.forEach(s => {
      const { sx, sy } = siteToCanvas(s, cx, cy, r);
      if (Math.hypot(mx - sx, my - sy) < 14) hit = s;
    });
    return hit;
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    const hit = getMouseSite(e);
    if (hit) {
      const canvas = canvasRef.current!;
      const rect = canvas.getBoundingClientRect();
      setTooltip({ x: e.clientX - rect.left + 12, y: e.clientY - rect.top - 8, site: hit });
    } else {
      setTooltip(null);
    }
  };

  const handleClick = (e: React.MouseEvent) => {
    const hit = getMouseSite(e);
    if (hit) onSelectSite(hit);
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
            boxShadow: "0 2px 8px rgba(0,0,0,0.5)", zIndex: 10, maxWidth: 200
          }}>
            <div style={{ fontWeight: 500, marginBottom: 2 }}>{tooltip.site.name}</div>
            <div style={{ color: "#888", marginBottom: 2 }}>
              {tooltip.site.coordinates.lat.toFixed(1)}°, {tooltip.site.coordinates.lon.toFixed(1)}°
            </div>
            <div style={{ color: "#888" }}>
              Score: {rankings.find(rk => rk.site_id === tooltip.site.id)?.score ?? "—"}/100
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
