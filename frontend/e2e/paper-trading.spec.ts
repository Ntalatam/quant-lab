import { expect, test } from "@playwright/test";

import { installAppMocks, waitForAppReady } from "./support/mockApi";

test.describe("Paper trading flows", () => {
  test("shows existing live paper sessions", async ({ page }) => {
    await installAppMocks(page);

    await page.goto("/paper");
    await waitForAppReady(page);
    await expect(page.getByRole("heading", { name: "Paper Trading" })).toBeVisible();
    await expect(page.getByText("SMA Crossover Live Session")).toBeVisible();
    await expect(page.getByText("2.10%")).toBeVisible();
    const sessionCard = page.getByRole("link", {
      name: /SMA Crossover Live Session/,
    });
    await expect(sessionCard.getByText("Simulated Paper")).toBeVisible();
  });

  test("creates a paper session and lands on the live dashboard", async ({ page }) => {
    await installAppMocks(page, { paperSessionId: "paper_live_1" });

    await page.goto("/paper");
    await waitForAppReady(page);
    await page.getByRole("button", { name: "Create Simulated Session" }).click();

    await page.waitForURL("**/paper/paper_live_1");
    await expect(page.getByRole("heading", { name: "SMA Crossover Live Session" })).toBeVisible();
    await expect(page.getByText("Live stream connected")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Open Positions" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Recent Orders" })).toBeVisible();
  });

  test("lets users create a broker paper session", async ({ page }) => {
    await installAppMocks(page, { paperSessionId: "paper_live_1" });

    await page.goto("/paper");
    await waitForAppReady(page);
    await page.getByRole("button", { name: /Broker Paper/ }).click();
    await page.getByRole("button", { name: "Create Broker Paper Session" }).click();

    await page.waitForURL("**/paper/paper_live_1");
    await expect(page.getByText("Broker Paper").first()).toBeVisible();
    await expect(page.getByText("Account: Alpaca paper • 5678")).toBeVisible();
  });
});
