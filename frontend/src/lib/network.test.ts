import { buildApiUrl, buildWebSocketUrl, getApiBaseUrl } from "./network";

describe("network helpers", () => {
  it("normalizes the configured API base URL", () => {
    expect(getApiBaseUrl("https://example.com/api/")).toBe(
      "https://example.com/api",
    );
    expect(getApiBaseUrl("/api/")).toBe("/api");
  });

  it("builds same-origin API paths for relative deployments", () => {
    expect(buildApiUrl("/demo/seed", "/api")).toBe("/api/demo/seed");
  });

  it("builds secure websocket URLs from absolute API bases", () => {
    expect(
      buildWebSocketUrl("/api/backtest/ws", "https://quantlab.dev/api"),
    ).toBe("wss://quantlab.dev/api/backtest/ws");
  });

  it("builds websocket URLs from relative API bases using the current origin", () => {
    expect(
      buildWebSocketUrl(
        "/api/paper/sessions/paper_1/ws",
        "/api",
        "https://quantlab.dev",
      ),
    ).toBe("wss://quantlab.dev/api/paper/sessions/paper_1/ws");
  });
});
