import type { Page, Route } from "@playwright/test";
import { expect } from "@playwright/test";

import {
  backtestSummaries,
  buildBacktestResult,
  buildPaperSessionDetail,
  comparisonResult,
  paperSessionSummaries,
  portfolioBlendResult,
  strategies,
} from "../fixtures/mockData";

const DEFAULT_ORIGIN = "http://127.0.0.1:3100";
const MOCK_ACCESS_TOKEN = "playwright-access-token";

const mockUser = {
  id: "user_e2e",
  email: "playwright@quantlab.dev",
  display_name: "Playwright User",
  created_at: "2026-04-05T12:00:00Z",
};

const mockWorkspace = {
  id: "ws_e2e",
  name: "Playwright Workspace",
  is_personal: true,
  role: "owner",
};

function corsHeaders(route: Route) {
  const requestHeaders = route.request().headers();
  const requestedHeaders =
    requestHeaders["access-control-request-headers"] ??
    requestHeaders["Access-Control-Request-Headers"];
  const origin = requestHeaders.origin ?? requestHeaders.Origin ?? DEFAULT_ORIGIN;

  return {
    "access-control-allow-origin": origin,
    "access-control-allow-credentials": "true",
    "access-control-allow-methods": "GET,POST,PATCH,DELETE,OPTIONS",
    "access-control-allow-headers":
      requestedHeaders || "Content-Type, Accept, Authorization",
    vary: "Origin",
  };
}

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({
    status,
    contentType: "application/json",
    headers: corsHeaders(route),
    body: JSON.stringify(body),
  });
}

export async function waitForAppReady(page: Page) {
  await expect(page.locator("html[data-app-hydrated='true']")).toHaveCount(1);
}

export async function installAppMocks(
  page: Page,
  options?: {
    backtestSocket?: "success" | "error";
    backtestId?: string;
    paperSessionId?: string;
  }
) {
  const backtestSocket = options?.backtestSocket ?? "success";
  const backtestId = options?.backtestId ?? "bt_sma_1";
  const paperSession = buildPaperSessionDetail({
    id: options?.paperSessionId ?? "paper_live_1",
  });

  await page.addInitScript(
    ({ behavior, resolvedBacktestId, snapshot, accessToken }) => {
      window.localStorage.setItem("quantlab.access_token", accessToken);
      const RealWebSocket = window.WebSocket;

      class MockWebSocket extends EventTarget {
        static CONNECTING = 0;
        static OPEN = 1;
        static CLOSING = 2;
        static CLOSED = 3;

        url: string;
        readyState = MockWebSocket.CONNECTING;
        protocol = "";
        extensions = "";
        bufferedAmount = 0;
        binaryType: BinaryType = "blob";
        onopen: ((event: Event) => void) | null = null;
        onclose: ((event: CloseEvent) => void) | null = null;
        onerror: ((event: Event) => void) | null = null;
        onmessage: ((event: MessageEvent) => void) | null = null;
        private realSocket?: WebSocket;

        constructor(url: string | URL, protocols?: string | string[]) {
          super();
          this.url = String(url);

          const isBacktestSocket = this.url.includes("/api/backtest/ws");
          const isPaperSocket =
            this.url.includes("/api/paper/sessions/") &&
            /\/ws(?:\?|$)/.test(this.url);

          if (!isBacktestSocket && !isPaperSocket) {
            this.realSocket = new RealWebSocket(url, protocols);
            this.realSocket.addEventListener("open", (event) => {
              this.readyState = MockWebSocket.OPEN;
              this.emit("open", event);
            });
            this.realSocket.addEventListener("close", (event) => {
              this.readyState = MockWebSocket.CLOSED;
              this.emit("close", event);
            });
            this.realSocket.addEventListener("error", (event) => {
              this.emit("error", event);
            });
            this.realSocket.addEventListener("message", (event) => {
              this.emit("message", event);
            });
            return;
          }

          setTimeout(() => {
            this.readyState = MockWebSocket.OPEN;
            this.emit("open", new Event("open"));
            if (isPaperSocket) {
              this.emit(
                "message",
                new MessageEvent("message", {
                  data: JSON.stringify({
                    type: "snapshot",
                    session: snapshot,
                  }),
                })
              );
            }
          }, 0);
        }

        send(data: string | ArrayBufferLike | Blob | ArrayBufferView) {
          if (this.realSocket) {
            this.realSocket.send(data);
            return;
          }

          if (!this.url.includes("/api/backtest/ws")) {
            return;
          }

          if (behavior === "error") {
            setTimeout(() => {
              this.emit(
                "message",
                new MessageEvent("message", {
                  data: JSON.stringify({
                    type: "error",
                    message: "Mock simulation failed",
                  }),
                })
              );
            }, 150);
            return;
          }

          setTimeout(() => {
            this.emit(
              "message",
              new MessageEvent("message", {
                data: JSON.stringify({
                  type: "progress",
                  bar: 25,
                  total: 100,
                  date: "2024-02-01",
                  equity: 103250,
                  pct: 0.25,
                  }),
                })
              );
          }, 150);

          setTimeout(() => {
            this.emit(
              "message",
              new MessageEvent("message", {
                data: JSON.stringify({
                  type: "progress",
                  bar: 100,
                  total: 100,
                  date: "2024-05-01",
                  equity: 118400,
                  pct: 1,
                  }),
                })
              );
          }, 400);

          setTimeout(() => {
            this.emit(
              "message",
              new MessageEvent("message", {
                data: JSON.stringify({
                  type: "complete",
                  id: resolvedBacktestId,
                }),
              })
            );
            this.close();
          }, 750);
        }

        close(code?: number, reason?: string) {
          if (this.realSocket) {
            this.realSocket.close(code, reason);
            return;
          }
          this.readyState = MockWebSocket.CLOSED;
          this.emit(
            "close",
            new CloseEvent("close", {
              code: code ?? 1000,
              reason: reason ?? "",
              wasClean: true,
            })
          );
        }

        private emit(type: "open" | "close" | "error" | "message", event: Event) {
          this.dispatchEvent(event);
          const handler =
            type === "open"
              ? this.onopen
              : type === "close"
              ? this.onclose
              : type === "error"
              ? this.onerror
              : this.onmessage;
          handler?.(event as never);
        }
      }

      Object.defineProperty(window, "WebSocket", {
        configurable: true,
        writable: true,
        value: MockWebSocket,
      });
    },
    {
      behavior: backtestSocket,
      resolvedBacktestId: backtestId,
      snapshot: paperSession,
      accessToken: MOCK_ACCESS_TOKEN,
    }
  );

  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const method = request.method();

    if (!path.startsWith("/api/")) {
      await route.fallback();
      return;
    }

    if (method === "OPTIONS") {
      await route.fulfill({
        status: 204,
        headers: corsHeaders(route),
      });
      return;
    }

    if (method === "GET" && path === "/api/auth/me") {
      const authorization = request.headers().authorization ?? "";
      if (authorization !== `Bearer ${MOCK_ACCESS_TOKEN}`) {
        await json(route, { detail: "Not authenticated" }, 401);
        return;
      }
      await json(route, {
        user: mockUser,
        workspace: mockWorkspace,
      });
      return;
    }

    if (
      method === "POST" &&
      (path === "/api/auth/refresh" ||
        path === "/api/auth/login" ||
        path === "/api/auth/register")
    ) {
      await json(route, {
        access_token: MOCK_ACCESS_TOKEN,
        token_type: "bearer",
        expires_at: "2026-04-05T13:00:00Z",
        user: mockUser,
        workspace: mockWorkspace,
      });
      return;
    }

    if (method === "POST" && path === "/api/auth/logout") {
      await json(route, { status: "ok" });
      return;
    }

    if (method === "GET" && path === "/api/strategies/list") {
      await json(route, strategies);
      return;
    }

    if (method === "GET" && path === "/api/backtest/list") {
      await json(route, {
        items: backtestSummaries,
        total: backtestSummaries.length,
      });
      return;
    }

    if (method === "GET" && path.startsWith("/api/backtest/")) {
      const id = path.split("/").pop() ?? backtestId;
      await json(route, buildBacktestResult(id));
      return;
    }

    if (method === "POST" && path === "/api/analytics/compare") {
      await json(route, comparisonResult);
      return;
    }

    if (method === "POST" && path === "/api/analytics/portfolio-blend") {
      await json(route, portfolioBlendResult);
      return;
    }

    if (method === "GET" && path === "/api/paper/sessions") {
      await json(route, paperSessionSummaries);
      return;
    }

    if (method === "POST" && path === "/api/paper/sessions") {
      const payload = JSON.parse(request.postData() ?? "{}");
      await json(
        route,
        buildPaperSessionDetail({
          id: paperSession.id,
          name: payload.name ?? paperSession.name,
          strategy_id: payload.strategy_id ?? paperSession.strategy_id,
          tickers: payload.tickers ?? paperSession.tickers,
        })
      );
      return;
    }

    if (method === "GET" && path === `/api/paper/sessions/${paperSession.id}`) {
      await json(route, paperSession);
      return;
    }

    if (
      method === "POST" &&
      path.startsWith(`/api/paper/sessions/${paperSession.id}/`)
    ) {
      await json(route, paperSession);
      return;
    }

    await json(
      route,
      { detail: `No mock registered for ${method} ${path}` },
      500
    );
  });
}
