"use client";

import { useCallback, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { BacktestConfig } from "@/lib/types";

const WS_URL =
  (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api")
    .replace(/^http/, "ws")
    .replace(/\/api$/, "") + "/api/backtest/ws";

export type ProgressState =
  | { status: "idle" }
  | { status: "connecting" }
  | { status: "running"; bar: number; total: number; date: string; equity: number; pct: number }
  | { status: "complete"; id: string }
  | { status: "error"; message: string };

export function useBacktestProgress() {
  const [progress, setProgress] = useState<ProgressState>({ status: "idle" });
  const wsRef = useRef<WebSocket | null>(null);
  const queryClient = useQueryClient();

  const run = useCallback(
    (config: BacktestConfig): Promise<string> =>
      new Promise((resolve, reject) => {
        if (wsRef.current) {
          wsRef.current.close();
        }

        setProgress({ status: "connecting" });
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
          ws.send(JSON.stringify(config));
        };

        ws.onmessage = (event) => {
          const msg = JSON.parse(event.data);

          if (msg.type === "progress") {
            setProgress({
              status: "running",
              bar:    msg.bar,
              total:  msg.total,
              date:   msg.date,
              equity: msg.equity,
              pct:    msg.pct,
            });
          } else if (msg.type === "complete") {
            setProgress({ status: "complete", id: msg.id });
            queryClient.invalidateQueries({ queryKey: ["backtests"] });
            ws.close();
            resolve(msg.id);
          } else if (msg.type === "error") {
            setProgress({ status: "error", message: msg.message });
            ws.close();
            reject(new Error(msg.message));
          }
        };

        ws.onerror = () => {
          setProgress({ status: "error", message: "WebSocket connection failed" });
          reject(new Error("WebSocket connection failed"));
        };

        ws.onclose = () => {
          if (progress.status === "running") {
            setProgress({ status: "error", message: "Connection lost" });
          }
        };
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [queryClient]
  );

  const reset = useCallback(() => {
    wsRef.current?.close();
    setProgress({ status: "idle" });
  }, []);

  return { progress, run, reset };
}
