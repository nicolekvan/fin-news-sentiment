import { defineConfig, devices } from "@playwright/test";

// Tests run against the static build in ./out (run `npm run build` first).
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://127.0.0.1:4321",
    trace: "off",
  },
  webServer: {
    command: "python3 -m http.server 4321 --bind 127.0.0.1 --directory out",
    url: "http://127.0.0.1:4321",
    reuseExistingServer: !process.env.CI,
  },
  projects: [
    {
      name: "desktop",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1400, height: 900 } },
      testIgnore: /responsive\.spec\.ts/,
    },
    { name: "mobile", use: { ...devices["Pixel 7"] }, testMatch: /responsive\.spec\.ts/ },
  ],
});
