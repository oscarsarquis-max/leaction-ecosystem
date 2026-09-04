import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { config } from "./config";
import { fiscalSummarySentence } from "./language/fiscal";
import { productsSummarySentence } from "./language/products";
import { DEMO_GUIDE_FALLBACK, formatGuideCount } from "./demo/guideFallback";
import { installApiMock } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
  config.demoMode = false;
});

describe("R028-002 guia da demonstração", () => {
  it("ausência ≠ inventar zero no formatador", () => {
    expect(formatGuideCount(null)).toBe("Não informado");
    expect(formatGuideCount(undefined)).toBe("Não informado");
    expect(formatGuideCount(0)).toBe("0");
  });

  it("fallback traz sete perfis e roteiro de 14 passos", () => {
    expect(DEMO_GUIDE_FALLBACK.profiles).toHaveLength(7);
    expect(DEMO_GUIDE_FALLBACK.roadmap).toHaveLength(14);
    expect(DEMO_GUIDE_FALLBACK.roadmap[8]?.path).toBe("/planejamento");
    expect(DEMO_GUIDE_FALLBACK.roadmap[9]?.path).toBe("/ordens");
  });

  it("página pública carrega com fallback se a API falhar", async () => {
    config.demoMode = true;
    installApiMock({
      "/api/v1/public/demo-guide": () =>
        new Response("fail", { status: 503, headers: { "Content-Type": "text/plain" } }),
    });
    await renderApp("/demonstracao", { signedIn: false });
    expect(await screen.findAllByRole("heading", { name: /Guia da demonstração/i })).not.toHaveLength(0);
    expect(screen.getByText(/fallback versionado/i)).toBeInTheDocument();
    expect(screen.getByText(/Roteiro recomendado/i)).toBeInTheDocument();
    expect(screen.getAllByText(/disponível após entrar/i).length).toBeGreaterThan(0);
  });

  it("/entrar mostra Como avaliar e Gigio aponta o guia", async () => {
    config.demoMode = true;
    installApiMock();
    const user = userEvent.setup();
    await renderApp("/entrar", { signedIn: false });
    expect(screen.getByRole("heading", { name: /Como avaliar esta demonstração/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Abrir guia completo da demonstração/i })).toHaveAttribute(
      "href",
      "/demonstracao",
    );
    expect(screen.queryByText(/provedor falso explícito/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Ajuda para entrar/i }));
    const assist = await screen.findByRole("dialog", { name: /Gigio/i });
    expect(assist).toHaveTextContent(/Não há senha/i);
    expect(within(assist).getByRole("link", { name: /Abrir guia da demonstração/i })).toHaveAttribute(
      "href",
      "/demonstracao",
    );
  });

  it("após login o roteiro liga às rotas reais e o menu oferece o guia", async () => {
    config.demoMode = true;
    installApiMock({
      "/api/v1/public/demo-guide": () =>
        new Response(JSON.stringify({ ...DEMO_GUIDE_FALLBACK, source: "live" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
    });
    const user = userEvent.setup();
    await renderApp("/demonstracao", { signedIn: true });
    expect(await screen.findByRole("link", { name: /Abrir Fluxo produtivo/i })).toHaveAttribute(
      "href",
      "/fluxo",
    );
    const { view } = await renderApp("/fluxo", { signedIn: true });
    await user.click(await view.findByRole("button", { name: /Abrir menu do usuário/i }));
    expect(view.getByRole("menuitem", { name: /Guia da demonstração/i })).toHaveAttribute(
      "href",
      "/demonstracao",
    );
  });
});

describe("R028-001 linguagem dos zeros", () => {
  it("entrada fiscal vazia não usa sequência de zeros como pendência principal", () => {
    const text = fiscalSummarySentence({
      total: 0,
      awaiting_match: 0,
      awaiting_check: 0,
      partially_received: 0,
      divergent: 0,
      confirmed: 0,
    });
    expect(text).toMatch(/Nenhuma entrada de mercadoria/i);
    expect(text).not.toMatch(/^0 entrada/);
  });

  it("produtos vazios usam linguagem humana", () => {
    const text = productsSummarySentence({
      total: 0,
      active: 0,
      produced_without_recipe: 0,
      purchased: 0,
      intermediate: 0,
    });
    expect(text).toMatch(/Nenhum produto cadastrado/i);
  });
});
