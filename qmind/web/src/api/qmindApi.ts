import {
  createQmindClient,
  type QmindClient,
  QmindApiError,
} from "@qmind/api-client";
import { getConfig } from "@/config/env";
import { createTrackedAbortController } from "@/api/abortRegistry";
import {
  getActiveOrganizationId,
  getRequestGeneration,
} from "@/api/tenantContext";

export { QmindApiError };

export type AuthBridge = {
  getAccessToken: () => string | null;
};

let client: QmindClient | null = null;
let bridge: AuthBridge | null = null;

export function bindAuthBridge(next: AuthBridge): void {
  bridge = next;
}

export function getQmindClient(): QmindClient {
  if (!client) {
    const cfg = getConfig();
    client = createQmindClient({
      baseUrl: cfg.apiBaseUrl || window.location.origin,
      getAccessToken: async () => bridge?.getAccessToken() ?? null,
      getOrganizationId: async () => getActiveOrganizationId(),
      devAuth: cfg.authMode === "dev" ? cfg.devAuth : undefined,
      fetch: (input, init) => {
        const controller = createTrackedAbortController();
        const external =
          init?.signal ?? (input instanceof Request ? input.signal : undefined);
        if (external) {
          if (external.aborted) controller.abort(external.reason);
          else {
            external.addEventListener(
              "abort",
              () => controller.abort(external.reason),
              { once: true },
            );
          }
        }
        if (input instanceof Request) {
          return globalThis.fetch(
            new Request(input, { ...init, signal: controller.signal }),
          );
        }
        return globalThis.fetch(input, { ...init, signal: controller.signal });
      },
    });
  }
  return client;
}

export class StaleTenantResponseError extends Error {
  constructor() {
    super("Stale response from a previous organization context");
    this.name = "StaleTenantResponseError";
  }
}

/**
 * Run an API call tied to the current request generation.
 * If the tenant switches before completion, ignore the result.
 */
export async function withTenantGeneration<T>(fn: () => Promise<T>): Promise<T> {
  const gen = getRequestGeneration();
  const orgId = getActiveOrganizationId();
  const result = await fn();
  if (getRequestGeneration() !== gen) {
    throw new StaleTenantResponseError();
  }
  const nextOrg = getActiveOrganizationId();
  // Ignore only concrete tenant switches (A→B). null→org boot is allowed.
  if (orgId && nextOrg && orgId !== nextOrg) {
    throw new StaleTenantResponseError();
  }
  return result;
}

/** Test helper */
export function resetQmindClient(): void {
  client = null;
  bridge = null;
}
