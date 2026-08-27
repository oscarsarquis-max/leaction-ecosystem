import {
  ISSUE_ID,
  ORG_A,
  ORDER_ID,
  PLAN_ID,
  boardFixture,
  boardContextFixture,
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
  reportingPayloadFixture,
  reportingSnapshotFixture,
  reportingViewFixture,
  CALC_ID,
  SNAPSHOT_ID,
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
    // jsdom AbortSignal ≠ undici AbortSignal (Node 18+); não repasse signal ao recriar Request.
    const initWithoutSignal = init ? { ...init, signal: undefined } : undefined;
    const request =
      input instanceof Request
        ? input
        : new Request(
            typeof input === "string" ? new URL(input, window.location.origin).toString() : input.toString(),
            initWithoutSignal,
          );
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
            status: "active",
            technical_product_id: "tp-1",
            row_version: 1,
            current_version: { id: RECIPE_VERSION_ID, version_number: 1, status: "draft" },
          },
          {
            id: "recipe-dev",
            code: "F-DEV",
            display_name: "Receita em desenvolvimento",
            status: "development",
            technical_product_id: "tp-2",
            row_version: 1,
            current_version: { id: "ver-dev", version_number: 1, status: "draft" },
          },
        ],
        total: 2,
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
      return json({
        data: [{ id: "tr1", code: "TR-PAO-OK", status: "completed", notes: null, planned_on: null, executed_on: null }],
      });
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
      return json({
        data: [
          {
            id: "scale-1",
            calculation_mode: "total_dough_mass",
            scale_factor: "1.9584569733",
            base_total_net_mass: "1685.000000",
            required_pre_bake_mass: "3300.000000",
            input_target_total_dough_mass: "3300.000000",
            presentation_decimal_places: 3,
          },
        ],
      });
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
              net_quantity: "1000.000000",
              gross_quantity: "1000.000000",
              measurement_unit_id: "u1",
              correction_factor: "1",
              is_flour_basis: true,
              role: "ingredient",
              notes: null,
              bakers_percentage: "100",
              ingredient: {
                id: "ing-1",
                code: "FAR-TRIGO",
                display_name: "Farinha de trigo tipo 1 (Demo)",
                version_id: "ffffffff-ffff-ffff-ffff-ffffffffffff",
                version_number: 1,
              },
              unit: { id: "u1", code: "g", symbol: "g", dimension: "mass" },
            },
            {
              id: "ri2",
              ingredient_version_id: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
              sequence: 2,
              net_quantity: "650.000000",
              gross_quantity: "650.000000",
              measurement_unit_id: "u1",
              correction_factor: "1",
              is_flour_basis: false,
              role: "ingredient",
              notes: null,
              bakers_percentage: "65.00",
              ingredient: {
                id: "ing-2",
                code: "AGUA",
                display_name: "Água (Demo)",
                version_id: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
                version_number: 1,
              },
              unit: { id: "u1", code: "g", symbol: "g", dimension: "mass" },
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
    if (path.endsWith("/inventory/balances")) {
      return json({
        as_of: "2026-08-24",
        timezone: "America/Sao_Paulo",
        items: [
          {
            id: "bal-1",
            inventory_item_id: "item-1",
            inventory_location_id: "loc-1",
            inventory_lot_id: "lot-1",
            item_label: "Farinha de trigo tipo 1",
            location_label: "Almoxarifado Central",
            lot_code: "LOT-000001",
            lot_status: "available",
            physical_quantity: "1500.000000",
            reserved_quantity: "0.000000",
            available_quantity: "1500.000000",
            unreserved_quantity: "1500.000000",
            eligible_quantity: "1500.000000",
            impeded_quantity: "0.000000",
            production_eligible: true,
            eligibility_reason: null,
            unit_code: "g",
          },
          {
            id: "bal-blocked",
            inventory_item_id: "item-1",
            inventory_location_id: "loc-1",
            inventory_lot_id: "lot-3",
            item_label: "Farinha de trigo tipo 1",
            location_label: "Almoxarifado Central",
            lot_code: "LOT-000003",
            lot_status: "blocked",
            physical_quantity: "1500.000000",
            reserved_quantity: "0.000000",
            available_quantity: "1500.000000",
            unreserved_quantity: "1500.000000",
            eligible_quantity: "0.000000",
            impeded_quantity: "1500.000000",
            production_eligible: false,
            eligibility_reason: "lot_status",
            unit_code: "g",
          },
          {
            id: "bal-2",
            inventory_item_id: "item-2",
            inventory_location_id: "loc-1",
            inventory_lot_id: "lot-2",
            item_label: "Embalagens",
            location_label: "Almoxarifado Central",
            lot_code: "LOT-000002",
            lot_status: "available",
            physical_quantity: "120.000000",
            reserved_quantity: "10.000000",
            available_quantity: "110.000000",
            unreserved_quantity: "110.000000",
            eligible_quantity: "110.000000",
            impeded_quantity: "0.000000",
            production_eligible: true,
            eligibility_reason: null,
            unit_code: "un",
          },
        ],
      });
    }
    if (path.endsWith("/inventory/lots")) {
      return json({
        as_of: "2026-08-24",
        timezone: "America/Sao_Paulo",
        items: [
          {
            id: "lot-1",
            internal_lot_code: "LOT-000001",
            item_label: "Farinha de trigo tipo 1",
            location_label: "Almoxarifado Central",
            status: "available",
            expires_on: "2026-09-10",
            physical_quantity: "20000",
            reserved_quantity: "20000",
            unreserved_quantity: "0",
            eligible_quantity: "0",
            impeded_quantity: "0",
            production_eligible: true,
            unit_code: "g",
          },
          {
            id: "lot-2",
            internal_lot_code: "LOT-000002",
            item_label: "Farinha de trigo tipo 1",
            location_label: "Almoxarifado Central",
            status: "available",
            expires_on: "2026-08-27",
            physical_quantity: "4000",
            reserved_quantity: "4000",
            unreserved_quantity: "0",
            eligible_quantity: "0",
            impeded_quantity: "0",
            production_eligible: true,
            unit_code: "g",
          },
          {
            id: "lot-3",
            internal_lot_code: "LOT-000003",
            item_label: "Farinha de trigo tipo 1",
            location_label: "Almoxarifado Central",
            status: "blocked",
            expires_on: "2026-09-13",
            physical_quantity: "1500",
            reserved_quantity: "0",
            unreserved_quantity: "1500",
            eligible_quantity: "0",
            impeded_quantity: "1500",
            production_eligible: false,
            eligibility_reason: "lot_status",
            unit_code: "g",
          },
        ],
      });
    }
    if (path.endsWith("/inventory/reservations")) {
      return json({
        items: [
          {
            id: "res-1",
            production_order_id: ORDER_ID,
            order_public_code: "ORD-20260824-0004",
            inventory_item_id: "item-1",
            item_label: "Farinha de trigo tipo 1",
            status: "reserved",
            required_quantity: "2500.000000",
            reserved_quantity: "2500.000000",
            shortage_quantity: "0.000000",
            unit_code: "g",
            adopted: true,
            created_at: "2026-08-24T12:00:00+00:00",
            allocations: [
              {
                lot_id: "lot-2",
                lot_code: "LOT-000002",
                location_id: "loc-1",
                location_label: "Almoxarifado Central",
                quantity: "2500.000000",
              },
            ],
          },
          {
            id: "res-2",
            production_order_id: ORDER_ID,
            order_public_code: "ORD-20260824-0004",
            inventory_item_id: "item-1",
            item_label: "Farinha de trigo tipo 1",
            status: "partial",
            required_quantity: "90000.000000",
            reserved_quantity: "21500.000000",
            shortage_quantity: "68500.000000",
            unit_code: "g",
            adopted: true,
            created_at: "2026-08-24T12:05:00+00:00",
            allocations: [
              {
                lot_id: "lot-2",
                lot_code: "LOT-000002",
                location_id: "loc-1",
                location_label: "Almoxarifado Central",
                quantity: "1500.000000",
              },
              {
                lot_id: "lot-1",
                lot_code: "LOT-000001",
                location_id: "loc-1",
                location_label: "Almoxarifado Central",
                quantity: "20000.000000",
              },
            ],
          },
        ],
      });
    }
    if (path.endsWith("/inventory/movements")) {
      return json({
        items: [
          {
            id: "mov-1",
            movement_type: "opening",
            item_label: "Farinha de trigo tipo 1",
            lot_code: "LOT-000001",
            to_location_label: "Almoxarifado Central",
            canonical_quantity: "20000.000000",
            unit_code: "g",
            sign: 1,
            origin_type: "opening",
            document_label: null,
            effective_at: "2026-08-24T12:00:00+00:00",
            created_at: "2026-08-24T12:00:00+00:00",
            content_hash: "h1",
          },
          {
            id: "mov-2",
            movement_type: "opening",
            item_label: "Farinha de trigo tipo 1",
            lot_code: "LOT-000002",
            to_location_label: "Almoxarifado Central",
            canonical_quantity: "4000.000000",
            unit_code: "g",
            sign: 1,
            origin_type: "opening",
            effective_at: "2026-08-24T12:00:00+00:00",
            created_at: "2026-08-24T12:00:00+00:00",
          },
          {
            id: "mov-5",
            movement_type: "receipt",
            item_label: "Farinha de trigo tipo 1",
            lot_code: "LOT-000005",
            to_location_label: "Almoxarifado Central",
            canonical_quantity: "4000.000000",
            unit_code: "g",
            sign: 1,
            origin_type: "procurement_receipt",
            document_label: "RCP-000001",
            effective_at: "2026-08-24T13:00:00+00:00",
            created_at: "2026-08-24T13:00:00+00:00",
          },
          {
            id: "mov-6",
            movement_type: "supplier_return",
            item_label: "Farinha de trigo tipo 1",
            lot_code: "LOT-000005",
            from_location_label: "Almoxarifado Central",
            canonical_quantity: "200.000000",
            unit_code: "g",
            sign: -1,
            origin_type: "procurement_return",
            document_label: "RET-000001",
            effective_at: "2026-08-24T14:00:00+00:00",
            created_at: "2026-08-24T14:00:00+00:00",
            content_hash: "h6",
          },
        ],
      });
    }
    if (path.endsWith("/inventory/picks") && request.method === "GET") {
      return json({
        items: [
          {
            id: "pick-1",
            public_code: "PICK-000001",
            production_order_id: ORDER_ID,
            order_public_code: "ORD-20260824-0004",
            product_label: "Pão francês (Demo)",
            status: "confirmed",
            created_at: "2026-08-24T15:00:00+00:00",
            created_by_label: "Proprietário Demo",
            line_count: 1,
            lines: [
              {
                id: "pl-1",
                item_label: "Farinha de trigo tipo 1",
                lot_code: "LOT-000001",
                location_label: "Almoxarifado Central",
                quantity: "500.000000",
                unit_code: "g",
                suggested: true,
                substituted: false,
                reason: null,
              },
            ],
          },
        ],
      });
    }
    if (path.endsWith("/inventory/counts")) {
      return json({
        items: [{ id: "cnt-1", public_code: "CNT-000001", status: "review", row_version: 2, variances: [{ scope_id: "s1", variance: "-10" }] }],
      });
    }
    if (path.endsWith("/inventory/replenishment")) {
      return json({
        data: {
          public_code: "RPL-000001",
          items: [
            {
              inventory_item_id: "item-1",
              item_label: "Farinha de trigo tipo 1",
              suggested_quantity: "500",
              gaps: ["embalagem_ausente"],
            },
          ],
        },
      });
    }
    if (path.includes("/procurement/quotations/compare")) {
      return json({
        items: [
          {
            quotation_id: "q1",
            supplier_id: "s1",
            supplier_name: "Moinho Demo",
            unit_price: "0.02",
            lead_time_days: 3,
            chosen: false,
          },
        ],
      });
    }
    if (path.endsWith("/procurement/quotations")) {
      return json({
        items: [
          {
            id: "q1",
            supplier_id: "s1",
            supplier_name: "Moinho Demo",
            lead_time_days: 3,
            items: [{ id: "qi1", inventory_item_id: "item-1", unit_price: "0.02" }],
          },
          {
            id: "q2",
            supplier_id: "s2",
            supplier_name: "Laticínio Demo",
            lead_time_days: 6,
            items: [{ id: "qi2", inventory_item_id: "item-1", unit_price: "0.03" }],
          },
        ],
      });
    }
    if (path.endsWith("/procurement/requisitions")) {
      return json({
        items: [
          { id: "req-1", public_code: "REQ-000001", status: "draft" },
          { id: "req-2", public_code: "REQ-000002", status: "submitted" },
          { id: "req-3", public_code: "REQ-000003", status: "approved" },
          { id: "req-4", public_code: "REQ-000004", status: "converted" },
        ],
      });
    }
    if (path.endsWith("/procurement/orders")) {
      return json({
        items: [
          {
            id: "po-1",
            public_code: "PO-000001",
            status: "partially_received",
            supplier_name: "Moinho Demo",
            items: [{ id: "poi1", unit_price: "0.02" }],
          },
          {
            id: "po-2",
            public_code: "PO-000002",
            status: "received",
            supplier_name: "Moinho Demo",
            items: [{ id: "poi2", unit_price: "0.03" }],
          },
        ],
      });
    }
    if (path.endsWith("/procurement/receipts")) {
      return json({ items: [{ id: "rcp-1", public_code: "RCP-000001", status: "posted" }] });
    }
    if (path.endsWith("/procurement/returns")) {
      return json({ items: [{ id: "ret-1", public_code: "RET-000001", status: "posted", reason: "embalagem avariada demo" }] });
    }
    if (path.includes("/inventory/") && request.method !== "GET") {
      return json({ data: { id: "inv-cmd", public_code: "CMD-1", status: "draft" }, row_version: 2 });
    }
    if (path.includes("/procurement/") && request.method !== "GET") {
      return json({ data: { id: "proc-cmd", public_code: "CMD-2", status: "draft" }, row_version: 2 });
    }
    if (path.endsWith("/reporting/catalog")) {
      return json({
        items: [
          { code: "executive", name: "Visão executiva", description: "Síntese" },
          { code: "production", name: "Produção", description: "Ordens" },
        ],
      });
    }
    if (path.includes("/reporting/reports/") && path.includes("/drill-down")) {
      return json({ data: { rows: reportingPayloadFixture.tables[0].rows, reconciled: true } });
    }
    if (path.includes("/reporting/reports/")) {
      return json({ data: reportingPayloadFixture });
    }
    if (path.endsWith("/reporting/snapshots") && request.method === "POST") {
      return json({ data: reportingSnapshotFixture });
    }
    if (path.endsWith("/reporting/snapshots")) {
      return json({ items: [reportingSnapshotFixture] });
    }
    if (path.includes(`/reporting/snapshots/${SNAPSHOT_ID}`)) {
      return json({ data: reportingSnapshotFixture });
    }
    if (path.endsWith("/reporting/saved-views") && request.method === "POST") {
      return json({ data: reportingViewFixture });
    }
    if (path.endsWith("/reporting/saved-views")) {
      return json({ items: [reportingViewFixture] });
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
            unit: { id: "u1", code: "kg", symbol: "kg", name: "quilograma", dimension: "mass" },
            supplier: {
              id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
              code: "FOR-1",
              display_name: "Moinho Demo",
            },
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
              nutrient: { id: "n1", code: "protein", name: "Proteína", group_code: "macro" },
              unit: { id: "u1", code: "g", symbol: "g", name: "grama", dimension: "mass" },
              loq_unit: { id: "u1", code: "g", symbol: "g", name: "grama", dimension: "mass" },
            },
          ],
          allergens: [
            {
              id: "a-row",
              allergen_id: "a1",
              presence: "contains",
              data_source_id: null,
              evidence_note: "rótulo",
              allergen: { id: "a1", code: "gluten", name: "Glúten" },
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
    if (path.endsWith("/suppliers") && request.method === "GET") {
      return json({
        data: [
          {
            id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            code: "FOR-MOINHO",
            display_name: "Moinho Demo",
            status: "active",
            row_version: 1,
            active_item_count: 1,
          },
          {
            id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
            code: "FOR-GRANJA",
            display_name: "Granja Demo",
            status: "active",
            row_version: 1,
            active_item_count: 1,
          },
          {
            id: "dddddddd-dddd-dddd-dddd-dddddddddddd",
            code: "FOR-LATIC",
            display_name: "Laticínio Demo",
            status: "active",
            row_version: 1,
            active_item_count: 1,
          },
          {
            id: "eeeeeeee-eeee-eeee-eeee-eeeeeeee0001",
            code: "FOR-SEMENTE",
            display_name: "Sementes Demo",
            status: "active",
            row_version: 1,
            active_item_count: 0,
          },
        ],
      });
    }
    if (
      path.includes("/suppliers/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb") &&
      request.method === "GET" &&
      !path.includes("/items")
    ) {
      return json({
        data: {
          id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
          code: "FOR-MOINHO",
          display_name: "Moinho Demo",
          status: "active",
          row_version: 1,
          active_item_count: 1,
          price_access: true,
          items: [
            {
              id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
              supplier_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
              ingredient_id: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
              supplier_sku: "SKU-FAR-25",
              description: "Embalagem de demonstração",
              package_quantity: "25",
              measurement_unit_id: "u1",
              status: "active",
              row_version: 1,
              unit: { id: "u1", code: "kg", symbol: "kg", name: "quilograma", dimension: "mass" },
              supplier: {
                id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                code: "FOR-MOINHO",
                display_name: "Moinho Demo",
              },
              ingredient: {
                id: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
                code: "FAR-TRIGO",
                display_name: "Farinha de trigo tipo 1 (Demo)",
              },
              latest_purchase: {
                unit_price: "13.00",
                currency: "BRL",
                observed_at: "2026-08-24T12:00:00+00:00",
              },
            },
          ],
        },
      });
    }
    if (
      path.includes("/items/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/prices") &&
      request.method === "GET"
    ) {
      return json({
        data: [
          {
            id: "price-3",
            supplier_item_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            unit_price: "13.00",
            currency: "BRL",
            observed_at: "2026-08-24T12:00:00+00:00",
            source: "receipt:demo",
            is_latest: true,
          },
          {
            id: "price-2",
            supplier_item_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            unit_price: "13.10",
            currency: "BRL",
            observed_at: "2026-08-23T12:00:00+00:00",
            source: "seed-demo",
            is_latest: false,
          },
          {
            id: "price-1",
            supplier_item_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            unit_price: "12.50",
            currency: "BRL",
            observed_at: "2026-08-14T12:00:00+00:00",
            source: "seed-demo",
            is_latest: false,
          },
        ],
        price_access: true,
      });
    }
    if (path.endsWith("/suppliers") && request.method === "POST") {
      return json({
        data: {
          id: "ffffffff-ffff-ffff-ffff-ffffffffff01",
          code: "FOR-NOVO",
          display_name: "Novo Demo",
          status: "active",
          row_version: 1,
          active_item_count: 0,
        },
        row_version: 1,
      });
    }
    if (path.endsWith("/catalog/units")) return json({ data: [{ id: "u1", code: "g", name: "grama", access: "somente_leitura" }] });
    if (path.endsWith("/catalog/nutrients")) return json({ data: [{ id: "n1", code: "protein", name: "proteína", access: "somente_leitura" }] });
    if (path.endsWith("/catalog/allergens")) return json({ data: [{ id: "a1", code: "gluten", name: "glúten", access: "somente_leitura" }] });
    if (path.endsWith("/catalog/sources")) return json({ data: [] });
    if (path.endsWith("/production/catalog")) return json(catalogFixture);
    if (path.endsWith(`/orders/${ORDER_ID}/execution`)) return json(executionFixture);
    if (path.endsWith("/production/board/context")) return json(boardContextFixture);
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
