"use client";
import { useRef, useState } from "react";
import { PageRow, api1 } from "@/lib/api";

async function downscale(file: File, maxW = 1800): Promise<string> {
  const url = URL.createObjectURL(file);
  try {
    const img = await new Promise<HTMLImageElement>((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = url; });
    const scale = Math.min(1, maxW / img.width);
    const c = document.createElement("canvas");
    c.width = Math.round(img.width * scale); c.height = Math.round(img.height * scale);
    c.getContext("2d")!.drawImage(img, 0, 0, c.width, c.height);
    return c.toDataURL("image/jpeg", 0.85);
  } finally { URL.revokeObjectURL(url); }
}

export function ImportPage({ teams, defaultTeam, defaultMode, title, onApplied }: { teams: Record<string, string>; defaultTeam: number; defaultMode: "replace" | "merge" | "transactions"; title: string; onApplied: () => void }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [rows, setRows] = useState<PageRow[] | null>(null);
  const [team, setTeam] = useState(defaultTeam);
  const [mode, setMode] = useState(defaultMode);
  const [msg, setMsg] = useState<string | null>(null);
  const onFile = async (f?: File) => {
    if (!f) return;
    setBusy(true); setMsg("Reading screenshot…"); setRows(null);
    try {
      const r = await api1.importPage(await downscale(f));
      setRows(r.rows);
      const guess = Object.entries(teams).find(([, n]) => r.fantasy_team && n.toLowerCase() === r.fantasy_team.toLowerCase());
      if (guess) setTeam(Number(guess[0]));
      if (r.page_type === "transactions") setMode("transactions");
      setMsg(`${r.page_type}: ${r.rows.filter((x) => x.status === "ok").length} matched, ${r.rows.filter((x) => x.status === "ambiguous").length} to confirm, ${r.rows.filter((x) => x.status === "unknown").length} unreadable`);
    } catch (e) { setMsg(String(e)); } finally { setBusy(false); if (fileRef.current) fileRef.current.value = ""; }
  };
  const apply = async () => {
    if (!rows) return;
    setBusy(true);
    try { const r = await api1.applyPage(team, mode, rows.filter((x) => x.player_id)); setMsg(`Applied ${r.applied} players (${mode}).`); setRows(null); onApplied(); }
    catch (e) { setMsg(String(e)); } finally { setBusy(false); }
  };
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between">
        <div className="text-[12px] font-semibold uppercase tracking-wide muted">{title}</div>
        <button disabled={busy} className="pill" onClick={() => fileRef.current?.click()}>{busy ? "Working…" : "Photo / screenshot"}</button>
        <input ref={fileRef} type="file" accept="image/*" capture="environment" hidden onChange={(e) => onFile(e.target.files?.[0])} />
      </div>
      {msg && <div className="text-[12px] mt-2">{msg}</div>}
      {rows && (
        <div className="mt-3">
          <div className="flex gap-2 mb-2">
            <select className="flex-1 text-[13px]" value={team} onChange={(e) => setTeam(Number(e.target.value))}>{Object.entries(teams).map(([s, n]) => <option key={s} value={s}>{s}. {n}</option>)}</select>
            <select className="text-[13px]" value={mode} onChange={(e) => setMode(e.target.value as typeof mode)}><option value="replace">Replace roster</option><option value="merge">Merge into roster</option><option value="transactions">Apply transactions</option></select>
          </div>
          <div className="divide-y line max-h-[45vh] overflow-y-auto">
            {rows.map((r, i) => (
              <div key={i} className="flex items-center gap-2 py-1.5 text-[13px]">
                <span className="dot" style={{ background: r.status === "ok" ? "var(--green)" : r.status === "ambiguous" ? "var(--amber)" : "var(--red)" }} />
                <span className="w-10 muted">{r.slot ?? r.action ?? ""}</span>
                <span className="flex-1 truncate">{r.player_name ?? r.text}{r.status_code ? <span className="muted"> · {r.status_code}</span> : null}</span>
                {r.status === "ambiguous" && <select className="text-[12px] py-1" value={r.player_id ?? ""} onChange={(e) => setRows(rows.map((x, j) => j === i ? { ...x, player_id: e.target.value, status: "ok" } : x))}>{r.candidates.map((c) => <option key={c.id} value={c.id}>{c.name} {Math.round(c.confidence * 100)}%</option>)}</select>}
                <span className="muted text-[11px]">{Math.round(r.confidence * 100)}%</span>
              </div>
            ))}
          </div>
          <button disabled={busy} className="btn btn-primary w-full mt-3" onClick={apply}>Apply to {teams[String(team)]}</button>
        </div>
      )}
    </div>
  );
}
