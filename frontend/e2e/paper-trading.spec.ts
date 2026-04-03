import { expect, test } from "@playwright/test";

import { installAppMocks } from "./support/mockApi";

test.describe("Paper trading flows", () => {
  test("shows existing live paper sessions", async ({ page }) => {
    await installAppMocks(page);

    await page.goto("/paper");
    await expect(page.getByRole("heading", { name: "Paper Trading" })).toBeVisible();
    await expect(page.getByText("SMA Crossover Live Session")).toBeVisible();
    await expect(page.getByText("2.10%")).toBeVisible();
  });

  test("creates a paper session and lands on the live dashboard", async ({ page }) => {
    await installAppMocks(page, { paperSessionId: "paper_live_1" });

    await page.goto("/paper");
    await page.getByRole("button", { name: "Create Live Session" }).click();

    await page.waitForURL("**/paper/paper_live_1");
    await expect(page.getByRole("heading", { name: "SMA Crossover Live Session" })).toBeVisible();
    await expect(page.getByText("Live stream connected")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Open Positions" })).toBeVisible();
  });
});
