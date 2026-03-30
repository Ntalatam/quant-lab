"use client";

import { useStrategies } from "@/hooks/useAnalytics";
import { PageLoading } from "@/components/shared/LoadingSpinner";
import { ErrorMessage } from "@/components/shared/ErrorBoundary";
import { CATEGORY_LABELS } from "@/lib/constants";
import Link from "next/link";

export default function StrategiesPage() {
  const { data: strategies, isLoading, error } = useStrategies();

  if (isLoading) return <PageLoading />;
  if (error) return <ErrorMessage message={error.message} />;

  return (
    <div>
      <h1 className="text-xl font-semibold mb-6">Strategy Library</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {strategies?.map((s) => (
          <div
            key={s.id}
            className="bg-bg-card border border-border rounded p-5 hover:border-text-muted/30 transition-colors"
          >
            <div className="flex items-start justify-between mb-2">
              <h2 className="font-medium text-text-primary">{s.name}</h2>
              <span className="text-[10px] uppercase tracking-wider text-text-muted bg-bg-hover px-2 py-0.5 rounded">
                {CATEGORY_LABELS[s.category] || s.category}
              </span>
            </div>
            <p className="text-xs text-text-secondary mb-4 leading-relaxed">
              {s.description}
            </p>

            <div className="mb-4">
              <h3 className="text-xs text-text-muted mb-2 uppercase tracking-wider">
                Parameters
              </h3>
              <div className="space-y-1">
                {s.params.map((p) => (
                  <div
                    key={p.name}
                    className="flex justify-between text-xs py-0.5"
                  >
                    <span className="text-text-secondary">{p.label}</span>
                    <span className="font-mono text-text-primary tabular-nums">
                      {String(p.default)}
                      {p.min !== undefined && p.max !== undefined && (
                        <span className="text-text-muted ml-1">
                          ({p.min}–{p.max})
                        </span>
                      )}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <Link
              href="/backtest"
              className="text-xs text-accent-blue hover:underline"
            >
              Use this strategy
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
}
