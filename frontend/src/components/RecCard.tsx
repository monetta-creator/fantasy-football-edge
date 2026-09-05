"use client";
import { Candidate, Recommend, fmt, pct } from "@/lib/api";

const confColor: Record<string, string> = { High: "var(--green)", Medium: "var(--amber)", Low: "var(--red)" };

export function RecCard({ rec, onDraftMe, onOpen, busy }: { rec: Recommend; onDraftMe: (c: Candidate) => void; onOpen: (c: Candidate) => void; busy: boolean }) {
  const c = rec.recommended;
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
          <div className="text-[28px] leading-none font-bold tabular">{rec.next_pick ? pct(c.p_gone_by_next) : "–"}</div>
          <div className="text-[11px] muted mt-1 uppercase tracking-wide">Gone by #{rec.next_pick ?? "–"}</div>
        </div>
      </div>
      <p className="text-[14px] mt-4 leading-snug">{rec.rationale_llm ?? rec.rationale}</p>
      <div className="flex items-center justify-between mt-2 text-[11px] muted">
        <span>+{fmt(rec.margin, 1)} roster value vs. runner-up · {rec.n_sims} sims · {rec.computed_ms} ms{rec.rationale_llm ? " · LLM" : ""}</span>
      </div>
      {rec.is_me ? (
        <button disabled={busy} className="btn btn-green w-full mt-4 text-[16px]" onClick={() => onDraftMe(c)}>I took {c.name.split(" ").slice(-1)[0]} · record pick #{rec.pick_no}</button>
      ) : (
        <div className="text-[12px] muted mt-3">Available at #{rec.decision_pick} with {pct(c.p_available_at_decision)} probability.</div>
      )}
    </div>
  );
}
