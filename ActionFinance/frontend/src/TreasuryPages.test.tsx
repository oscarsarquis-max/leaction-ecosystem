import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { AgendaPage, TreasurySummaryPage } from "./TreasuryPages";
import { setSession } from "./session";

const summary = {
  businessDate: "2026-10-16",
  zone: "America/Sao_Paulo",
  periodFrom: "2026-10-01",
  periodTo: "2026-10-16",
  note: "Estas bases não se somam.",
  scopes: {
    obligations: "Situação atual.",
    realized: "Período do realizado.",
    conference: "Lotes confirmados.",
    position: "Data de referência.",
  },
  obligations: { available: false },
  realized: { available: false },
  conference: {
    available: true,
    partialCount: 2,
    divergentCount: 1,
    reviewCount: 3,
    reviewUnit: "OCCURRENCE",
    reviewNote: "ocorrências, não eventos únicos",
    reviewBatches: [{ batchId: "batch-1", fileName: "relatorio.csv", occurrenceCount: 3 }],
    meaning: "livro",
  },
  position: { available: true, known: false, label: "Posição não apurada", guidance: "Consulte as contas.", exclusions: [], accountCount: 0, coveredAccounts: 0 },
};

function session() {
  setSession({
    token: "operator-demo-token",
    mode: "demo",
    actorId: "actor",
    displayName: "Operador",
    permissions: ["titles:read", "financial-accounts:read"],
    companies: [{ id: "company-a", tenantId: "t", name: "Empresa A", active: true, demo: true, permissions: ["titles:read"] }],
    companyId: "company-a",
  });
}

describe("Treasury presentation", () => {
  afterEach(() => {
    setSession(null);
    vi.unstubAllGlobals();
  });

  it("does not show zero while a slice is unavailable and opens each conference set", async () => {
    session();
    const visited: string[] = [];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/treasury/agenda")) {
        return { ok: true, status: 200, text: async () => JSON.stringify({ buckets: [], items: { total: 0, items: [] }, businessDate: "2026-10-16", zone: "America/Sao_Paulo", accountNote: "empresa", notice: null }) };
      }
      return { ok: true, status: 200, text: async () => JSON.stringify(summary) };
    }));
    const user = userEvent.setup();
    render(<TreasurySummaryPage onNavigate={(path) => visited.push(path)} />);
    expect(screen.getByRole("status")).toHaveTextContent("Carregando");
    expect(screen.queryByText("não está disponível nesta sessão")).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("Posição não apurada")).toBeInTheDocument());
    expect(screen.queryByText("R$ 0,00")).not.toBeInTheDocument();
    expect(screen.getByText("As obrigações não estão disponíveis nesta sessão.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Conciliação parcial/ }));
    await user.click(screen.getByRole("button", { name: /Diferença em aberto/ }));
    await user.click(screen.getByRole("button", { name: /relatorio.csv/ }));
    expect(visited).toEqual([
      "/financial-accounts/reconciliation?situacao=PARCIAL",
      "/financial-accounts/reconciliation?situacao=DIVERGENCIA",
      "/financial-accounts/statement/batches/batch-1?revisao=1",
    ]);
  });

  it("keeps the agenda return path and ignores a stale response", async () => {
    session();
    window.history.replaceState(null, "", "/financial-accounts/agenda?faixa=TODAY&direcao=PAYABLE&pagina=2");
    let releaseSecond: (value: string) => void = () => undefined;
    const second = new Promise<string>((resolve) => {
      releaseSecond = resolve;
    });
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("bucket=TODAY")) {
        await second;
      }
      const body = {
        businessDate: "2026-10-16",
        zone: "America/Sao_Paulo",
        bucket: url.includes("bucket=OVERDUE") ? "OVERDUE" : "TODAY",
        direction: "PAYABLE",
        notice: null,
        accountNote: "Conta ainda não definida",
        buckets: [
          { id: "OVERDUE", label: "Vencidos", count: 1, residualMinor: "1000" },
          { id: "TODAY", label: "Hoje", count: 1, residualMinor: "2000" },
          { id: "NEXT_7", label: "Próximos 7 dias", count: 0, residualMinor: "0" },
          { id: "NEXT_30", label: "Do 8º ao 30º dia", count: 0, residualMinor: "0" },
          { id: "UNDATED", label: "Sem data", count: 0, residualMinor: "0" },
        ],
        items: {
          total: 1,
          items: [{ id: "title-1", direction: "PAYABLE", description: "Aluguel", dueDate: "2026-10-16", counterparty: "Imobiliária", residualMinor: "2000", account: "Conta ainda não definida" }],
        },
        page: 2,
        size: 20,
      };
      return { ok: true, status: 200, text: async () => JSON.stringify(body) };
    }));
    const user = userEvent.setup();
    const visited: string[] = [];
    render(<AgendaPage onNavigate={(path) => visited.push(path)} />);
    await user.click(screen.getByRole("tab", { name: /Vencidos/ }));
    await waitFor(() => expect(window.location.search).toContain("faixa=OVERDUE"));
    releaseSecond("late");
    await waitFor(() => expect(screen.getByRole("tab", { name: /Vencidos/ })).toHaveAttribute("aria-selected", "true"));
    expect(screen.getByRole("tab", { name: /Hoje/ })).toHaveAttribute("aria-selected", "false");
    await user.click(screen.getByRole("button", { name: /Imobiliária/ }));
    expect(visited[0]).toContain("/payables/title-1?retorno=");
    expect(decodeURIComponent(visited[0])).toContain("faixa=OVERDUE");
  });

  it("ends loading when the agenda fails and retries", async () => {
    session();
    window.history.replaceState(null, "", "/financial-accounts/agenda");
    let calls = 0;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      calls += 1;
      if (calls === 1) {
        return { ok: false, status: 500, text: async () => "{\"message\":\"falha\"}" };
      }
      return { ok: true, status: 200, text: async () => JSON.stringify(calendarFixture(String(input))) };
    }));
    function Harness() {
      const [path, setPath] = useState("/financial-accounts/agenda");
      return path ? <AgendaPage onNavigate={setPath} /> : null;
    }
    const user = userEvent.setup();
    render(<Harness />);
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Não foi possível consultar a agenda."));
    expect(screen.queryByText("Carregando a agenda…")).not.toBeInTheDocument();
    expect(screen.queryByText("R$ 0,00")).not.toBeInTheDocument();
    expect(screen.getByRole("grid")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
    await waitFor(() => expect(screen.getByText("Nenhum vencimento neste mês.")).toBeInTheDocument());
  });

  it("shows the calendar legend and the full day even when the detail is short", async () => {
    session();
    window.history.replaceState(null, "", "/financial-accounts/agenda");
    const visited: string[] = [];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const body = calendarFixture(String(input));
      const target = body.days.find((day) => day.date === body.selectedDay);
      if (target && !String(input).includes("direction=")) {
        target.receivableCount = 3;
        target.receivableMinor = "120000";
        target.payableCount = 2;
        target.payableMinor = "45000";
        body.monthTotals = { receivableCount: 3, receivableMinor: "120000", payableCount: 2, payableMinor: "45000", differenceMinor: "75000" };
        body.items = {
          total: 5,
          items: [
            { id: "rec-1", direction: "RECEIVABLE", description: "Parcial", dueDate: target.date, counterparty: "Padaria", residualMinor: "40000", partial: true, partialLabel: "Parcialmente recebido", overdue: false, account: "Conta ainda não definida" },
            { id: "pay-1", direction: "PAYABLE", description: "Aluguel", dueDate: target.date, counterparty: "Imobiliária", residualMinor: "22500", partial: false, partialLabel: null, overdue: false, account: "Conta ainda não definida" },
          ],
        };
      }
      return { ok: true, status: 200, text: async () => JSON.stringify(body) };
    }));
    const user = userEvent.setup();
    render(<AgendaPage onNavigate={(path) => visited.push(path)} />);
    await waitFor(() => expect(document.body.textContent).toContain("R$ 1.200,00"));
    expect(document.body.textContent).toContain("R$ 450,00");
    expect(document.body.textContent).toContain("A receber");
    expect(document.body.textContent).toContain("A pagar");
    expect(document.body.textContent).toContain("Vencido");
    expect(screen.getByText(/Diferença prevista/)).toBeInTheDocument();
    expect(screen.getByText(/Não é saldo bancário/)).toBeInTheDocument();
    expect(document.body.textContent).toContain("Parcialmente recebido");
    await user.click(screen.getByRole("button", { name: /Padaria/ }));
    expect(visited[0]).toContain("/receivables/rec-1?retorno=");
    expect(decodeURIComponent(visited[0])).toContain("vista=calendario");
    expect(visited).toHaveLength(1);
  });

  it("discards a late month and keeps an old band link on the list", async () => {
    session();
    const today = businessToday();
    window.history.replaceState(null, "", "/financial-accounts/agenda");
    let releaseLate: (value: string) => void = () => undefined;
    const late = new Promise<string>((resolve) => {
      releaseLate = resolve;
    });
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      const body = calendarFixture(url);
      if (url.includes(`month=${today.slice(0, 7)}`)) {
        await late;
        body.notice = "resposta atrasada";
      } else {
        body.notice = "mês seguinte confirmado";
      }
      return { ok: true, status: 200, text: async () => JSON.stringify(body) };
    }));
    const user = userEvent.setup();
    const { unmount } = render(<AgendaPage onNavigate={() => undefined} />);
    await user.click(screen.getByRole("button", { name: "Mês seguinte" }));
    const next = shiftMonth(today.slice(0, 7), 1);
    await waitFor(() => expect(screen.getByText("mês seguinte confirmado")).toBeInTheDocument());
    expect(screen.getByRole("heading", { level: 2, name: monthLabel(next) })).toBeInTheDocument();
    releaseLate("late");
    await waitFor(() => expect(screen.queryByText("resposta atrasada")).not.toBeInTheDocument());
    expect(screen.getByText("mês seguinte confirmado")).toBeInTheDocument();
    unmount();

    window.history.replaceState(null, "", "/financial-accounts/agenda?faixa=OVERDUE");
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: true,
      status: 200,
      text: async () => JSON.stringify({
        businessDate: today, zone: "America/Sao_Paulo", bucket: "OVERDUE", direction: "ALL", notice: null,
        accountNote: "empresa",
        buckets: [{ id: "OVERDUE", label: "Vencidos", count: 0, residualMinor: "0" }],
        items: { total: 0, items: [] }, page: 0, size: 20,
      }),
    })));
    render(<AgendaPage onNavigate={() => undefined} />);
    await waitFor(() => expect(screen.getByRole("tab", { name: /Vencidos/ })).toBeInTheDocument());
    expect(screen.queryByRole("grid")).not.toBeInTheDocument();
  });

  it("separates a denied calendar from an empty month", async () => {
    session();
    window.history.replaceState(null, "", "/financial-accounts/agenda?vista=calendario");
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false, status: 403, text: async () => "{\"message\":\"negado\"}" })));
    render(<AgendaPage onNavigate={() => undefined} />);
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Esta sessão não consulta a agenda."));
    expect(screen.queryByRole("button", { name: "Tentar novamente" })).not.toBeInTheDocument();
    expect(screen.queryByText("R$ 0,00")).not.toBeInTheDocument();
    expect(screen.queryByText("Nenhum vencimento neste mês.")).not.toBeInTheDocument();
  });
});

const MONTHS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];

function businessToday() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
}

function monthLabel(month: string) {
  const [year, monthNumber] = month.split("-").map(Number);
  const name = MONTHS[monthNumber - 1];
  return `${name.charAt(0).toUpperCase()}${name.slice(1)} de ${year}`;
}

function shiftMonth(month: string, amount: number) {
  const [year, monthNumber] = month.split("-").map(Number);
  const date = new Date(Date.UTC(year, monthNumber - 1 + amount, 1));
  return date.toISOString().slice(0, 7);
}

function monthGrid(month: string) {
  const [year, monthNumber] = month.split("-").map(Number);
  const start = new Date(Date.UTC(year, monthNumber - 1, 1));
  const end = new Date(Date.UTC(year, monthNumber, 0));
  const lead = (start.getUTCDay() + 6) % 7;
  const tail = end.getUTCDay() === 0 ? 0 : 7 - end.getUTCDay();
  const cursor = new Date(start);
  cursor.setUTCDate(cursor.getUTCDate() - lead);
  const last = new Date(end);
  last.setUTCDate(last.getUTCDate() + tail);
  const dates: string[] = [];
  for (let day = new Date(cursor); day <= last; day.setUTCDate(day.getUTCDate() + 1)) {
    dates.push(day.toISOString().slice(0, 10));
  }
  return dates;
}

function calendarFixture(url: string) {
  const params = new URL(url, "http://local").searchParams;
  const today = businessToday();
  const month = params.get("month") || today.slice(0, 7);
  const day = params.get("day") || (today.startsWith(month) ? today : `${month}-01`);
  const direction = params.get("direction") || "ALL";
  const focus = params.get("focus") || "DAY";
  const zero = { receivableCount: 0, receivableMinor: "0", payableCount: 0, payableMinor: "0" };
  return {
    businessDate: today,
    zone: "America/Sao_Paulo",
    month,
    monthLabel: monthLabel(month),
    monthFrom: `${month}-01`,
    monthTo: `${month}-28`,
    coverage: "MONTH_AND_ADJACENT_DAYS",
    monthTotalScope: "Somente vencimentos do mês consultado.",
    direction,
    selectedDay: focus === "DAY" ? day : null,
    focus,
    notice: null as string | null,
    days: monthGrid(month).map((date) => ({
      date,
      inMonth: date.startsWith(month),
      today: date === today,
      overdue: date < today,
      collected: true,
      ...zero,
    })),
    monthTotals: { ...zero, differenceMinor: "0" },
    differenceMeaning: "Não é saldo bancário",
    undated: zero,
    undatedNote: "exige vencimento",
    overdueOutside: zero,
    items: { total: 0, items: [] as Array<Record<string, unknown>> },
    page: Number(params.get("page") || "0"),
    size: 8,
    accountNote: "Conta ainda não definida",
  };
}
