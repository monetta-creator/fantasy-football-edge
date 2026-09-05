export function Stub({ title, phase, bullets }: { title: string; phase: string; bullets: string[] }) {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">{title}</h1>
      <div className="card p-5">
        <div className="pill mb-3"><span className="dot" style={{ background: "var(--blue)" }} />{phase}</div>
        <ul className="space-y-2 text-sm muted">{bullets.map((b) => <li key={b}>• {b}</li>)}</ul>
      </div>
    </div>
  );
}
