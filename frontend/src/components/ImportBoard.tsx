"use client";
import { useRef, useState } from "react";
import { fmt } from "@/lib/api";

type Row = { text: string; position: string | null; nfl_team: string | null; fantasy_team: string | null; pick_no: number | null; team: number | null;
  status: "ok" | "ambiguous" | "unknown" | "already_drafted"; confidence: number; player_id: string | null; player_name: string | null;
  candidates: { id: string; name: string; pos: string; team: string | null; confidence: number }[] };
type Result = { board_type: string; model: string; rows: Row[]; next_pick_no: number; ok: number; ambiguous: number; unknown: number };

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

export function ImportBoard({ teams, onApplied }: { teams: Record<string, string>; onApplied: () => void }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<Result | null>(null);
  const [sel, setSel] = useState<Record<number, string | null>>({});
  const [msg, setMsg] = useState<string | null>(null);

  const onFile = async (f: File | undefined) => {
    if (!f) return;
    setBusy(true); setMsg("Reading board photo…"); setRes(null);
    try {
      const image = await downscale(f);
      const r = await fetch("/api/import-screenshot", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ image }) });
      if (!r.ok) throw new Error(await r.text());
      const data: Result = await r.json();
      setRes(data);
      const s: Record<number, string | null> = {};
      data.rows.forEach((row, i) => { s[i] = row.status === "ok" || row.status === "ambiguous" ? row.player_id : null; });
      setSel(s);
      setMsg(`${data.ok} matched, ${data.ambiguous} to confirm, ${data.unknown} unreadable · ${data.model}`);
    } catch (e) { setMsg(String(e)); } finally { setBusy(false); if (fileRef.current) fileRef.current.value = ""; }
  };
  const apply = async () => {
    if (!res) return;
    const picks = res.rows.map((r, i) => ({ r, id: sel[i] })).filter((x) => x.id && x.r.status !== "already_drafted").map((x) => ({ player_id: x.id!, team: x.r.team ?? undefined }));
    setBusy(true);
    try {
      const r = await fetch("/api/picks/bulk", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ picks }) });
      const data = await r.json();
      setMsg(`Applied ${data.applied?.length ?? 0} picks${data.errors?.length ? ` · ${data.errors.length} skipped: ${data.errors.join("; ")}` : ""}`);
      setRes(null); onApplied();
    } catch (e) { setMsg(String(e)); } finally { setBusy(false); }
  };
  const color = (s: Row["status"]) => s === "ok" ? "var(--green)" : s === "ambiguous" ? "var(--amber)" : s === "already_drafted" ? "var(--blue)" : "var(--red)";
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between">
        <div className="text-[12px] font-semibold uppercase tracking-wide muted">Import board photo</div>
        <button disabled={busy} className="pill" onClick={() => fileRef.current?.click()}>{busy ? "Working…" : "Photo / screenshot"}</button>
        <input ref={fileRef} type="file" accept="image/*" capture="environment" hidden onChange={(e) => onFile(e.target.files?.[0])} />
      </div>
      <div className="text-[12px] muted mt-1">Screenshot the Yahoo draft board; a vision model transcribes it, every name is matched to our pool, and you confirm before anything is applied. Picks are applied in order from pick #{res?.next_pick_no ?? "…"}.</div>
      {msg && <div className="text-[12px] mt-2">{msg}</div>}
      {res && (
        <div className="mt-3">
          <div className="divide-y line max-h-[50vh] overflow-y-auto">
            {res.rows.map((r, i) => (
              <div key={i} className="flex items-center gap-2 py-2 text-[13px]">
                <input type="checkbox" checked={!!sel[i] && r.status !== "already_drafted"} disabled={r.status === "already_drafted" || r.status === "unknown"} onChange={(e) => setSel({ ...sel, [i]: e.target.checked ? (sel[i] ?? r.player_id) : null })} />
                <span className="dot" style={{ background: color(r.status) }} />
                <span className="w-10 muted tabular">#{r.pick_no ?? "?"}</span>
                <span className="flex-1 min-w-0">
                  {r.status === "ambiguous" ? (
                    <select className="w-full text-[13px] py-1" value={sel[i] ?? ""} onChange={(e) => setSel({ ...sel, [i]: e.target.value || null })}>
                      {r.candidates.map((c) => <option key={c.id} value={c.id}>{c.name} ({c.pos} {c.team}) {Math.round(c.confidence * 100)}%</option>)}
                    </select>
                  ) : (
                    <span className="block truncate">{r.player_name ?? r.text}{r.status === "unknown" ? <span className="muted"> (read as “{r.text}”, no match)</span> : null}{r.status === "already_drafted" ? <span className="muted"> · already on board</span> : null}</span>
                  )}
                  <span className="block text-[11px] muted">read “{r.text}” {r.position ?? ""} {r.nfl_team ?? ""} → {r.team ? teams[String(r.team)] : "team ?"} · {fmt(r.confidence * 100)}%</span>
                </span>
              </div>
            ))}
          </div>
          <button disabled={busy} className="btn btn-primary w-full mt-3" onClick={apply}>Apply {res.rows.filter((r, i) => sel[i] && r.status !== "already_drafted").length} picks in order</button>
        </div>
      )}
    </div>
  );
}
