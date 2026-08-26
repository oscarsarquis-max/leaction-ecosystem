import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { buildAssistantMatrix, guideGaps, samplePath } from "./guide/matrix";
import { collectRouterPaths } from "./guide/collectRoutes";
import { matchGuide } from "./guide/routes";
import { installApiMock } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});

describe("assistente global 025", () => {
  it("mostra avatar em páginas de cada domínio e não usa botão textual minimizado", async () => {
    installApiMock();
    const paths = [
      "/inicio",
      "/producao",
      "/planejamento",
      "/ordens",
      "/rastreabilidade",
      "/receitas",
      "/componentes/ingredientes",
      "/componentes/estoque",
      "/componentes/lotes",
      "/componentes/fornecedores",
      "/conformidade",
      "/gestao/custos",
      "/gestao/compras/necessidades",
      "/gestao/inventarios",
      "/gestao/relatorios",
    ];
    for (const path of paths) {
      const { view } = await renderApp(path);
      expect(await screen.findByRole("button", { name: "Abrir assistente da Panne" })).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Assistente" })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Retomar assistente" })).not.toBeInTheDocument();
      view.unmount();
    }
  });

  it("expõe avatar público no login sem botão textual minimizado", async () => {
    installApiMock();
    await renderApp("/entrar", { signedIn: false });
    expect(await screen.findByRole("button", { name: "Abrir ajuda para entrar" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Assistente" })).not.toBeInTheDocument();
  });

  it("compara o router real com os guias e registra fallback", () => {
    expect(guideGaps()).toEqual([]);
    for (const path of collectRouterPaths()) {
      if (path === "/") continue;
      expect(matchGuide(samplePath(path))).toBeTruthy();
    }
  });

  it("gera matriz de aceitação a partir das rotas reais", () => {
    const rows = buildAssistantMatrix();
    expect(rows.length).toBeGreaterThan(40);
    expect(rows.every((row) => row.avatar.startsWith("sim"))).toBe(true);
    expect(rows.filter((row) => row.guide === "fallback")).toEqual([]);
  });

  it("atualiza o contexto ao abrir uma ordem e limpa ao trocar a rota", async () => {
    installApiMock();
    const user = userEvent.setup();
    const { view } = await renderApp("/producao");
    await user.click(await screen.findByRole("button", { name: "Usar este contexto" }));
    await user.click(await screen.findByRole("button", { name: "Abrir assistente da Panne" }));
    expect(await screen.findByRole("dialog", { name: "Assistente" })).toHaveTextContent(/Quadro de produção/);
    view.unmount();
    await renderApp("/receitas");
    await user.click(await screen.findByRole("button", { name: "Abrir assistente da Panne" }));
    expect(await screen.findByRole("dialog", { name: "Assistente" })).toHaveTextContent(/Receitas/);
    expect(screen.getByRole("dialog", { name: "Assistente" })).not.toHaveTextContent(/Quadro de produção/);
  });
});
