import { waitFor } from "@testing-library/react";

import { SessionProvider, useSession } from "@/components/auth/SessionProvider";
import { AUTH_TOKEN_STORAGE_KEY, api } from "@/lib/api";
import { renderWithProviders } from "@/test/test-utils";

function SessionProbe() {
  const { status, user, workspace } = useSession();
  return (
    <div>
      <span data-testid="status">{status}</span>
      <span data-testid="email">{user?.email ?? "none"}</span>
      <span data-testid="workspace">{workspace?.name ?? "none"}</span>
    </div>
  );
}

describe("SessionProvider", () => {
  beforeEach(() => {
    api.setAccessToken(null);
    window.localStorage.clear();
    vi.restoreAllMocks();
  });

  it("bootstraps with refresh rotation when the stored access token is stale", async () => {
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, "expired-token");

    const fetchMock = vi
      .spyOn(global, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "Authentication required" }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            access_token: "fresh-token",
            token_type: "bearer",
            expires_at: "2026-04-05T12:00:00Z",
            user: {
              id: "user_1",
              email: "analyst@example.com",
              display_name: "Analyst",
              created_at: "2026-04-05T00:00:00Z",
            },
            workspace: {
              id: "ws_1",
              name: "Analyst Personal",
              is_personal: true,
              role: "owner",
            },
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            user: {
              id: "user_1",
              email: "analyst@example.com",
              display_name: "Analyst",
              created_at: "2026-04-05T00:00:00Z",
            },
            workspace: {
              id: "ws_1",
              name: "Analyst Personal",
              is_personal: true,
              role: "owner",
            },
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        ),
      );

    const { getByTestId } = renderWithProviders(
      <SessionProvider bootstrap>
        <SessionProbe />
      </SessionProvider>,
    );

    await waitFor(() => {
      expect(getByTestId("status").textContent).toBe("authenticated");
    });

    expect(getByTestId("email").textContent).toBe("analyst@example.com");
    expect(getByTestId("workspace").textContent).toBe("Analyst Personal");
    expect(window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBe(
      "fresh-token",
    );
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });
});
