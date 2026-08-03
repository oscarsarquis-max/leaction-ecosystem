import { afterEach, describe, expect, it, vi } from "vitest";
import { getConfig, resetConfigCache } from "@/config/env";

describe("env config", () => {
  afterEach(() => {
    resetConfigCache();
    vi.unstubAllEnvs();
  });

  it("blocks AUTH_MODE=dev when ENVIRONMENT=prod", () => {
    vi.stubEnv("VITE_ENVIRONMENT", "prod");
    vi.stubEnv("VITE_AUTH_MODE", "dev");
    expect(() => getConfig()).toThrow(/forbidden/i);
  });

  it("allows local + dev", () => {
    vi.stubEnv("VITE_ENVIRONMENT", "local");
    vi.stubEnv("VITE_AUTH_MODE", "dev");
    vi.stubEnv("VITE_DEV_USER_SUB", "u1");
    vi.stubEnv("VITE_DEV_USER_EMAIL", "u1@example.com");
    const cfg = getConfig();
    expect(cfg.authMode).toBe("dev");
    expect(cfg.environment).toBe("local");
  });
});
