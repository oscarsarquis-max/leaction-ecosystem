import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.QMIND_E2E_BASE_URL || "http://127.0.0.1:4178";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 180_000,
  expect: { timeout: 20_000 },
  reporter: [["list"], ["json", { outputFile: "e2e-results.json" }]],
  use: {
    ...devices["Desktop Chrome"],
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
});
