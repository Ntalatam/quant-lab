import { expect, test } from "@playwright/test";

import { installAppMocks, waitForAppReady } from "./support/mockApi";

test.describe("Results and compare flows", () => {
  test("opens a saved result from the results table", async ({ page }) => {
    await installAppMocks(page);

    await page.goto("/results");
    await waitForAppReady(page);
    await expect(page.getByRole("heading", { name: "Backtest Results" })).toBeVisible();

    await page.getByRole("link", { name: "sma_crossover" }).click();

    await page.waitForURL("**/backtest/bt_sma_1");
    await expect(page.getByText(/AAPL, MSFT/)).toBeVisible();
    await expect(page.getByText("Sharpe Ratio")).toBeVisible();
  });

  test("loads comparison analytics after selecting two runs", async ({ page }) => {
    await installAppMocks(page);

    await page.goto("/compare");
    await waitForAppReady(page);
    await page.getByLabel("Select sma_crossover").check();
    await page.getByLabel("Select market_neutral_momentum").check();

    await expect(
      page.getByRole("heading", { name: "Normalized Equity Curves" })
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Return Correlation Matrix" })
    ).toBeVisible();
    await expect(page.getByRole("cell", { name: "0.41" }).first()).toBeVisible();
  });

  test("builds a blended portfolio from compared runs", async ({ page }) => {
    await installAppMocks(page);

    await page.goto("/compare");
    await waitForAppReady(page);
    await page.getByLabel("Select sma_crossover").check();
    await page.getByLabel("Select market_neutral_momentum").check();

    await page.getByRole("button", { name: "Equal Weight" }).click();

    await expect(page.getByText("Portfolio Return")).toBeVisible();
    await expect(page.getByText("15.20%")).toBeVisible();
    await expect(
      page.getByText("Blended Portfolio", { exact: true }).last()
    ).toBeVisible();
  });
});
