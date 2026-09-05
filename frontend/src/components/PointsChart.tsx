"use client";
import { useState } from "react";

export type WeekPoint = { week: number; opp: string | null; pts: number };

/** Single-series weekly points line with a projected-mean reference line and hover crosshair. */
export function PointsChart({ weeks, projMean, projLabel, maxWeek = 18 }: { weeks: WeekPoint[]; projMean?: number | null; projLabel?: string; maxWeek?: number }) {
  const [hover, setHover] = useState<number | null>(null);
  const W = 640, H = 200, padL = 34, padR = 12, padT = 14, padB = 26;
  const ys = weeks.map((w) => w.pts);
  const yMax = Math.max(10, ...ys, projMean ?? 0) * 1.1;
  const yMin = Math.min(0, ...ys);
  const x = (wk: number) => padL + ((wk - 1) / (maxWeek - 1)) * (W - padL - padR);
  const y = (v: number) => padT + (1 - (v - yMin) / (yMax - yMin)) * (H - padT - padB);
  const byWeek = new Map(weeks.map((w) => [w.week, w]));
  const path = weeks.map((w, i) => `${i === 0 ? "M" : "L"}${x(w.week).toFixed(1)},${y(w.pts).toFixed(1)}`).join(" ");
  const ticks = niceTicks(yMin, yMax, 4);
  const hp = hover != null ? byWeek.get(hover) : null;
  const onMove = (e: React.MouseEvent<SVGSVGElement> | React.TouchEvent<SVGSVGElement>) => {
    const svg = e.currentTarget; const rect = svg.getBoundingClientRect();
    const cx = "touches" in e ? e.touches[0].clientX : e.clientX;
    const px = ((cx - rect.left) / rect.width) * W;
    const wk = Math.round(((px - padL) / (W - padL - padR)) * (maxWeek - 1) + 1);
    setHover(Math.max(1, Math.min(maxWeek, wk)));
  };
  if (!weeks.length) return <div className="text-sm muted py-6 text-center">No weekly history for this player.</div>;
  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" onMouseMove={onMove} onMouseLeave={() => setHover(null)} onTouchMove={onMove} onTouchEnd={() => setHover(null)} role="img" aria-label="Weekly fantasy points">
        {ticks.map((t) => (
          <g key={t}>
            <line x1={padL} x2={W - padR} y1={y(t)} y2={y(t)} stroke="var(--line)" strokeWidth={1} />
            <text x={padL - 6} y={y(t) + 4} fontSize={11} textAnchor="end" fill="var(--muted)">{t}</text>
          </g>
        ))}
        {Array.from({ length: maxWeek }, (_, i) => i + 1).filter((w) => w % 2 === 1).map((w) => (
          <text key={w} x={x(w)} y={H - 8} fontSize={11} textAnchor="middle" fill="var(--muted)">{w}</text>
        ))}
        {projMean != null && projMean > 0 && (
          <g>
            <line x1={padL} x2={W - padR} y1={y(projMean)} y2={y(projMean)} stroke="var(--green)" strokeWidth={2} strokeDasharray="6 4" />
            <text x={padL + 4} y={y(projMean) - 5} fontSize={11} textAnchor="start" fill="var(--text)">{projLabel ?? "proj"} {projMean.toFixed(1)}</text>
          </g>
        )}
        <path d={path} fill="none" stroke="var(--blue)" strokeWidth={2} strokeLinejoin="round" />
        {weeks.map((w) => <circle key={w.week} cx={x(w.week)} cy={y(w.pts)} r={hover === w.week ? 6 : 4} fill="var(--blue)" stroke="var(--card)" strokeWidth={2} />)}
        {hp && <line x1={x(hp.week)} x2={x(hp.week)} y1={padT} y2={H - padB} stroke="var(--muted)" strokeWidth={1} strokeDasharray="3 3" />}
      </svg>
      {hp && (
        <div className="absolute top-0 left-1/2 -translate-x-1/2 pill" style={{ background: "var(--card)" }}>
          <span className="muted">Wk {hp.week}{hp.opp ? ` vs ${hp.opp}` : ""}</span> <b className="tabular">{hp.pts.toFixed(1)}</b>
        </div>
      )}
    </div>
  );
}

function niceTicks(min: number, max: number, n: number): number[] {
  const span = max - min; const raw = span / n; const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? mag * 10;
  const out: number[] = []; for (let v = Math.ceil(min / step) * step; v <= max; v += step) out.push(Math.round(v * 100) / 100);
  return out;
}
