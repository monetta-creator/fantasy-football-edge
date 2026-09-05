"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { MarkWedge } from "@/components/logos/Marks";
import { ThemeToggle } from "@/components/ThemeToggle";

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
        <Link href="/draft" className="flex items-center gap-2 shrink-0" aria-label="Edge home">
          <MarkWedge size={22} />
          <span className="wordmark">Edge</span>
          <span className="muted text-[13px]">· Marian Prayers</span>
        </Link>
        <nav className="flex items-center gap-1 overflow-x-auto ml-auto" aria-label="App sections">
          {tabs.map(([href, label]) => {
            const active = path?.startsWith(href) || (href === "/draft" && path?.startsWith("/player"));
            return (
              <Link key={href} href={href} className="nav-item" data-active={active ? "true" : undefined}>{label}</Link>
            );
          })}
        </nav>
        <ThemeToggle />
      </div>
    </header>
  );
}
