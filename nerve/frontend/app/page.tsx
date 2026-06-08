"use client";
import { useEffect, useState } from "react";
import axios from "axios";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from "recharts";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

type Signal = { status: string; severity: number; alert: string; [key: string]: any; };
type ScoreData = { silent_killer_score: number; risk_level: string; cross_signal_reason: string | null; cross_signal_bonus: number; signals: { [key: string]: Signal }; };
type WhatIfResult = { baseline: { runway_days: number; true_cash: number; silent_killer_score: number }; projected: { runway_days: number; true_cash: number; silent_killer_score: number; daily_burn: number; freed_capital: number }; improvement: { runway_change: number; score_change: number; cash_freed: number }; };

const SIGNAL_META: { [key: string]: { name: string; icon: string; headline: (s: Signal) => string; subline: (s: Signal) => string; } } = {
  zombie_sku: {
    name: "Dead Stock Alert",
    icon: "",
    headline: (s) => s.status === "CRITICAL" ? `${s.zombies?.length || 0} products haven't sold in 30+ days` : "All products are moving. Nice work!",
    subline: (s) => s.status === "CRITICAL" ? `You're bleeding Rs.${s.total_locked_capital?.toLocaleString()} in stock nobody wants — and still paying ads for it.` : "Your inventory is healthy with no dead stock sitting around.",
  },
  cash_cliff: {
    name: "Cash Runway",
    icon: "",
    headline: (s) => s.status === "CRITICAL" ? `You'll run out of cash in ${s.runway_days} days` : s.status === "WARNING" ? `${s.runway_days} days of cash left — stay alert` : `${s.runway_days} days of cash runway. You're good.`,
    subline: (s) => s.status === "CRITICAL" ? `At your current burn rate of Rs.${s.daily_burn_rate?.toLocaleString()}/day, the clock is ticking loud.` : s.status === "WARNING" ? "Not urgent, but now is a good time to reduce non-essential spending." : "Your cash position is comfortable. Keep monitoring monthly.",
  },
  margin_drift: {
    name: "Profit Margin",
    icon: "",
    headline: (s) => s.status === "CRITICAL" ? `Your margins just fell ${Math.abs(s.drift || 0)}% in 30 days` : s.status === "WARNING" ? "Margins slipping slightly — keep an eye out" : "Your profit margins are rock solid",
    subline: (s) => s.status === "CRITICAL" ? `From ${s.previous_margin}% down to ${s.current_margin}%. You're selling more but making less. Your ROAS dashboard is hiding this.` : "Every rupee of revenue is converting well to profit.",
  },
  inventory_collision: {
    name: "Stock vs Bills",
    icon: "",
    headline: (s) => s.status === "CRITICAL" ? `Money stuck in stock + big bill due in ${s.nearest_due_days} days` : "Your inventory and bills are in balance",
    subline: (s) => s.status === "CRITICAL" ? `Rs.${s.locked_capital?.toLocaleString()} frozen in unsold inventory while Rs.${s.upcoming_bills?.toLocaleString()} in bills are coming. Classic cash crunch setup.` : "No dangerous overlap between your stock investment and upcoming payments.",
  },
  phantom_liability: {
    name: "Hidden Ad Debt",
    icon: "",
    headline: (s) => s.status === "CRITICAL" ? `Your real cash is Rs.${s.true_cash?.toLocaleString()} — not what your bank says` : "Your ad bills are under control",
    subline: (s) => s.status === "CRITICAL" ? `Rs.${s.total_unbilled?.toLocaleString()} in Meta/Google ads will auto-charge soon. Your bank looks fine. It's not.` : "No surprise ad charges lurking. Your balance is what it says.",
  },
};

const scoreColor = (s: number) => s > 60 ? "#f87171" : s > 30 ? "#fbbf24" : "#4ade80";
const statusColor = (st: string) => st === "CRITICAL" ? "#f87171" : st === "WARNING" ? "#fbbf24" : "#4ade80";
const statusBadge = (st: string) => st === "CRITICAL" ? "ACTION NEEDED" : st === "WARNING" ? "WATCH THIS" : "ALL GOOD";

export default function NerveDashboard() {
  const [score, setScore] = useState<ScoreData | null>(null);
  const [fivetran, setFivetran] = useState<any>(null);
  const [whatif, setWhatif] = useState<WhatIfResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [adSpend, setAdSpend] = useState(0);
  const [pauseZombie, setPauseZombie] = useState(false);
  const [delayPayment, setDelayPayment] = useState(0);
  const [executing, setExecuting] = useState<string | null>(null);
  const [executed, setExecuted] = useState<{ [key: string]: any }>({});
  const [chat, setChat] = useState("");
  const [reply, setReply] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [headerSmall, setHeaderSmall] = useState(false);

  const [sessions, setSessions] = useState<any[]>([]);
const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
const [messages, setMessages] = useState<{role: string, content: string}[]>([]);
const [streamingReply, setStreamingReply] = useState("");
const [sidebarOpen, setSidebarOpen] = useState(true);

  useEffect(() => { fetchAll(); }, []);
  useEffect(() => { runWhatIf(); }, [adSpend, pauseZombie, delayPayment]);
  useEffect(() => { fetchAll(); loadSessions(); }, []);

  async function fetchAll() {
    setLoading(true);
    try {
      const [s, f] = await Promise.all([axios.get(`${API}/score`), axios.get(`${API}/fivetran/sync`)]);
      setScore(s.data); setFivetran(f.data);
    } catch (e) { console.error(e); }
    setLoading(false);
  }

  

  async function runWhatIf() {
    try {
      const res = await axios.post(`${API}/whatif`, { ad_spend_change: adSpend, return_rate_change: 0, pause_zombie_sku: pauseZombie, delay_payment_days: delayPayment });
      setWhatif(res.data);
    } catch (e) {}
  }

  async function executeAction(id: string) {
    setExecuting(id);
    try {
      const res = await axios.post(`${API}/execute`, { action_id: id, confirmed: true });
      setExecuted((p) => ({ ...p, [id]: res.data }));
    } catch (e) {}
    setExecuting(null);
  }

  async function loadSessions() {
  try {
    const res = await axios.get(`${API}/chat/sessions`);
    setSessions(res.data.sessions || []);
  } catch(e) {}
}

async function newSession() {
  const res = await axios.post(`${API}/chat/sessions/new`, { first_message: "" });
  setCurrentSessionId(res.data.session_id);
  setMessages([]); setReply(""); setStreamingReply("");
  await loadSessions();
}

async function loadSession(session_id: string) {
  setCurrentSessionId(session_id);
  setStreamingReply(""); setReply("");
  const res = await axios.get(`${API}/chat/sessions/${session_id}`);
  setMessages(res.data.messages || []);
}

async function deleteSession(session_id: string, e: React.MouseEvent) {
  e.stopPropagation();
  await axios.delete(`${API}/chat/sessions/${session_id}`);
  if (currentSessionId === session_id) { setCurrentSessionId(null); setMessages([]); }
  await loadSessions();
}

 const handleAsk = async () => {
  if (!chat.trim()) return;
  let sessionId = currentSessionId;
  if (!sessionId) {
    const res = await axios.post(`${API}/chat/sessions/new`, { first_message: chat });
    sessionId = res.data.session_id;
    setCurrentSessionId(sessionId);
    await loadSessions();
  }
  const userMsg = chat.trim();
  setMessages(prev => [...prev, { role: "user", content: userMsg }]);
  setChatLoading(true); setStreamingReply(""); setReply(""); setChat("");
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: userMsg, session_id: sessionId, stream: true }),
  });
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let accumulated = "";
  setChatLoading(false);
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const lines = decoder.decode(value).split("\n");
    for (const line of lines) {
      if (line.startsWith("data: ") && line !== "data: [DONE]") {
        try {
          const parsed = JSON.parse(line.slice(6));
          if (parsed.type === "text") { accumulated += parsed.content; setStreamingReply(accumulated); }
          else if (parsed.type === "action_progress") { fetchAll(); }
        } catch {}
      }
    }
  }
  setMessages(prev => [...prev, { role: "model", content: accumulated }]);
  setStreamingReply("");
  await loadSessions();
};

  if (loading) return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#05091a" }}>
      <div style={{ textAlign: "center" }}>
        <div style={{ fontSize: 48, marginBottom: 16, animation: "spin 2s linear infinite" }}>⚡</div>
        <div style={{ color: "#60a5fa", fontFamily: "monospace", fontSize: 13, letterSpacing: "3px" }}>SCANNING YOUR FINANCIALS...</div>
        <div style={{ color: "#1e3a5f", fontSize: 11, marginTop: 8, fontFamily: "monospace" }}>This takes about 3 seconds</div>
      </div>
    </div>
  );

  const criticalCount = score ? Object.values(score.signals).filter(s => s.status === "CRITICAL").length : 0;
  const warningCount = score ? Object.values(score.signals).filter(s => s.status === "WARNING").length : 0;
  const sk = score?.silent_killer_score || 0;

  return (
    <div style={{ minHeight: "100vh", background: "#05091a", color: "#e2e8f0", fontFamily: "ui-monospace, 'SF Mono', Consolas, monospace" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;600;700&family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500;600&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #05091a; }
        @keyframes fadeUp { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes pulse { 0%,100%{opacity:1;box-shadow:0 0 8px currentColor;} 50%{opacity:0.5;box-shadow:0 0 2px currentColor;} }
        @keyframes spin { from{transform:rotate(0deg);} to{transform:rotate(360deg);} }
        @keyframes shimmer { 0%{background-position:-200px 0} 100%{background-position:calc(200px + 100%) 0} }
        .fade1{animation:fadeUp 0.5s ease 0.05s both;}
        .fade2{animation:fadeUp 0.5s ease 0.15s both;}
        .fade3{animation:fadeUp 0.5s ease 0.25s both;}
        .fade4{animation:fadeUp 0.5s ease 0.35s both;}
        .fade5{animation:fadeUp 0.5s ease 0.45s both;}
        .fade6{animation:fadeUp 0.5s ease 0.55s both;}
        .hover-card { transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s; }
        .hover-card:hover { transform: translateY(-2px); box-shadow: 0 8px 32px rgba(96,165,250,0.08); }
        .exec-btn { transition: all 0.2s; }
        .exec-btn:hover { background: rgba(96,165,250,0.1) !important; color: #93c5fd !important; }
        input[type=range] { -webkit-appearance: none; height: 3px; border-radius: 2px; outline: none; }
        input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; width: 14px; height: 14px; border-radius: 50%; cursor: pointer; }
      `}</style>

    {/* ── HEADER ── */}
<div style={{ background: "rgba(5,9,26,0.95)", borderBottom: "1px solid #0d1f3c", padding: "32px 48px", position: "sticky", top: 0, zIndex: 100, backdropFilter: "blur(20px)" }}>
  
  {/* Center — NERVE + subheading */}
  <div style={{ textAlign: "center", marginBottom: 24 }}>
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 12, marginBottom: 8 }}>
      <span style={{ fontSize: 60, fontWeight: 900, color: "#fff", fontFamily: "-apple-system, sans-serif", letterSpacing: "-2px" }}>NERVE</span>
      <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#60a5fa", animation: "pulse 2s infinite", display: "inline-block" }} />
    </div>
    <div style={{ fontSize: 13, color: "#94a3b8", letterSpacing: "3px", textTransform: "uppercase", fontFamily: "ui-monospace, Consolas, monospace" }}>
      Your business health monitor. We find hidden problems, explain them simply, and show you exactly what to do next.
    </div>
  </div>

  {/* Pipeline: Shopify → Stripe → Fivetran → BigQuery → Nerve */}
  <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 0 }}>
    {[
      { icon: "", label: "Shopify", sub: "140 orders", color: "#96bf48" },
      { icon: "", label: "Stripe", sub: "50 payments", color: "#6772e5" },
      { icon: "", label: "Fivetran", sub: fivetran ? `Synced ${fivetran.last_synced}` : "Syncing...", color: "#60a5fa" },
      { icon: "", label: "BigQuery", sub: "Live data", color: "#4285f4" },
      { icon: "", label: "Nerve AI", sub: "Analysing", color: "#f87171" },
    ].map((node, i) => (
      <div key={node.label} style={{ display: "flex", alignItems: "center" }}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "10px 16px", background: "rgba(255,255,255,0.03)", border: `1px solid ${node.color}25`, borderRadius: 10 }}>
          <span style={{ fontSize: 18, marginBottom: 4 }}>{node.icon}</span>
          <span style={{ fontSize: 11, fontWeight: 700, color: node.color }}>{node.label}</span>
          <span style={{ fontSize: 9, color: "#64748b", marginTop: 2 }}>{node.sub}</span>
        </div>
        {i < 4 && (
          <div style={{ display: "flex", alignItems: "center", gap: 2, padding: "0 6px" }}>
            <div style={{ width: 20, height: 1, background: "linear-gradient(to right, #1e3a5f, #60a5fa)" }} />
            <span style={{ color: "#60a5fa", fontSize: 10 }}>▶</span>
          </div>
        )}
      </div>
    ))}
    
    {/* Fivetran status pill */}
    {fivetran && (
      <div style={{ marginLeft: 20, display: "flex", alignItems: "center", gap: 6, padding: "6px 12px", background: "rgba(74,222,128,0.08)", border: "1px solid rgba(74,222,128,0.2)", borderRadius: 20 }}>
        <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#4ade80", display: "inline-block", animation: "pulse 2s infinite" }} />
        <span style={{ fontSize: 10, color: "#4ade80" }}>Live · Next sync {fivetran.next_sync}</span>
      </div>
    )}
  </div>
</div>
      <div style={{ padding: "40px 48px", maxWidth: 1300, margin: "0 auto" }}>

        {/* ── HERO SUMMARY ── */}
     {/* ── HERO SUMMARY V2 ── */}
{score && (
  <div
    className="fade1"
    style={{
      marginBottom: 40,
      padding: "36px",
      borderRadius: 28,
      background:
        "linear-gradient(135deg, rgba(13,31,60,0.95), rgba(8,15,30,0.95))",
      border: "1px solid rgba(96,165,250,0.12)",
      position: "relative",
      overflow: "hidden",
    }}
  >
    {/* glow */}
    <div
      style={{
        position: "absolute",
        right: -100,
        top: -100,
        width: 280,
        height: 280,
        borderRadius: "50%",
        background: `${scoreColor(sk)}15`,
        filter: "blur(80px)",
      }}
    />

    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1.5fr 0.8fr",
        gap: 40,
        alignItems: "center",
        position: "relative",
        zIndex: 2,
      }}
    >
      {/* LEFT */}
      <div>
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            padding: "8px 14px",
            borderRadius: 999,
            background: "rgba(96,165,250,0.08)",
            border: "1px solid rgba(96,165,250,0.15)",
            marginBottom: 18,
          }}
        >
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: "#60a5fa",
            }}
          />
          <span
            style={{
              fontSize: 12,
              color: "#94a3b8",
              fontWeight: 600,
            }}
          >
            Live Financial Pulse
          </span>
        </div>

        <h1
          style={{
            fontSize: 48,
            fontWeight: 800,
            color: "#fff",
            lineHeight: 1.05,
            marginBottom: 16,
            letterSpacing: "-1.5px",
          }}
        >
          {criticalCount > 0
            ? `${criticalCount} issue${
                criticalCount > 1 ? "s" : ""
              } silently hurting your business.`
            : warningCount > 0
            ? "A few financial signals need attention."
            : "Everything looks healthy today."}
        </h1>

        <p
          style={{
            color: "#94a3b8",
            maxWidth: 650,
            fontSize: 16,
            lineHeight: 1.7,
          }}
        >
          {criticalCount > 0
            ? `Nerve detected ${criticalCount} critical pattern${
                criticalCount > 1 ? "s" : ""
              } hidden inside your financial data. Here's exactly what requires attention right now.`
            : "No major threats detected. Nerve continuously monitors your business and alerts you before small problems become expensive ones."}
        </p>

        {/* quick pills */}
        <div
          style={{
            display: "flex",
            gap: 12,
            flexWrap: "wrap",
            marginTop: 24,
          }}
        >
          <div
            style={{
              padding: "10px 14px",
              borderRadius: 12,
              background: "rgba(248,113,113,0.08)",
              border: "1px solid rgba(248,113,113,0.12)",
            }}
          >
            <div style={{ fontSize: 11, color: "#64748b" }}>
              Critical Issues
            </div>
            <div
              style={{
                color: "#f87171",
                fontSize: 20,
                fontWeight: 700,
              }}
            >
              {criticalCount}
            </div>
          </div>

          <div
            style={{
              padding: "10px 14px",
              borderRadius: 12,
              background: "rgba(251,191,36,0.08)",
              border: "1px solid rgba(251,191,36,0.12)",
            }}
          >
            <div style={{ fontSize: 11, color: "#64748b" }}>
              Warnings
            </div>
            <div
              style={{
                color: "#fbbf24",
                fontSize: 20,
                fontWeight: 700,
              }}
            >
              {warningCount}
            </div>
          </div>

          <div
            style={{
              padding: "10px 14px",
              borderRadius: 12,
              background: "rgba(96,165,250,0.08)",
              border: "1px solid rgba(96,165,250,0.12)",
            }}
          >
            <div style={{ fontSize: 11, color: "#64748b" }}>
              Cash Runway
            </div>
            <div
              style={{
                color: "#60a5fa",
                fontSize: 20,
                fontWeight: 700,
              }}
            >
              {score.signals.cash_cliff?.runway_days || "--"}d
            </div>
          </div>
        </div>
      </div>

      {/* RIGHT */}
      <div
        style={{
          background: "rgba(255,255,255,0.03)",
          border: `1px solid ${scoreColor(sk)}20`,
          borderRadius: 24,
          padding: 28,
          textAlign: "center",
          backdropFilter: "blur(20px)",
        }}
      >
        <div
          style={{
            fontSize: 12,
            color: "#64748b",
            marginBottom: 12,
            letterSpacing: "2px",
          }}
        >
          RISK SCORE
        </div>

        <div
          style={{
            fontSize: 92,
            fontWeight: 800,
            color: scoreColor(sk),
            lineHeight: 1,
            letterSpacing: "-4px",
          }}
        >
          {sk}
        </div>

        <div
          style={{
            color: "#64748b",
            marginTop: 6,
            fontSize: 13,
          }}
        >
          out of 100
        </div>

        <div
          style={{
            marginTop: 20,
            padding: "8px 18px",
            borderRadius: 999,
            display: "inline-block",
            background: `${scoreColor(sk)}15`,
            border: `1px solid ${scoreColor(sk)}30`,
            color: scoreColor(sk),
            fontWeight: 700,
            fontSize: 12,
          }}
        >
          {score.risk_level}
        </div>

        <div
          style={{
            marginTop: 24,
            fontSize: 12,
            color: "#64748b",
          }}
        >
          Lower score = healthier business
        </div>
      </div>
    </div>
  </div>
)}

    {/* ── SIGNAL FEED V2 ── */}
{score && (
  <div className="fade2" style={{ marginBottom: 40 }}>
    
    {/* Header */}
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: 28,
      }}
    >
      <div>
        <div
          style={{
            fontSize: 12,
            color: "#60a5fa",
            fontWeight: 700,
            letterSpacing: "2px",
            marginBottom: 6,
          }}
        >
          LIVE SIGNALS
        </div>

        <div
          style={{
            fontSize: 28,
            fontWeight: 800,
            color: "#fff",
          }}
        >
          Financial Intelligence Feed
        </div>
      </div>

      <div
        style={{
          padding: "8px 14px",
          borderRadius: 999,
          background: "rgba(96,165,250,0.08)",
          border: "1px solid rgba(96,165,250,0.15)",
          color: "#60a5fa",
          fontSize: 12,
          fontWeight: 600,
        }}
      >
        {Object.keys(score.signals).length} Signals Active
      </div>
    </div>

    {/* Cards */}
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 14,
      }}
    >
      {Object.entries(score.signals).map(([key, sig]) => {
        const meta = SIGNAL_META[key];

        return (
          <div
            key={key}
            className="hover-card"
            style={{
              borderRadius: 20,
              padding: 24,
              background:
                "linear-gradient(135deg, rgba(13,31,60,0.95), rgba(8,15,30,0.95))",
              border: "1px solid rgba(96,165,250,0.12)",
              boxShadow:
                "0 10px 40px rgba(59,130,246,0.08)",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
              }}
            >
              {/* Left */}
              <div
                style={{
                  display: "flex",
                  gap: 18,
                  flex: 1,
                }}
              >
                <div
                  style={{
                    width: 56,
                    height: 56,
                    borderRadius: 14,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    background:
                      "rgba(96,165,250,0.08)",
                    border:
                      "1px solid rgba(96,165,250,0.15)",
                    fontSize: 24,
                  }}
                >
                  {meta.icon}
                </div>

                <div>
                  <div
                    style={{
                      color: "#60a5fa",
                      fontSize: 12,
                      fontWeight: 700,
                      letterSpacing: "1px",
                      marginBottom: 8,
                    }}
                  >
                    {meta.name}
                  </div>

                  <div
                    style={{
                      color: "#fff",
                      fontSize: 18,
                      fontWeight: 700,
                      marginBottom: 10,
                    }}
                  >
                    {meta.headline(sig)}
                  </div>

                  <div
                    style={{
                      color: "#94a3b8",
                      fontSize: 13,
                      lineHeight: 1.7,
                      maxWidth: 700,
                    }}
                  >
                    {meta.subline(sig)}
                  </div>
                </div>
              </div>

              {/* Right */}
              <div
                style={{
                  textAlign: "center",
                  minWidth: 100,
                }}
              >
                <div
                  style={{
                    fontSize: 42,
                    fontWeight: 800,
                    color: "#60a5fa",
                    textShadow:
                      "0 0 30px rgba(96,165,250,0.35)",
                  }}
                >
                  {sig.severity}
                </div>

                <div
                  style={{
                    color: "#64748b",
                    fontSize: 11,
                  }}
                >
                  Severity
                </div>

                <div
                  style={{
                    marginTop: 10,
                    padding: "6px 10px",
                    borderRadius: 999,
                    background:
                      "rgba(96,165,250,0.08)",
                    border:
                      "1px solid rgba(96,165,250,0.15)",
                    color: "#60a5fa",
                    fontSize: 11,
                    fontWeight: 600,
                  }}
                >
                  {sig.status}
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  </div>
)}
       {/* ── AI CORRELATION INSIGHT ── */}
{score?.cross_signal_reason && (
  <div
    className="fade3"
    style={{
      marginBottom: 40,
      padding: "28px 32px",
      borderRadius: 24,
      background:
        "linear-gradient(135deg, rgba(13,31,60,0.95), rgba(8,15,30,0.95))",
      border: "1px solid rgba(96,165,250,0.12)",
      position: "relative",
      overflow: "hidden",
      boxShadow: "0 10px 40px rgba(59,130,246,0.08)",
    }}
  >
    {/* Glow */}
    <div
      style={{
        position: "absolute",
        top: -80,
        right: -80,
        width: 220,
        height: 220,
        borderRadius: "50%",
        background: "rgba(96,165,250,0.08)",
        filter: "blur(70px)",
      }}
    />

    <div
      style={{
        display: "flex",
        gap: 20,
        alignItems: "flex-start",
        position: "relative",
        zIndex: 2,
      }}
    >
      {/* Icon */}
      <div
        style={{
          width: 64,
          height: 64,
          borderRadius: 18,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "rgba(96,165,250,0.08)",
          border: "1px solid rgba(96,165,250,0.15)",
          flexShrink: 0,
          fontSize: 28,
        }}
      >
        
      </div>

      {/* Content */}
      <div style={{ flex: 1 }}>
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            padding: "6px 12px",
            borderRadius: 999,
            background: "rgba(96,165,250,0.08)",
            border: "1px solid rgba(96,165,250,0.15)",
            marginBottom: 14,
          }}
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: "#60a5fa",
            }}
          />

          <span
            style={{
              color: "#60a5fa",
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: "1px",
            }}
          >
            AI CORRELATION DETECTED
          </span>
        </div>

        <div
          style={{
            fontSize: 24,
            fontWeight: 800,
            color: "#fff",
            marginBottom: 10,
            lineHeight: 1.3,
          }}
        >
          {score.cross_signal_reason}
        </div>

        <div
          style={{
            fontSize: 14,
            color: "#94a3b8",
            lineHeight: 1.8,
            maxWidth: 850,
          }}
        >
          Nerve discovered a relationship between multiple financial signals.
          These patterns often appear together before cash flow pressure,
          inventory problems, or profitability issues become visible.
        </div>
      </div>

      {/* Risk Score */}
      <div
        style={{
          textAlign: "center",
          minWidth: 120,
        }}
      >
        <div
          style={{
            fontSize: 42,
            fontWeight: 800,
            color: "#60a5fa",
            textShadow: "0 0 30px rgba(96,165,250,0.35)",
          }}
        >
          +{score.cross_signal_bonus}
        </div>

        <div
          style={{
            fontSize: 11,
            color: "#64748b",
          }}
        >
          Risk Points
        </div>
      </div>
    </div>
  </div>
)}

      {/* ── RECOMMENDED ACTIONS ── */}
<div className="fade3" style={{ marginBottom: 40 }}>
  <div style={{ marginBottom: 24 }}>
    <div
      style={{
        color: "#60a5fa",
        fontSize: 12,
        fontWeight: 700,
        letterSpacing: "2px",
        marginBottom: 6,
      }}
    >
      RECOMMENDED ACTIONS
    </div>

    <div
      style={{
        color: "#fff",
        fontSize: 30,
        fontWeight: 800,
        marginBottom: 8,
        lineHeight: 1.2,
      }}
    >
      AI-Generated Action Plan
    </div>

    <div
      style={{
        color: "#94a3b8",
        fontSize: 14,
        maxWidth: 720,
        lineHeight: 1.7,
      }}
    >
      Based on your financial signals, Nerve has identified the highest-impact
      actions that can improve liquidity, reduce risk, and strengthen business
      health.
    </div>
  </div>

  <div
    style={{
      display: "grid",
      gridTemplateColumns: "repeat(4, 1fr)",
      gap: 16,
    }}
  >
    {[
      {
        id: "pause_zombie_ads",
    
        label: "Pause Low-Performing Product Campaigns",
        tagline: "Highest Financial Impact",
        desc:
          "Nerve detected advertising spend on products with consistently low sales velocity. Pausing these campaigns can immediately reduce waste and improve cash efficiency.",
      },
      {
        id: "flash_discount",
    
        label: "Liquidate Slow-Moving Inventory",
        tagline: "Unlock Trapped Capital",
        desc:
          "Convert dormant inventory into working capital through targeted discounts and inventory clearance campaigns.",
      },
      {
        id: "send_receivable_reminder",
      
        label: "Recover Outstanding Payments",
        tagline: "Improve Cash Flow",
        desc:
          "Automatically follow up on unpaid invoices and receivables to accelerate cash collection and strengthen liquidity.",
      },
      {
        id: "reduce_ad_budget",
      
        label: "Optimize Marketing Spend",
        tagline: "Reduce Hidden Liabilities",
        desc:
          "Adjust advertising budgets to align spending with current cash position and prevent future payment obligations from accumulating.",
      },
    ].map((action) => {
      const done = executed[action.id];

    return (
  <div
    key={action.id}
    className="hover-card"
    style={{
      borderRadius: 20,
      padding: 22,
      display: "flex",
      flexDirection: "column",
      background:
        "linear-gradient(135deg, rgba(13,31,60,0.95), rgba(8,15,30,0.95))",
      border: done
        ? "1px solid rgba(74,222,128,0.20)"
        : "1px solid rgba(96,165,250,0.10)",
      boxShadow: "0 10px 40px rgba(59,130,246,0.05)",
      minHeight: 280,
    }}
  >
    {/* Header */}
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
        marginBottom: 12,
      }}
    >
      <div
        style={{
          color: "#fff",
          fontSize: 16,
          fontWeight: 700,
          lineHeight: 1.4,
          maxWidth: "75%",
          fontFamily:
            "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        }}
      >
        {action.label}
      </div>

      <div
        style={{
          padding: "4px 8px",
          borderRadius: 999,
          background: "rgba(96,165,250,0.08)",
          border: "1px solid rgba(96,165,250,0.15)",
          color: "#60a5fa",
          fontSize: 10,
          fontWeight: 700,
          letterSpacing: "0.5px",
          whiteSpace: "nowrap",
        }}
      >
        HIGH IMPACT
      </div>
    </div>

    {/* Tagline */}
    <div
      style={{
        color: "#60a5fa",
        fontSize: 11,
        fontWeight: 600,
        marginBottom: 12,
        fontFamily:
          "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      }}
    >
      {action.tagline}
    </div>

    {/* Description */}
    <div
      style={{
        color: "#94a3b8",
        fontSize: 12,
        lineHeight: 1.7,
        flex: 1,
        marginBottom: 20,
        fontFamily:
          "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      }}
    >
      {action.desc}
    </div>

    {done ? (
      <div
        style={{
          padding: 12,
          borderRadius: 12,
          background: "rgba(74,222,128,0.08)",
          border: "1px solid rgba(74,222,128,0.15)",
        }}
      >
        <div
          style={{
            color: "#4ade80",
            fontSize: 12,
            fontWeight: 700,
            marginBottom: 4,
          }}
        >
          Recommendation Applied
        </div>

        <div
          style={{
            color: "#94a3b8",
            fontSize: 11,
            marginBottom: 4,
          }}
        >
          {done.message}
        </div>

        <div
          style={{
            color: "#64748b",
            fontSize: 10,
          }}
        >
          {done.impact}
        </div>
      </div>
    ) : (
      <button
        className="exec-btn"
        onClick={() => executeAction(action.id)}
        disabled={executing === action.id}
        style={{
          width: "100%",
          padding: "12px 16px",
          borderRadius: 12,
          border: "1px solid rgba(96,165,250,0.15)",
          background: "rgba(96,165,250,0.08)",
          color: "#60a5fa",
          cursor: "pointer",
          fontSize: 12,
          fontWeight: 600,
          transition: "all .2s ease",
        }}
      >
        {executing === action.id
          ? "Applying..."
          : "Apply Recommendation →"}
      </button>
    )}
  </div>

  )})}
  </div>
</div>

  {/* ── SCENARIO LAB ── */}
<div
  className="fade4"
  style={{
    marginBottom: 40,
    padding: "32px",
    borderRadius: 24,
    background:
      "linear-gradient(135deg, rgba(13,31,60,0.95), rgba(8,15,30,0.95))",
    border: "1px solid rgba(96,165,250,0.12)",
    boxShadow: "0 10px 40px rgba(59,130,246,0.08)",
  }}
>
  {/* Header */}
  <div style={{ marginBottom: 28 }}>
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: 12,
      }}
    >
      <div>
        <div
          style={{
            color: "#60a5fa",
            fontSize: 12,
            fontWeight: 700,
            letterSpacing: "2px",
            marginBottom: 6,
          }}
        >
          SCENARIO LAB
        </div>

        <div
          style={{
            color: "#fff",
            fontSize: 30,
            fontWeight: 800,
            lineHeight: 1.2,
          }}
        >
          Simulate Before You Execute
        </div>
      </div>

      <div
        style={{
          padding: "8px 14px",
          borderRadius: 999,
          background: "rgba(96,165,250,0.08)",
          border: "1px solid rgba(96,165,250,0.15)",
          color: "#60a5fa",
          fontSize: 12,
          fontWeight: 600,
        }}
      >
        Live Projection
      </div>
    </div>

    <div
      style={{
        color: "#94a3b8",
        fontSize: 14,
        lineHeight: 1.8,
      }}
    >
      Test financial decisions before making them. Nerve forecasts how
      changes affect runway, cash flow and risk score in real time.
    </div>
  </div>

  <div
    style={{
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      gap: 40,
    }}
  >
    {/* LEFT SIDE */}
    <div>
      {[
        {
          label: "Ad Spend Adjustment",
          value: adSpend,
          min: -50,
          max: 50,
          step: 5,
          unit: "%",
          color: "#60a5fa",
          onChange: setAdSpend,
          left: "Cut 50%",
          right: "Increase 50%",
          desc:
            adSpend < 0
              ? "Freeing up working capital"
              : adSpend > 0
              ? "Higher spend increases liability"
              : "No change",
        },
        {
          label: "Supplier Payment Delay",
          value: delayPayment,
          min: 0,
          max: 30,
          step: 5,
          unit: "d",
          color: "#60a5fa",
          onChange: setDelayPayment,
          left: "Pay Now",
          right: "Delay 30d",
          desc:
            delayPayment > 0
              ? "Improves liquidity short-term"
              : "Paying on time",
        },
      ].map((sl) => (
        <div
          key={sl.label}
          style={{
            marginBottom: 24,
            padding: 18,
            borderRadius: 16,
            background: "rgba(255,255,255,0.02)",
            border: "1px solid rgba(96,165,250,0.08)",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginBottom: 12,
            }}
          >
            <span
              style={{
                color: "#e2e8f0",
                fontSize: 13,
                fontWeight: 600,
              }}
            >
              {sl.label}
            </span>

            <span
              style={{
                color: "#60a5fa",
                fontWeight: 700,
              }}
            >
              {sl.value > 0 ? "+" : ""}
              {sl.value}
              {sl.unit}
            </span>
          </div>

          <input
            type="range"
            min={sl.min}
            max={sl.max}
            value={sl.value}
            step={sl.step}
            onChange={(e) => sl.onChange(Number(e.target.value))}
            style={{
              width: "100%",
              accentColor: sl.color,
            }}
          />

          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginTop: 8,
              fontSize: 10,
              color: "#64748b",
            }}
          >
            <span>{sl.left}</span>
            <span>{sl.right}</span>
          </div>

          <div
            style={{
              marginTop: 10,
              color: "#94a3b8",
              fontSize: 11,
            }}
          >
            {sl.desc}
          </div>
        </div>
      ))}

      <div
        onClick={() => setPauseZombie(!pauseZombie)}
        style={{
          padding: 18,
          borderRadius: 16,
          cursor: "pointer",
          display: "flex",
          gap: 14,
          alignItems: "center",
          background: "rgba(255,255,255,0.02)",
          border: pauseZombie
            ? "1px solid rgba(96,165,250,0.25)"
            : "1px solid rgba(96,165,250,0.08)",
        }}
      >
        <div
          style={{
            width: 22,
            height: 22,
            borderRadius: 6,
            border: "2px solid #60a5fa",
            background: pauseZombie ? "#60a5fa" : "transparent",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            color: "#000",
            fontWeight: 700,
          }}
        >
          {pauseZombie && "✓"}
        </div>

        <div>
          <div
            style={{
              color: "#e2e8f0",
              fontSize: 13,
              fontWeight: 600,
            }}
          >
            Stop Zombie Product Ads
          </div>

          <div
            style={{
              color: "#94a3b8",
              fontSize: 11,
              marginTop: 4,
            }}
          >
            Instantly simulate recovered capital.
          </div>
        </div>
      </div>
    </div>

    {/* RIGHT SIDE */}
    {whatif && (
      <div>
        <div
          style={{
            color: "#60a5fa",
            fontSize: 12,
            fontWeight: 700,
            letterSpacing: "1px",
            marginBottom: 14,
          }}
        >
          PROJECTED OUTCOME
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 12,
            marginBottom: 20,
          }}
        >
          {[
            {
              icon: "",
              label: "Cash Runway",
              proj: `${whatif.projected.runway_days}d`,
              change: whatif.improvement.runway_change,
              positive: true,
            },
            {
              icon: "",
              label: "True Cash",
              proj: `₹${Math.round(
                whatif.projected.true_cash
              ).toLocaleString()}`,
              change:
                whatif.projected.true_cash -
                whatif.baseline.true_cash,
              positive: true,
            },
            {
              icon: "",
              label: "Risk Score",
              proj: `${whatif.projected.silent_killer_score}`,
              change: -whatif.improvement.score_change,
              positive: false,
            },
            {
              icon: "",
              label: "Cash Unlocked",
              proj: `₹${Math.round(
                whatif.projected.freed_capital
              ).toLocaleString()}`,
              change: whatif.projected.freed_capital,
              positive: true,
            },
          ].map((item) => {
            const improved = item.positive
              ? item.change > 0
              : item.change < 0;

            return (
              <div
                key={item.label}
                style={{
                  background: "rgba(255,255,255,0.02)",
                  border: "1px solid rgba(96,165,250,0.08)",
                  borderRadius: 18,
                  padding: 18,
                }}
              >
                <div style={{ fontSize: 20, marginBottom: 8 }}>
                  {item.icon}
                </div>

                <div
                  style={{
                    color: "#64748b",
                    fontSize: 11,
                    marginBottom: 8,
                  }}
                >
                  {item.label}
                </div>

                <div
                  style={{
                    fontSize: 24,
                    fontWeight: 800,
                    color: improved ? "#4ade80" : "#60a5fa",
                  }}
                >
                  {item.proj}
                </div>
              </div>
            );
          })}
        </div>

        <div
          style={{
            background: "rgba(255,255,255,0.02)",
            border: "1px solid rgba(96,165,250,0.08)",
            borderRadius: 18,
            padding: 16,
          }}
        >
          <ResponsiveContainer width="100%" height={140}>
            <AreaChart
              data={[
                {
                  name: "Now",
                  score: whatif.baseline.silent_killer_score,
                },
                {
                  name: "After",
                  score: whatif.projected.silent_killer_score,
                },
              ]}
            >
              <XAxis
                dataKey="name"
                tick={{ fill: "#64748b", fontSize: 10 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fill: "#64748b", fontSize: 10 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  background: "#08101f",
                  border: "1px solid rgba(96,165,250,0.15)",
                  borderRadius: 10,
                }}
              />
              <Area
                type="monotone"
                dataKey="score"
                stroke="#60a5fa"
                fill="rgba(96,165,250,0.08)"
                strokeWidth={3}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    )}
  </div>
</div>
     {/* ── BUSINESS SNAPSHOT ── */}
{score && (
  <div className="fade5" style={{ marginBottom: 40 }}>
    <div style={{ marginBottom: 24 }}>
      <div
        style={{
          color: "#60a5fa",
          fontSize: 12,
          fontWeight: 700,
          letterSpacing: "2px",
          marginBottom: 6,
        }}
      >
        BUSINESS SNAPSHOT
      </div>

      <div
        style={{
          color: "#fff",
          fontSize: 30,
          fontWeight: 800,
          marginBottom: 8,
        }}
      >
        Understand Your Money
      </div>

      <div
        style={{
          color: "#94a3b8",
          fontSize: 14,
        }}
      >
        Simple visual summaries of your business finances.
      </div>
    </div>

    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: 16,
      }}
    >
      {[
        {
          title: "How much money can I actually use?",
          sub: "Your available cash after deducting pending expenses.",
          color: "#60a5fa",
          fill: "rgba(96,165,250,0.08)",
          total: score.signals.phantom_liability?.true_cash || 0,
          data: [
            {
              name: "Bank Balance",
              amount: score.signals.cash_cliff?.bank_balance || 0,
            },
            {
              name: "Usable Cash",
              amount: score.signals.phantom_liability?.true_cash || 0,
            },
            {
              name: "After Bills",
              amount: score.signals.cash_cliff?.net_position || 0,
            },
          ],
        },
        {
          title: "Where is my money stuck?",
          sub: "Money locked in inventory and unpaid expenses.",
          color: "#60a5fa",
          fill: "rgba(96,165,250,0.08)",
          total:
            (score.signals.zombie_sku?.total_locked_capital || 0) +
            (score.signals.phantom_liability?.total_unbilled || 0),

          data: [
            {
              name: "Available",
              amount: score.signals.phantom_liability?.true_cash || 0,
            },
            {
              name: "Old Stock",
              amount: score.signals.zombie_sku?.total_locked_capital || 0,
            },
            {
              name: "Ad Bills",
              amount: score.signals.phantom_liability?.total_unbilled || 0,
            },
            {
              name: "Upcoming Bills",
              amount:
                score.signals.inventory_collision?.upcoming_bills || 0,
            },
          ],
        },
      ].map((chart) => (
        <div
          key={chart.title}
          className="hover-card"
          style={{
            background:
              "linear-gradient(135deg, rgba(13,31,60,0.95), rgba(8,15,30,0.95))",
            border: "1px solid rgba(96,165,250,0.10)",
            borderRadius: 20,
            padding: 24,
          }}
        >
          <div
            style={{
              color: "#fff",
              fontSize: 22,
              fontWeight: 700,
              marginBottom: 6,
              lineHeight: 1.3,
            }}
          >
            {chart.title}
          </div>

          <div
            style={{
              color: "#94a3b8",
              fontSize: 13,
              marginBottom: 16,
            }}
          >
            {chart.sub}
          </div>

          <div
            style={{
              marginBottom: 18,
            }}
          >
            <div
              style={{
                color: "#60a5fa",
                fontSize: 11,
                fontWeight: 700,
                letterSpacing: "1px",
                marginBottom: 4,
              }}
            >
              TOTAL
            </div>

            <div
              style={{
                color: "#fff",
                fontSize: 34,
                fontWeight: 800,
              }}
            >
              ₹{Math.round(chart.total).toLocaleString()}
            </div>
          </div>

          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={chart.data}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(96,165,250,0.08)"
              />

              <XAxis
                dataKey="name"
                tick={{
                  fill: "#94a3b8",
                  fontSize: 11,
                }}
                axisLine={false}
                tickLine={false}
              />

              <YAxis
                tick={{
                  fill: "#94a3b8",
                  fontSize: 11,
                }}
                tickFormatter={(v) =>
                  `₹${(v / 1000).toFixed(0)}k`
                }
                axisLine={false}
                tickLine={false}
              />

              <Tooltip
                contentStyle={{
                  background: "#08101f",
                  border:
                    "1px solid rgba(96,165,250,0.15)",
                  borderRadius: 12,
                  color: "#fff",
                }}
                formatter={(v: any) => [
                  `₹${Math.round(v).toLocaleString()}`,
                  "",
                ]}
              />

              <Area
                type="monotone"
                dataKey="amount"
                stroke={chart.color}
                fill={chart.fill}
                strokeWidth={3}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ))}
    </div>
  </div>
)}

       {/* ── CHAT ── */}
<div className="fade6" style={{ display: "flex", gap: 0, background: "#080f1e", border: "1px solid #0d1f3c", borderRadius: 16, overflow: "hidden", minHeight: 500 }}>

  {/* SIDEBAR — threads */}
  <div style={{ width: sidebarOpen ? 220 : 0, minWidth: sidebarOpen ? 220 : 0, background: "#050c1a", borderRight: "1px solid #0d1f3c", transition: "all 0.3s ease", overflow: "hidden", display: "flex", flexDirection: "column" }}>
    <div style={{ padding: "16px 14px 10px", borderBottom: "1px solid #0d1f3c" }}>
      <button onClick={newSession} style={{ width: "100%", padding: "9px 12px", background: "#1d4ed8", border: "none", borderRadius: 8, color: "#fff", fontSize: 11, cursor: "pointer", fontFamily: "inherit", fontWeight: 600, letterSpacing: "1px" }}>
        + NEW CHAT
      </button>
    </div>
    <div style={{ flex: 1, overflowY: "auto", padding: "8px 8px" }}>
      {sessions.length === 0 && (
        <div style={{ fontSize: 10, color: "#1e3a5f", padding: "12px 6px", textAlign: "center" }}>No chats yet</div>
      )}
      {sessions.map((s) => (
        <div key={s.session_id} onClick={() => loadSession(s.session_id)}
          style={{ padding: "9px 10px", borderRadius: 8, cursor: "pointer", marginBottom: 4, background: currentSessionId === s.session_id ? "rgba(29,78,216,0.15)" : "transparent", border: currentSessionId === s.session_id ? "1px solid #1d4ed820" : "1px solid transparent", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 6, transition: "all 0.15s" }}>
          <div style={{ fontSize: 11, color: currentSessionId === s.session_id ? "#93c5fd" : "#475569", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>
            {s.title || "Untitled"}
          </div>
          <button onClick={(e) => deleteSession(s.session_id, e)}
            style={{ background: "none", border: "none", color: "#1e3a5f", cursor: "pointer", fontSize: 12, padding: "0 2px", flexShrink: 0, lineHeight: 1 }}>
            ×
          </button>
        </div>
      ))}
    </div>
  </div>

  {/* MAIN CHAT AREA */}
  <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>

    {/* Chat header */}
    <div style={{ padding: "16px 20px 12px", borderBottom: "1px solid #0d1f3c", display: "flex", alignItems: "center", gap: 12 }}>
      <button onClick={() => setSidebarOpen(o => !o)} style={{ background: "none", border: "1px solid #0d1f3c", borderRadius: 6, color: "#475569", cursor: "pointer", padding: "4px 8px", fontSize: 14 }}>
        {sidebarOpen ? "◀" : "▶"}
      </button>
      <div>
        <div style={{ fontSize: 11, color: "#334155", letterSpacing: "4px", textTransform: "uppercase", fontFamily: "ui-monospace, monospace" }}>Ask Nerve</div>
        <div style={{ fontSize: 15, fontWeight: 800, color: "#fff", fontFamily: "-apple-system, sans-serif" }}>Got a question about your finances? Just ask.</div>
      </div>
    </div>

    {/* Messages */}
    <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px", display: "flex", flexDirection: "column", gap: 12, minHeight: 280, maxHeight: 380 }}>
      {messages.length === 0 && !streamingReply && (
        <div style={{ textAlign: "center", color: "#1e3a5f", fontSize: 12, marginTop: 40, fontFamily: "ui-monospace, monospace" }}>
          Start a conversation — ask about zombie SKUs, cash flow, margins...
        </div>
      )}
      {messages.map((m, i) => (
        <div key={i} style={{ display: "flex", justifyContent: m.role === "user" ? "flex-end" : "flex-start" }}>
          <div style={{
            maxWidth: "80%", padding: "10px 14px", borderRadius: 10, fontSize: 12, lineHeight: 1.7, fontFamily: "-apple-system, sans-serif",
            background: m.role === "user" ? "#1d4ed8" : "#0a1322",
            color: m.role === "user" ? "#fff" : "#cbd5e1",
            border: m.role === "user" ? "none" : "1px solid #1e3a5f"
          }}>
            {m.content}
          </div>
        </div>
      ))}
      {streamingReply && (
        <div style={{ display: "flex", justifyContent: "flex-start" }}>
          <div style={{ maxWidth: "80%", padding: "10px 14px", borderRadius: 10, fontSize: 12, lineHeight: 1.7, background: "#0a1322", color: "#cbd5e1", border: "1px solid #1e3a5f", fontFamily: "-apple-system, sans-serif" }}>
            {streamingReply}
            <span style={{ borderRight: "2px solid #60a5fa", marginLeft: 2, animation: "pulse 1s infinite" }} />
          </div>
        </div>
      )}
      {chatLoading && !streamingReply && (
        <div style={{ display: "flex", justifyContent: "flex-start" }}>
          <div style={{ padding: "10px 14px", borderRadius: 10, fontSize: 11, background: "#0a1322", color: "#334155", border: "1px solid #0d1f3c", fontFamily: "ui-monospace, monospace", letterSpacing: "2px" }}>
            NERVE THINKING...
          </div>
        </div>
      )}
    </div>

    {/* Input */}
    <div style={{ padding: "12px 20px 16px", borderTop: "1px solid #0d1f3c" }}>
      <div style={{ display: "flex", gap: 10 }}>
        <input value={chat} onChange={(e) => setChat(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleAsk()}
          placeholder="Why is my profit dropping? Unpublish zombie SKUs..."
          style={{ flex: 1, background: "#0a1322", border: "1px solid #1e3a5f", borderRadius: 10, padding: "11px 16px", color: "#e2e8f0", fontSize: 12, fontFamily: "inherit", outline: "none" }}
        />
        <button onClick={handleAsk} disabled={chatLoading}
          style={{ padding: "11px 24px", background: chatLoading ? "#0d1f3c" : "#1d4ed8", border: "none", borderRadius: 10, color: "#fff", fontSize: 12, cursor: "pointer", fontFamily: "inherit", whiteSpace: "nowrap", transition: "all 0.2s" }}>
          {chatLoading ? "..." : "Send →"}
        </button>
      </div>
      <div style={{ marginTop: 8, fontSize: 10, color: "#1e3a5f" }}>
        Powered by Gemini 2.5 Flash · Connected to your live Stripe + Shopify data
      </div>
    </div>
  </div>
</div>

      </div>

      {/* ── GLOSSARY ── */}
<div
  style={{
    marginTop: 40,
    marginBottom: 40,
    padding: 32,
    borderRadius: 24,
    background:
      "linear-gradient(135deg, rgba(13,31,60,0.95), rgba(8,15,30,0.95))",
    border: "1px solid rgba(96,165,250,0.12)",
  }}
>
  <div style={{ marginBottom: 24 }}>
    <div
      style={{
        color: "#60a5fa",
        fontSize: 12,
        fontWeight: 700,
        letterSpacing: "2px",
        marginBottom: 6,
      }}
    >
      NO MBA REQUIRED
    </div>

    <div
      style={{
        fontSize: 30,
        fontWeight: 800,
        color: "#fff",
        marginBottom: 10,
      }}
    >
      Financial Terms Explained
    </div>

    <div
      style={{
        color: "#94a3b8",
        fontSize: 14,
      }}
    >
      Simple explanations of the terms Nerve uses.
    </div>
  </div>

  <div
    style={{
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      gap: 14,
    }}
  >
    {[
      {
        icon: "",
        term: "Zombie SKU",
        meaning:
          "A product that has been sitting in your shop for a long time and nobody is buying it.",
      },
      {
        icon: "",
        term: "Cash Runway",
        meaning:
          "How many days your business can survive before cash runs out.",
      },
      {
        icon: "",
        term: "Ad Bills",
        meaning:
          "Advertising money you've already spent but haven't paid yet.",
      },
      {
        icon: "",
        term: "Inventory Collision",
        meaning:
          "Too much money stuck in stock while important bills are due soon.",
      },
      {
        icon: "",
        term: "Phantom Liability",
        meaning:
          "Hidden expenses that haven't been charged yet but will hit your account later.",
      },
      {
        icon: "",
        term: "Margin Drift",
        meaning:
          "Sales are increasing but actual profit is slowly decreasing.",
      },
      {
        icon: "",
        term: "Ad Spend Adjustment",
        meaning:
          "Increasing or decreasing your advertising budget.",
      },
      {
        icon: "",
        term: "Supplier Payment Delay",
        meaning:
          "Postponing payments to suppliers to keep cash available longer.",
      },
      {
        icon: "",
        term: "Cash Unlocked",
        meaning:
          "Money freed up by reducing wasteful spending or selling old stock.",
      },
      {
        icon: "",
        term: "Risk Score",
        meaning:
          "Nerve's estimate of how financially healthy or risky your business is.",
      },
    ].map((item) => (
      <div
        key={item.term}
        style={{
          padding: 18,
          borderRadius: 18,
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(96,165,250,0.08)",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            marginBottom: 8,
          }}
        >
          <span style={{ fontSize: 20 }}>{item.icon}</span>

          <span
            style={{
              color: "#fff",
              fontWeight: 700,
              fontSize: 14,
            }}
          >
            {item.term}
          </span>
        </div>

        <div
          style={{
            color: "#94a3b8",
            fontSize: 13,
            lineHeight: 1.7,
          }}
        >
          {item.meaning}
        </div>
      </div>
    ))}
  </div>
</div>
    </div>
  );
}
