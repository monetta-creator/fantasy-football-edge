"use client";
import { useEffect, useRef, useState } from "react";

export function PickClock({ pickNo, seconds = 120 }: { pickNo: number | null; seconds?: number }) {
  const [left, setLeft] = useState(seconds);
  const started = useRef<number>(0);
  const lastPick = useRef<number | null>(null);
  useEffect(() => {
    if (pickNo !== lastPick.current) {
      lastPick.current = pickNo;
      started.current = Date.now();
      setLeft(seconds);
    }
  }, [pickNo, seconds]);
  useEffect(() => {
    if (!started.current) started.current = Date.now();
    const t = setInterval(() => setLeft(Math.max(0, seconds - Math.floor((Date.now() - started.current) / 1000))), 250);
    return () => clearInterval(t);
  }, [seconds]);
  const m = Math.floor(left / 60), s = left % 60;
  const color = left <= 20 ? "var(--red)" : left <= 45 ? "var(--amber)" : "var(--green)";
  return (
    <button className="pill tabular" onClick={() => { started.current = Date.now(); setLeft(seconds); }} title="Tap to restart clock">
      <span className="dot" style={{ background: color }} />
      {m}:{s.toString().padStart(2, "0")}
    </button>
  );
}
