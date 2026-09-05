"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const tabs = [
  ["/draft", "Draft"],
  ["/dashboard", "Week"],
  ["/roster", "Roster"],
  ["/free-agents", "Free agents"],
  ["/trades", "Trades"],
  ["/playoffs", "Playoffs"],
  ["/ideas", "Ideas"],
  ["/settings", "Settings"],
  ["/about", "About"],
];

/** App-level navigation: a sticky top bar. In-page sections use underlined tabs inside the page instead. */
export function TabBar() {
  const path = usePathname();
  return (
    <header className="sticky top-0 z-40 border-b line backdrop-blur" style={{ background: "color-mix(in srgb, var(--bg) 88%, transparent)" }}>
      <div className="mx-auto max-w-5xl px-4 h-12 flex items-center gap-4">
        <Link href="/draft" className="font-bold text-[15px] tracking-tight shrink-0">Edge <span className="muted font-normal">· Marian Prayers</span></Link>
        <nav className="flex items-center gap-1 overflow-x-auto ml-auto" aria-label="App sections">
          {tabs.map(([href, label]) => {
            const active = path?.startsWith(href) || (href === "/draft" && path?.startsWith("/player"));
            return (
              <Link key={href} href={href} className="px-3 py-1.5 rounded-full text-[13px] whitespace-nowrap" style={active ? { background: "var(--text)", color: "var(--bg)", fontWeight: 600 } : { color: "var(--muted)" }}>{label}</Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
