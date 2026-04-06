"use client";

import { useCallback, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useSession } from "@/components/auth/SessionProvider";
import type { BacktestConfig } from "@/lib/types";
import { buildWebSocketUrl } from "@/lib/network";

export type ProgressState =
  | { status: "idle" }
  | { status: "connecting" }
  | {
      status: "running";
      bar: number;
      total: number;
      date: string;
      equity: number;
      pct: number;
    }
  | { status: "complete"; id: string }
  | { status: "error"; message: string };

export function useBacktestProgress() {
  const [progress, setProgress] = useState<ProgressState>({ status: "idle" });
  const wsRef = useRef<WebSocket | null>(null);
  const progressRef = useRef<ProgressState>({ status: "idle" });
  const queryClient = useQueryClient();
  const { accessToken, workspace } = useSession();
  const workspaceId = workspace?.id;

  const updateProgress = useCallback((next: ProgressState) => {
    progressRef.current = next;
    setProgress(next);
  }, []);

  const run = useCallback(
    (config: BacktestConfig): Promise<string> =>
      new Promise((resolve, reject) => {
        if (wsRef.current) {
          wsRef.current.close();
        }

        updateProgress({ status: "connecting" });
        const wsUrl = new URL(buildWebSocketUrl("/api/backtest/ws"));
        if (accessToken) {
          wsUrl.searchParams.set("access_token", accessToken);
        }
        if (workspaceId) {
          wsUrl.searchParams.set("workspace_id", workspaceId);
        }
        const ws = new WebSocket(wsUrl.toString());
        wsRef.current = ws;

        ws.onopen = () => {
          ws.send(JSON.stringify(config));
        };

        ws.onmessage = (event) => {
          const msg = JSON.parse(event.data);

          if (msg.type === "progress") {
            updateProgress({
              status: "running",
              bar: msg.bar,
              total: msg.total,
              date: msg.date,
              equity: msg.equity,
              pct: msg.pct,
            });
          } else if (msg.type === "complete") {
            updateProgress({ status: "complete", id: msg.id });
            queryClient.invalidateQueries({ queryKey: ["backtests"] });
            ws.close();
            resolve(msg.id);
          } else if (msg.type === "error") {
            updateProgress({ status: "error", message: msg.message });
            ws.close();
            reject(new Error(msg.message));
          }
        };

        ws.onerror = () => {
          updateProgress({
            status: "error",
            message: "WebSocket connection failed",
          });
          reject(new Error("WebSocket connection failed"));
        };

        ws.onclose = () => {
          if (wsRef.current === ws) {
            wsRef.current = null;
          }
          if (progressRef.current.status === "running") {
            updateProgress({ status: "error", message: "Connection lost" });
          }
        };
      }),
    [accessToken, queryClient, updateProgress, workspaceId],
  );

  const reset = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    updateProgress({ status: "idle" });
  }, [updateProgress]);

  return { progress, run, reset };
}
