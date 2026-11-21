import { expect, test } from "@playwright/test";

for (const route of ["/", "/news/", "/screener/", "/performance/"]) {
  test(`no horizontal page scroll on a phone: ${route}`, async ({ page }) => {
    await page.goto(route);
    await page.waitForLoadState("networkidle");
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - window.innerWidth,
    );
    expect(overflow).toBeLessThanOrEqual(0);
    await expect(page.getByRole("navigation", { name: "Main" })).toBeVisible();
  });
}
