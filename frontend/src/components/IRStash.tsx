"use client";
import { useEffect, useState } from "react";
import { StashRow, api, fmt } from "@/lib/api";

export function IRStashPanel({ version, onOpen }: { version: number; onOpen: (p: StashRow) => void }) {
  const [rows, setRows] = useState<StashRow[]>([]);
  const [irPlus, setIrPlus] = useState(false);
  useEffect(() => { api.irStash().then((r) => { setRows(r.rows); setIrPlus(r.ir_plus); }).catch(() => {}); }, [version]);
  return (
    <div className="card p-4">
      <div className="text-[12px] font-semibold uppercase tracking-wide muted mb-1">IR stash candidates</div>
      <div className="text-[12px] muted mb-2">Value = weighted surplus over replacement from expected return week through week 17 (playoff weeks ×1.5). Blue = can go straight to IR{irPlus ? " (IR+ mode)" : ""}; amber = must sit on the bench first.</div>
      <div className="divide-y line">
        {rows.filter((r) => !r.drafted).slice(0, 25).map((r) => (
          <button key={r.id} className="w-full flex items-center gap-2 py-2 text-left" onClick={() => onOpen(r)}>
            <span className="dot" style={{ background: r.ir_eligible ? "var(--blue)" : "var(--amber)" }} />
            <span className={`w-8 text-[12px] font-bold pos-${r.pos}`}>{r.pos}</span>
            <span className="flex-1 min-w-0">
              <span className="block truncate text-[15px] font-medium">{r.name}</span>
              <span className="block text-[11px] muted">{r.label}{r.type ? ` · ${r.type}` : ""} · back wk {r.return_week ?? "?"} · ADP {fmt(r.adp, 1)} · {fmt(r.ppg, 1)} ppg</span>
            </span>
            <span className="text-right tabular w-14"><span className="block font-bold text-[16px]">{fmt(r.stash_value)}</span><span className="block text-[10px] muted">stash</span></span>
          </button>
        ))}
      </div>
    </div>
  );
}
