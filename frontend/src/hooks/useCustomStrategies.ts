"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export function useStrategyEditorSpec() {
  return useQuery({
    queryKey: ["strategy-editor-spec"],
    queryFn: () => api.getStrategyEditorSpec(),
    staleTime: 1000 * 60 * 10,
  });
}

export function useCustomStrategies() {
  return useQuery({
    queryKey: ["custom-strategies"],
    queryFn: () => api.listCustomStrategies(),
  });
}

export function useCustomStrategy(strategyId: string | null) {
  return useQuery({
    queryKey: ["custom-strategy", strategyId],
    queryFn: () => api.getCustomStrategy(strategyId!),
    enabled: !!strategyId,
  });
}

export function useCreateCustomStrategy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (code: string) => api.createCustomStrategy(code),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["custom-strategies"] });
      await queryClient.invalidateQueries({ queryKey: ["strategies"] });
    },
  });
}

export function useUpdateCustomStrategy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, code }: { id: string; code: string }) =>
      api.updateCustomStrategy(id, code),
    onSuccess: async (data) => {
      await queryClient.invalidateQueries({ queryKey: ["custom-strategies"] });
      await queryClient.invalidateQueries({ queryKey: ["strategies"] });
      queryClient.setQueryData(["custom-strategy", data.id], data);
    },
  });
}

export function useDeleteCustomStrategy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteCustomStrategy(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["custom-strategies"] });
      await queryClient.invalidateQueries({ queryKey: ["strategies"] });
    },
  });
}
