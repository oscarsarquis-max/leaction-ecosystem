import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import {
  CALC_ID,
  DOSSIER_ID,
  ISSUE_ID,
  ORDER_ID,
  PLAN_ID,
  PROPOSAL_ID,
  RECIPE_ID,
  RECIPE_VERSION_ID,
  SNAPSHOT_ID,
} from "./api/fixtures";
import { collectRouterPaths } from "./guide/collectRoutes";
import { DEMO_PROFILES } from "./demo/profiles";
import { installApiMock } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});

const FIXTURE_IDS: Record<string, string> = {
  ingredientId: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
  supplierId: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
  recipeId: RECIPE_ID,
  versionId: RECIPE_VERSION_ID,
  proposalId: PROPOSAL_ID,
  planId: PLAN_ID,
  orderId: ORDER_ID,
  issueId: ISSUE_ID,
  dossierId: DOSSIER_ID,
  calcId: CALC_ID,
  snapshotId: SNAPSHOT_ID,
};

function concretePath(path: string): string {
  return path.replace(/:([A-Za-z]+)/g, (_, name: string) => FIXTURE_IDS[name] || "amostra");
}

describe("aceitação demo 026", () => {
  it(
    "abre todas as rotas reais com avatar e sem botão textual minimizado",
    async () => {
    installApiMock();
    const paths = collectRouterPaths().filter((path) => path !== "/");
    expect(paths.length).toBeGreaterThan(40);
    for (const path of paths) {
      const signedIn = path !== "/entrar" && path !== "/callback";
      const { view } = await renderApp(concretePath(path), { signedIn });
      if (signedIn) {
        expect(await screen.findByRole("button", { name: "Abrir Gigio, assistente da Panne" })).toBeInTheDocument();
      } else if (path === "/entrar") {
        expect(await screen.findByRole("button", { name: "Abrir ajuda de Gigio para entrar" })).toBeInTheDocument();
      }
      expect(screen.queryByRole("button", { name: "Assistente" })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Retomar assistente" })).not.toBeInTheDocument();
      view.unmount();
    }
  },
    20_000,
  );

  it("lista os sete perfis demo e as compras completas com nomes", async () => {
    expect(DEMO_PROFILES.map((row) => row.subject)).toEqual([
      "demo-owner",
      "demo-manager",
      "demo-formulator",
      "demo-baker",
      "demo-reviewer",
      "demo-buyer",
      "demo-reader",
    ]);
    installApiMock();
    await renderApp("/componentes/estoque/posicao");
    expect((await screen.findAllByText("Farinha de trigo tipo 1")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Almoxarifado Central").length).toBeGreaterThan(0);
    expect(screen.getByRole("table").textContent).not.toMatch(
      /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i,
    );
    await renderApp("/gestao/compras/cotacoes");
    expect(await screen.findByText(/Moinho Demo/)).toBeInTheDocument();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Comparar" }));
    expect(await screen.findByText("não")).toBeInTheDocument();
    await renderApp("/gestao/compras/requisicoes");
    expect(await screen.findByText("REQ-000004")).toBeInTheDocument();
    expect(screen.getByText("Convertido")).toBeInTheDocument();
    await renderApp("/gestao/compras/pedidos");
    expect(await screen.findByText("Recebido em parte")).toBeInTheDocument();
    expect(screen.getByText("Recebido")).toBeInTheDocument();
  });

  it("mantém axe limpo nas páginas críticas em largura de tablet", async () => {
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1024 });
    installApiMock();
    for (const path of ["/entrar", "/producao", "/componentes/estoque", "/gestao/compras/pedidos", "/gestao/relatorios"]) {
      const { view } = await renderApp(path, { signedIn: path !== "/entrar" });
      const results = await axe(view.container);
      expect(results.violations.filter((item) => item.impact === "critical")).toEqual([]);
      view.unmount();
    }
  });
});
