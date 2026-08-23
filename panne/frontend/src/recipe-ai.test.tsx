import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { PROPOSAL_ID, meFixture } from "./api/fixtures";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("assistente de receitas", () => {
  it("abre o hub com criar, adaptar e histórico", async () => {
    installApiMock();
    const { view } = await renderApp("/receitas/assistente");
    expect(await screen.findByRole("heading", { name: "Assistente de receitas" })).toBeInTheDocument();
    expect(screen.getByText("Assistido por IA")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Criar com assistência" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Adaptar receita" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Abrir histórico" })).toBeInTheDocument();
    expect(await axe(view.container)).toEqual(expect.objectContaining({ violations: [] }));
  });

  it("coleta objetivo e restrições na criação guiada", async () => {
    installApiMock();
    await renderApp("/receitas/assistente/criar");
    const user = userEvent.setup();
    expect(await screen.findByRole("heading", { name: "Criar com assistência" })).toBeInTheDocument();
    await user.type(screen.getByLabelText("Objetivo"), "Criar pão com farinha de trigo");
    await user.type(screen.getByLabelText("Alergênicos a evitar"), "amendoim");
    await user.click(screen.getByRole("button", { name: "Gerar proposta" }));
    await waitFor(() => {
      expect(
        vi.mocked(fetch).mock.calls.some(([input]) => String(input).includes("/recipe-ai/proposals")),
      ).toBe(true);
    });
  });

  it("adapta receita pedindo versão-base", async () => {
    installApiMock();
    await renderApp("/receitas/assistente/adaptar");
    expect(await screen.findByLabelText("Versão-base")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Adaptar receita" })).toBeInTheDocument();
  });

  it("mostra grounding insuficiente e progresso da mentoria", async () => {
    installApiMock({
      "/recipe-ai/proposals/": () =>
        json({
          data: {
            id: PROPOSAL_ID,
            intent: "create_recipe",
            title: "Sem evidência",
            objective_summary: "objetivo",
            status: "grounding_insufficient",
            status_label: "grounding insuficiente",
            assisted_by_ai: true,
            warnings: [],
            missing_data: ["evidência"],
            row_version: 1,
            items: [],
            changes: [],
            citations: [],
          },
        }),
    });
    await renderApp(`/receitas/assistente/${PROPOSAL_ID}`);
    expect(await screen.findByText(/Grounding insuficiente/)).toBeInTheDocument();
    expect(screen.getByRole("dialog", { name: "Mentoria do assistente" })).toBeInTheDocument();
  });

  it("compara, cita, aceita, rejeita e materializa rascunho", async () => {
    installApiMock();
    const { view } = await renderApp(`/receitas/assistente/${PROPOSAL_ID}`);
    const user = userEvent.setup();
    expect(await screen.findByRole("heading", { name: "Pão de teste assistivo" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Comparação" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Citações" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Itens não resolvidos" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Aceitar" }));
    await user.click(screen.getByRole("button", { name: "Aceitar em conjunto" }));
    await user.click(screen.getByRole("button", { name: "Materializar rascunho" }));
    await waitFor(() => {
      expect(screen.getByText(/Resultado materializado/)).toBeInTheDocument();
    });
    expect(await axe(view.container)).toEqual(expect.objectContaining({ violations: [] }));
  });

  it("trata proposta já materializada e conflito", async () => {
    installApiMock({
      materialize: () =>
        json({ code: "proposta_ja_materializada", message: "Esta proposta já foi materializada em rascunho." }, 409),
    });
    await renderApp(`/receitas/assistente/${PROPOSAL_ID}`);
    const user = userEvent.setup();
    expect(await screen.findByRole("button", { name: "Materializar rascunho" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Materializar rascunho" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/já foi materializada|Falha|conflito|versão/i);
  });

  it("oculta geração quando a organização não tem permissão", async () => {
    installApiMock({
      "/api/v1/me": () =>
        json({
          ...meFixture,
          permissions: meFixture.permissions.filter((item) => !item.startsWith("recipe.ai.")),
          associations: meFixture.associations.map((item) => ({
            ...item,
            permissions: item.permissions.filter((code) => !code.startsWith("recipe.ai.")),
          })),
        }),
    });
    await renderApp("/receitas/assistente");
    expect(await screen.findByText("Este papel não gera propostas.")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Criar com assistência" })).not.toBeInTheDocument();
  });

  it("mostra timeout sem chamar serviço externo", async () => {
    installApiMock({
      "/recipe-ai/proposals": () =>
        json({ code: "timeout", message: "A geração excedeu o tempo limite." }, 422),
    });
    await renderApp("/receitas/assistente/criar");
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Objetivo"), "Criar pão com farinha de trigo");
    await user.click(screen.getByRole("button", { name: "Gerar proposta" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/tempo limite/i);
  });

  it("mantém o formulário em viewport de tablet", async () => {
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 768 });
    installApiMock();
    await renderApp("/receitas/assistente/criar");
    expect(await screen.findByLabelText("Objetivo")).toBeVisible();
    expect(screen.getByLabelText("Alergênicos a evitar")).toBeVisible();
  });

  it("lista o histórico sem chamadas externas", async () => {
    installApiMock();
    await renderApp("/receitas/assistente/historico");
    expect(await screen.findByRole("heading", { name: "Histórico de propostas" })).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "Pão de teste assistivo" })).toBeInTheDocument();
    const urls = vi.mocked(fetch).mock.calls.map(([input]) =>
      input instanceof Request ? input.url : String(input),
    );
    expect(urls.every((url) => !/amazonaws|anthropic/i.test(url))).toBe(true);
    expect(
      urls.every(
        (url) =>
          url.startsWith("/") ||
          url.startsWith("http://127.0.0.1") ||
          url.startsWith("http://localhost"),
      ),
    ).toBe(true);
  });
});
