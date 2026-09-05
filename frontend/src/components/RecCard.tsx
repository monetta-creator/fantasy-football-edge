"use client";
import { useState } from "react";
import { Candidate, Recommend, fmt, pct } from "@/lib/api";

const confColor: Record<string, string> = { High: "var(--green)", Medium: "var(--amber)", Low: "var(--red)" };

export function RecCard({ rec, onDraftMe, onOpen, busy }: { rec: Recommend; onDraftMe: (c: Candidate) => void; onOpen: (c: Candidate) => void; busy: boolean }) {
  const c = rec.recommended;
  const [explain, setExplain] = useState<{ text: string | null; status: string; model?: string | null; detail?: string | null } | null>(null);
  const [explaining, setExplaining] = useState(false);
  const askExplain = async () => {
    setExplaining(true);
    try { const r = await fetch("/api/explain-pick", { method: "POST" }); setExplain(await r.json()); } catch (e) { setExplain({ text: null, status: "error", detail: String(e) }); } finally { setExplaining(false); }
  };
  const inj = c.injury?.flag ? c.injury : null;
  return (
    <div className="card p-5 border-l-4" style={{ borderLeftColor: "var(--green)" }}>
      <div className="flex items-center justify-between">
        <div className="text-[12px] font-semibold uppercase tracking-wide muted">{rec.is_me ? "Recommended pick" : `Target for your pick #${rec.decision_pick}`}</div>
        <span className="pill"><span className="dot" style={{ background: confColor[rec.confidence] }} />{rec.confidence}</span>
      </div>
      <button className="text-left w-full mt-2" onClick={() => onOpen(c)}>
        <div className="text-[28px] font-bold leading-tight">{c.name}</div>
        <div className="text-sm muted mt-0.5"><span className={`font-semibold pos-${c.pos}`}>{c.pos}</span> · {c.team} · ADP {fmt(c.adp, 1)} · bye {c.bye ?? "–"}{inj ? ` · ${inj.label}${inj.return_week ? ` (wk ${inj.return_week})` : ""}` : ""}</div>
      </button>
      <div className="grid grid-cols-3 gap-3 mt-4 items-end">
        <div>
          <div className="text-[56px] leading-none font-bold tabular">{fmt(c.vorp)}</div>
          <div className="text-[11px] muted mt-1 uppercase tracking-wide">VORP</div>
        </div>
        <div>
          <div className="text-[28px] leading-none font-bold tabular">{fmt(c.pts)}</div>
          <div className="text-[11px] muted mt-1 uppercase tracking-wide">Proj pts</div>
        </div>
        <div>
          <div className="text-[28px] leading-none font-bold tabular">{(() => { const sc = rec.scarcity.find((x) => x.pos === c.pos); return sc?.dropoff_to_next != null ? `−${fmt(sc.dropoff_to_next)}` : "–"; })()}</div>
          <div className="text-[11px] muted mt-1 uppercase tracking-wide">If you wait on {c.pos} to #{rec.next_pick ?? "–"}</div>
        </div>
      </div>
      <p className="text-[14px] mt-4 leading-snug">{rec.rationale_llm ?? rec.rationale}</p>
      <div className="flex items-center justify-between mt-2 text-[11px] muted">
        <span>+{fmt(rec.margin, 1)} roster value vs. runner-up · {rec.n_sims} sims · {rec.computed_ms} ms · {rec.rationale_llm ? `AI-written (${rec.llm?.model ?? "LLM"}), numbers verified` : rec.llm?.status && rec.llm.status !== "ok" ? `model text (LLM ${rec.llm.status}${rec.llm.detail ? `: ${rec.llm.detail}` : ""})` : "model text"}</span>
      </div>
      <div className="mt-2">
        {!explain ? <button disabled={explaining} className="pill" onClick={askExplain}>{explaining ? "Asking the model…" : "Explain this pick (AI)"}</button> : explain.text ? (
          <div className="text-[13px] p-3 rounded-xl" style={{ background: "var(--bg)" }}><span className="text-[11px] muted uppercase tracking-wide">AI explanation · {explain.model} · numbers verified</span><p className="mt-1">{explain.text}</p></div>
        ) : <div className="text-[12px] muted">AI explanation unavailable ({explain.status}{explain.detail ? `: ${explain.detail}` : ""}).</div>}
      </div>
      {rec.is_me ? (
        <button disabled={busy} className="btn btn-green w-full mt-4 text-[16px]" onClick={() => onDraftMe(c)}>I took {c.name.split(" ").slice(-1)[0]} · record pick #{rec.pick_no}</button>
      ) : (
        <div className="text-[12px] muted mt-3">Available at #{rec.decision_pick} with {pct(c.p_available_at_decision)} probability.</div>
      )}
    </div>
  );
}
