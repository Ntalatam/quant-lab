"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useAvailableTickers() {
  return useQuery({
    queryKey: ["tickers"],
    queryFn: () => api.getAvailableTickers(),
  });
}

export function useOHLCV(
  ticker: string,
  startDate: string,
  endDate: string,
  enabled = true
) {
  return useQuery({
    queryKey: ["ohlcv", ticker, startDate, endDate],
    queryFn: () => api.getOHLCV(ticker, startDate, endDate),
    enabled: enabled && !!ticker && !!startDate && !!endDate,
  });
}

export function useLoadTicker() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      ticker,
      startDate,
      endDate,
    }: {
      ticker: string;
      startDate: string;
      endDate: string;
    }) => api.loadTickerData(ticker, startDate, endDate),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tickers"] });
    },
  });
}
