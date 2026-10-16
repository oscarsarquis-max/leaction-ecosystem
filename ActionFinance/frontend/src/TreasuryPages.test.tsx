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
    vi.stubGlobal("fetch", vi.fn(async () => {
      calls += 1;
      if (calls === 1) {
        return { ok: false, status: 500, text: async () => "{\"message\":\"falha\"}" };
      }
      return {
        ok: true,
        status: 200,
        text: async () => JSON.stringify({
          businessDate: "2026-10-16", zone: "America/Sao_Paulo", bucket: "OVERDUE", direction: "ALL", notice: null,
          accountNote: "empresa", buckets: [{ id: "OVERDUE", label: "Vencidos", count: 0, residualMinor: "0" }],
          items: { total: 0, items: [] }, page: 0, size: 20,
        }),
      };
    }));
    function Harness() {
      const [path, setPath] = useState("/financial-accounts/agenda");
      return path ? <AgendaPage onNavigate={setPath} /> : null;
    }
    const user = userEvent.setup();
    render(<Harness />);
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Não foi possível consultar a agenda."));
    expect(screen.queryByText("Carregando a agenda…")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
    await waitFor(() => expect(screen.getByText(/Nenhum compromisso exigível/)).toBeInTheDocument());
  });
});
