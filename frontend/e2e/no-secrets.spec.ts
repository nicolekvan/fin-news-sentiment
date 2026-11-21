import { expect, test } from "@playwright/test";
import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";

// The built site must never contain credentials or server-side configuration.
const OUT = path.join(__dirname, "..", "out");
const PATTERNS = [
  /sk-ant-[A-Za-z0-9_-]{8,}/,
  /X-Finnhub-Token/i,
  /apikey\s+[A-Za-z0-9]{8,}/i,
  /(FINNHUB|TWELVE_DATA|ANTHROPIC|ALPHA_VANTAGE|FRED)_API_KEY/,
  /DATABASE_URL/,
  /ADMIN_API_TOKEN/,
  /postgresql(\+psycopg)?:\/\//,
];

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((f) => {
    const p = path.join(dir, f);
    return statSync(p).isDirectory() ? files(p) : [p];
  });
}

test("static build contains no secrets or connection strings", () => {
  const texts = files(OUT).filter((f) => /\.(html|js|json|txt|css)$/.test(f));
  expect(texts.length).toBeGreaterThan(10);
  for (const f of texts) {
    const body = readFileSync(f, "utf8");
    for (const p of PATTERNS) {
      expect(p.test(body), `${path.relative(OUT, f)} matches ${p}`).toBe(false);
    }
  }
});
