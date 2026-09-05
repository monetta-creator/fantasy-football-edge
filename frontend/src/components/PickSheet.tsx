"use client";
import Link from "next/link";
import { TeamChips } from "@/components/TeamChips";
import { Board, Brief, fmt } from "@/lib/api";

type P = Brief & { ppg?: number; vols?: number; injury?: Brief["injury"]; stash_value?: number; mechanism?: string; p_gone_by_next?: number | null };

export function PickSheet({ p, board, onClose, onPick, busy }: { p: P; board: Board; onClose: () => void; onPick: (id: string, team?: number) => void; busy: boolean }) {
  const inj = p.injury;
  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center sm:justify-center" onClick={onClose} style={{ background: "rgba(0,0,0,.35)" }}>
      <div className="card w-full sm:max-w-md p-5 rounded-b-none sm:rounded-b-[18px]" onClick={(e) => e.stopPropagation()}>
        <div className="text-[22px] font-bold">{p.name}</div>
        <div className="text-sm muted"><span className={`font-semibold pos-${p.pos}`}>{p.pos}</span> · {p.team ?? "FA"} · ADP {fmt(p.adp, 1)} · bye {p.bye ?? "–"}</div>
        <div className="grid grid-cols-3 gap-3 mt-3">
          <div><div className="text-[26px] font-bold tabular">{fmt(p.vorp)}</div><div className="text-[10px] muted uppercase">VORP</div></div>
          <div><div className="text-[26px] font-bold tabular">{fmt(p.pts)}</div><div className="text-[10px] muted uppercase">Proj pts</div></div>
          <div><div className="text-[26px] font-bold tabular">{p.ppg != null ? fmt(p.ppg, 1) : "–"}</div><div className="text-[10px] muted uppercase">Per game</div></div>
        </div>
        {inj?.flag && (
          <div className="mt-3 text-[13px] flex items-center gap-2"><span className="dot" style={{ background: inj.ir_eligible ? "var(--blue)" : "var(--amber)" }} />{inj.label}{inj.type ? ` · ${inj.type}` : ""}{inj.return_week ? ` · back wk ${inj.return_week}` : ""} · {inj.ir_eligible ? "IR-eligible" : "not IR-eligible"}{p.stash_value ? ` · stash ${fmt(p.stash_value)}` : ""}</div>
        )}
        {p.mechanism && <p className="mt-3 text-[13px] muted">{p.mechanism}</p>}
        {board.pick_no ? (
          <div className="mt-4 space-y-2">
            <div className="text-[11px] muted">Who took him at #{board.pick_no}? Tap a team.</div>
            <TeamChips teams={board.teams} onClock={board.on_clock_team} mySlot={5} busy={busy} onPick={(team) => onPick(p.id, team)} />
          </div>
        ) : <div className="mt-4 muted text-sm">Draft complete.</div>}
        <div className="flex gap-2 mt-2">
          <Link href={`/player/${encodeURIComponent(p.id)}`} className="btn btn-ghost flex-1 text-[14px] text-center">Details & 2025 chart</Link>
          <button className="btn btn-ghost flex-1 text-[14px]" onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  );
}
