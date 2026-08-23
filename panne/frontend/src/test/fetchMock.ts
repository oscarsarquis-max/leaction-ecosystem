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
  PROPOSAL_ID,
  DOSSIER_ID,
  labelingDossierFixture,
  costingPolicyFixture,
  costingCalculationFixture,
  pricingSimulationFixture,
  practicedPriceFixture,
  CALC_ID,
  proposalFixture,
  RECIPE_ID,
  RECIPE_VERSION_ID,
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
    if (path.includes("/recipe-ai/proposals") && path.endsWith("/grounding")) {
      return json({
        data: {
          results: [
            {
              title: "Manual de pão",
              source_kind: "technical",
              locator: "paragraph:1",
              excerpt: "Criar pão com farinha de trigo.",
            },
          ],
        },
      });
    }
    if (path.includes("/recipe-ai/proposals") && path.endsWith("/comparison")) {
      return json({ data: { changes: proposalFixture.changes, items: proposalFixture.items } });
    }
    if (path.includes("/recipe-ai/proposals") && path.endsWith("/changes") && request.method !== "GET") {
      return json({
        data: {
          ...proposalFixture,
          changes: proposalFixture.changes.map((item) => ({ ...item, decision: "accepted" })),
          row_version: 2,
        },
        row_version: 2,
      });
    }
    if (path.includes("/recipe-ai/proposals") && path.endsWith("/review") && request.method !== "GET") {
      return json({ data: { ...proposalFixture, status: "accepted", status_label: "aceito", row_version: 3 }, row_version: 3 });
    }
    if (path.includes("/recipe-ai/proposals") && path.endsWith("/materialize")) {
      return json({
        data: {
          ...proposalFixture,
          status: "materialized",
          status_label: "materializado",
          materialized_formulation_version_id: RECIPE_VERSION_ID,
          materialized: { formulation_id: RECIPE_ID, version_id: RECIPE_VERSION_ID, status: "draft" },
          row_version: 4,
        },
        row_version: 4,
      });
    }
    if (path.endsWith("/recipe-ai/proposals") && request.method === "GET") {
      return json({ items: [proposalFixture], total: 1 });
    }
    if (path.endsWith("/recipe-ai/proposals") && request.method === "POST") {
      return json({ data: proposalFixture, row_version: 1 });
    }
    if (path.includes(`/recipe-ai/proposals/${PROPOSAL_ID}`)) {
      return json({ data: proposalFixture, row_version: 1 });
    }
    if (path.endsWith("/recipes") && request.method === "GET") {
      return json({
        items: [
          {
            id: RECIPE_ID,
            code: "PAO-1",
            display_name: "Pão francês",
            status: "development",
            technical_product_id: "tp-1",
            row_version: 1,
            current_version: { id: RECIPE_VERSION_ID, version_number: 1, status: "draft" },
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      });
    }
    if (path.endsWith("/recipes") && request.method === "POST") {
      return json({
        data: {
          id: RECIPE_ID,
          code: "PAO-9",
          display_name: "Pão novo",
          status: "development",
          current_version: { id: RECIPE_VERSION_ID, version_number: 1, status: "draft" },
        },
        row_version: 1,
      });
    }
    if (path.includes("/recipes/") && path.endsWith("/trials")) {
      return json({ data: [] });
    }
    if (path.includes("/recipes/") && path.endsWith("/nutrition")) {
      return json({
        data: null,
        disclaimer: "Prévia técnica incompleta e não validada regulatoriamente.",
      });
    }
    if (path.includes("/recipes/") && path.endsWith("/approvals")) {
      return json({ data: [] });
    }
    if (path.includes("/recipes/") && path.endsWith("/scales")) {
      return json({ data: [] });
    }
    if (path.includes("/recipes/") && path.endsWith("/references")) {
      return json({ data: [] });
    }
    if (path.includes("/recipes/") && path.endsWith("/sheet")) {
      return json({
        data: {
          kind: "ficha_tecnica_derivada",
          disclaimer: "Prévia técnica incompleta e não validada regulatoriamente.",
          payload_sha256: "abc123",
          identity: { display_name: "Pão francês", code: "PAO-1", status: "development" },
          version: { version_number: 1, status: "draft" },
          organization: { display_name: "Padaria Central" },
          responsible: { display_name: "Ana Padeiro" },
          components: [{ sequence: 1, label: "Farinha", net_quantity: "1000", bakers_percentage: "100" }],
          steps: [{ sequence: 1, title: "Mistura", instructions: "Juntar." }],
          completeness: { ready_to_publish: false, complete_dossier: false, items: [] },
        },
      });
    }
    if (path.includes("/recipes/") && request.method !== "GET") {
      return json({
        data: { id: RECIPE_ID, status: "draft", decision: "approved", persisted: false, row_version: 2 },
        row_version: 2,
      });
    }
    if (path.includes("/recipes/")) {
      return json({
        data: {
          id: RECIPE_ID,
          code: "PAO-1",
          display_name: "Pão francês",
          status: "development",
          technical_product_id: "tp-1",
          row_version: 1,
          versions: [
            {
              id: RECIPE_VERSION_ID,
              formulation_id: RECIPE_ID,
              version_number: 1,
              status: "draft",
              yield_units: 10,
              target_unit_weight_g: "50",
              expected_bake_loss_rate: "0.12",
              notes: null,
              published_at: null,
              row_version: 1,
            },
          ],
          identity: {
            id: RECIPE_ID,
            code: "PAO-1",
            display_name: "Pão francês",
            status: "development",
            technical_product_id: "tp-1",
            row_version: 1,
            current_version: { id: RECIPE_VERSION_ID, version_number: 1, status: "draft" },
          },
          version: {
            id: RECIPE_VERSION_ID,
            formulation_id: RECIPE_ID,
            version_number: 1,
            status: "draft",
            yield_units: 10,
            target_unit_weight_g: "50",
            expected_bake_loss_rate: "0.12",
            notes: null,
            published_at: null,
            row_version: 1,
          },
          items: [
            {
              id: "ri1",
              ingredient_version_id: "ffffffff-ffff-ffff-ffff-ffffffffffff",
              sequence: 1,
              net_quantity: "1000",
              gross_quantity: "1000",
              measurement_unit_id: "u1",
              correction_factor: "1",
              is_flour_basis: true,
              role: "ingredient",
              notes: null,
              bakers_percentage: "100",
            },
          ],
          steps: [
            {
              id: "rs1",
              sequence: 1,
              title: "Mistura",
              instructions: "Juntar farinha e água.",
              duration_seconds: 600,
              temperature_celsius: "24",
            },
          ],
          bakers: {
            flour_mass: "1000",
            explained_absence: false,
            items: [{ id: "ri1", net_quantity: "1000", gross_quantity: "1000", is_flour_basis: true, bakers_percentage: "100" }],
          },
          yield: {
            base_net_mass: "1000",
            yield_units: 10,
            target_unit_weight_g: "50",
            expected_bake_loss_rate: "0.12",
            expected_final_mass_g: "500",
            portion_mass_g: null,
          },
          completeness: {
            ready_to_publish: false,
            complete_dossier: false,
            items: [
              { code: "aprovacao", label: "Aprovação válida mais recente ausente", blocking: true, origin: "approval" },
              { code: "nutricao", label: "Prévia nutricional técnica ausente", blocking: false, origin: "nutrition_calculation" },
            ],
          },
        },
        row_version: 1,
      });
    }
    if (path.endsWith("/labeling/dossiers") && request.method === "GET") {
      return json({ items: [labelingDossierFixture], total: 1 });
    }
    if (path.endsWith("/labeling/dossiers") && request.method === "POST") {
      return json({ data: labelingDossierFixture, row_version: 1 });
    }
    if (path.includes("/labeling/dossiers/") && path.endsWith("/profile")) {
      return json({ data: { completeness: "incomplete", id: "p1" }, row_version: 2 });
    }
    if (path.includes("/labeling/dossiers/") && path.endsWith("/evaluate")) {
      return json({ data: { id: "v2", version_number: 2, status: "evaluated" }, row_version: 3 });
    }
    if (path.includes("/labeling/dossiers/") && path.endsWith("/review")) {
      return json({ data: { id: "v2", version_number: 2, status: "reviewed" }, row_version: 4 });
    }
    if (path.includes("/labeling/dossiers/") && path.endsWith("/invalidate")) {
      return json({ data: { id: "v2", version_number: 2, status: "invalidated" }, row_version: 5 });
    }
    if (path.includes("/labeling/dossiers/") && path.endsWith("/mandatory")) {
      return json({ data: { id: "v2", version_number: 2, status: "evaluated" }, row_version: 3 });
    }
    if (path.includes("/labeling/dossiers/") && path.endsWith("/compare")) {
      return json({ data: { left: labelingDossierFixture.current, right: labelingDossierFixture.current } });
    }
    if (path.includes("/labeling/dossiers/") && path.endsWith("/render")) {
      return json({
        data: {
          html: "<p>Candidato para conferência. Não é rótulo final.</p>",
          candidate: labelingDossierFixture.current,
        },
      });
    }
    if (path.includes(`/labeling/dossiers/${DOSSIER_ID}`)) {
      return json({ data: labelingDossierFixture, row_version: labelingDossierFixture.row_version });
    }
    if (path.endsWith("/labeling/assessments")) {
      return json({ items: [{ id: "a1", status: "evaluated", proposal_summary: labelingDossierFixture.current.assessment.proposal_summary }], total: 1 });
    }
    if (path.endsWith("/labeling/candidates")) {
      return json({ items: [{ id: "c1", watermark: "Proposta técnica para revisão", payload_sha256: "bbb" }], total: 1 });
    }
    if (path.endsWith("/labeling/sources")) {
      return json({
        items: [
          {
            code: "rdc-429-2020",
            title: "RDC nº 429/2020 — Rotulagem nutricional",
            force: "in_force_act",
            normative: true,
            accessed_at: "2026-08-23",
          },
        ],
      });
    }
    if (path.endsWith("/labeling/portions")) {
      return json({ items: [{ code: "pao", label: "Pães", reference_g: "50.000000", confirmation_required: true }] });
    }
    if (path.endsWith("/costing/policies") && request.method === "GET") {
      return json({ items: [costingPolicyFixture] });
    }
    if (path.endsWith("/costing/policies") && request.method === "POST") {
      return json({ data: costingPolicyFixture, row_version: 1 });
    }
    if (path.includes("/costing/policies/") && path.endsWith("/publish")) {
      return json({ data: { ...costingPolicyFixture, status: "published" }, row_version: 2 });
    }
    if (path.endsWith("/costing/calculations") && request.method === "GET") {
      return json({ items: [costingCalculationFixture] });
    }
    if (path.endsWith("/costing/calculations") && request.method === "POST") {
      return json({ data: costingCalculationFixture });
    }
    if (path.includes(`/costing/calculations/${CALC_ID}`) && path.endsWith("/simulations")) {
      return json({ data: pricingSimulationFixture });
    }
    if (path.includes(`/costing/calculations/${CALC_ID}/compare/`)) {
      return json({
        data: {
          left_kind: "planned",
          right_kind: "actual",
          total_delta: "1.50",
          sellable_delta: null,
          sensitivity: { cost_plus_10: "13.750000", note: "Projeção determinística." },
        },
      });
    }
    if (path.includes(`/costing/calculations/${CALC_ID}`)) {
      return json({ data: costingCalculationFixture });
    }
    if (path.endsWith("/pricing/simulations")) {
      return json({ items: [pricingSimulationFixture] });
    }
    if (path.endsWith("/pricing/practiced") && request.method === "GET") {
      return json({ items: [practicedPriceFixture] });
    }
    if (path.endsWith("/pricing/practiced") && request.method === "POST") {
      return json({ data: practicedPriceFixture, row_version: 1 });
    }
    if (path.includes("/pricing/practiced/") && path.endsWith("/decide")) {
      return json({ data: { ...practicedPriceFixture, status: "active" }, row_version: 2 });
    }
    if (path.endsWith("/recipe-references")) return json({ data: [{ id: "ref-1", title: "Manual interno", source_type: "internal" }] });
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
