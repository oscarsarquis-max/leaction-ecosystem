import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import {
  bindAuthBridge,
  getQmindClient,
  resetQmindClient,
  StaleTenantResponseError,
  withTenantGeneration,
} from "@/api/qmindApi";
import { abortAllInFlight, createTrackedAbortController } from "@/api/abortRegistry";
import { resetConfigCache } from "@/config/env";
import {
  bumpRequestGeneration,
  resetTenantContext,
  setActiveOrganizationId,
} from "@/api/tenantContext";

describe("withTenantGeneration", () => {
  it("rejects late responses after generation bump", async () => {
    resetQmindClient();
    resetTenantContext();
    setActiveOrganizationId("org-a");
    bindAuthBridge({ getAccessToken: () => "t" });

    const slow = withTenantGeneration(
      () =>
        new Promise<string>((resolve) => {
          setTimeout(() => resolve("from-a"), 20);
        }),
    );
    bumpRequestGeneration();
    await expect(slow).rejects.toBeInstanceOf(StaleTenantResponseError);
  });

  it("rejects when concrete organization switches mid-flight", async () => {
    resetQmindClient();
    resetTenantContext();
    setActiveOrganizationId("org-a");
    const slow = withTenantGeneration(
      () =>
        new Promise<string>((resolve) => {
          setTimeout(() => resolve("from-a"), 20);
        }),
    );
    setActiveOrganizationId("org-b");
    await expect(slow).rejects.toBeInstanceOf(StaleTenantResponseError);
  });

  it("allows null→org boot without treating as stale", async () => {
    resetQmindClient();
    resetTenantContext();
    const pending = withTenantGeneration(async () => {
      setActiveOrganizationId("org-a");
      return "ok";
    });
    await expect(pending).resolves.toBe("ok");
  });
});

describe("abort registry wiring", () => {
  beforeEach(() => {
    vi.stubEnv("VITE_ENVIRONMENT", "local");
    vi.stubEnv("VITE_AUTH_MODE", "dev");
    resetConfigCache();
    resetQmindClient();
    resetTenantContext();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("aborts tracked controllers on abortAllInFlight", async () => {
    const controller = createTrackedAbortController();
    expect(controller.signal.aborted).toBe(false);
    abortAllInFlight("tenant_switch");
    expect(controller.signal.aborted).toBe(true);
  });

  it("client fetch uses abort signal that abortAllInFlight cancels", async () => {
    setActiveOrganizationId("11111111-1111-4111-8111-111111111111");
    bindAuthBridge({ getAccessToken: () => "dev" });

    let sawSignal: AbortSignal | undefined;
    let fetchStarted!: () => void;
    const started = new Promise<void>((r) => {
      fetchStarted = r;
    });

    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        sawSignal =
          init?.signal ?? (input instanceof Request ? input.signal : undefined);
        fetchStarted();
        return new Promise((_resolve, reject) => {
          sawSignal?.addEventListener(
            "abort",
            () => reject(new DOMException("Aborted", "AbortError")),
            { once: true },
          );
        });
      }),
    );

    const client = getQmindClient();
    const pending = client.api.listAssessments().catch((e: unknown) => e);
    await started;
    abortAllInFlight("tenant_switch");
    const result = await pending;
    expect(sawSignal?.aborted).toBe(true);
    expect(result).toBeInstanceOf(DOMException);
  });
});
