"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
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
  CircleDollarSign,
  GitBranch,
  Menu,
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
      { href: "/options", label: "Options Lab", icon: CircleDollarSign },
      { href: "/lineage", label: "Research Timeline", icon: GitBranch },
      { href: "/strategies", label: "Strategy Library", icon: Code2 },
      { href: "/strategies/custom", label: "Strategy Studio", icon: Code2 },
    ],
  },
  {
    label: "Data",
    items: [{ href: "/data", label: "Data Explorer", icon: Database }],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  useKeyboardShortcuts();

  const closeMobile = useCallback(() => setMobileOpen(false), []);

  // Close on escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMobileOpen(false);
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    if (href === "/strategies") return pathname === "/strategies";
    return pathname === href || pathname.startsWith(`${href}/`);
  };

  const sidebarContent = (
    <>
      <div className="shrink-0 px-4 pb-3 pt-4">
        <div className="panel-glass panel-grid p-4">
          <div className="flex items-start gap-3">
            <Link href="/" className="flex min-w-0 items-center gap-3 group">
              <div
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl"
                style={{
                  background:
                    "linear-gradient(135deg, rgba(40,221,176,0.28) 0%, rgba(107,149,255,0.22) 100%)",
                  border: "1px solid rgba(160,176,206,0.16)",
                  boxShadow: "0 18px 28px rgba(40,221,176,0.1)",
                }}
              >
                <TrendingUp size={16} className="text-accent-green" />
              </div>
              <div className="min-w-0">
                <span className="block text-[15px] font-semibold tracking-tight text-text-primary">
                  Quant<span className="text-accent-green">Lab</span>
                </span>
                <span className="mt-1 block text-[11px] text-text-muted">
                  Quant research workstation
                </span>
              </div>
            </Link>
            <button
              onClick={() => setMobileOpen(false)}
              className="ml-auto rounded-full border border-transparent p-1.5 text-text-muted hover:border-border hover:bg-bg-hover hover:text-text-primary lg:hidden"
            >
              <X size={16} />
            </button>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            <span className="status-pill">
              <span className="h-1.5 w-1.5 rounded-full bg-accent-green shadow-[0_0_10px_rgba(40,221,176,0.8)]" />
              Live paper ready
            </span>
            <span className="status-pill">
              <Activity size={12} className="text-accent-blue" />
              Event-driven
            </span>
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-5 overflow-y-auto px-3 pb-4">
        {NAV_SECTIONS.map((section) => (
          <div key={section.label} className="panel-soft p-2.5">
            <p className="section-label px-2 pb-2">{section.label}</p>
            <div className="space-y-0.5">
              {section.items.map((item) => {
                const active = isActive(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={closeMobile}
                    className={`relative flex items-center gap-3 rounded-2xl px-3 py-2.5 text-[13px] transition-all duration-150 ${
                      active
                        ? "text-text-primary font-medium"
                        : "text-text-secondary hover:text-text-primary"
                    }`}
                    style={
                      active
                        ? {
                            background:
                              "linear-gradient(135deg, rgba(107,149,255,0.18) 0%, rgba(40,221,176,0.12) 100%)",
                            border: "1px solid rgba(107,149,255,0.24)",
                            boxShadow: "0 16px 24px rgba(5,10,24,0.16)",
                          }
                        : {
                            border: "1px solid transparent",
                          }
                    }
                  >
                    <span
                      className="flex h-8 w-8 items-center justify-center rounded-xl"
                      style={{
                        background: active
                          ? "rgba(255,255,255,0.12)"
                          : "rgba(255,255,255,0.03)",
                        border: active
                          ? "1px solid rgba(255,255,255,0.08)"
                          : "1px solid rgba(111,130,166,0.08)",
                      }}
                    >
                      <item.icon
                        size={14}
                        className={active ? "text-text-primary" : ""}
                      />
                    </span>
                    <span className="flex-1">{item.label}</span>
                    {active ? (
                      <span className="h-1.5 w-1.5 rounded-full bg-accent-green shadow-[0_0_10px_rgba(40,221,176,0.7)]" />
                    ) : null}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="shrink-0 px-4 pb-4">
        <div className="panel-soft space-y-3 p-3.5">
          <div className="flex items-center justify-between">
            <div>
              <p className="section-label mb-1">Workspace mode</p>
              <p className="text-xs text-text-primary">Local research lab</p>
            </div>
            <button
              onClick={() => setShowShortcuts(true)}
              className="rounded-full border border-border/60 p-2 text-text-muted hover:bg-bg-hover hover:text-text-primary"
              title="Keyboard shortcuts"
            >
              <Keyboard size={12} />
            </button>
          </div>

          <div className="grid grid-cols-2 gap-2 text-[10px] text-text-muted">
            <div className="rounded-2xl border border-border/60 bg-bg-card/70 px-2.5 py-2">
              <p className="mb-1 text-text-secondary">Execution</p>
              <p className="text-text-primary">Slippage + impact</p>
            </div>
            <div className="rounded-2xl border border-border/60 bg-bg-card/70 px-2.5 py-2">
              <p className="mb-1 text-text-secondary">Analytics</p>
              <p className="text-text-primary">TCA + risk budget</p>
            </div>
          </div>

          <p className="text-[10px] text-text-muted/80">
            Charts by{" "}
            <a
              href="https://www.tradingview.com/"
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2 transition-opacity hover:opacity-70"
            >
              TradingView
            </a>
          </p>
        </div>
      </div>
    </>
  );

  return (
    <>
      {/* Mobile hamburger button */}
      <button
        onClick={() => setMobileOpen(true)}
        className="fixed left-3 top-3 z-50 rounded-2xl p-2.5 lg:hidden"
        style={{
          background: "rgba(12,22,39,0.82)",
          border: "1px solid rgba(160,176,206,0.12)",
          backdropFilter: "blur(18px)",
          boxShadow: "0 18px 28px rgba(2,6,23,0.32)",
        }}
        aria-label="Open navigation"
      >
        <Menu size={18} className="text-text-primary" />
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-[90] lg:hidden"
          style={{
            background: "rgba(3,8,19,0.72)",
            backdropFilter: "blur(8px)",
          }}
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar — always visible on lg+, slide-in drawer on mobile */}
      <aside
        className={`fixed left-0 top-0 z-[95] flex h-screen w-64 flex-col transition-transform duration-200 ease-out lg:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
        style={{
          background:
            "linear-gradient(180deg, rgba(10,20,35,0.96) 0%, rgba(9,16,30,0.96) 100%)",
          borderRight: "1px solid rgba(111,130,166,0.12)",
          boxShadow: mobileOpen
            ? "14px 0 40px rgba(2,6,23,0.45)"
            : "1px 0 0 rgba(255,255,255,0.02)",
        }}
      >
        {sidebarContent}
      </aside>

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
              <h3 className="text-sm font-semibold text-text-primary">
                Keyboard Shortcuts
              </h3>
              <button onClick={() => setShowShortcuts(false)}>
                <X
                  size={14}
                  className="text-text-muted hover:text-text-primary transition-colors"
                />
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
    </>
  );
}
