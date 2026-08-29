"use client";

import { useState, useRef, useEffect } from "react";

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

interface Props {
  selectedSite: Site | null;
  mission: string;
  apiBase: string;
  sites?: Site[];
  rankings?: Ranking[];
  analystMode?: string;
  /** What-if weights currently active (null = default) */
  customWeights?: Record<string, number> | null;
  isCustomWeights?: boolean;
}

interface Message {
  text: string;
  isUser: boolean;
  model?: string;
}

const QUICK_QUESTIONS = [
  "Why is this site ranked first?",
  "Compare top 2 sites",
  "Show score breakdown",
  "What are the risks?",
  "What changes if I prioritize science?",
  "Explain current weights",
];

export default function AnalystChat({
  selectedSite,
  mission,
  apiBase,
  sites = [],
  rankings = [],
  analystMode,
  customWeights = null,
  isCustomWeights = false,
}: Props) {
  const [messages, setMessages] = useState<Message[]>([
    {
      text: "RedSite AI analyst is online. Select a candidate site to receive a mission-specific assessment, or ask comparative questions without selecting a site. When you adjust weights, I'll explain the CURRENT scenario.",
      isUser: false,
      model: "system",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMessage = async (text: string) => {
    if (!text.trim()) return;

    setMessages(prev => [...prev, { text, isUser: true }]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${apiBase}/api/analyst/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          context: {
            mission,
            selected_site: selectedSite?.id ?? null,
            // Pass sites with ranking info AND decomposition
            sites: sites.map(s => {
              const rk = rankings.find(r => r.site_id === s.id);
              return {
                id: s.id,
                name: s.name,
                code: s.code,
                coordinates: s.coordinates,
                features: s.features,
                description: s.description,
                score: rk?.score ?? null,
                rank: rk?.rank ?? null,
                decomposition: rk?.decomposition ?? null,
              };
            }),
            // Pass current what-if weights so analyst explains current scenario
            custom_weights: customWeights,
            is_custom_weights: isCustomWeights,
          },
        }),
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data = await res.json();
      setMessages(prev => [...prev, { text: data.response, isUser: false, model: data.model_used }]);
    } catch {
      setMessages(prev => [
        ...prev,
        {
          text: "Sorry, the analyst is temporarily unavailable. Please check that the backend is running and try again.",
          isUser: false,
          model: "error",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const isRulesBased = analystMode === "rule-based" || !analystMode;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12, minHeight: 0 }}>
      <div style={{ fontSize: 14, fontWeight: 500, color: "#aaa", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 6 }}>
        <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={{ color: "#666" }}>
            <path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.387-1 1.732V7h1a7 7 0 0 1 7 7v4a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3v-4a7 7 0 0 1 7-7h1V5.732A2.001 2.001 0 0 1 12 2z"/><path d="M9 22h6"/>
          </svg>
          AI analyst
        </span>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {isCustomWeights && (
            <span style={{ fontSize: 11, color: "#f59e0b", background: "#1c1600", border: "1px solid #4a3800", borderRadius: 4, padding: "2px 6px" }}>
              Custom weights active
            </span>
          )}
          {isRulesBased && (
            <span style={{ fontSize: 11, color: "#555", background: "#111", border: "1px solid #333", borderRadius: 4, padding: "2px 6px" }}>
              Rule-based
            </span>
          )}
        </div>
      </div>
      <div style={{
        flex: 1, border: "1px solid #333", borderRadius: 12, padding: 14,
        display: "flex", flexDirection: "column", gap: 12,
        background: "#111", minHeight: 320, overflow: "hidden"
      }}>
        <div ref={scrollRef} style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 10, fontSize: 13, lineHeight: 1.5 }}>
          {messages.map((msg, i) => (
            <div
              key={i}
              style={{
                alignSelf: msg.isUser ? "flex-end" : "flex-start",
                maxWidth: "92%",
                padding: "10px 12px",
                borderRadius: 10,
                borderBottomLeftRadius: msg.isUser ? 10 : 4,
                borderBottomRightRadius: msg.isUser ? 4 : 10,
                background: msg.isUser ? "#e0e0e0" : "#1a1a1a",
                color: msg.isUser ? "#0a0a0a" : "#e0e0e0",
                border: msg.isUser ? "none" : "1px solid #333",
              }}
            >
              {!msg.isUser && msg.model && msg.model !== "system" && (
                <div style={{ fontSize: 11, color: "#666", marginBottom: 4, fontWeight: 500 }}>
                  {msg.model.startsWith("rule-based") ? "Rule-based analyst" : `Granite analyst · ${msg.model}`}
                  {msg.model.includes("unavailable") && " (fallback)"}
                </div>
              )}
              <div dangerouslySetInnerHTML={{ __html: msg.text.replace(/\n/g, "<br/>") }} />
            </div>
          ))}
          {loading && (
            <div style={{ alignSelf: "flex-start", padding: "10px 12px", borderRadius: 10, borderBottomLeftRadius: 4, background: "#1a1a1a", border: "1px solid #333", color: "#888", fontSize: 13 }}>
              <div style={{ fontSize: 11, color: "#666", marginBottom: 4, fontWeight: 500 }}>Analyst</div>
              Analyzing…
            </div>
          )}
        </div>
        <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && sendMessage(input)}
            placeholder={selectedSite ? `Ask about ${selectedSite.name}…` : "Ask a question…"}
            style={{
              flex: 1, padding: "8px 10px", borderRadius: 8, border: "1px solid #444",
              background: "#1a1a1a", color: "#e0e0e0", fontFamily: "inherit", fontSize: 13, outline: "none"
            }}
          />
          <button
            onClick={() => sendMessage(input)}
            disabled={!input.trim() || loading}
            style={{
              padding: "8px 12px", borderRadius: 8, border: "none",
              background: "#e0e0e0", color: "#0a0a0a", fontFamily: "inherit",
              fontSize: 13, fontWeight: 500, cursor: "pointer",
              opacity: !input.trim() || loading ? 0.5 : 1
            }}
          >
            Send
          </button>
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
          {QUICK_QUESTIONS.map(q => (
            <button
              key={q}
              onClick={() => sendMessage(q)}
              disabled={loading}
              style={{
                fontSize: 11, padding: "4px 8px", borderRadius: 6,
                border: "1px solid #444", background: "transparent",
                color: "#888", cursor: "pointer",
                opacity: loading ? 0.5 : 1
              }}
            >
              {q}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
