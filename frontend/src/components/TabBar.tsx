"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const tabs = [
  ["/draft", "Draft"],
  ["/dashboard", "Week"],
  ["/roster", "Roster"],
  ["/free-agents", "FA"],
  ["/trades", "Trades"],
  ["/playoffs", "Playoffs"],
  ["/ideas", "Ideas"],
  ["/settings", "Settings"],
];

export function TabBar() {
  const path = usePathname();
  return (
    <nav className="fixed bottom-0 inset-x-0 border-t line backdrop-blur" style={{ background: "color-mix(in srgb, var(--bg) 85%, transparent)" }}>
      <div className="mx-auto max-w-5xl flex overflow-x-auto no-scrollbar">
        {tabs.map(([href, label]) => {
          const active = path?.startsWith(href);
          return (
            <Link key={href} href={href} className={`flex-1 min-w-[64px] text-center py-3 text-[12px] font-semibold ${active ? "" : "muted"}`}>
              <span className={active ? "border-b-2 pb-1" : ""} style={active ? { borderColor: "var(--text)" } : {}}>{label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
