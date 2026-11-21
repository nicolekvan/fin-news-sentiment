import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import path from "node:path";

// Read the snapshot under test so assertions work for both demo and real data.
const DATA = path.join(__dirname, "..", "public", "data");
const json = <T,>(f: string): T => JSON.parse(readFileSync(path.join(DATA, f), "utf8")) as T;
const meta = json<{ has_demo_prices: boolean; has_demo_news: boolean; demo_mode: boolean }>("meta.json");
const companies = json<{ ticker: string; is_benchmark: boolean }[]>("companies.json");
const isDemo = meta.demo_mode || meta.has_demo_prices || meta.has_demo_news;

function collectErrors(page: Page) {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  return errors;
}

test("overview shows counts, heatmap, disclaimer and data labels", async ({ page }) => {
  const errors = collectErrors(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Market Overview" })).toBeVisible();
  const stocks = companies.filter((c) => !c.is_benchmark);
  let total = 0;
  for (const l of ["bullish", "bearish", "neutral", "insufficient_evidence"]) {
    total += Number(await page.getByTestId(`count-${l}`).locator(".num").innerText());
  }
  expect(total).toBe(stocks.length);
  await expect(page.getByRole("list", { name: "Company sentiment heatmap" }).getByRole("listitem")).toHaveCount(stocks.length);
  await expect(page.getByTestId("disclaimer")).toContainText("not investment advice");
  await expect(page.getByTestId("snapshot-badge")).toContainText("Historical snapshot");
  if (isDemo) await expect(page.getByTestId("demo-badge")).toBeVisible();
  else await expect(page.getByTestId("demo-badge")).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("heatmap tile navigates to the company page", async ({ page }) => {
  await page.goto("/");
  const first = page.getByRole("list", { name: "Company sentiment heatmap" }).getByRole("link").first();
  await first.click();
  await expect(page).toHaveURL(/\/company\/[A-Z.]+\/$/);
  await expect(page.getByTestId("price-chart").locator("canvas").first()).toBeVisible();
});

test("company page: chart, indicator toggles, sourced news", async ({ page }) => {
  const errors = collectErrors(page);
  const ticker = companies.find((c) => !c.is_benchmark)!.ticker;
  await page.goto(`/company/${ticker}/`);
  const chart = page.getByTestId("price-chart");
  await expect(chart.locator("canvas").first()).toBeVisible();
  const before = (await chart.boundingBox())!.height;
  await page.getByRole("button", { name: "MACD 12/26/9" }).click();
  await expect(page.getByRole("button", { name: "MACD 12/26/9" })).toHaveAttribute("aria-pressed", "true");
  await expect.poll(async () => (await chart.boundingBox())!.height).toBeGreaterThan(before);

  const card = page.getByTestId("news-card").first();
  await expect(card).toBeVisible();
  const link = card.getByRole("link", { name: /opens original article/ });
  await expect(link).toHaveAttribute("target", "_blank");
  await expect(link).toHaveAttribute("rel", /noopener/);
  await expect(card.locator("blockquote")).not.toBeEmpty();
  expect(errors).toEqual([]);
});

test("news feed: filters, search, empty state", async ({ page }) => {
  await page.goto("/news/");
  await expect(page.getByTestId("news-card").first()).toBeVisible();
  await page.getByLabel("Sentiment").selectOption("bearish");
  const badges = page.getByTestId("news-card").locator("span[title='Bearish']");
  await expect(badges.first()).toBeVisible();
  const cards = await page.getByTestId("news-card").count();
  expect(await badges.count()).toBe(cards);
  await page.getByLabel("Search headlines").fill("zzzz-no-such-headline");
  await expect(page.getByTestId("news-empty")).toBeVisible();
  await page.getByRole("button", { name: "Clear filters" }).click();
  await expect(page.getByTestId("news-card").first()).toBeVisible();
});

test("news feed: ticker from URL and error state", async ({ page }) => {
  const ticker = companies.find((c) => !c.is_benchmark)!.ticker;
  await page.goto(`/news/?ticker=${ticker}`);
  await expect(page.getByLabel("Company")).toHaveValue(ticker);

  await page.route("**/data/news.json", (r) => r.abort());
  await page.goto("/news/");
  await expect(page.getByRole("alert").filter({ hasText: "Could not load" })).toBeVisible();
});

test("screener lists every company and sorts", async ({ page }) => {
  await page.goto("/screener/");
  const rows = page.getByTestId("screener-table").locator("tbody tr");
  await expect(rows).toHaveCount(companies.length);
  await page.getByRole("button", { name: "1D", exact: true }).click();
  await expect(page.getByRole("columnheader", { name: "1D" })).toHaveAttribute("aria-sort", /descending|ascending/);
  await page.getByLabel("Filter companies").fill(companies[0]!.ticker);
  await expect(rows.first()).toContainText(companies[0]!.ticker);
});

test("model performance shows only measured numbers", async ({ page }) => {
  const perf = json<{ classification: unknown; forward_returns: unknown } | null>("performance.json");
  await page.goto("/performance/");
  if (perf?.classification) await expect(page.getByTestId("classification-section")).toBeVisible();
  else await expect(page.getByTestId("performance-empty")).toContainText("labelling in progress");
  if (perf?.forward_returns) {
    await expect(page.getByTestId("returns-section")).toContainText("historical association");
  }
});

test("theme toggle switches to light and back", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Switch to light theme" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.getByRole("button", { name: "Switch to dark theme" }).click();
  await expect(page.locator("html")).not.toHaveAttribute("data-theme", "light");
});
