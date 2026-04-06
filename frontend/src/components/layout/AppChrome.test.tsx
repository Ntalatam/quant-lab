import { waitFor } from "@testing-library/react";

import { SessionProvider } from "@/components/auth/SessionProvider";
import { AppChrome } from "@/components/layout/AppChrome";
import { renderWithProviders } from "@/test/test-utils";

const replaceMock = vi.fn();

let pathname = "/results";

vi.mock("next/navigation", () => ({
  usePathname: () => pathname,
  useRouter: () => ({
    replace: replaceMock,
  }),
}));

describe("AppChrome", () => {
  beforeEach(() => {
    pathname = "/results";
    replaceMock.mockReset();
    window.history.pushState({}, "", pathname);
  });

  it("redirects unauthenticated users away from protected routes", async () => {
    renderWithProviders(
      <SessionProvider bootstrap={false}>
        <AppChrome>
          <div>Protected content</div>
        </AppChrome>
      </SessionProvider>,
    );

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/login?next=%2Fresults");
    });
  });

  it("redirects authenticated users away from auth pages", async () => {
    pathname = "/login";
    window.history.pushState({}, "", "/login?next=%2Fpaper");

    renderWithProviders(
      <SessionProvider
        bootstrap={false}
        initialSession={{
          accessToken: "token",
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
        }}
      >
        <AppChrome>
          <div>Auth page</div>
        </AppChrome>
      </SessionProvider>,
    );

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/paper");
    });
  });
});
