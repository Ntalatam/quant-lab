"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

export function useEconomicIndicatorCatalog() {
  return useQuery({
    queryKey: ["alternative-data", "catalog"],
    queryFn: () => api.getEconomicIndicatorCatalog(),
    staleTime: 1000 * 60 * 60,
  });
}

export function useEconomicIndicators(
  seriesIds: string[],
  startDate: string,
  endDate: string,
) {
  return useQuery({
    queryKey: ["alternative-data", "macro", seriesIds, startDate, endDate],
    queryFn: () => api.getEconomicIndicators(seriesIds, startDate, endDate),
    enabled: seriesIds.length > 0 && !!startDate && !!endDate,
  });
}

export function useEarningsOverview(ticker: string, enabled = true) {
  return useQuery({
    queryKey: ["alternative-data", "earnings", ticker],
    queryFn: () => api.getEarningsOverview(ticker),
    enabled: enabled && !!ticker,
  });
}

export function useNewsSentiment(
  ticker: string,
  lookbackDays: number = 30,
  limit: number = 10,
  enabled = true,
) {
  return useQuery({
    queryKey: ["alternative-data", "sentiment", ticker, lookbackDays, limit],
    queryFn: () => api.getNewsSentiment(ticker, lookbackDays, limit),
    enabled: enabled && !!ticker,
  });
}
