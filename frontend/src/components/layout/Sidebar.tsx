"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Play,
  BarChart3,
  Columns3,
  Database,
  Code2,
  TrendingUp,
  Keyboard,
  X,
  RadioTower,
  GitCompareArrows,
} from "lucide-react";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";

const SHORTCUTS = [
  { key: "N", label: "New Backtest" },
  { key: "R", label: "Results" },
  { key: "D", label: "Dashboard" },
  { key: "C", label: "Compare" },
];

const NAV_SECTIONS = [
  {
    label: "Workspace",
    items: [
      { href: "/", label: "Dashboard", icon: LayoutDashboard },
      { href: "/backtest", label: "New Backtest", icon: Play },
      { href: "/results", label: "Results", icon: BarChart3 },
      { href: "/paper", label: "Paper Trading", icon: RadioTower },
    ],
  },
  {
    label: "Analysis",
    items: [
      { href: "/compare", label: "Compare", icon: Columns3 },
      { href: "/correlation", label: "Correlation", icon: GitCompareArrows },
      { href: "/strategies", label: "Strategy Library", icon: Code2 },
    ],
  },
  {
    label: "Data",
    items: [
      { href: "/data", label: "Data Explorer", icon: Database },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const [showShortcuts, setShowShortcuts] = useState(false);
  useKeyboardShortcuts();

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <aside
      className="fixed left-0 top-0 h-screen w-60 flex flex-col z-50"
      style={{
        background: "var(--color-bg-secondary)",
        borderRight: "1px solid var(--color-border)",
        boxShadow: "1px 0 0 rgba(255,255,255,0.02)",
      }}
    >
      {/* Logo */}
      <div
        className="h-14 flex items-center px-5 shrink-0"
        style={{ borderBottom: "1px solid var(--color-border)" }}
      >
        <Link href="/" className="flex items-center gap-2.5 group">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
            style={{
              background:
                "linear-gradient(135deg, rgba(0,212,170,0.22) 0%, rgba(68,136,255,0.14) 100%)",
              border: "1px solid rgba(0,212,170,0.28)",
              boxShadow: "0 0 12px rgba(0,212,170,0.08)",
            }}
          >
            <TrendingUp size={14} className="text-accent-green" />
          </div>
          <div className="flex flex-col leading-none gap-0.5">
            <span className="font-bold text-[13px] text-text-primary tracking-tight">
              Quant<span className="text-accent-green">Lab</span>
            </span>
            <span
              className="section-label"
              style={{ letterSpacing: "0.15em" }}
            >
              Research Platform
            </span>
          </div>
        </Link>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-5 px-2 overflow-y-auto space-y-5">
        {NAV_SECTIONS.map((section) => (
          <div key={section.label}>
            <p className="section-label px-3 mb-2">{section.label}</p>
            <div className="space-y-0.5">
              {section.items.map((item) => {
                const active = isActive(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`relative flex items-center gap-3 px-3 py-2 rounded text-[13px] transition-all duration-150 ${
                      active
                        ? "text-text-primary font-medium"
                        : "text-text-secondary hover:text-text-primary hover:bg-bg-hover"
                    }`}
                    style={
                      active
                        ? {
                            background: "rgba(68,136,255,0.08)",
                            border: "1px solid rgba(68,136,255,0.18)",
                            borderLeft: "2px solid var(--color-accent-blue)",
                          }
                        : { border: "1px solid transparent" }
                    }
                  >
                    <item.icon
                      size={14}
                      className={active ? "text-accent-blue" : ""}
                    />
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div
        className="px-4 py-3 shrink-0 space-y-1.5"
        style={{ borderTop: "1px solid var(--color-border)" }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <span
              className="w-1.5 h-1.5 rounded-full bg-accent-green shrink-0"
              style={{ boxShadow: "0 0 6px rgba(0,212,170,0.6)" }}
            />
            <span className="text-[10px] text-text-muted">
              Event-driven · No lookahead
            </span>
          </div>
          <button
            onClick={() => setShowShortcuts(true)}
            className="text-text-muted hover:text-text-secondary transition-colors"
            title="Keyboard shortcuts"
          >
            <Keyboard size={12} />
          </button>
        </div>
        <p className="text-[10px]" style={{ color: "var(--color-text-muted)", opacity: 0.55 }}>
          QuantLab v1.0 — Local
        </p>
        <p className="text-[10px]" style={{ color: "var(--color-text-muted)", opacity: 0.4 }}>
          Charts by{" "}
          <a
            href="https://www.tradingview.com/"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:opacity-70 transition-opacity underline underline-offset-2"
          >
            TradingView
          </a>
        </p>
      </div>

      {/* Shortcuts modal */}
      {showShortcuts && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center"
          style={{ background: "rgba(0,0,0,0.6)" }}
          onClick={() => setShowShortcuts(false)}
        >
          <div
            className="rounded-lg p-6 w-72"
            style={{
              background: "var(--color-bg-card)",
              border: "1px solid var(--color-border)",
              boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-sm font-semibold text-text-primary">Keyboard Shortcuts</h3>
              <button onClick={() => setShowShortcuts(false)}>
                <X size={14} className="text-text-muted hover:text-text-primary transition-colors" />
              </button>
            </div>
            <div className="space-y-3">
              {SHORTCUTS.map(({ key, label }) => (
                <div key={key} className="flex items-center justify-between">
                  <span className="text-xs text-text-secondary">{label}</span>
                  <kbd
                    className="text-[10px] font-mono px-2 py-0.5 rounded"
                    style={{
                      background: "rgba(255,255,255,0.06)",
                      border: "1px solid var(--color-border)",
                      color: "var(--color-text-primary)",
                    }}
                  >
                    {key}
                  </kbd>
                </div>
              ))}
            </div>
            <p className="text-[10px] text-text-muted mt-4">
              Shortcuts are disabled when typing in input fields.
            </p>
          </div>
        </div>
      )}
    </aside>
  );
}
