import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HomePage } from "./HomePage";
import { setSession } from "./session";

const COMPANY = "11111111-1111-1111-1111-111111111111";
const OTHER = "22222222-2222-2222-2222-222222222222";

function session() {
  setSession({
    token: "operator-demo-token",
    mode: "demo",
    actorId: "actor",
    displayName: "Oscar",
    permissions: ["titles:read"],
    companies: [
      { id: COMPANY, tenantId: "t", name: "Loja de Pães", active: true, demo: false, permissions: ["titles:read"] },
      { id: OTHER, tenantId: "t", name: "Outra Empresa", active: true, demo: true, permissions: ["titles:read"] },
    ],
    companyId: COMPANY,
  });
}

function overview(partial = false) {
  return {
    title: "Novembro até hoje",
    rangeLabel: "1 a 10 de novembro",
    sales: { state: "APURADO", minor: 648000 },
    fees: partial ? { state: "NAO_APURADO", minor: null } : { state: "APURADO", minor: 27860 },
    production: { state: "NAO_CONECTADO", minor: null },
    expenses: { state: "APURADO", minor: 119000 },
    leftover: partial
      ? { complete: false, state: "PARCIAL", minor: 529000, missing: ["Taxas", "Custos de produção"] }
      : { complete: false, state: "PARCIAL", minor: 501140, missing: ["Custos de produção"] },
    methods: [
      { label: "Pix", minor: 311000 },
      { label: "Cartão de crédito", minor: 259000 },
    ],
    categories: [{ label: "Aluguel", minor: 119000 }],
    cash: {
      state: "APURADO",
      positionMinor: 421530,
      accountName: "Mercado Pago",
      weeks: [
        { start: "2026-11-09", label: "09/11", minor: 421530, lowest: false },
        { start: "2026-11-16", label: "16/11", minor: 300000, lowest: true },
      ].concat(Array.from({ length: 6 }, (_, index) => ({
        start: `2026-11-${23 + index}`,
        label: "23/11",
        minor: 350000,
        lowest: false,
      }))),
    },
    attention: [
      { tag: "Vence amanhã", text: "Farinha: R$ 860,00 vence em 11/11.", href: "/payables", action: "Ver pagamento" },
    ],
    statementLines: 47,
    reconciliationPending: 3,
    lastPaySyncAt: new Date(Date.now() - 12 * 60 * 1000).toISOString(),
    lastStatementAt: new Date(Date.now() - 12 * 60 * 1000).toISOString(),
    accountName: "Mercado Pago",
  };
}

describe("HomePage", () => {
  afterEach(() => {
    setSession(null);
    vi.unstubAllGlobals();
  });

  it("shows the measured reading and never invents zero for a missing source", async () => {
    session();
    const calls: string[] = [];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      calls.push(url);
      return { ok: true, status: 200, text: async () => JSON.stringify(overview(true)) };
    }));
    render(<HomePage onNavigate={() => undefined} />);
    expect(await screen.findByRole("heading", { name: "Novembro até hoje" })).toBeInTheDocument();
    expect(screen.getByText(/Entraram R\$ 6\.480,00 em vendas/)).toBeInTheDocument();
    expect(screen.getByText(/Ainda faltam as taxas \(chegam com o extrato do banco\) e os custos de produção/)).toBeInTheDocument();
    expect(screen.getAllByText("Não conectado").length).toBeGreaterThan(0);
    expect(screen.queryByText("R$ 0,00")).not.toBeInTheDocument();
    expect(screen.queryByText("Outra Empresa")).not.toBeInTheDocument();
    expect(calls.some((url) => url.includes(COMPANY))).toBe(true);
    expect(calls.some((url) => url.includes(OTHER))).toBe(false);
    expect(screen.getByText("44 de 47 lançamentos já conferidos com as vendas e os pagamentos. Faltam 3 para você decidir.")).toBeInTheDocument();
  });

  it("follows an attention item to the existing screen", async () => {
    session();
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, status: 200, text: async () => JSON.stringify(overview(false)) })));
    const visited: string[] = [];
    const user = userEvent.setup();
    render(<HomePage onNavigate={(to) => visited.push(to)} />);
    await user.click(await screen.findByRole("button", { name: "Ver pagamento" }));
    expect(visited).toEqual(["/payables"]);
    await user.click(screen.getByRole("button", { name: "Revisar 3 lançamentos" }));
    expect(visited).toContain("/financial-accounts/reconciliation");
  });

  it("asks the session company again when the period changes", async () => {
    session();
    const calls: string[] = [];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      calls.push(String(input));
      return { ok: true, status: 200, text: async () => JSON.stringify(overview(false)) };
    }));
    const user = userEvent.setup();
    render(<HomePage onNavigate={() => undefined} />);
    await screen.findByRole("heading", { name: "Leitura do mês" });
    await user.click(screen.getByRole("button", { name: "Semana" }));
    await waitFor(() => expect(calls.some((url) => url.includes("period=week") && url.includes(COMPANY))).toBe(true));
    expect(calls.some((url) => url.includes(OTHER))).toBe(false);
  });

  it("explains a failure in plain words and reads again on Tentar de novo", async () => {
    session();
    let calls = 0;
    vi.stubGlobal("fetch", vi.fn(async () => {
      calls += 1;
      if (calls === 1) {
        return { ok: false, status: 500, text: async () => JSON.stringify({ message: "internal" }) };
      }
      return { ok: true, status: 200, text: async () => JSON.stringify(overview(false)) };
    }));
    const user = userEvent.setup();
    render(<HomePage onNavigate={() => undefined} />);
    expect(await screen.findByText(/Não conseguimos montar a leitura da loja agora/)).toBeInTheDocument();
    expect(screen.queryByText("A leitura da empresa desta sessão.")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Tentar de novo" }));
    expect(await screen.findByRole("heading", { name: "Novembro até hoje" })).toBeInTheDocument();
  });

  it("does not show sales as leftover when nothing was deducted, and points to the first steps", async () => {
    session();
    const real = {
      ...overview(false),
      fees: { state: "NAO_APURADO", minor: null },
      expenses: { state: "NAO_APURADO", minor: null },
      leftover: { complete: false, state: "PARCIAL", minor: 77100, missing: ["Taxas", "Custos de produção", "Despesas"] },
      sales: { state: "APURADO", minor: 77100 },
      cash: { state: "NAO_APURADO", positionMinor: null, accountName: "Mercado Pago", weeks: [], lowest: null },
      attention: [],
      statementLines: 0,
      reconciliationPending: 0,
      lastStatementAt: null,
    };
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, status: 200, text: async () => JSON.stringify(real) })));
    const visited: string[] = [];
    const user = userEvent.setup();
    render(<HomePage onNavigate={(to) => visited.push(to)} />);
    expect(await screen.findByText(/Ainda não dá para dizer quanto sobrou/)).toBeInTheDocument();
    expect(screen.queryByText(/O que já está apurado soma/)).not.toBeInTheDocument();
    const sobrou = screen.getByText("Sobrou").parentElement as HTMLElement;
    expect(sobrou).toHaveTextContent("Não apurado");
    expect(sobrou).not.toHaveTextContent("R$ 771,00");
    expect(screen.queryByText("Nada urgente nesta leitura.")).not.toBeInTheDocument();
    await user.click(screen.getAllByRole("button", { name: "Enviar o extrato" })[0]);
    expect(visited).toContain("/financial-accounts/statement");
    await user.click(screen.getAllByRole("button", { name: "Registrar um pagamento" })[0]);
    expect(visited).toContain("/payables/new");
  });
});
