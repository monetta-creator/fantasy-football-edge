"use client";
import { useCallback, useEffect, useState } from "react";
import { Board, Brief, Recommend, api } from "@/lib/api";
import { PickClock } from "@/components/PickClock";
import { RecCard } from "@/components/RecCard";
import { Alternatives } from "@/components/Alternatives";
import { RosterTray } from "@/components/RosterTray";
import { ScarcityPanel } from "@/components/Scarcity";
import { PlayerList } from "@/components/PlayerList";
import { PickSheet } from "@/components/PickSheet";
import { BoardStrip, TeamRosters } from "@/components/BoardStrip";
import { IRStashPanel } from "@/components/IRStash";
import { Pick4Panel } from "@/components/Pick4";
import { ImportBoard } from "@/components/ImportBoard";
import { Rankings } from "@/components/Rankings";
import { Decide } from "@/components/Decide";

type SheetP = Brief & { ppg?: number; vols?: number; stash_value?: number; mechanism?: string; p_gone_by_next?: number | null };
const SUBTABS = ["Decide", "Rankings", "Board", "Roster", "Scarcity", "Stash", "Plan"] as const;

export default function DraftPage() {
  const [board, setBoard] = useState<Board | null>(null);
  const [rec, setRec] = useState<Recommend | null>(null);
  const [version, setVersion] = useState(0);
  const [sheet, setSheet] = useState<SheetP | null>(null);
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState<(typeof SUBTABS)[number]>("Decide");
  const [live, setLive] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const b = await api.board();
      setBoard(b);
      setErr(null);
      const r = await api.recommend();
      setRec(r);
    } catch (e) {
      setErr(String(e));
    }
  }, []);

  useEffect(() => {
    const t0 = setTimeout(refresh, 0);
    const t = live ? setInterval(refresh, 2500) : null;
    return () => { clearTimeout(t0); if (t) clearInterval(t); };
  }, [refresh, version, live]);

  const doPick = async (id: string, team?: number) => {
    setBusy(true);
    try {
      await api.pick(id, team);
      setSheet(null);
      setVersion((v) => v + 1);
      await refresh();
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  };
  const doUndo = async () => {
    setBusy(true);
    try { await api.undo(); setVersion((v) => v + 1); await refresh(); } finally { setBusy(false); }
  };

  if (!board) return <div className="muted text-sm">{err ? `Backend not reachable: ${err}` : "Loading board…"}</div>;
  const done = board.pick_no == null;
  return (
    <div className="space-y-3">
      <header className="flex items-center justify-between gap-2">
        <div>
          <div className="text-[22px] font-bold leading-tight">{done ? "Draft complete" : board.is_me ? "You're on the clock (draft in Yahoo, record here)" : `${board.on_clock_name} is on the clock`}</div>
          <div className="text-[13px] muted">{done ? `${board.drafted_count} picks` : `Pick ${board.pick_no} · Round ${board.round} · your next: #${board.my_next_picks.slice(0, 2).join(", #")}${board.picks_until_me ? ` (${board.picks_until_me} away)` : ""}`}</div>
        </div>
        <div className="flex items-center gap-2">
          {!done && live && <PickClock pickNo={board.pick_no} />}
          <button className="pill" onClick={() => setLive(!live)} title="Live mode: 2-minute clock and auto-refresh">{live ? "Live" : "Tool"}</button>
          <button className="pill" onClick={() => { setVersion((v) => v + 1); refresh(); }}>Refresh</button>
        </div>
      </header>
      {err && <div className="text-[12px]" style={{ color: "var(--red)" }}>{err}</div>}

      {tab !== "Decide" && (rec && !rec.done ? (
        <>
          <RecCard rec={rec} busy={busy} onDraftMe={(c) => doPick(c.id)} onOpen={(c) => setSheet(c)} />
          <Alternatives rec={rec} onOpen={(c) => setSheet(c)} />
        </>
      ) : !done ? <div className="card p-5 text-sm muted">Computing recommendation…</div> : null)}

      <div className="flex gap-1.5 overflow-x-auto pt-1">
        {SUBTABS.map((t) => (
          <button key={t} onClick={() => setTab(t)} className="pill" style={tab === t ? { background: "var(--text)", color: "var(--bg)" } : {}}>{t}</button>
        ))}
      </div>

      {tab === "Decide" && <Decide busy={busy} onChoose={(id) => doPick(id, board.is_me ? undefined : 5)} />}
      {tab === "Rankings" && (
        <Rankings version={version} busy={busy} onGone={(p) => setSheet(p)} onMine={(p) => doPick(p.id, board.is_me ? undefined : 5)} />
      )}
      {tab === "Board" && (
        <>
          <BoardStrip board={board} onUndo={doUndo} busy={busy} />
          <ImportBoard teams={board.teams} onApplied={() => { setVersion((v) => v + 1); refresh(); }} />
          <PlayerList version={version} nextPick={rec?.next_pick ?? null} onOpen={(p) => setSheet(p)} />
          <TeamRosters board={board} />
        </>
      )}
      {tab === "Roster" && <RosterTray board={board} />}
      {tab === "Scarcity" && rec && !rec.done && <ScarcityPanel rec={rec} />}
      {tab === "Stash" && <IRStashPanel version={version} onOpen={(p) => setSheet(p)} />}
      {tab === "Plan" && <Pick4Panel />}

      {sheet && <PickSheet p={sheet} board={board} busy={busy} onClose={() => setSheet(null)} onPick={doPick} />}
    </div>
  );
}
