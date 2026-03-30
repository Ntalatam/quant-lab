"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useStrategies() {
  return useQuery({
    queryKey: ["strategies"],
    queryFn: () => api.getStrategies(),
  });
}

export function useCompareBacktests(ids: string[]) {
  return useQuery({
    queryKey: ["compare", ids],
    queryFn: () => api.compareBacktests(ids),
    enabled: ids.length >= 2,
  });
}

export function useMonteCarlo() {
  return useMutation({
    mutationFn: ({
      backtestId,
      nSimulations,
      nDays,
    }: {
      backtestId: string;
      nSimulations?: number;
      nDays?: number;
    }) => api.runMonteCarlo(backtestId, nSimulations, nDays),
  });
}
