"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Play,
  BarChart3,
  Columns3,
  Database,
  Code2,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/backtest", label: "New Backtest", icon: Play },
  { href: "/results", label: "Results", icon: BarChart3 },
  { href: "/compare", label: "Compare", icon: Columns3 },
  { href: "/data", label: "Data Explorer", icon: Database },
  { href: "/strategies", label: "Strategies", icon: Code2 },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 h-screen w-56 bg-bg-secondary border-r border-border flex flex-col z-50">
      <div className="h-14 flex items-center px-5 border-b border-border">
        <Link href="/" className="flex items-center gap-2">
          <div className="w-7 h-7 rounded bg-accent-green/20 flex items-center justify-center">
            <BarChart3 size={16} className="text-accent-green" />
          </div>
          <span className="font-semibold text-text-primary tracking-tight">
            QuantLab
          </span>
        </Link>
      </div>

      <nav className="flex-1 py-3 px-2">
        {NAV_ITEMS.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded text-sm transition-colors ${
                isActive
                  ? "bg-bg-hover text-text-primary"
                  : "text-text-secondary hover:text-text-primary hover:bg-bg-hover"
              }`}
            >
              <item.icon size={16} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-border">
        <p className="text-xs text-text-muted">QuantLab v1.0</p>
      </div>
    </aside>
  );
}
