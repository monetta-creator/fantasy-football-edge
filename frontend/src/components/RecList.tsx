"use client";
import { Rec, fmt } from "@/lib/api";

const confColor: Record<string, string> = { High: "var(--green)", Medium: "var(--amber)", Low: "var(--red)" };
const kindColor: Record<string, string> = { lineup: "var(--green)", stream: "var(--blue)", ir: "var(--amber)", bye: "var(--red)" };

export function RecList({ recs, onAction, busy }: { recs: Rec[]; onAction: (r: Rec) => void; busy: boolean }) {
  if (!recs.length) return <div className="card p-4 text-sm muted">No changes recommended. Lineup is already the max-win-probability lineup.</div>;
  return (
    <div className="space-y-3">
      {recs.map((r, i) => (
        <div key={i} className="card p-4 border-l-4" style={{ borderLeftColor: kindColor[r.kind] ?? "var(--blue)" }}>
          <div className="flex items-center justify-between">
            <div className="text-[12px] font-semibold uppercase tracking-wide muted">{r.kind}</div>
            <span className="pill"><span className="dot" style={{ background: confColor[r.confidence] }} />{r.confidence}</span>
          </div>
          <div className="text-[18px] font-bold mt-1">{r.headline}</div>
          <div className="flex items-end gap-4 mt-2">
            <div><div className="text-[40px] leading-none font-bold tabular">{r.number > 0 ? "+" : ""}{fmt(r.number, r.unit.includes("prob") ? 1 : r.unit === "pts" || r.unit.includes("pts") ? 1 : 0)}</div><div className="text-[11px] muted uppercase mt-1">{r.unit}</div></div>
            <div className="text-[13px] muted pb-2">{r.secondary}</div>
          </div>
          <p className="text-[13px] mt-2">{r.rationale}</p>
          {r.action !== "none" && (
            <button disabled={busy} className="btn btn-primary mt-3 text-[14px]" onClick={() => onAction(r)}>
              {r.action === "apply_lineup" ? "Apply lineup (record)" : r.action === "add" ? "Record add" : r.action === "move_ir" ? "Record move to IR" : "Do it"}
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
