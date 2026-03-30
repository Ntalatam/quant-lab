"use client";

import { use } from "react";
import { useBacktestResult } from "@/hooks/useBacktest";
import { TearSheet } from "@/components/analytics/TearSheet";
import { PageLoading } from "@/components/shared/LoadingSpinner";
import { ErrorMessage } from "@/components/shared/ErrorBoundary";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function BacktestResultPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: result, isLoading, error } = useBacktestResult(id);

  if (isLoading) return <PageLoading />;
  if (error) return <ErrorMessage message={error.message} />;
  if (!result) return <ErrorMessage message="Backtest not found" />;

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <Link
          href="/results"
          className="text-text-muted hover:text-text-primary transition-colors"
        >
          <ArrowLeft size={18} />
        </Link>
        <div>
          <h1 className="text-xl font-semibold">
            {result.config.strategy_id} — {result.config.tickers.join(", ")}
          </h1>
          <p className="text-xs text-text-muted">
            {result.config.start_date} to {result.config.end_date} | ID:{" "}
            {result.id.slice(0, 8)}
          </p>
        </div>
      </div>

      <TearSheet result={result} />
    </div>
  );
}
