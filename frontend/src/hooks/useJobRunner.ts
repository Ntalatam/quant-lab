"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/lib/api";
import type { ResearchJob } from "@/lib/types";

function isTerminalStatus(status: string) {
  return status === "completed" || status === "failed";
}

export function useJobRunner<T = Record<string, unknown> | null>(
  pollIntervalMs: number = 1000,
) {
  const [job, setJob] = useState<ResearchJob<T> | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearPolling = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    clearPolling();
    setJob(null);
  }, [clearPolling]);

  const run = useCallback(
    async <TResult>(
      start: () => Promise<ResearchJob<T>>,
      extractResult: (nextJob: ResearchJob<T>) => TResult | null | undefined,
    ): Promise<TResult> => {
      clearPolling();
      const initialJob = await start();
      setJob(initialJob);

      const awaitCompletion = (nextJob: ResearchJob<T>): Promise<TResult> =>
        new Promise((resolve, reject) => {
          if (nextJob.status === "completed") {
            const result = extractResult(nextJob);
            if (result === null || result === undefined) {
              reject(new Error("Job completed without a usable result"));
              return;
            }
            resolve(result);
            return;
          }

          if (nextJob.status === "failed") {
            reject(new Error(nextJob.error_message || "Job failed"));
            return;
          }

          const poll = async () => {
            try {
              const latestJob = await api.getResearchJob<T>(nextJob.id);
              setJob(latestJob);
              if (latestJob.status === "completed") {
                const result = extractResult(latestJob);
                if (result === null || result === undefined) {
                  reject(new Error("Job completed without a usable result"));
                  return;
                }
                resolve(result);
                return;
              }

              if (latestJob.status === "failed") {
                reject(new Error(latestJob.error_message || "Job failed"));
                return;
              }

              timeoutRef.current = setTimeout(poll, pollIntervalMs);
            } catch (error) {
              reject(
                error instanceof Error
                  ? error
                  : new Error("Job polling failed"),
              );
            }
          };

          timeoutRef.current = setTimeout(poll, pollIntervalMs);
        });

      return awaitCompletion(initialJob);
    },
    [clearPolling, pollIntervalMs],
  );

  useEffect(() => () => clearPolling(), [clearPolling]);

  return {
    job,
    run,
    reset,
    isRunning: job !== null && !isTerminalStatus(job.status),
  };
}
