import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../App";
import { setSession } from "../session";

const emptyList = {
  items: [],
  totalItems: 0,
  page: 0,
  size: 20,
  summary: { openCount: 0, openAmountMinor: "0", overdueCount: 0, overdueAmountMinor: "0", draftCount: 0 },
  businessDate: "2026-09-29",
};

function headerCompanyCodepoints(text: string): number[] {
  return [...text].map((ch) => ch.codePointAt(0) ?? 0);
}

function longSession() {
  setSession({
    token: "operator-demo-token",
    mode: "demo",
    actorId: "actor",
    displayName: "Operadora com nome bastante extenso da demonstração local",
    permissions: ["titles:write", "catalogs:write", "financial-accounts:read", "financial-accounts:write", "settlements:read", "settlements:write", "settlements:reverse"],
    companies: [
      {
        id: "11111111-1111-1111-1111-111111111111",
        tenantId: "t",
        name: "Empresa Cooperativa Agroindustrial do Vale do Rio Longo Ltda",
        active: true,
        demo: true,
        permissions: ["titles:write", "catalogs:write", "financial-accounts:read", "financial-accounts:write", "settlements:read", "settlements:write", "settlements:reverse"],
      },
    ],
    companyId: "11111111-1111-1111-1111-111111111111",
  });
}

function stubLists(receiptSync = true) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/system/info")) {
        return {
          ok: true,
          status: 200,
          json: async () => ({ receiptSyncEnabled: receiptSync }),
          text: async (): Promise<string> => "{}",
        };
      }
      if (url.includes("/treasury/summary")) {
        return {
          ok: true,
          status: 200,
          text: async () =>
            JSON.stringify({
              businessDate: "2026-10-16",
              zone: "America/Sao_Paulo",
              periodFrom: "2026-10-01",
              periodTo: "2026-10-16",
              note: "Estas bases não se somam.",
              obligations: { available: true, receivableOpenMinor: "0", receivableOpenCount: 0, receivableOverdueMinor: "0", receivableOverdueCount: 0, payableOpenMinor: "0", payableOpenCount: 0, payableOverdueMinor: "0", payableOverdueCount: 0, draftCount: 0, draftNote: "Rascunhos entram só como quantidade." },
              realized: { available: true, receivedMinor: "0", receivedCount: 0, paidMinor: "0", paidCount: 0, meaning: "Baixas válidas no Finance." },
              conference: { available: true, eligibleCount: 0, partialCount: 0, divergentCount: 0, reviewCount: 0, meaning: "Conciliação é o livro." },
              position: { available: true, label: "Posição das contas apuradas", knownMinor: "0", coveredAccounts: 0, accountCount: 0, uncovered: [], source: "Livro", limit: "Não é o saldo total da empresa." },
            }),
        };
      }
      if (url.includes("/catalogs/") || url.includes("/financial-accounts")) {
        return { ok: true, status: 200, text: async () => "[]" };
      }
      if (url.includes("/pay-receipts")) {
        return {
          ok: true,
          status: 200,
          text: async () =>
            JSON.stringify({
              environment: "PRODUCTION",
              homolog: false,
              createsFinancialMovement: false,
              latestRun: null,
              items: [],
            }),
        };
      }
      return { ok: true, status: 200, text: async () => JSON.stringify(emptyList) };
    }),
  );
}

describe("AppShell two-level menus", () => {
  afterEach(() => {
    setSession(null);
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    window.history.replaceState(null, "", "/");
  });

  it("renders company display names with their original Unicode letters", async () => {
    setSession({
      token: "operator-demo-token",
      mode: "demo",
      actorId: "actor",
      displayName: "Operador",
      permissions: ["titles:write"],
      companies: [
        {
          id: "624023a4-57e3-415c-b7d0-925ca1acd3b7",
          tenantId: "4f150085-f5f0-4138-80c3-fcf06db15c3c",
          name: "Padaria São João — Ação e Pães",
          active: true,
          demo: true,
          permissions: ["titles:write"],
        },
      ],
      companyId: "624023a4-57e3-415c-b7d0-925ca1acd3b7",
    });
    stubLists();
    render(<App />);
    const company = screen.getByText("Padaria São João — Ação e Pães");
    expect(company.textContent).toBe("Padaria São João — Ação e Pães");
    expect(company.textContent).not.toContain("Ã");
    expect(screen.queryByRole("button", { name: "Tesouraria" })).not.toBeInTheDocument();
    expect(headerCompanyCodepoints(company.textContent ?? "")).toEqual(
      [..."Padaria São João — Ação e Pães"].map((ch) => ch.codePointAt(0)),
    );
  });

  it("keeps long company and user names out of the brand region", async () => {
    longSession();
    stubLists();
    render(<App />);
    const header = document.querySelector("header.top");
    expect(header).not.toBeNull();
    const brand = header?.querySelector(".top-brand");
    const company = screen.getByText("Empresa Cooperativa Agroindustrial do Vale do Rio Longo Ltda");
    const user = screen.getByText("Operadora com nome bastante extenso da demonstração local");
    expect(brand).not.toBeNull();
    expect(brand).not.toContainElement(company);
    expect(brand).not.toContainElement(user);
    expect(screen.getByRole("button", { name: "Sair" })).toBeVisible();
    expect(screen.getByText("Empresa")).toBeVisible();
    expect(header?.querySelector(".top-company")).toContainElement(company);
    expect(header?.querySelector(".top-meta")).toContainElement(user);
  });

  it("exposes the four areas and their functional submenus without Mais", async () => {
    longSession();
    stubLists();
    const user = userEvent.setup();
    render(<App />);
    const areas = screen.getByRole("navigation", { name: "Áreas" });
    expect(within(areas).getAllByRole("button").map((button) => button.getAttribute("aria-label"))).toEqual([
      "Tesouraria",
      "Recebimentos",
      "Pagamentos",
      "Cadastros",
    ]);
    expect(within(areas).getByRole("button", { name: "Recebimentos" })).toHaveAttribute("aria-current", "page");
    expect(within(areas).queryByRole("button", { name: "Mais" })).not.toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: "Principal móvel" })).not.toBeInTheDocument();
    expect(document.querySelector(".more-panel")).toBeNull();
    expect(document.querySelector(".bottom-nav")).toBeNull();
    expect(document.querySelector(".nav-backdrop")).toBeNull();

    const sub = screen.getByRole("navigation", { name: "Nesta área" });
    expect(within(sub).getByRole("button", { name: "A receber" })).toHaveAttribute("aria-current", "page");
    await waitFor(() => expect(within(sub).getByRole("button", { name: "Recebimentos integrados" })).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: "Registrar recebível" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Registrar pagável" })).not.toBeInTheDocument();

    await user.click(within(areas).getByRole("button", { name: "Pagamentos" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "Contas a pagar" })).toHaveFocus());
    expect(within(screen.getByRole("navigation", { name: "Nesta área" })).getByRole("button", { name: "A pagar" })).toHaveAttribute(
      "aria-current",
      "page",
    );

    await user.click(screen.getByRole("button", { name: "Tesouraria" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "Resumo da tesouraria" })).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Resumo" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("button", { name: "Contas" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Extratos" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Conciliação" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Agenda" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Cadastros" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "Clientes e fornecedores" })).toBeInTheDocument());
    expect(window.location.pathname).toBe("/catalogs/counterparties");
    await user.click(screen.getByRole("button", { name: "Categorias" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "Categorias" })).toBeInTheDocument());
    expect(window.location.pathname).toBe("/catalogs/categories");
  });

  it("rebuilds both bars from a deep link and sends the main menu to the first submenu", async () => {
    longSession();
    stubLists();
    window.history.replaceState(null, "", "/pay-receipts");
    const user = userEvent.setup();
    render(<App />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Recebimentos integrados" })).toHaveAttribute("aria-current", "page"));
    expect(screen.getByRole("button", { name: "Recebimentos" })).toHaveAttribute("aria-current", "page");
    await user.click(screen.getByRole("button", { name: "Recebimentos" }));
    await waitFor(() => expect(window.location.pathname).toBe("/receivables"));
    expect(screen.getByRole("button", { name: "A receber" })).toHaveAttribute("aria-current", "page");
  });

  it("forwards /catalogs to clientes e fornecedores", async () => {
    longSession();
    stubLists();
    window.history.replaceState(null, "", "/catalogs");
    render(<App />);
    await waitFor(() => expect(window.location.pathname).toBe("/catalogs/counterparties"));
    expect(await screen.findByRole("heading", { name: "Clientes e fornecedores" })).toBeInTheDocument();
  });

  it("keeps the form and useful focus when dirty navigation is refused", async () => {
    longSession();
    stubLists();
    vi.spyOn(window, "confirm").mockReturnValue(false);
    window.history.replaceState(null, "", "/receivables/new");
    const user = userEvent.setup();
    render(<App />);
    await user.type(screen.getByLabelText(/Descrição/), "Rascunho sujo");
    await user.click(screen.getByRole("button", { name: "Pagamentos" }));
    expect(screen.getByRole("heading", { name: "Nova conta a receber" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Contas a pagar" })).not.toBeInTheDocument();
    expect(document.activeElement).not.toBe(screen.getByRole("heading", { name: "Nova conta a receber" }));
  });

  it("leaves a dirty form when the operator confirms", async () => {
    longSession();
    stubLists();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    window.history.replaceState(null, "", "/receivables/new");
    const user = userEvent.setup();
    render(<App />);
    await user.type(screen.getByLabelText(/Descrição/), "Rascunho sujo");
    await user.click(screen.getByRole("button", { name: "Pagamentos" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "Contas a pagar" })).toBeInTheDocument());
    expect(window.location.pathname).toBe("/payables");
  });

  it("toggles title filters without clearing the chosen extras", async () => {
    longSession();
    stubLists();
    const user = userEvent.setup();
    render(<App />);
    const overdue = await screen.findByRole("checkbox", { name: "Só vencidos" });
    await user.click(overdue);
    expect(overdue).toBeChecked();
    await user.click(screen.getByRole("button", { name: "Ocultar filtros" }));
    expect(screen.queryByRole("checkbox", { name: "Só vencidos" })).not.toBeInTheDocument();
    expect(screen.getByText(/Filtros ativos:.*Só vencidos/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Filtros (ativos)" }));
    expect(screen.getByRole("checkbox", { name: "Só vencidos" })).toBeChecked();
  });
});
