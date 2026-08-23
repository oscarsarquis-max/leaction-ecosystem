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
    if (path.endsWith("/ingredients") && request.method === "GET") {
      return json({
        items: [
          {
            id: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
            code: "FAR-1",
            display_name: "Farinha de trigo tipo 1",
            ingredient_type: "simple",
            status: "active",
            row_version: 1,
            current_version: { id: "ffffffff-ffff-ffff-ffff-ffffffffffff", version_number: 1, status: "draft" },
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      });
    }
    if (path.endsWith("/ingredients") && request.method === "POST") {
      return json({
        data: { id: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee", versions: [] },
        row_version: 1,
      });
    }
    if (path.includes("/ingredients/") && path.endsWith("/items") && request.method === "GET") {
      return json({
        data: [
          {
            id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            supplier_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            ingredient_id: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
            supplier_sku: "SKU-1",
            description: "saco 25 kg",
            package_quantity: "25",
            measurement_unit_id: "u1",
            status: "active",
            row_version: 1,
            latest_purchase: { unit_price: "18.40", currency: "BRL", observed_at: "2026-08-23T10:00:00Z" },
          },
        ],
      });
    }
    if (path.includes("/ingredients/") && path.endsWith("/publish") && request.method === "POST") {
      return json({ data: { id: "ffffffff-ffff-ffff-ffff-ffffffffffff", status: "published", row_version: 2 }, row_version: 2 });
    }
    if (path.includes("/ingredients/") && request.method !== "GET") {
      return json({ data: { id: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee", versions: [] }, row_version: 1 });
    }
    if (path.includes("/ingredients/")) {
      return json({
        data: {
          id: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
          code: "FAR-1",
          display_name: "Farinha de trigo tipo 1",
          ingredient_type: "simple",
          status: "active",
          row_version: 1,
          versions: [
            {
              id: "ffffffff-ffff-ffff-ffff-ffffffffffff",
              ingredient_id: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
              version_number: 1,
              status: "draft",
              data_source_id: null,
              notes: null,
              row_version: 1,
              nutrition_basis_unit_id: "u1",
            },
          ],
          identity: { display_name: "Farinha de trigo tipo 1" },
          version: {
            id: "ffffffff-ffff-ffff-ffff-ffffffffffff",
            status: "draft",
            row_version: 1,
            notes: null,
          },
          composition: [
            {
              id: "c1",
              component_version_id: "v-comp",
              component_type: "constituent",
              quantity: "80",
              measurement_unit_id: "u1",
              sequence: 1,
            },
          ],
          nutrients: [
            {
              id: "n-row",
              nutrient_id: "n1",
              value: null,
              value_status: "below_loq",
              limit_of_quantification: "0.1",
              loq_unit_id: "u1",
              method_or_source: "laudo",
            },
          ],
          allergens: [
            {
              id: "a-row",
              allergen_id: "a1",
              presence: "contains",
              data_source_id: null,
              evidence_note: "rótulo",
            },
          ],
          completeness: {
            ready_to_publish: true,
            complete_dossier: false,
            items: [
              {
                code: "fonte_pendente",
                label: "Versão sem fonte técnica associada.",
                blocking: false,
                origin: "ingredient_version.data_source_id",
              },
            ],
          },
        },
        row_version: 1,
      });
    }
    if (path.endsWith("/suppliers")) return json({ data: [] });
    if (path.endsWith("/catalog/units")) return json({ data: [{ id: "u1", code: "g", name: "grama", access: "somente_leitura" }] });
    if (path.endsWith("/catalog/nutrients")) return json({ data: [{ id: "n1", code: "protein", name: "proteína", access: "somente_leitura" }] });
    if (path.endsWith("/catalog/allergens")) return json({ data: [{ id: "a1", code: "gluten", name: "glúten", access: "somente_leitura" }] });
    if (path.endsWith("/catalog/sources")) return json({ data: [] });
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
