import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { DOSSIER_ID, labelingDossierFixture, meFixture } from "./api/fixtures";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("conformidade e rotulagem", () => {
  it("mostra o domínio e a visão geral sem selo de conformidade", async () => {
    installApiMock();
    const { view } = await renderApp("/conformidade");
    expect(await screen.findByRole("heading", { name: "Conformidade" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Conformidade" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Dossiês" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Avaliações" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Rótulos candidatos" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Fontes e normas" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Cadastros" })).not.toBeInTheDocument();
    expect(document.body.textContent?.toLowerCase()).not.toMatch(/está conforme|declaramos conformidade/);
    expect(await axe(view.container)).toEqual(expect.objectContaining({ violations: [] }));
  });

  it("lista dossiês, vazio, carregamento e erro", async () => {
    installApiMock();
    await renderApp("/conformidade/dossies");
    expect(await screen.findByRole("heading", { name: "Dossiês de rotulagem" })).toBeInTheDocument();
    expect(await screen.findByText(/Proposta técnica para revisão/)).toBeInTheDocument();

    installApiMock({
      "/labeling/dossiers": () => json({ items: [], total: 0 }),
    });
    await renderApp("/conformidade/dossies");
    expect(await screen.findByText("Não há dossiês nesta organização.")).toBeInTheDocument();

    installApiMock({
      "/labeling/dossiers": () => json({ code: "indisponivel", message: "API fora" }, 503),
    });
    await renderApp("/conformidade/dossies");
    expect(await screen.findByRole("alert")).toHaveTextContent("API fora");
  });

  it("cria dossiê guiado a partir da receita", async () => {
    installApiMock();
    await renderApp("/conformidade/dossies/novo");
    const user = userEvent.setup();
    expect(await screen.findByRole("heading", { name: "Novo dossiê" })).toBeInTheDocument();
    expect(screen.getByRole("dialog", { name: "Assistente de rotulagem" })).toBeInTheDocument();
    await user.click(await screen.findByRole("button", { name: "Criar dossiê" }));
    await waitFor(() => {
      expect(vi.mocked(fetch).mock.calls.some(([input]) => String(input).includes("/labeling/dossiers"))).toBe(true);
    });
  });

  it("mostra perfil incompleto, achados, tabela, lupa e advertências", async () => {
    installApiMock();
    const { view } = await renderApp(`/conformidade/dossies/${DOSSIER_ID}`);
    expect(await screen.findByRole("heading", { name: "Dossiê de rotulagem" })).toBeInTheDocument();
    expect(screen.getByText(/Categoria exige confirmação humana/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Tabela nutricional candidata" })).toBeInTheDocument();
    expect(screen.getByText("added_sugars")).toBeInTheDocument();
    expect(screen.getByText("sem evidência")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Lupa candidata" })).toBeInTheDocument();
    expect(screen.getByLabelText("Representação candidata da lupa")).toBeInTheDocument();
    expect(screen.getByText(/Declaração de glúten pendente/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Achados" })).toBeInTheDocument();
    expect(document.body.textContent?.toLowerCase()).not.toMatch(/está conforme|declaramos conformidade/);
    expect(await axe(view.container)).toEqual(expect.objectContaining({ violations: [] }));
  });

  it("compara versões e registra revisão sem certificar", async () => {
    installApiMock();
    await renderApp(`/conformidade/dossies/${DOSSIER_ID}`);
    const user = userEvent.setup();
    await screen.findByRole("heading", { name: "Comparar versões" });
    await user.selectOptions(screen.getByLabelText("Esquerda"), "v1");
    await user.selectOptions(screen.getByLabelText("Direita"), "v2");
    await user.click(screen.getByRole("button", { name: "Comparar" }));
    await waitFor(() => {
      expect(vi.mocked(fetch).mock.calls.some(([input]) => String(input).includes("/compare"))).toBe(true);
    });
    await user.click(screen.getByRole("button", { name: "Registrar revisão humana" }));
    await waitFor(() => {
      expect(vi.mocked(fetch).mock.calls.some(([input]) => String(input).includes("/review"))).toBe(true);
    });
  });

  it("imprime sem alterar dados", async () => {
    const print = vi.fn();
    window.print = print;
    installApiMock();
    await renderApp(`/conformidade/dossies/${DOSSIER_ID}/imprimir`);
    const user = userEvent.setup();
    expect(await screen.findByRole("heading", { name: "Dossiê de rotulagem" })).toBeInTheDocument();
    const writes = vi.mocked(fetch).mock.calls.length;
    await user.click(await screen.findByRole("button", { name: "Imprimir conferência" }));
    expect(print).toHaveBeenCalled();
    const after = vi.mocked(fetch).mock.calls.filter(([, init]) => init && String((init as RequestInit).method ?? "GET") !== "GET");
    expect(after.length).toBe(0);
    expect(vi.mocked(fetch).mock.calls.length).toBeGreaterThanOrEqual(writes);
    expect(document.body.textContent).toContain("Proposta técnica para revisão");
  });

  it("oculta o domínio sem permissão e trata conflito", async () => {
    installApiMock({
      "/api/v1/me": () =>
        json({
          ...meFixture,
          permissions: meFixture.permissions.filter((item) => !item.startsWith("labeling.") && item !== "regulatory.source.read"),
          associations: meFixture.associations.map((item) => ({
            ...item,
            permissions: item.permissions.filter((code) => !code.startsWith("labeling.") && code !== "regulatory.source.read"),
          })),
        }),
    });
    await renderApp("/inicio");
    expect(await screen.findByRole("heading", { name: "Hoje na Panne" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Conformidade" })).not.toBeInTheDocument();

    installApiMock({
      [`/labeling/dossiers/${DOSSIER_ID}/evaluate`]: () =>
        json({ code: "versao_conflito", message: "A versão do recurso mudou. Recarregue e tente de novo." }, 409),
    });
    await renderApp(`/conformidade/dossies/${DOSSIER_ID}`);
    const user = userEvent.setup();
    await screen.findByRole("button", { name: "Executar avaliação" });
    await user.click(screen.getByRole("button", { name: "Executar avaliação" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/versão|estado|mudou/i);
  });

  it("mostra fontes e candidatos sem expressão automática de conformidade", async () => {
    installApiMock();
    await renderApp("/conformidade/fontes");
    expect(await screen.findByText(/RDC nº 429\/2020/)).toBeInTheDocument();
    await renderApp("/conformidade/rotulos");
    expect(await screen.findByText(/Proposta técnica para revisão/)).toBeInTheDocument();
    expect(document.body.textContent?.toLowerCase()).not.toMatch(/está conforme|declaramos conformidade/);
  });

  it("mostra estado de revisão e pendência", async () => {
    installApiMock({
      [`/labeling/dossiers/${DOSSIER_ID}`]: () =>
        json({
          data: {
            ...labelingDossierFixture,
            status: "reviewed",
            current: {
              ...labelingDossierFixture.current,
              reviews: [{ decision: "accepted", notes: "revisão humana" }],
            },
          },
          row_version: 4,
        }),
    });
    await renderApp(`/conformidade/dossies/${DOSSIER_ID}`);
    expect(await screen.findByText(/revisão humana/)).toBeInTheDocument();
    expect(screen.getByText("Lote")).toBeInTheDocument();
  });
});
