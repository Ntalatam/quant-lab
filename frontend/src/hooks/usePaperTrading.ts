"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useSession } from "@/components/auth/SessionProvider";
import { api } from "@/lib/api";
import { buildWebSocketUrl } from "@/lib/network";
import type {
  PaperTradingSessionDetail,
  PaperTradingSessionSummary,
} from "@/lib/types";

function toPaperSessionSummary(
  session: PaperTradingSessionDetail,
): PaperTradingSessionSummary {
  return {
    id: session.id,
    name: session.name,
    status: session.status,
    strategy_id: session.strategy_id,
    tickers: session.tickers,
    bar_interval: session.bar_interval,
    polling_interval_seconds: session.polling_interval_seconds,
    initial_capital: session.initial_capital,
    cash: session.cash,
    market_value: session.market_value,
    total_equity: session.total_equity,
    total_return_pct: session.total_return_pct,
    created_at: session.created_at,
    started_at: session.started_at,
    stopped_at: session.stopped_at,
    last_price_at: session.last_price_at,
    last_heartbeat_at: session.last_heartbeat_at,
    last_error: session.last_error,
  };
}

export function usePaperSessions() {
  return useQuery({
    queryKey: ["paper-sessions"],
    queryFn: () => api.listPaperSessions(),
    refetchInterval: 30_000,
  });
}

export function usePaperSession(sessionId: string | undefined) {
  return useQuery({
    queryKey: ["paper-session", sessionId],
    queryFn: () => api.getPaperSession(sessionId!),
    enabled: !!sessionId,
  });
}

function useInvalidatePaperQueries() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["paper-sessions"] });
    queryClient.invalidateQueries({ queryKey: ["paper-session"] });
  };
}

export function useCreatePaperSession() {
  const invalidate = useInvalidatePaperQueries();
  return useMutation({
    mutationFn: api.createPaperSession.bind(api),
    onSuccess: invalidate,
  });
}

export function useStartPaperSession() {
  const invalidate = useInvalidatePaperQueries();
  return useMutation({
    mutationFn: (sessionId: string) => api.startPaperSession(sessionId),
    onSuccess: invalidate,
  });
}

export function usePausePaperSession() {
  const invalidate = useInvalidatePaperQueries();
  return useMutation({
    mutationFn: (sessionId: string) => api.pausePaperSession(sessionId),
    onSuccess: invalidate,
  });
}

export function useStopPaperSession() {
  const invalidate = useInvalidatePaperQueries();
  return useMutation({
    mutationFn: (sessionId: string) => api.stopPaperSession(sessionId),
    onSuccess: invalidate,
  });
}

export function usePaperSessionStream(
  sessionId: string | undefined,
  initialSession: PaperTradingSessionDetail | undefined,
) {
  const { accessToken, workspace } = useSession();
  const workspaceId = workspace?.id;
  const queryClient = useQueryClient();
  const [session, setSession] = useState<PaperTradingSessionDetail | undefined>(
    initialSession,
  );
  const [connection, setConnection] = useState<
    "idle" | "connecting" | "connected" | "error"
  >(sessionId ? "connecting" : "idle");

  useEffect(() => {
    setSession(initialSession);
  }, [initialSession]);

  useEffect(() => {
    if (!sessionId) {
      setConnection("idle");
      return;
    }

    let disposed = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let reconnectAttempt = 0;
    let ws: WebSocket | null = null;

    const handleSnapshot = (nextSession: PaperTradingSessionDetail) => {
      setSession(nextSession);
      queryClient.setQueryData(["paper-session", sessionId], nextSession);
      queryClient.setQueryData<PaperTradingSessionSummary[] | undefined>(
        ["paper-sessions"],
        (current) => {
          const nextSummary = toPaperSessionSummary(nextSession);
          if (!current) return [nextSummary];
          const existingIndex = current.findIndex(
            (item) => item.id === nextSummary.id,
          );
          if (existingIndex === -1) {
            return [nextSummary, ...current];
          }
          return current.map((item) =>
            item.id === nextSummary.id ? nextSummary : item,
          );
        },
      );
    };

    const connect = () => {
      if (disposed) return;
      setConnection("connecting");
      const wsUrl = new URL(
        buildWebSocketUrl(`/api/paper/sessions/${sessionId}/ws`),
      );
      if (accessToken) {
        wsUrl.searchParams.set("access_token", accessToken);
      }
      if (workspaceId) {
        wsUrl.searchParams.set("workspace_id", workspaceId);
      }
      ws = new WebSocket(wsUrl.toString());

      ws.onopen = () => {
        reconnectAttempt = 0;
        setConnection("connected");
      };
      ws.onerror = () => setConnection("error");
      ws.onclose = () => {
        if (disposed) return;
        reconnectAttempt += 1;
        setConnection("connecting");
        reconnectTimer = setTimeout(
          connect,
          Math.min(10_000, 1_000 * reconnectAttempt),
        );
      };
      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === "snapshot") {
            handleSnapshot(message.session as PaperTradingSessionDetail);
          } else if (message.type === "error") {
            setConnection("error");
          }
        } catch {
          setConnection("error");
        }
      };
    };

    connect();

    return () => {
      disposed = true;
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }
      ws?.close();
    };
  }, [accessToken, queryClient, sessionId, workspaceId]);

  const summary = useMemo<PaperTradingSessionSummary | undefined>(
    () => (session ? toPaperSessionSummary(session) : undefined),
    [session],
  );

  return { session, summary, connection };
}
