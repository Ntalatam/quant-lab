import { expect, test } from "@playwright/test";

import { installAppMocks, waitForAppReady } from "./support/mockApi";

test.describe("Backtest flow", () => {
  test("runs a backtest over the WebSocket progress channel and lands on the tear sheet", async ({
    page,
  }) => {
    await installAppMocks(page, { backtestId: "bt_sma_1" });

    await page.goto("/backtest");
    await waitForAppReady(page);
    await expect(page.getByRole("heading", { name: "New Backtest" })).toBeVisible();

    await page.getByRole("button", { name: /Run Backtest/i }).click();

    await expect(page.getByText(/Simulating/)).toBeVisible();
    await page.waitForURL("**/backtest/bt_sma_1");
    await expect(page.getByRole("heading", { name: /sma_crossover/i })).toBeVisible();
    await expect(page.getByText("Total Return")).toBeVisible();
    await expect(page.getByText("+18.40%", { exact: true }).first()).toBeVisible();
  });

  test("surfaces websocket failures without navigating away from the setup page", async ({
    page,
  }) => {
    await installAppMocks(page, { backtestSocket: "error" });

    await page.goto("/backtest");
    await waitForAppReady(page);
    await page.getByRole("button", { name: /Run Backtest/i }).click();

    await expect(page.getByText("Mock simulation failed")).toBeVisible();
    await expect(page).toHaveURL(/\/backtest$/);
  });
});
