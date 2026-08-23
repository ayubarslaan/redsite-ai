"use client";

import { useState, useRef, useEffect } from "react";

interface Site {
  id: string;
  name: string;
  code: string;
  features: { terrain: number; water: number; solar: number; science: number; edl: number };
  description: string;
}

interface Props {
  selectedSite: Site | null;
  mission: string;
  apiBase: string;
}

interface Message {
  text: string;
  isUser: boolean;
  model?: string;
}

const QUICK_QUESTIONS = [
  "Why is this site best?",
  "Compare top 2",
  "What are the risks?",
];

export default function AnalystChat({ selectedSite, mission, apiBase }: Props) {
  const [messages, setMessages] = useState<Message[]>([
    { text: "RedSite AI analyst is online. Select a candidate site to receive a mission-specific assessment. You can also ask comparative questions.", isUser: false, model: "system" },
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
    if (!text.trim() || !selectedSite) return;

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
            selected_site: selectedSite.id,
          },
        }),
      });
      const data = await res.json();
      setMessages(prev => [...prev, { text: data.response, isUser: false, model: data.model_used }]);
    } catch (err) {
      setMessages(prev => [...prev, { text: "Sorry, the analyst is temporarily unavailable. Please try again.", isUser: false, model: "error" }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12, minHeight: 0 }}>
      <div style={{ fontSize: 14, fontWeight: 500, color: "#aaa", display: "flex", alignItems: "center", gap: 6 }}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={{ color: "#666" }}>
          <path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.387-1 1.732V7h1a7 7 0 0 1 7 7v4a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3v-4a7 7 0 0 1 7-7h1V5.732A2.001 2.001 0 0 1 12 2z"/><path d="M9 22h6"/>
        </svg>
        Granite AI analyst
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
                  Granite analyst {msg.model !== "rule-based" && `• ${msg.model}`}
                </div>
              )}
              <div dangerouslySetInnerHTML={{ __html: msg.text.replace(/\n/g, "<br/>") }} />
            </div>
          ))}
          {loading && (
            <div style={{ alignSelf: "flex-start", padding: "10px 12px", borderRadius: 10, borderBottomLeftRadius: 4, background: "#1a1a1a", border: "1px solid #333", color: "#888", fontSize: 13 }}>
              <div style={{ fontSize: 11, color: "#666", marginBottom: 4, fontWeight: 500 }}>Granite analyst</div>
              Analyzing...
            </div>
          )}
        </div>
        <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && sendMessage(input)}
            placeholder={selectedSite ? `Ask about ${selectedSite.name}...` : "Select a site first..."}
            disabled={!selectedSite}
            style={{
              flex: 1, padding: "8px 10px", borderRadius: 8, border: "1px solid #444",
              background: "#1a1a1a", color: "#e0e0e0", fontFamily: "inherit", fontSize: 13, outline: "none"
            }}
          />
          <button
            onClick={() => sendMessage(input)}
            disabled={!selectedSite || !input.trim()}
            style={{
              padding: "8px 12px", borderRadius: 8, border: "none",
              background: "#e0e0e0", color: "#0a0a0a", fontFamily: "inherit",
              fontSize: 13, fontWeight: 500, cursor: "pointer",
              opacity: !selectedSite || !input.trim() ? 0.5 : 1
            }}
          >
            Send
          </button>
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {QUICK_QUESTIONS.map(q => (
            <button
              key={q}
              onClick={() => sendMessage(q)}
              disabled={!selectedSite}
              style={{
                fontSize: 11, padding: "4px 8px", borderRadius: 6,
                border: "1px solid #444", background: "transparent",
                color: "#888", cursor: "pointer",
                opacity: !selectedSite ? 0.5 : 1
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
