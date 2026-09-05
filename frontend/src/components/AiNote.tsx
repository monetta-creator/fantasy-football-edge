"use client";
import { useState } from "react";

type Res = { text: string | null; status: string; model?: string | null; detail?: string | null; ms?: number | null };

/** "Explain (AI)" button: the server builds a fact sheet for `topic`, the model rephrases it, numbers are verified. */
export function AiNote({ topic, id, label = "✨ Explain", compact = false }: { topic: string; id?: string; label?: string; compact?: boolean }) {
  const [res, setRes] = useState<Res | null>(null);
  const [busy, setBusy] = useState(false);
  const ask = async () => {
    setBusy(true);
    try { const r = await fetch("/api/explain", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ topic, id }) }); setRes(await r.json()); }
    catch (e) { setRes({ text: null, status: "error", detail: String(e) }); } finally { setBusy(false); }
  };
  if (!res) return <button type="button" disabled={busy} className={`pill ${compact ? "text-[11px]" : ""}`} onClick={ask}>{busy ? "Asking the model…" : label}</button>;
  return res.text ? (
    <div className="text-[13px] p-3 rounded-xl mt-1" style={{ background: "var(--bg)" }}>
      <div className="flex items-center justify-between"><span className="text-[11px] muted uppercase tracking-wide">AI · {res.model} · numbers verified</span><button type="button" className="text-[11px] underline" onClick={() => setRes(null)}>redo</button></div>
      <p className="mt-1">{res.text}</p>
    </div>
  ) : <div className="text-[12px] muted mt-1">AI note unavailable ({res.status}{res.detail ? `: ${res.detail}` : ""}). <button type="button" className="underline" onClick={() => setRes(null)}>retry</button></div>;
}
