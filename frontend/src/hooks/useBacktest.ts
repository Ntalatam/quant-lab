"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { BacktestConfig } from "@/lib/types";

export function useBacktestList() {
  return useQuery({
    queryKey: ["backtests"],
    queryFn: () => api.listBacktests(),
  });
}

export function useBacktestResult(id: string | undefined) {
  return useQuery({
    queryKey: ["backtest", id],
    queryFn: () => api.getBacktestResult(id!),
    enabled: !!id,
  });
}

export function useRunBacktest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (config: BacktestConfig) => api.runBacktest(config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["backtests"] });
    },
  });
}

export function useDeleteBacktest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteBacktest(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["backtests"] });
    },
  });
}
