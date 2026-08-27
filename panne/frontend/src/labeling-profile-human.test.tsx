import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DOSSIER_ID, labelingDossierFixture } from "./api/fixtures";
import {
  findingRuleLabel,
  physicalStateLabel,
  salesChannelLabel,
  triStateLabel,
  UNCATALOGED_OPTION_LABEL,
  UNCATALOGED_RULE_LABEL,
  UNKNOWN_LABELING_CODE,
} from "./language/labeling";
import { formatOperationalQuantity } from "./language/quantities";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});

describe("R026-004 perfil e achados humanos", () => {
  it("traduz booleanos, enums e lactose sem fallback técnico", () => {
    expect(triStateLabel(true)).toBe("Sim");
    expect(triStateLabel(false)).toBe("Não");
    expect(triStateLabel(null)).toBe("Não informado");
    expect(triStateLabel(undefined)).toBe("Não informado");
    expect(salesChannelLabel("retail")).toBe("Varejo");
    expect(physicalStateLabel("solid")).toBe("Sólido");
    expect(salesChannelLabel("canal_inventado")).toBe(UNCATALOGED_OPTION_LABEL);
    expect(findingRuleLabel("lactose")).toBe("Lactose — evidência insuficiente");
    expect(findingRuleLabel("gluten_contains")).toBe("Glúten — contém");
    expect(findingRuleLabel("may_contain")).toBe("Possível presença de alergênicos");
    expect(findingRuleLabel("regra_futura_xyz")).toBe(UNCATALOGED_RULE_LABEL);
    expect(findingRuleLabel("regra_futura_xyz")).not.toBe(UNKNOWN_LABELING_CODE);
  });

  it("perfil mostra Sim/Não/Não informado e Varejo/Sólido na superfície", async () => {
    installApiMock({
      [`/labeling/dossiers/${DOSSIER_ID}`]: () =>
        json({
          data: {
            ...labelingDossierFixture,
            profile: {
              ...labelingDossierFixture.profile,
              packed_food: true,
              packed_away_from_consumer: true,
              packed_at_point_of_sale: null,
              ready_to_eat: false,
              sales_channel: "retail",
              physical_state: "solid",
              net_content_g: "50.000000",
            },
          },
          row_version: labelingDossierFixture.row_version,
        }),
    });
    await renderApp(`/conformidade/dossies/${DOSSIER_ID}`);
    expect(await screen.findByRole("heading", { name: /Dossi/ })).toBeInTheDocument();

    expect(screen.getByLabelText("Alimento embalado")).toHaveDisplayValue("Sim");
    expect(screen.getByLabelText("Embalado na ausência do consumidor")).toHaveDisplayValue("Sim");
    expect(screen.getByLabelText("Embalado no ponto de venda")).toHaveDisplayValue("Não informado");
    expect(screen.getByLabelText("Pronto para consumo")).toHaveDisplayValue("Não");
    expect(screen.getByLabelText("Canal de venda")).toHaveDisplayValue("Varejo");
    expect(screen.getByLabelText("Estado físico")).toHaveDisplayValue("Sólido");
    expect(screen.getAllByText(/50 g/).length).toBeGreaterThan(0);

    const surface = document.body.textContent ?? "";
    // Códigos técnicos não devem aparecer como valor principal dos selects.
    expect(screen.queryByDisplayValue("true")).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue("false")).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue("retail")).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue("solid")).not.toBeInTheDocument();
    expect(surface).not.toContain("Código técnico não catalogado");
    expect(surface).toContain("Lactose — evidência insuficiente");
    expect(formatOperationalQuantity("50.000000", "g")).toBe("50 g");
  });

  it("grava perfil preservando contrato da API (true/false/null/retail/solid)", async () => {
    installApiMock();
    const user = userEvent.setup();
    await renderApp(`/conformidade/dossies/${DOSSIER_ID}`);
    expect(await screen.findByLabelText("Alimento embalado")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Alimento embalado"), "true");
    await user.selectOptions(screen.getByLabelText("Embalado no ponto de venda"), "");
    await user.selectOptions(screen.getByLabelText("Pronto para consumo"), "false");
    await user.selectOptions(screen.getByLabelText("Canal de venda"), "retail");
    await user.selectOptions(screen.getByLabelText("Estado físico"), "solid");
    await user.click(screen.getByRole("button", { name: "Gravar perfil" }));

    await waitFor(() => {
      expect(
        vi.mocked(fetch).mock.calls.some(
          ([input, init]) => String(input).includes("/profile") && (init as RequestInit | undefined)?.method === "POST",
        ),
      ).toBe(true);
    });
    const posted = vi.mocked(fetch).mock.calls.find(
      ([input, init]) => String(input).includes("/profile") && (init as RequestInit | undefined)?.method === "POST",
    );
    const body = JSON.parse(String((posted?.[1] as RequestInit).body)) as Record<string, unknown>;
    expect(body.packed_food).toBe(true);
    expect(body.packed_at_point_of_sale).toBeNull();
    expect(body.ready_to_eat).toBe(false);
    expect(body.sales_channel).toBe("retail");
    expect(body.physical_state).toBe("solid");
  });

  it("fallback futuro usa texto prudente e código só na auditoria", async () => {
    installApiMock({
      [`/labeling/dossiers/${DOSSIER_ID}`]: () =>
        json({
          data: {
            ...labelingDossierFixture,
            profile: {
              ...labelingDossierFixture.profile,
              sales_channel: "canal_ainda_nao_mapeado",
            },
            current: {
              ...labelingDossierFixture.current,
              findings: [
                {
                  rule_code: "regra_futura_xyz",
                  result: "insufficient_evidence",
                  fact: "x",
                  expected_value: null,
                  found_value: null,
                  source_code: "rdc",
                  source_locator: "—",
                  explanation: "Achado futuro de proteção.",
                  action_needed: true,
                },
              ],
            },
          },
          row_version: 2,
        }),
    });
    await renderApp(`/conformidade/dossies/${DOSSIER_ID}`);
    expect(await screen.findByText(UNCATALOGED_RULE_LABEL)).toBeInTheDocument();
    expect(screen.getByLabelText("Canal de venda")).toHaveDisplayValue(UNCATALOGED_OPTION_LABEL);
    expect(document.body.textContent ?? "").not.toContain("Código técnico não catalogado");
    expect(screen.getByText("regra_futura_xyz")).toBeInTheDocument(); // detalhe técnico
  });
});
