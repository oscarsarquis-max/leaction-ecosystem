import {
  ISSUE_ID,
  ORG_A,
  ORDER_ID,
  PLAN_ID,
  boardFixture,
  catalogFixture,
  executionFixture,
  materialsFixture,
  meFixture,
  ordersFixture,
  planDetailFixture,
  plansFixture,
  sheetFixture,
  stepsFixture,
  traceFixture,
  weighingsFixture,
} from "../api/fixtures";

export function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export function installApiMock(overrides: Record<string, (url: URL, request: Request) => Response> = {}) {
  const handler = async (input: RequestInfo | URL, init?: RequestInit) => {
    const request =
      input instanceof Request ? input : new Request(typeof input === "string" ? input : input.toString(), init);
    const url = new URL(request.url);
    const path = url.pathname;
    for (const [prefix, fn] of Object.entries(overrides)) {
      if (path.includes(prefix)) return fn(url, request);
    }
    if (path === "/api/v1/me") return json(meFixture);
    if (path.endsWith("/production/catalog")) return json(catalogFixture);
    if (path.endsWith(`/orders/${ORDER_ID}/execution`)) return json(executionFixture);
    if (path.endsWith("/production/board")) return json({ data: boardFixture });
    if (path.endsWith("/production/plans") && !path.includes(PLAN_ID)) return json(plansFixture);
    if (path.includes(`/plans/${PLAN_ID}`)) return json(planDetailFixture);
    if (path.endsWith("/production/orders") && !path.includes(ORDER_ID)) return json(ordersFixture);
    if (path.endsWith(`/orders/${ORDER_ID}/materials`)) return json(materialsFixture);
    if (path.endsWith(`/orders/${ORDER_ID}/steps`)) return json(stepsFixture);
    if (path.endsWith(`/orders/${ORDER_ID}/weighings`)) return json(weighingsFixture);
    if (path.endsWith(`/orders/${ORDER_ID}/consumptions`)) return json({ data: [] });
    if (path.endsWith(`/orders/${ORDER_ID}/yields`)) return json({ data: [] });
    if (path.endsWith(`/orders/${ORDER_ID}/occurrences`)) {
      return json({ data: [{ id: "o-1", category: "delay", status: "open" }] });
    }
    if (path.endsWith(`/orders/${ORDER_ID}/dependencies`)) return json({ data: [] });
    if (path.endsWith(`/orders/${ORDER_ID}/events`)) return json({ items: [], next_cursor: null });
    if (path.endsWith(`/orders/${ORDER_ID}/sheets/${ISSUE_ID}`)) return json(sheetFixture);
    if (path.endsWith(`/orders/${ORDER_ID}/sheets`)) {
      return json({ data: [{ id: ISSUE_ID, issue_number: 2, payload_sha256: "fff111", purpose: "operational" }] });
    }
    if (path.endsWith(`/orders/${ORDER_ID}/traceability`)) return json(traceFixture);
    if (path.endsWith(`/orders/${ORDER_ID}`)) return json({ data: ordersFixture.items[0], row_version: 4 });
    if (request.method !== "GET" && path.includes("/production")) {
      return json({ data: { id: "cmd-1" } });
    }
    if (path.includes("/organizations/") && path.includes("/production")) {
      return json({ items: [], next_cursor: null });
    }
    return json({ detail: "nao_encontrado" }, 404);
  };
  vi.stubGlobal("fetch", vi.fn(handler));
  return { orgA: ORG_A };
}
