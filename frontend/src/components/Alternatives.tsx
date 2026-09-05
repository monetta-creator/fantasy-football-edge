"use client";
import { Candidate, Recommend, fmt, pct } from "@/lib/api";

export function Alternatives({ rec, onOpen }: { rec: Recommend; onOpen: (c: Candidate) => void }) {
  return (
    <div className="card p-4">
      <div className="text-[12px] font-semibold uppercase tracking-wide muted mb-2">Next best</div>
      <div className="divide-y line">
        {rec.alternatives.map((a) => (
          <button key={a.id} className="w-full flex items-center gap-3 py-2.5 text-left" onClick={() => onOpen(a)}>
            <span className={`w-8 text-[12px] font-bold pos-${a.pos}`}>{a.pos}</span>
            <span className="flex-1 min-w-0">
              <span className="block truncate font-semibold text-[15px]">{a.name}</span>
              <span className="block text-[12px] muted">{a.team} · ADP {fmt(a.adp, 1)} · {fmt(a.delta_vs_best, 1)} vs #1{a.injury?.flag ? ` · ${a.injury.label}` : ""}</span>
            </span>
            <span className="text-right tabular">
              <span className="block font-bold text-[17px]">{fmt(a.vorp)}</span>
              <span className="block text-[11px] muted">VORP</span>
            </span>
            <span className="text-right tabular w-16">
              <span className="block font-bold text-[15px]" style={{ color: (a.p_gone_by_next ?? 0) > 0.7 ? "var(--red)" : (a.p_gone_by_next ?? 0) > 0.35 ? "var(--amber)" : "var(--green)" }}>{rec.next_pick ? pct(a.p_gone_by_next) : "–"}</span>
              <span className="block text-[11px] muted">gone #{rec.next_pick ?? "–"}</span>
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
