/**
 * Cliente do satélite de referência SpiderBank (DEMO-001 / DEMO-002).
 */
export function getSpiderBankEntry(ctx, { signal } = {}) {
  const q = new URLSearchParams({ ctx });
  return fetch(`/v1/demo/spiderbank/entry?${q}`, {
    method: "GET",
    signal,
    headers: { Accept: "application/json" },
  }).then(async (res) => {
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const err = new Error(data.detail || data.title || `HTTP ${res.status}`);
      err.status = res.status;
      err.body = data;
      throw err;
    }
    return data;
  });
}

export function understandObjective(
  { contextId, objective, amount, decisionId },
  { signal } = {},
) {
  return fetch("/v1/demo/spiderbank/understand", {
    method: "POST",
    signal,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-Spider-Credential-Ref": "local-demo-console",
    },
    body: JSON.stringify({
      contextId: contextId || undefined,
      objective: objective || undefined,
      amount: amount || undefined,
      decisionId: decisionId || undefined,
    }),
  }).then(async (res) => {
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const err = new Error(data.detail || data.title || `HTTP ${res.status}`);
      err.status = res.status;
      err.body = data;
      throw err;
    }
    return data;
  });
}

export function opaqueContextIdFromLocation(search = window.location.search) {
  const ctx = new URLSearchParams(search).get("ctx");
  if (!ctx || !ctx.startsWith("ctx-")) {
    return null;
  }
  return ctx;
}

const CONTEXTUAL_QUERY = /(intent|campaign|cropFailure|workingCapital|articleId|contextId|purpose|amount|produto|rota|capability)/i;

export function isGenericGatewayHref(href) {
  if (!href) return false;
  try {
    const url = new URL(href, "http://127.0.0.1:8080");
    if (url.pathname !== "/go") return false;
    if (url.search && CONTEXTUAL_QUERY.test(url.search)) return false;
    return !url.search || url.search === "";
  } catch {
    return false;
  }
}
