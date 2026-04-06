import type { ReactElement, ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderOptions } from "@testing-library/react";

import { SessionProvider } from "@/components/auth/SessionProvider";

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

function TestProviders({ children }: { children: ReactNode }) {
  const queryClient = createTestQueryClient();
  return (
    <QueryClientProvider client={queryClient}>
      <SessionProvider
        bootstrap={false}
        initialSession={{
          accessToken: "test-access-token",
          user: {
            id: "user_test",
            email: "tester@example.com",
            display_name: "Test User",
            created_at: "2026-04-05T00:00:00Z",
          },
          workspace: {
            id: "ws_test",
            name: "Test User Personal",
            is_personal: true,
            role: "owner",
          },
        }}
      >
        {children}
      </SessionProvider>
    </QueryClientProvider>
  );
}

export function renderWithProviders(
  ui: ReactElement,
  options?: Omit<RenderOptions, "wrapper">,
) {
  return render(ui, {
    wrapper: TestProviders,
    ...options,
  });
}
