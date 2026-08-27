import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { boardContextFixture, boardFixture, meFixture, ORG_A, ORG_B } from "./api/fixtures";
import { config } from "./config";
import { boardDefaultOperationalDate } from "./format";
import { installApiMock, json } from "./test/fetchMock";
import { stripBoardQueryParams } from "./session/operationalContext";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
  config.demoMode = false;
});

const EST_CENTRAL = "est-1";
const EST_HORIZONTE = "est-horizonte-1";

function boardMock() {
  return {
    "/production/board": (url: URL) => {
      if (url.pathname.endsWith("/context")) {
        if (url.pathname.includes(ORG_B)) {
          return json({
            data: {
              establishments: [{ id: EST_HORIZONTE, code: "HZ", display_name: "Unidade Horizonte" }],
              shifts: boardContextFixture.data.shifts,
              areas: boardContextFixture.data.areas,
            },
          });
        }
        return json(boardContextFixture);
      }
      if (url.pathname.includes(ORG_B)) return json({ data: [] });
      return json({ data: boardFixture });
    },
  };
}

describe("R026-002 troca de organização limpa contexto residual", () => {
  it("stripBoardQueryParams remove establishment_id e filtros do quadro", () => {
    const raw = new URLSearchParams(
      "operational_date=2026-08-24&establishment_id=8f941e25-d6a5-5b27-93aa-cbc4c7fa1ce8&shift=morning&q=x",
    );
    const cleaned = stripBoardQueryParams(raw);
    expect(cleaned.get("establishment_id")).toBeNull();
    expect(cleaned.get("operational_date")).toBeNull();
    expect(cleaned.get("shift")).toBeNull();
    expect(cleaned.get("q")).toBeNull();
  });

  it("fora do demo a âncora não é forçada", () => {
    expect(boardDefaultOperationalDate(false, "2026-08-24", "2026-08-27")).toBe("2026-08-27");
  });

  it("modo demo: Panne → Horizonte → Panne sem contexto residual nem âncora cruzada", async () => {
    config.demoMode = true;
    config.demoAnchorDate = "2026-08-24";

    const boardCalls: { org: string; establishmentId: string | null }[] = [];
    installApiMock({
      "/production/board": (url) => {
        if (url.pathname.endsWith("/context")) {
          return boardMock()["/production/board"](url);
        }
        const org = url.pathname.includes(ORG_B) ? ORG_B : ORG_A;
        boardCalls.push({
          org,
          establishmentId: url.searchParams.get("establishment_id"),
        });
        return boardMock()["/production/board"](url);
      },
    });

    const { view } = await renderApp(
      `/producao?operational_date=2026-08-24&establishment_id=${EST_CENTRAL}&shift=morning`,
    );
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText(/Padaria Central · Manhã · Todas as áreas/)).toBeInTheDocument();
    });
    expect(await screen.findByText("Pão tradicional")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Organização ativa"), ORG_B);

    await waitFor(() => {
      expect(screen.queryByText(/Padaria Central · Manhã/)).not.toBeInTheDocument();
    });
    expect(screen.queryByText(/Sem acesso a este estabelecimento/)).not.toBeInTheDocument();
    expect(screen.queryByText("Pão tradicional")).not.toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Unidade Horizonte · Manhã · Todas as áreas/)).toBeInTheDocument();
    });
    expect(screen.getByText(/Não há ordens para os filtros atuais nesta organização/)).toBeInTheDocument();

    await waitFor(() => {
      const forB = boardCalls.filter((row) => row.org === ORG_B);
      expect(forB.length).toBeGreaterThan(0);
      expect(forB.every((row) => row.establishmentId !== EST_CENTRAL)).toBe(true);
    });

    await user.selectOptions(screen.getByLabelText("Organização ativa"), ORG_A);

    await waitFor(() => {
      expect(screen.getByText(/Padaria Central · Manhã · Todas as áreas/)).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(screen.getByText("Pão tradicional")).toBeInTheDocument();
    });
    expect(screen.queryByText(/Unidade Horizonte · Manhã/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Sem acesso a este estabelecimento/)).not.toBeInTheDocument();

    view.unmount();
  });

  it("fora do demo: troca limpa contexto e pede novo, sem âncora forçada", async () => {
    config.demoMode = false;
    installApiMock(boardMock());

    const { view } = await renderApp(
      `/producao?operational_date=2026-08-24&establishment_id=${EST_CENTRAL}&shift=morning`,
    );
    const user = userEvent.setup();

    expect(await screen.findByRole("heading", { name: "Definir contexto do turno" })).toBeInTheDocument();
    expect(screen.queryByText(/Cenário demonstrativo/)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Usar este contexto" }));
    expect(await screen.findByText(/Padaria Central · Manhã · Todas as áreas/)).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Organização ativa"), ORG_B);

    expect(await screen.findByRole("heading", { name: "Definir contexto do turno" })).toBeInTheDocument();
    expect(screen.queryByText(/Padaria Central · Manhã/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Sem acesso a este estabelecimento/)).not.toBeInTheDocument();
    expect(screen.queryByText("Pão tradicional")).not.toBeInTheDocument();

    const horizonteEst = await screen.findByLabelText("Estabelecimento");
    expect(within(horizonteEst).getByRole("option", { name: "Unidade Horizonte" })).toBeInTheDocument();
    expect(within(horizonteEst).queryByRole("option", { name: "Padaria Central" })).not.toBeInTheDocument();
    expect(screen.queryByText(/Cenário demonstrativo/)).not.toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Organização ativa"), ORG_A);
    expect(await screen.findByRole("heading", { name: "Definir contexto do turno" })).toBeInTheDocument();
    const panneEst = await screen.findByLabelText("Estabelecimento");
    await waitFor(() => {
      expect(within(panneEst).getByRole("option", { name: "Padaria Central" })).toBeInTheDocument();
    });
    expect(within(panneEst).queryByRole("option", { name: "Unidade Horizonte" })).not.toBeInTheDocument();

    view.unmount();
  });

  it("associações de fixture cobrem Panne e segunda org", () => {
    expect(meFixture.associations.some((row) => row.organization_id === ORG_A)).toBe(true);
    expect(meFixture.associations.some((row) => row.organization_id === ORG_B)).toBe(true);
  });
});
