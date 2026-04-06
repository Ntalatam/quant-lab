"use client";

import { useCallback, useMemo, useState } from "react";

import { useJobRunner } from "@/hooks/useJobRunner";
import { api } from "@/lib/api";
import type { BacktestConfig } from "@/lib/types";

export type ProgressState =
  | { status: "idle" }
  | { status: "queued"; jobId: string; message: string }
  | {
      status: "running";
      jobId: string;
      bar: number;
      total: number;
      date: string;
      equity: number;
      pct: number;
    }
  | { status: "complete"; jobId: string; id: string }
  | { status: "error"; message: string };

function toProgressState(
  job: ReturnType<typeof useJobRunner>["job"],
): ProgressState {
  if (!job) {
    return { status: "idle" };
  }

  if (job.status === "queued") {
    return {
      status: "queued",
      jobId: job.id,
      message: job.progress_message || "Queued for worker pickup.",
    };
  }

  if (job.status === "running") {
    return {
      status: "running",
      jobId: job.id,
      bar: job.progress_current,
      total: job.progress_total || 1,
      date: job.progress_date || "—",
      equity: job.progress_equity || 0,
      pct: job.progress_pct || 0,
    };
  }

  if (job.status === "completed" && job.result_backtest_run_id) {
    return {
      status: "complete",
      jobId: job.id,
      id: job.result_backtest_run_id,
    };
  }

  if (job.status === "failed") {
    return {
      status: "error",
      message: job.error_message || job.progress_message || "Backtest failed",
    };
  }

  return { status: "idle" };
}

export function useBacktestProgress() {
  const { job, run: runJob, reset: resetJob } = useJobRunner();
  const [errorState, setErrorState] = useState<ProgressState | null>(null);

  const progress = useMemo(
    () => errorState ?? toProgressState(job),
    [errorState, job],
  );

  const run = useCallback(
    async (config: BacktestConfig): Promise<string> => {
      setErrorState(null);
      try {
        return await runJob(
          () => api.runBacktest(config),
          (nextJob) => nextJob.result_backtest_run_id,
        );
      } catch (error) {
        setErrorState({
          status: "error",
          message:
            error instanceof Error
              ? error.message
              : "Backtest execution failed",
        });
        throw error;
      }
    },
    [runJob],
  );

  const reset = useCallback(() => {
    resetJob();
    setErrorState(null);
  }, [resetJob]);

  return { progress, run, reset };
}
