import { afterEach, describe, expect, it, vi } from "vitest";
import {
  consumeRequestedPath,
  freezeWrite,
  isUnknownWriteOutcome,
  rememberRequestedPath,
  request,
  RETURN_PATH_KEY,
  sanitizeReturnPath,
  sendPending,
  signOut,
  continueToProviderLogout,
} from "./api";
import { canWrite, getSession, setSession, subscribeSession, withCompanyPermissions, type Session } from "./session";
import { clearUnknownWrite, getUnknownWrite } from "./pendingWrites";

const session: Session = {
  token: "operator-demo-token",
  mode: "demo",
  actorId: "actor",
  displayName: "Operador",
  permissions: ["titles:write"],
  companies: [{ id: "c1", tenantId: "t1", name: "Padaria", active: true, demo: true, permissions: ["titles:write"] }],
  companyId: "c1",
};

describe("api and session", () => {
  afterEach(() => {
    setSession(null);
    clearUnknownWrite();
    sessionStorage.removeItem(RETURN_PATH_KEY);
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("notifies subscribers and clears protected session on 401", async () => {
    setSession(session);
    const seen: Array<Session | null> = [];
    const stop = subscribeSession(() => seen.push(getSession()));
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        status: 401,
        ok: false,
        text: async () => JSON.stringify({ message: "expired" }),
      }),
    );
    await expect(request("/api/v1/receivables")).rejects.toMatchObject({ status: 401 });
    expect(getSession()).toBeNull();
    expect(seen.at(-1)).toBeNull();
    stop();
  });

  it("rejects a body that arrived after company or logout change", async () => {
    setSession(session);
    let finish: ((value: { status: number; ok: boolean; text: () => Promise<string> }) => void) | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn(
        () =>
          new Promise((resolve) => {
            finish = resolve;
          }),
      ),
    );
    const pending = request<{ id: string }>("/api/v1/receivables");
    setSession({ ...session, companyId: "c2" });
    finish?.({ status: 200, ok: true, text: async () => JSON.stringify({ id: "stale" }) });
    await expect(pending).rejects.toMatchObject({ code: "STALE" });
  });

  it("freezes key payload and route for an unresolved write", () => {
    setSession(session);
    const first = freezeWrite("/api/v1/receivables?register=true", "POST", { description: "A" });
    const second = freezeWrite("/api/v1/receivables?register=true", "POST", { description: "B" }, first);
    expect(second).toBe(first);
    expect(second.body).toContain("A");
    expect(second.body).not.toContain("B");
    expect(first.companyId).toBe("c1");
    expect(first.actorId).toBe("actor");
  });

  it("classifies transport and invalid-response failures as unknown write outcomes", async () => {
    setSession(session);
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(request("/api/v1/receivables")).rejects.toMatchObject({ code: "UNKNOWN_WRITE", unknown: true });
    expect(isUnknownWriteOutcome({ status: 0, unknown: true, code: "UNKNOWN_WRITE", message: "x" })).toBe(true);
    expect(isUnknownWriteOutcome({ status: 500, unknown: true, message: "x" })).toBe(true);
    expect(isUnknownWriteOutcome({ status: 400, message: "x", fields: { description: "obrigatória" } })).toBe(false);
    expect(isUnknownWriteOutcome({ status: 0, code: "STALE", message: "x" })).toBe(false);
  });

  it("does not resend a frozen write after company or actor change", async () => {
    setSession(session);
    const frozen = freezeWrite("/api/v1/receivables", "POST", { description: "A" });
    setSession({ ...session, companyId: "c2" });
    await expect(sendPending(frozen)).rejects.toMatchObject({ code: "STALE" });
  });

  it("treats unconfirmed logout as failure and keeps retry available", async () => {
    setSession(session);
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/csrf")) {
          return { ok: true, status: 200, json: async () => ({ token: "t", headerName: "X-XSRF-TOKEN" }) };
        }
        return { status: 500, ok: false, text: async () => "{}" };
      }),
    );
    await expect(signOut()).resolves.toMatchObject({ confirmed: false });
    expect(getSession()).not.toBeNull();
  });

  it("confirms logout only after 204", async () => {
    setSession(session);
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/csrf")) {
          return { ok: true, status: 200, json: async () => ({ token: "t", headerName: "X-XSRF-TOKEN" }) };
        }
        return { status: 204, ok: true, text: async () => "", json: async () => ({}) };
      }),
    );
    await expect(signOut()).resolves.toEqual({ confirmed: true });
    expect(getSession()).toBeNull();
  });

  it("does not treat a followed 200 HTML response as confirmed logout", async () => {
    setSession(session);
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/csrf")) {
          return { ok: true, status: 200, json: async () => ({ token: "t", headerName: "X-XSRF-TOKEN" }) };
        }
        return { status: 200, ok: true, text: async () => "<html></html>", json: async () => ({}) };
      }),
    );
    await expect(signOut()).resolves.toMatchObject({ confirmed: false });
    expect(getSession()).not.toBeNull();
  });

  it("refuses logout when CSRF is invalid and keeps a valid session", async () => {
    setSession(session);
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/csrf")) {
          return { ok: true, status: 200, json: async () => ({ token: "t", headerName: "X-XSRF-TOKEN" }) };
        }
        return { status: 403, ok: false, text: async () => "{}", json: async () => ({}) };
      }),
    );
    await expect(signOut()).resolves.toMatchObject({ confirmed: false });
    expect(getSession()).not.toBeNull();
  });

  it("continues provider logout through the backend route and drops return path", () => {
    sessionStorage.setItem(RETURN_PATH_KEY, "/receivables");
    const assign = vi.fn();
    const previous = window.location;
    Object.defineProperty(window, "location", {
      configurable: true,
      value: { pathname: "/", search: "", assign, href: "http://localhost/" },
    });
    continueToProviderLogout();
    expect(assign).toHaveBeenCalledWith("/access/cognito-logout");
    expect(sessionStorage.getItem(RETURN_PATH_KEY)).toBeNull();
    Object.defineProperty(window, "location", { configurable: true, value: previous });
  });

  it("confirms logout after 401 only when the session endpoint is also 401", async () => {
    setSession(session);
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/csrf")) {
          return { ok: true, status: 200, json: async () => ({ token: "t", headerName: "X-XSRF-TOKEN" }) };
        }
        if (url.includes("/access/me")) {
          return { status: 401, ok: false, text: async () => "{}", json: async () => ({}) };
        }
        return { status: 401, ok: false, text: async () => "{}", json: async () => ({}) };
      }),
    );
    await expect(signOut()).resolves.toEqual({ confirmed: true });
    expect(getSession()).toBeNull();
  });

  it("does not confirm logout when POST /logout is 401 but /access/me still answers", async () => {
    setSession(session);
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/csrf")) {
          return { ok: true, status: 200, json: async () => ({ token: "t", headerName: "X-XSRF-TOKEN" }) };
        }
        if (url.includes("/access/me")) {
          return {
            status: 200,
            ok: true,
            json: async () => ({ actorId: "a", displayName: "A", accessState: "READY", permissions: [], authorizedCompanies: [] }),
            text: async () => "{}",
          };
        }
        return { status: 401, ok: false, text: async () => "{}", json: async () => ({}) };
      }),
    );
    await expect(signOut()).resolves.toMatchObject({ confirmed: false });
    expect(getSession()).not.toBeNull();
  });

  it("keeps unknown write uncertainty when a retry receives 401", async () => {
    setSession(session);
    const frozen = { ...freezeWrite("/api/v1/receivables", "POST", { description: "A" }), unknownOutcome: true };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        status: 401,
        ok: false,
        text: async () => JSON.stringify({ message: "expired" }),
      }),
    );
    await expect(sendPending(frozen)).rejects.toMatchObject({ code: "UNKNOWN_WRITE_UNCONFIRMED", unknown: true });
    expect(frozen.key).toBeTruthy();
    expect(getUnknownWrite()?.key).toBe(frozen.key);
  });

  it("keeps only an internal Finance path for return after Cognito", () => {
    expect(sanitizeReturnPath("/pay-receipts/abc-1?q=ped")).toBe("/pay-receipts/abc-1?q=ped");
    expect(sanitizeReturnPath("/receivables")).toBe("/receivables");
    expect(sanitizeReturnPath("/")).toBeNull();
    expect(sanitizeReturnPath("//evil.example/phish")).toBeNull();
    expect(sanitizeReturnPath("https://evil.example/x")).toBeNull();
    expect(sanitizeReturnPath("/oauth2/authorization/actionfinance")).toBeNull();
    expect(sanitizeReturnPath("/?login=failed")).toBeNull();
    expect(sanitizeReturnPath("/payables?logout=1")).toBeNull();
  });

  it("remembers the requested page and rejects an open redirect on restore", () => {
    window.history.replaceState(null, "", "/pay-receipts/rec-1");
    expect(rememberRequestedPath()).toBe("/pay-receipts/rec-1");
    expect(sessionStorage.getItem(RETURN_PATH_KEY)).toBe("/pay-receipts/rec-1");
    expect(consumeRequestedPath()).toBe("/pay-receipts/rec-1");
    expect(sessionStorage.getItem(RETURN_PATH_KEY)).toBeNull();
    sessionStorage.setItem(RETURN_PATH_KEY, "//evil.example");
    expect(consumeRequestedPath()).toBeNull();
  });

  it("switches UI write permission with the selected company", () => {
    const mixed: Session = {
      ...session,
      companies: [
        { id: "c1", tenantId: "t1", name: "A", active: true, demo: true, permissions: ["titles:write"] },
        { id: "c2", tenantId: "t2", name: "B", active: true, demo: false, permissions: ["titles:read"] },
      ],
      companyId: "c1",
      permissions: ["titles:write"],
    };
    setSession(mixed);
    expect(canWrite()).toBe(true);
    setSession(withCompanyPermissions(mixed, "c2"));
    expect(canWrite()).toBe(false);
    expect(getSession()?.permissions).toEqual(["titles:read"]);
  });
});

