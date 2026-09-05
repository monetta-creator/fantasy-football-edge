"use client";
import { useState } from "react";

/** Small ⓘ sticker that opens interpretive notes for the block it sits in. */
export function Info({ title, children }: { title?: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <span className="relative inline-block align-middle">
      <button type="button" aria-label="About this" onClick={() => setOpen(!open)} className="inline-flex items-center justify-center w-5 h-5 rounded-full text-[11px] font-bold border line" style={{ color: "var(--blue)", borderColor: "var(--blue)" }}>i</button>
      {open && (
        <span className="absolute z-30 left-0 top-6 w-72 sm:w-96 card p-3 text-[12px] leading-snug text-left" style={{ background: "var(--card)" }} onClick={(e) => e.stopPropagation()}>
          {title && <span className="block font-semibold mb-1">{title}</span>}
          <span className="block muted">{children}</span>
          <button type="button" className="block mt-2 text-[11px] underline" onClick={() => setOpen(false)}>close</button>
        </span>
      )}
    </span>
  );
}
