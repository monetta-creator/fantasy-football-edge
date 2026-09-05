"use client";
import { useCallback, useEffect, useState } from "react";
import { WeekPlayer, api, api1, fmt } from "@/lib/api";
import { ImportPage } from "@/components/ImportPage";

const SLOTS = ["QB", "WR", "RB", "TE", "W/R", "W/R/T", "K", "DEF", "BN", "IR"];

export default function RosterPage() {
  const [teams, setTeams] = useState<{ slot: number; name: string; players: WeekPlayer[] }[]>([]);
  const [names, setNames] = useState<Record<string, string>>({});
  const [mySlot, setMySlot] = useState(5);
  const [view, setView] = useState<number | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    try {
      const [r, m, b] = await Promise.all([api1.rosters(), api.meta(), api.board()]);
      setTeams(r.teams); setMySlot(m.my_slot); setNames(b.teams); setView((v) => v ?? m.my_slot);
    } catch (e) { setMsg(String(e)); }
  }, []);
  useEffect(() => { const t = setTimeout(load, 0); return () => clearTimeout(t); }, [load]);
  const team = teams.find((t) => t.slot === view);
  const run = async (fn: () => Promise<unknown>, ok: string) => { setBusy(true); try { await fn(); setMsg(ok); await load(); } catch (e) { setMsg(String(e)); } finally { setBusy(false); } };
  const bench = team?.players.filter((p) => p.slot === "BN").length ?? 0;
  const ir = team?.players.filter((p) => p.slot === "IR").length ?? 0;
  const irCandidates = team?.players.filter((p) => p.injury?.ir_eligible && p.slot !== "IR") ?? [];
  return (
    <div className="space-y-3">
      <h1 className="text-2xl font-bold">Roster</h1>
      <div className="flex gap-2 items-center">
        <select className="flex-1" value={view ?? mySlot} onChange={(e) => setView(Number(e.target.value))}>{Object.entries(names).map(([s, n]) => <option key={s} value={s}>{s}. {n}{Number(s) === mySlot ? " (me)" : ""}</option>)}</select>
        {team && team.players.length === 0 && <button disabled={busy} className="btn btn-primary text-[13px]" onClick={() => run(() => api1.seed(false), "Rosters seeded from the draft board.")}>Seed from draft</button>}
      </div>
      {msg && <div className="text-[13px] card p-3">{msg}</div>}
      {team && view === mySlot && (
        <div className="card p-4 border-l-4" style={{ borderLeftColor: irCandidates.length ? "var(--amber)" : "var(--green)" }}>
          <div className="text-[12px] font-semibold uppercase tracking-wide muted">IR choreography</div>
          <div className="text-[13px] mt-1">Bench {bench}/6 · IR {ir}/6. {irCandidates.length ? `${irCandidates.length} IR-eligible player(s) not on IR: ${irCandidates.map((p) => p.name).join(", ")}. Move them to open bench slots before Tuesday waivers.` : "Every IR-eligible player is parked. Keep one bench slot open before Tuesday processing."}</div>
          {irCandidates.map((p) => <button key={p.id} disabled={busy} className="btn btn-primary mt-2 mr-2 text-[13px]" onClick={() => run(() => api1.move(p.id, "IR"), `Recorded ${p.name} → IR. Make the move in Yahoo.`)}>Record {p.name} → IR</button>)}
        </div>
      )}
      {team && (
        <div className="card p-4">
          <div className="text-[12px] font-semibold uppercase tracking-wide muted mb-1">{team.name} · {team.players.length} players</div>
          {team.players.length === 0 && <div className="text-sm muted">Empty. Seed from the draft board after the draft, or import a roster screenshot below.</div>}
          {[...team.players].sort((a, b) => SLOTS.indexOf(a.slot ?? "BN") - SLOTS.indexOf(b.slot ?? "BN")).map((p) => (
            <div key={p.id} className="flex items-center gap-2 py-1.5 border-b line last:border-0 text-[13px]">
              <select className="text-[12px] py-1 w-20" value={p.slot ?? "BN"} disabled={busy} onChange={(e) => run(() => api1.move(p.id, e.target.value, team.slot), `Moved ${p.name} to ${e.target.value}.`)}>{SLOTS.map((s) => <option key={s} value={s}>{s}</option>)}</select>
              <span className="flex-1 min-w-0 truncate"><span className={`font-semibold pos-${p.pos}`}>{p.pos}</span> {p.name} <span className="muted">{p.team ?? ""}{p.on_bye ? " · BYE" : p.opp ? ` · vs ${p.opp}` : ""}{p.injury?.flag ? ` · ${p.injury.code}${p.injury.ir_eligible ? " (IR-ok)" : ""}` : ""}</span></span>
              <span className="tabular w-10 text-right font-semibold">{fmt(p.mean, 1)}</span>
              <span className="tabular w-10 text-right muted text-[11px]">{fmt(p.season_pts, 0)}</span>
              <button disabled={busy} className="pill text-[11px]" onClick={() => run(() => api1.drop(p.id, team.slot), `Dropped ${p.name} (recorded).`)}>Drop</button>
            </div>
          ))}
        </div>
      )}
      <ImportPage teams={names} defaultTeam={view ?? mySlot} defaultMode="replace" title="Import roster / transactions screenshot" onApplied={load} />
    </div>
  );
}
