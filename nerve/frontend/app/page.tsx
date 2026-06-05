"use client";
import { useEffect, useState } from "react";
import axios from "axios";
import {
  LineChart, Line, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, RadialBarChart, RadialBar
} from "recharts";

const API = "http://localhost:8000/api";


type Signal = {
  status: string;
  severity: number;
  alert: string;
  [key: string]: any;
};

type ScoreData = {
  silent_killer_score: number;
  risk_level: string;
  cross_signal_reason: string | null;
  cross_signal_bonus: number;
  signals: { [key: string]: Signal };
};

type WhatIfResult = {
  baseline: { runway_days: number; true_cash: number; silent_killer_score: number };
  projected: { runway_days: number; true_cash: number; silent_killer_score: number; daily_burn: number; freed_capital: number };
  improvement: { runway_change: number; score_change: number; cash_freed: number };
};

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

  useEffect(() => {
    fetchAll();
  }, []);

  useEffect(() => {
    runWhatIf();
  }, [adSpend, pauseZombie, delayPayment]);

  async function fetchAll() {
    setLoading(true);
    try {
      const [scoreRes, fivetranRes] = await Promise.all([
        axios.get(`${API}/score`),
        axios.get(`${API}/fivetran/sync`),
      ]);
      setScore(scoreRes.data);
      setFivetran(fivetranRes.data);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  }

  async function runWhatIf() {
    try {
      const res = await axios.post(`${API}/whatif`, {
        ad_spend_change: adSpend,
        return_rate_change: 0,
        pause_zombie_sku: pauseZombie,
        delay_payment_days: delayPayment,
      });
      setWhatif(res.data);
    } catch (e) {}
  }

  async function executeAction(actionId: string) {
    setExecuting(actionId);
    try {
      const res = await axios.post(`${API}/execute`, {
        action_id: actionId,
        confirmed: true,
      });
      setExecuted((prev) => ({ ...prev, [actionId]: res.data }));
    } catch (e) {}
    setExecuting(null);
  }

  const scoreColor = (s: number) =>
    s > 60 ? "#E24B4A" : s > 30 ? "#EF9F27" : "#639922";

  const statusColor = (status: string) =>
    status === "CRITICAL" ? "#E24B4A" : status === "WARNING" ? "#EF9F27" : "#639922";

  const statusBg = (status: string) =>
    status === "CRITICAL" ? "#FCEBEB" : status === "WARNING" ? "#FAEEDA" : "#EAF3DE";

  const signalNames: { [key: string]: string } = {
    zombie_sku: "Zombie SKU",
    cash_cliff: "Cash Cliff",
    margin_drift: "Margin Drift",
    inventory_collision: "Inventory Collision",
    phantom_liability: "Phantom Liability",
  };

  const signalIcons: { [key: string]: string } = {
    zombie_sku: "",
    cash_cliff: "",
    margin_drift: "",
    inventory_collision: "",
    phantom_liability: "",
  };

  const runwayData = whatif
    ? [
        { name: "Baseline", days: whatif.baseline.runway_days },
        { name: "Projected", days: whatif.projected.runway_days },
      ]
    : [];

  const scoreGaugeData = score
    ? [{ value: score.silent_killer_score, fill: scoreColor(score.silent_killer_score) }]
    : [];

    const handleAsk = async () => {
  if (!chat.trim()) return;
  setChatLoading(true);
  setReply("");
  
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: chat }),
  });
  
  const data = await res.json();
  setReply(data.reply);
  setChatLoading(false);
  setChat("");
};

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#0a0a0a" }}>
        <div style={{ textAlign: "center", color: "#888" }}>
          <div style={{ fontSize: 32, marginBottom: 16 }}>⚡</div>
          <div style={{ fontFamily: "monospace", fontSize: 14 }}>Nerve is scanning your financials...</div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", background: "#0a0a0a", color: "#f0f0f0", fontFamily: "'IBM Plex Mono', monospace" }}>

    {/* HEADER */}
<div style={{ borderBottom: "1px solid #1a1a1a", padding: "28px 40px", display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
  <div>
    <div style={{ display: "flex", alignItems: "baseline", gap: 16 }}>
      <h1 style={{
        fontSize: 72, fontWeight: 900, letterSpacing: "-4px", color: "#fff", margin: 0,
        lineHeight: 1, fontFamily: "'IBM Plex Mono', monospace",
        textShadow: "0 0 40px rgba(226,75,74,0.3)"
      }}>
        NERVE
      </h1>
      <div style={{
        width: 8, height: 8, borderRadius: "50%", background: "#E24B4A",
        marginBottom: 8, boxShadow: "0 0 12px #E24B4A", animation: "pulse 2s infinite"
      }} />
    </div>
    <p style={{
      color: "#333", fontSize: 11, margin: "6px 0 0",
      letterSpacing: "6px", textTransform: "uppercase",
      fontFamily: "'IBM Plex Mono', monospace"
    }}>
      Autonomous D2C Financial Intelligence Engine
    </p>
    <p style={{
      color: "#E24B4A", fontSize: 10, margin: "4px 0 0",
      letterSpacing: "3px", opacity: 0.7
    }}>
      detects hidden losses before they become disasters
    </p>
  </div>
  {fivetran && (
    <div style={{ textAlign: "right", fontSize: 11, color: "#555" }}>
      <div style={{ color: "#639922", marginBottom: 2 }}>● Fivetran {fivetran.status}</div>
      <div>Last sync: {fivetran.last_synced}</div>
      <div>Next: {fivetran.next_sync}</div>
    </div>
  )}
</div>
      <div style={{ padding: "32px 40px", maxWidth: 1200, margin: "0 auto" }}>

        {/* SILENT KILLER SCORE */}
        {score && (
          <div style={{ marginBottom: 40 }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 24, alignItems: "center" }}>

              {/* Score Circle */}
              <div style={{ background: "#111", border: "1px solid #1e1e1e", borderRadius: 16, padding: 32, textAlign: "center" }}>
                <div style={{ fontSize: 11, letterSpacing: "2px", color: "#555", marginBottom: 16, textTransform: "uppercase" }}>
                  Silent Killer Score
                </div>
                <div style={{ fontSize: 72, fontWeight: 700, color: scoreColor(score.silent_killer_score), lineHeight: 1 }}>
                  {score.silent_killer_score}
                </div>
                <div style={{ fontSize: 11, color: "#555", marginTop: 4 }}>/100</div>
                <div style={{
                  marginTop: 16, display: "inline-block", padding: "4px 16px",
                  borderRadius: 4, fontSize: 11, fontWeight: 600, letterSpacing: "2px",
                  background: statusBg(score.risk_level),
                  color: statusColor(score.risk_level),
                }}>
                  {score.risk_level}
                </div>
              </div>

              {/* Cross Signal Reason */}
              <div style={{ background: "#111", border: "1px solid #1e1e1e", borderRadius: 16, padding: 32 }}>
                {score.cross_signal_reason ? (
                  <>
                    <div style={{ fontSize: 11, letterSpacing: "2px", color: "#555", marginBottom: 16, textTransform: "uppercase" }}>
                      Cross-Signal Intelligence
                    </div>
                    <div style={{ fontSize: 15, lineHeight: 1.7, color: "#E24B4A" }}>
                      {score.cross_signal_reason}
                    </div>
                    {score.cross_signal_bonus > 0 && (
                      <div style={{ marginTop: 16, fontSize: 11, color: "#555" }}>
                        +{score.cross_signal_bonus} severity bonus applied
                      </div>
                    )}
                  </>
                ) : (
                  <div style={{ color: "#555", fontSize: 14 }}>No cross-signal patterns detected</div>
                )}

                {/* Severity bars */}
                <div style={{ marginTop: 24 }}>
                  {Object.entries(score.signals).map(([key, sig]) => (
                    <div key={key} style={{ marginBottom: 10 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#555", marginBottom: 4 }}>
                        <span>{signalIcons[key]} {signalNames[key]}</span>
                        <span style={{ color: statusColor(sig.status) }}>{sig.severity}/10</span>
                      </div>
                      <div style={{ background: "#1a1a1a", borderRadius: 2, height: 4 }}>
                        <div style={{
                          height: 4, borderRadius: 2,
                          width: `${sig.severity * 10}%`,
                          background: statusColor(sig.status),
                          transition: "width 0.5s ease"
                        }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* SIGNAL CARDS */}
      {/* SIGNAL CARDS */}
{score && (
  <div style={{ marginBottom: 40 }}>
    <div style={{ fontSize: 11, letterSpacing: "2px", color: "#555", marginBottom: 20, textTransform: "uppercase" }}>
      Signal Detection
    </div>

    {/* CRITICAL signals — full width horizontal */}
    {Object.entries(score.signals)
      .filter(([, sig]) => sig.status === "CRITICAL")
      .map(([key, sig]) => (
        <div key={key} style={{
          marginBottom: 10,
          display: "grid",
          gridTemplateColumns: "180px 1fr auto",
          alignItems: "center",
          gap: 0,
          borderRadius: 8,
          overflow: "hidden",
          border: "1px solid #2a0a0a",
        }}>
          {/* Left — name block */}
          <div style={{
            background: "#E24B4A",
            padding: "20px 24px",
            display: "flex", flexDirection: "column", justifyContent: "center",
          }}>
            <div style={{ fontSize: 22 }}>{signalIcons[key]}</div>
            <div style={{ fontSize: 13, fontWeight: 700, color: "#fff", marginTop: 6, letterSpacing: "-0.5px" }}>
              {signalNames[key]}
            </div>
            <div style={{ fontSize: 10, color: "rgba(255,255,255,0.6)", letterSpacing: "2px", marginTop: 2 }}>
              CRITICAL
            </div>
          </div>

          {/* Middle — alert */}
          <div style={{ background: "#0f0505", padding: "20px 28px" }}>
            <div style={{ fontSize: 12, color: "#ccc", lineHeight: 1.7, marginBottom: 8 }}>
              {sig.alert}
            </div>
            {key === "zombie_sku" && sig.zombies?.map((z: any) => (
              <span key={z.sku_id} style={{
                display: "inline-block", marginRight: 8, marginTop: 4,
                padding: "3px 10px", borderRadius: 2,
                background: "#1a0a0a", border: "1px solid #2a1010",
                fontSize: 10, color: "#E24B4A"
              }}>
                {z.product_name} · {z.days_since_sold}d · ₹{z.locked_capital.toLocaleString()}
              </span>
            ))}
            {key === "phantom_liability" && sig.platforms?.map((p: any) => (
              <span key={p.platform} style={{
                display: "inline-block", marginRight: 8, marginTop: 4,
                padding: "3px 10px", borderRadius: 2,
                background: "#1a0a0a", border: "1px solid #2a1010",
                fontSize: 10, color: "#E24B4A"
              }}>
                {p.platform} · ₹{Math.round(p.unbilled_amount).toLocaleString()} · {p.earliest_charge}
              </span>
            ))}
          </div>

          {/* Right — severity */}
          <div style={{
            background: "#0f0505", padding: "20px 24px",
            textAlign: "center", borderLeft: "1px solid #1a0808"
          }}>
            <div style={{ fontSize: 32, fontWeight: 900, color: "#E24B4A", lineHeight: 1 }}>
              {sig.severity}
            </div>
            <div style={{ fontSize: 9, color: "#555", letterSpacing: "1px", marginTop: 2 }}>/10</div>
          </div>
        </div>
      ))}

    {/* WARNING + HEALTHY — compact horizontal list */}
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 10 }}>
      {Object.entries(score.signals)
        .filter(([, sig]) => sig.status !== "CRITICAL")
        .map(([key, sig]) => (
          <div key={key} style={{
            display: "flex", alignItems: "center", gap: 16,
            padding: "14px 20px",
            background: "#0d0d0d",
            border: `1px solid ${sig.status === "WARNING" ? "#2a2010" : "#0d1a0d"}`,
            borderRadius: 8,
            borderLeft: `3px solid ${statusColor(sig.status)}`,
          }}>
            <span style={{ fontSize: 20 }}>{signalIcons[key]}</span>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: "#aaa" }}>{signalNames[key]}</div>
              <div style={{ fontSize: 10, color: "#555", marginTop: 2 }}>{sig.alert}</div>
            </div>
            <div style={{
              fontSize: 20, fontWeight: 900,
              color: statusColor(sig.status), minWidth: 28, textAlign: "right"
            }}>
              {sig.severity}
            </div>
          </div>
        ))}
    </div>
  </div>
)}
        

        {/* WHAT-IF SIMULATOR */}
        <div style={{ marginBottom: 40, background: "#111", border: "1px solid #1e1e1e", borderRadius: 16, padding: 32 }}>
          <div style={{ fontSize: 11, letterSpacing: "2px", color: "#555", marginBottom: 24, textTransform: "uppercase" }}>
            What-If Simulator
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 32 }}>
            {/* Controls */}
            <div>
              <div style={{ marginBottom: 24 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#888", marginBottom: 8 }}>
                  <span>Ad Spend Change</span>
                  <span style={{ color: adSpend < 0 ? "#639922" : adSpend > 0 ? "#E24B4A" : "#888" }}>
                    {adSpend > 0 ? "+" : ""}{adSpend}%
                  </span>
                </div>
                <input type="range" min={-50} max={50} value={adSpend} step={5}
                  onChange={(e) => setAdSpend(Number(e.target.value))}
                  style={{ width: "100%", accentColor: "#E24B4A" }}
                />
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "#444", marginTop: 4 }}>
                  <span>-50%</span><span>0</span><span>+50%</span>
                </div>
              </div>

              <div style={{ marginBottom: 24 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#888", marginBottom: 8 }}>
                  <span>Delay Payment</span>
                  <span style={{ color: "#EF9F27" }}>{delayPayment} days</span>
                </div>
                <input type="range" min={0} max={30} value={delayPayment} step={5}
                  onChange={(e) => setDelayPayment(Number(e.target.value))}
                  style={{ width: "100%", accentColor: "#EF9F27" }}
                />
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "#444", marginTop: 4 }}>
                  <span>0</span><span>15d</span><span>30d</span>
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 16px", background: "#1a1a1a", borderRadius: 8, cursor: "pointer" }}
                onClick={() => setPauseZombie(!pauseZombie)}>
                <div style={{
                  width: 20, height: 20, borderRadius: 4,
                  border: `2px solid ${pauseZombie ? "#639922" : "#333"}`,
                  background: pauseZombie ? "#639922" : "transparent",
                  display: "flex", alignItems: "center", justifyContent: "center"
                }}>
                  {pauseZombie && <span style={{ fontSize: 12, color: "#fff" }}>✓</span>}
                </div>
                <span style={{ fontSize: 12, color: "#888" }}>🧟 Pause Zombie SKU Ads</span>
              </div>
            </div>

            {/* Results */}
            {whatif && (
              <div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 20 }}>
                  {[
                    { label: "Runway", base: `${whatif.baseline.runway_days}d`, proj: `${whatif.projected.runway_days}d`, change: whatif.improvement.runway_change },
                    { label: "True Cash", base: `₹${Math.round(whatif.baseline.true_cash).toLocaleString()}`, proj: `₹${Math.round(whatif.projected.true_cash).toLocaleString()}`, change: whatif.projected.true_cash - whatif.baseline.true_cash },
                    { label: "Kill Score", base: `${whatif.baseline.silent_killer_score}`, proj: `${whatif.projected.silent_killer_score}`, change: -whatif.improvement.score_change },
                    { label: "Cash Freed", base: "₹0", proj: `₹${Math.round(whatif.projected.freed_capital).toLocaleString()}`, change: whatif.projected.freed_capital },
                  ].map((item) => (
                    <div key={item.label} style={{ background: "#1a1a1a", borderRadius: 8, padding: 12 }}>
                      <div style={{ fontSize: 10, color: "#555", marginBottom: 4, letterSpacing: "1px" }}>{item.label}</div>
                      <div style={{ fontSize: 11, color: "#555", marginBottom: 2 }}>{item.base} →</div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: item.change > 0 ? "#639922" : item.change < 0 ? "#E24B4A" : "#888" }}>
                        {item.proj}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Mini chart */}
                <ResponsiveContainer width="100%" height={120}>
                  <AreaChart data={[
                    { name: "Now", score: whatif.baseline.silent_killer_score },
                    { name: "Projected", score: whatif.projected.silent_killer_score },
                  ]}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" />
                    <XAxis dataKey="name" tick={{ fill: "#555", fontSize: 10 }} />
                    <YAxis domain={[0, 100]} tick={{ fill: "#555", fontSize: 10 }} />
                    <Tooltip contentStyle={{ background: "#111", border: "1px solid #333", borderRadius: 4, fontSize: 11 }} />
                    <Area type="monotone" dataKey="score" stroke="#E24B4A" fill="#3a1a1a" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </div>

        {/* GUARDRAIL ACTIONS */}
        <div style={{ marginBottom: 40 }}>
          <div style={{ fontSize: 11, letterSpacing: "2px", color: "#555", marginBottom: 16, textTransform: "uppercase" }}>
            Guardrail Actions — Execute via Nerve
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 12 }}>
            {[
              { id: "pause_zombie_ads", label: "⏸Pause Zombie Ads", desc: "Stop bleeding ad spend on dead SKUs", severity: "CRITICAL" },
              { id: "flash_discount", label: " Apply 40% Flash Sale", desc: "Liquidate dead stock to free capital", severity: "CRITICAL" },
              { id: "send_receivable_reminder", label: "Send Payment Reminder", desc: "Chase pending receivables today", severity: "WARNING" },
              { id: "reduce_ad_budget", label: " Reduce Ad Budget 30%", desc: "Reduce phantom liability exposure", severity: "WARNING" },
            ].map((action) => {
              const done = executed[action.id];
              return (
                <div key={action.id} style={{
                  background: "#111", border: `1px solid ${done ? "#1a2a1a" : "#1e1e1e"}`,
                  borderRadius: 12, padding: 20,
                }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "#ccc", marginBottom: 6 }}>{action.label}</div>
                  <div style={{ fontSize: 11, color: "#555", marginBottom: 16, lineHeight: 1.5 }}>{action.desc}</div>
                  {done ? (
                    <div>
                      <div style={{ fontSize: 11, color: "#639922", marginBottom: 4 }}>{done.message}</div>
                      <div style={{ fontSize: 10, color: "#555" }}>{done.impact}</div>
                    </div>
                  ) : (
                    <button
                      onClick={() => executeAction(action.id)}
                      disabled={executing === action.id}
                      style={{
                        width: "100%", padding: "8px 16px", borderRadius: 6,
                        border: `1px solid ${action.severity === "CRITICAL" ? "#3a1a1a" : "#2a2010"}`,
                        background: "transparent", cursor: "pointer", fontSize: 11,
                        color: action.severity === "CRITICAL" ? "#E24B4A" : "#EF9F27",
                        fontFamily: "inherit"
                      }}
                    >
                      {executing === action.id ? "Executing..." : "Execute via Nerve →"}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* FINANCIAL CHARTS */}
        {score && (
          <div style={{ marginBottom: 40 }}>
            <div style={{ fontSize: 11, letterSpacing: "2px", color: "#555", marginBottom: 16, textTransform: "uppercase" }}>
              Financial Overview
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>

              {/* Cash vs Phantom */}
              <div style={{ background: "#111", border: "1px solid #1e1e1e", borderRadius: 12, padding: 20 }}>
                <div style={{ fontSize: 11, color: "#555", marginBottom: 16 }}>Cash Position Reality</div>
                <ResponsiveContainer width="100%" height={180}>
                  <AreaChart data={[
                    { name: "Bank Balance", amount: score.signals.cash_cliff?.bank_balance || 0 },
                    { name: "True Cash", amount: score.signals.phantom_liability?.true_cash || 0 },
                    { name: "After Bills", amount: score.signals.cash_cliff?.net_position || 0 },
                  ]}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" />
                    <XAxis dataKey="name" tick={{ fill: "#555", fontSize: 10 }} />
                    <YAxis tick={{ fill: "#555", fontSize: 10 }} tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} />
                    <Tooltip
                      contentStyle={{ background: "#111", border: "1px solid #333", borderRadius: 4, fontSize: 11 }}
                      formatter={(v: any) => [`₹${Math.round(v).toLocaleString()}`, ""]}
                    />
                    <Area type="monotone" dataKey="amount" stroke="#E24B4A" fill="#1a0a0a" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              {/* Locked Capital */}
              <div style={{ background: "#111", border: "1px solid #1e1e1e", borderRadius: 12, padding: 20 }}>
                <div style={{ fontSize: 11, color: "#555", marginBottom: 16 }}>Capital Breakdown</div>
                <ResponsiveContainer width="100%" height={180}>
                  <AreaChart data={[
                    { name: "Liquid Cash", amount: score.signals.phantom_liability?.true_cash || 0 },
                    { name: "Dead Stock", amount: score.signals.zombie_sku?.total_locked_capital || 0 },
                    { name: "Unbilled Ads", amount: score.signals.phantom_liability?.total_unbilled || 0 },
                    { name: "Upcoming Bills", amount: score.signals.inventory_collision?.upcoming_bills || 0 },
                  ]}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" />
                    <XAxis dataKey="name" tick={{ fill: "#555", fontSize: 9 }} />
                    <YAxis tick={{ fill: "#555", fontSize: 10 }} tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} />
                    <Tooltip
                      contentStyle={{ background: "#111", border: "1px solid #333", borderRadius: 4, fontSize: 11 }}
                      formatter={(v: any) => [`₹${Math.round(v).toLocaleString()}`, ""]}
                    />
                    <Area type="monotone" dataKey="amount" stroke="#EF9F27" fill="#1a1200" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}

        {/* CHAT */}
        <div style={{ background: "#111", border: "1px solid #1e1e1e", borderRadius: 16, padding: 24 }}>
          <div style={{ fontSize: 11, letterSpacing: "2px", color: "#555", marginBottom: 16, textTransform: "uppercase" }}>
            Chat with Nerve
          </div>
          <div style={{ display: "flex", gap: 12 }}>
            <input
              value={chat}
              onChange={(e) => setChat(e.target.value)}
              placeholder="Why is my margin dropping? What should I do first?"
              style={{
                flex: 1, background: "#1a1a1a", border: "1px solid #2a2a2a",
                borderRadius: 8, padding: "10px 16px", color: "#ccc",
                fontSize: 12, fontFamily: "inherit", outline: "none"
              }}
            />
          <button
  onClick={handleAsk}
  disabled={chatLoading}
  style={{
    padding: "10px 20px", background: "#E24B4A", border: "none",
    borderRadius: 8, color: "#fff", fontSize: 12, cursor: "pointer",
    fontFamily: "inherit", opacity: chatLoading ? 0.6 : 1
  }}
>
  {chatLoading ? "..." : "Ask →"}
</button>

{reply && (
  <div style={{
    marginTop: 16, padding: 16, background: "#1a1a1a",
    border: "1px solid #2a2a2a", borderRadius: 8,
    fontSize: 12, color: "#ccc", lineHeight: 1.6
  }}>
    {reply}
  </div>
)}
          </div>
          <div style={{ marginTop: 12, fontSize: 11, color: "#444" }}>
            Ask Nerve anything about your D2C financials • Powered by Gemini 2.5 Flash
          </div>
        </div>

      </div>
    </div>
  );
}