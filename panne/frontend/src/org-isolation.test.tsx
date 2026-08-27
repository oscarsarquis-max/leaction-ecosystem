import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  CALC_ID,
  DOSSIER_ID,
  ORDER_ID,
  ORG_A,
  ORG_B,
  PLAN_ID,
  costingCalculationFixture,
  labelingDossierFixture,
  meFixture,
  planDetailFixture,
  reportingPayloadFixture,
} from "./api/fixtures";
import { findingRuleLabel, mandatoryCodeLabel } from "./language/labeling";
import { formatOperationalQuantity, pluralize } from "./language/quantities";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});

function orgFromUrl(url: URL): string {
  return url.pathname.includes(ORG_B) ? ORG_B : ORG_A;
}

function notFound(message: string) {
  return json({ code: "nao_encontrado", message }, 404);
}

/** ORG_B no fixture base e viewer sem labeling/estoque/rastreio — amplia para o teste de isolamento. */
function meWithIsolationPerms() {
  return {
    ...meFixture,
    associations: meFixture.associations.map((row) =>
      row.organization_id === ORG_B
        ? {
            ...row,
            permissions: [
              ...row.permissions,
              "labeling.read",
              "inventory.read",
              "production.traceability.read",
              "costing.read",
              "reporting.dashboard.read",
              "reporting.production.read",
            ],
          }
        : row,
    ),
  };
}

function isolationMocks(extra: Record<string, (url: URL, request: Request) => Response> = {}) {
  installApiMock({
    "/api/v1/me": () => json(meWithIsolationPerms()),
    ...extra,
  });
}

describe("R026-004 isolamento org", () => {
  it("dossier: conteudo A some imediatamente e B nao herda dados", async () => {
    const dossierCalls: string[] = [];
    isolationMocks({
      [`/labeling/dossiers/${DOSSIER_ID}`]: (url) => {
        const org = orgFromUrl(url);
        dossierCalls.push(org);
        if (org === ORG_B) {
          return notFound("Este dossie nao esta disponivel nesta organizacao.");
        }
        return json({ data: labelingDossierFixture, row_version: labelingDossierFixture.row_version });
      },
    });
    const user = userEvent.setup();
    await renderApp(`/conformidade/dossies/${DOSSIER_ID}`);
    expect(await screen.findByRole("heading", { name: /Dossi/ })).toBeInTheDocument();
    expect(await screen.findByText(/Pão francês|Pao frances/i)).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Organização ativa"), ORG_B);

    await waitFor(() => {
      expect(screen.queryByText(/Pão francês|Pao frances/i)).not.toBeInTheDocument();
    });
    expect(
      await screen.findByRole("heading", { name: /Não foi possível carregar|Nao foi possivel carregar/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/lista de dossi/i)).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Organização ativa"), ORG_A);
    expect(await screen.findByText(/Pão francês|Pao frances/i)).toBeInTheDocument();
    expect(dossierCalls.filter((row) => row === ORG_B).length).toBeGreaterThan(0);
  });

  it("plano: nome some na troca e responde 404 em B", async () => {
    isolationMocks({
      [`/plans/${PLAN_ID}`]: (url) => {
        if (orgFromUrl(url) === ORG_B) return notFound("Plano indisponivel nesta organizacao.");
        return json(planDetailFixture);
      },
    });
    const user = userEvent.setup();
    await renderApp(`/planejamento/${PLAN_ID}`);
    expect(await screen.findAllByText(/Pão francês|Pao frances/i)).not.toHaveLength(0);
    await user.selectOptions(screen.getByLabelText("Organização ativa"), ORG_B);
    await waitFor(() => expect(screen.queryByText(/Pão francês|Pao frances/i)).not.toBeInTheDocument());
    expect(
      await screen.findByRole("heading", { name: /Não foi possível carregar|Nao foi possivel carregar/i }),
    ).toBeInTheDocument();
  });

  it("rastreabilidade: codigo publico de A some em B", async () => {
    isolationMocks({
      [`/orders/${ORDER_ID}/traceability`]: (url) => {
        if (orgFromUrl(url) === ORG_B) return notFound("Rastreio indisponivel nesta organizacao.");
        return json({
          data: {
            order: {
              id: ORDER_ID,
              public_code: "ORD-ORG-A-ONLY",
              status: "in_progress",
              formulation_version_id: null,
              scale_calculation_id: null,
              materials_hash: null,
              steps_hash: null,
              snapshot_hash: null,
              policy_hash: null,
            },
            batches: [],
            planned_materials: [],
            planned_steps: [],
            actual_materials: [],
            weighings: [],
            verifications: [],
            consumptions: [],
            step_runs: [],
            yields: [],
            occurrences: [],
            dependencies: [],
            overrides: [],
            sheet_issues: [],
            events: [],
          },
        });
      },
    });
    const user = userEvent.setup();
    await renderApp(`/rastreabilidade/${ORDER_ID}`);
    expect(await screen.findByText(/ORD-ORG-A-ONLY/)).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Organização ativa"), ORG_B);
    await waitFor(() => expect(screen.queryByText(/ORD-ORG-A-ONLY/)).not.toBeInTheDocument());
    expect(
      await screen.findByRole("heading", { name: /Não foi possível carregar|Nao foi possivel carregar/i }),
    ).toBeInTheDocument();
  });

  it("estoque limpa saldos ao trocar organizacao", async () => {
    isolationMocks({
      "/inventory/balances": (url) => {
        if (orgFromUrl(url) === ORG_B) return json({ items: [] });
        return json({
          items: [
            {
              id: "bal-a",
              item_label: "Farinha Org A",
              location_label: "Almox A",
              lot_code: "LOT-A",
              physical_quantity: "1500.000000",
              reserved_quantity: "0",
              available_quantity: "1500",
              unit_code: "g",
            },
          ],
        });
      },
    });
    const user = userEvent.setup();
    await renderApp("/componentes/estoque");
    expect(await screen.findByText(/Unidade: g/)).toBeInTheDocument();
    expect(screen.getAllByText(formatOperationalQuantity("1500", "g")).length).toBeGreaterThan(0);
    await user.selectOptions(screen.getByLabelText("Organização ativa"), ORG_B);
    await waitFor(() => {
      expect(screen.queryByText(/Unidade: g/)).not.toBeInTheDocument();
    });
    expect(await screen.findByText(/Não há saldos|Nao ha saldos/i)).toBeInTheDocument();
  });

  it("custos: total de A some em B", async () => {
    isolationMocks({
      [`/costing/calculations/${CALC_ID}`]: (url) => {
        if (orgFromUrl(url) === ORG_B) return notFound("Calculo indisponivel nesta organizacao.");
        return json({ data: { ...costingCalculationFixture, total_amount: "99.91-ORG-A" } });
      },
    });
    const user = userEvent.setup();
    await renderApp(`/gestao/custos/calculos/${CALC_ID}`);
    expect(await screen.findByText(/99\.91-ORG-A/)).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Organização ativa"), ORG_B);
    await waitFor(() => expect(screen.queryByText(/99\.91-ORG-A/)).not.toBeInTheDocument());
    expect(
      await screen.findByRole("heading", { name: /Não foi possível carregar|Nao foi possivel carregar/i }),
    ).toBeInTheDocument();
  });

  it("relatorios: indicador de A some em B", async () => {
    isolationMocks({
      "/reporting/reports/executive": (url) => {
        if (orgFromUrl(url) === ORG_B) return notFound("Relatorio indisponivel nesta organizacao.");
        return json({
          data: {
            ...reportingPayloadFixture,
            indicators: [
              {
                code: "orders_by_status",
                name: "Indicador exclusivo Org A",
                status: "available",
                value: "42-ORG-A",
                unit: "count",
                coverage: { universe: 3, valid_count: 3, missing_count: 0 },
              },
            ],
          },
        });
      },
    });
    const user = userEvent.setup();
    await renderApp("/gestao/relatorios/executivo");
    expect(await screen.findByRole("heading", { name: /Visão executiva|Visao executiva/i })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: /Indicador exclusivo Org A/i })).toBeInTheDocument();
    expect(screen.getByText(/42-ORG-A/)).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Organização ativa"), ORG_B);
    await waitFor(() => expect(screen.queryByText(/42-ORG-A/)).not.toBeInTheDocument());
    expect(
      await screen.findByRole("heading", { name: /Não foi possível carregar|Nao foi possivel carregar/i }),
    ).toBeInTheDocument();
  });

  it("resposta atrasada de A nao aparece em B (corrida)", async () => {
    let resolveA: ((value: Response) => void) | null = null;
    isolationMocks({
      [`/labeling/dossiers/${DOSSIER_ID}`]: (url) => {
        const org = orgFromUrl(url);
        if (org === ORG_B) {
          return notFound("Este dossie nao esta disponivel nesta organizacao.");
        }
        return new Promise<Response>((resolve) => {
          resolveA = resolve;
        }) as unknown as Response;
      },
    });
    const user = userEvent.setup();
    const renderPromise = renderApp(`/conformidade/dossies/${DOSSIER_ID}`);
    await waitFor(() => expect(resolveA).not.toBeNull());
    await user.selectOptions(await screen.findByLabelText("Organização ativa"), ORG_B);
    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: /Não foi possível carregar|Nao foi possivel carregar/i }),
      ).toBeInTheDocument(),
    );
    const settleA = resolveA as ((value: Response) => void) | null;
    expect(settleA).not.toBeNull();
    settleA!(json({ data: labelingDossierFixture, row_version: labelingDossierFixture.row_version }));
    await renderPromise;
    await waitFor(() => {
      expect(screen.queryByText(/Pão francês|Pao frances/i)).not.toBeInTheDocument();
    });
  });
});

describe("R026-004 residuos de linguagem e quantidade", () => {
  it("traduz regras nutrient_* e mandatory_* do cenario demo", () => {
    expect(findingRuleLabel("nutrient_energy_kcal")).toBe("Valor energético obrigatório");
    expect(findingRuleLabel("nutrient_carbohydrate")).toBe("Carboidratos obrigatórios");
    expect(findingRuleLabel("nutrient_total_sugars")).toBe("Açúcares totais obrigatórios");
    expect(findingRuleLabel("may_contain")).toBe("Possível presença de alergênicos");
    expect(findingRuleLabel("lactose")).toBe("Lactose — evidência insuficiente");
    expect(mandatoryCodeLabel("mandatory_lote")).toBe("Lote");
    expect(findingRuleLabel("mandatory_prazo_validade")).toBe("Prazo de validade obrigatório");
    expect(findingRuleLabel("mandatory_conservacao")).toBe("Conservação obrigatória");
    expect(findingRuleLabel("mandatory_preparo")).toBe("Instruções de preparo obrigatórias");
    expect(findingRuleLabel("mandatory_identificacao_responsavel")).toBe(
      "Identificação do responsável obrigatória",
    );
  });

  it("formata conteudo liquido e pluraliza posicoes", () => {
    expect(formatOperationalQuantity("50.000000", "g")).toBe("50 g");
    expect(pluralize(1, "posição", "posições")).toBe("1 posição");
    expect(pluralize(6, "posição", "posições")).toBe("6 posições");
  });

  it("dossie nao mostra 50.000000 cru no conteudo liquido", async () => {
    const dossier = {
      ...labelingDossierFixture,
      profile: { ...labelingDossierFixture.profile, net_content_g: "50.000000" },
      current: {
        ...labelingDossierFixture.current,
        mandatory: [
          ...(labelingDossierFixture.current.mandatory ?? []),
          {
            code: "conteudo_liquido",
            label: "Conteúdo líquido",
            value: "50.000000",
            status: "filled",
          },
        ],
      },
    };
    isolationMocks({
      [`/labeling/dossiers/${DOSSIER_ID}`]: () =>
        json({ data: dossier, row_version: dossier.row_version }),
    });
    await renderApp(`/conformidade/dossies/${DOSSIER_ID}`);
    expect(await screen.findByRole("heading", { name: /Dossi/ })).toBeInTheDocument();
    await waitFor(() => {
      expect(document.body.textContent ?? "").toMatch(/50 g/);
      expect(document.body.textContent ?? "").not.toMatch(/50\.000000/);
    });
  });
});
