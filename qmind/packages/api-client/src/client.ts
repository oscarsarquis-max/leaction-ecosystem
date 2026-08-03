/**
 * Hand-written façade over the generated SDK.
 * Files under ./generated are AUTO-GENERATED — do not edit.
 */

import { createClient, createConfig, type Client } from "./generated/client/index.js";
import * as sdk from "./generated/sdk.gen.js";
import { isErrorBody, QmindApiError, type ErrorBody } from "./errors.js";

export type TokenProvider = () => string | null | Promise<string | null>;
export type OrganizationIdProvider = () => string | null | Promise<string | null>;

export type QmindClientOptions = {
  /** API origin, e.g. https://api.example.com or http://localhost:8008 */
  baseUrl: string;
  /** Cognito access token (Bearer). Return null to omit (public probes). */
  getAccessToken?: TokenProvider;
  /** Active organization UUID for X-Organization-Id. */
  getOrganizationId?: OrganizationIdProvider;
  /** Optional fetch override (tests). */
  fetch?: typeof fetch;
  /** Local AUTH_MODE=dev only — never ship to production builds. */
  devAuth?: { sub: string; email: string };
};

type Sdk = typeof sdk;
type SdkFn = (...args: never[]) => unknown;

export type QmindClient = {
  /** Low-level hey-api client. */
  raw: Client;
  /**
   * Generated operation helpers (stable operationIds).
   * Each call is bound to this client instance (tenant + token).
   */
  api: Sdk;
  /** Bump after organization switch so apps can drop tenant-scoped caches. */
  invalidateTenant: () => void;
  /** Monotonic epoch increased by invalidateTenant(). */
  getTenantEpoch: () => number;
};

function toApiError(status: number, error: unknown): QmindApiError {
  if (isErrorBody(error)) {
    return new QmindApiError(status, error);
  }
  const fallback: ErrorBody = {
    code: "http_error",
    message: "Request failed",
    correlation_id: "",
  };
  return new QmindApiError(status, fallback);
}

/**
 * Create a configured QMind API client.
 *
 * - Authorization: Bearer &lt;token&gt; (or X-Dev-* in local)
 * - X-Organization-Id from getOrganizationId
 * - Non-2xx → QmindApiError (ErrorBody)
 * - After switching organization, call invalidateTenant()
 */
export function createQmindClient(options: QmindClientOptions): QmindClient {
  let tenantEpoch = 0;

  const raw = createClient(
    createConfig({
      baseUrl: options.baseUrl.replace(/\/$/, ""),
      fetch: options.fetch ?? globalThis.fetch.bind(globalThis),
      throwOnError: true,
    }),
  );

  raw.interceptors.request.use(async (request: Request) => {
    const headers = new Headers(request.headers);

    if (options.devAuth) {
      headers.set("X-Dev-User-Sub", options.devAuth.sub);
      headers.set("X-Dev-User-Email", options.devAuth.email);
    } else if (options.getAccessToken) {
      const token = await options.getAccessToken();
      if (token) headers.set("Authorization", `Bearer ${token}`);
    }

    if (options.getOrganizationId) {
      const orgId = await options.getOrganizationId();
      if (orgId) headers.set("X-Organization-Id", orgId);
    }

    headers.set("X-QMind-Tenant-Epoch", String(tenantEpoch));
    return new Request(request, { headers });
  });

  raw.interceptors.error.use((error: unknown, response: Response) => {
    throw toApiError(response.status, error);
  });

  const api = new Proxy(sdk, {
    get(target, prop, receiver) {
      const value = Reflect.get(target, prop, receiver);
      if (typeof value !== "function") return value;
      const fn = value as SdkFn;
      return (callOptions: Record<string, unknown> = {}) =>
        fn({ ...callOptions, client: raw } as never);
    },
  }) as Sdk;

  return {
    raw,
    api,
    invalidateTenant: () => {
      tenantEpoch += 1;
    },
    getTenantEpoch: () => tenantEpoch,
  };
}

export { QmindApiError };
