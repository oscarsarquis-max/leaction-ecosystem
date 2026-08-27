import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { boardContextFixture, boardFixture, meFixture } from "./api/fixtures";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});

describe("quadro refinado", () => {
  it("define contexto sem IDs e troca visualização", async () => {
    installApiMock();
    await renderApp("/producao");
    const user = userEvent.setup();
    expect(await screen.findByRole("heading", { name: "Definir contexto do turno" })).toBeInTheDocument();
    expect(await screen.findByDisplayValue("Padaria Central")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Usar este contexto" }));
    expect(await screen.findByText(/Padaria Central · Manhã · Todas as áreas/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Fluxo por estado" }));
    await user.click(screen.getByRole("button", { name: "Por estação" }));
    await user.click(screen.getByRole("button", { name: "Lista gerencial" }));
    expect(screen.getByText("Pão tradicional")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Bloqueadas/ })).toBeInTheDocument();
    await user.click(screen.getByText("Pão tradicional"));
    const drawer = await screen.findByRole("dialog", { name: "Ordem selecionada" });
    expect(drawer).toHaveTextContent(/Próxima ação/);
  });

  it("distingue vazio por filtro e limpa contexto ao trocar organização", async () => {
    installApiMock({
      "/production/board": (url) => {
        if (url.pathname.endsWith("/context")) return json(boardContextFixture);
        if (url.searchParams.get("q") === "sem-resultado") return json({ data: [] });
        return json({ data: boardFixture });
      },
    });
    await renderApp("/producao?q=sem-resultado");
    const user = userEvent.setup();
    expect(await screen.findByText(/filtros eliminaram/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Usar este contexto" }));
    expect(
      Object.keys(sessionStorage).some((key) => key.startsWith("panne.operationalContext.")),
    ).toBe(true);
    await user.selectOptions(
      screen.getByLabelText("Organização ativa"),
      meFixture.associations[1].organization_id,
    );
    expect(Object.keys(sessionStorage).filter((key) => key.startsWith("panne.operationalContext."))).toEqual([]);
  });
});
