"use client";
import { Recommend, fmt } from "@/lib/api";

export function ScarcityPanel({ rec }: { rec: Recommend }) {
  return (
    <div className="card p-4">
      <div className="text-[12px] font-semibold uppercase tracking-wide muted mb-2">Positional drop-off to #{rec.next_pick ?? "–"}</div>
      <div className="grid grid-cols-[auto_1fr_auto_auto_auto] gap-x-3 gap-y-1 text-[13px] tabular">
        <div className="muted text-[11px]">POS</div><div className="muted text-[11px]">BEST NOW</div><div className="muted text-[11px] text-right">NOW</div><div className="muted text-[11px] text-right">@#{rec.next_pick ?? "–"}</div><div className="muted text-[11px] text-right">DROP</div>
        {rec.scarcity.map((s) => (
          <>
            <div key={s.pos + "a"} className={`font-bold pos-${s.pos}`}>{s.pos}</div>
            <div key={s.pos + "b"} className="truncate">{s.best_now.name}</div>
            <div key={s.pos + "c"} className="text-right">{fmt(s.best_now.pts)}</div>
            <div key={s.pos + "d"} className="text-right">{fmt(s.expected_best_at_next)}</div>
            <div key={s.pos + "e"} className="text-right font-semibold" style={{ color: (s.dropoff_to_next ?? 0) > 40 ? "var(--red)" : (s.dropoff_to_next ?? 0) > 15 ? "var(--amber)" : "var(--green)" }}>{fmt(s.dropoff_to_next)}</div>
          </>
        ))}
      </div>
      {rec.likely_available_next.length > 0 && (
        <div className="mt-4">
          <div className="text-[12px] font-semibold uppercase tracking-wide muted mb-1">Likely there at #{rec.next_pick}</div>
          <div className="flex flex-wrap gap-2">
            {rec.likely_available_next.map((p) => (
              <span key={p.id} className="pill"><span className={`pos-${p.pos}`}>{p.pos}</span> {p.name} <span className="muted">{Math.round(p.p_available * 100)}%</span></span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
