import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PayReceiptsPage } from "./PayReceiptsPage";
import { setSession } from "./session";

const writePerms = ["titles:read", "titles:write"];
const FILTER_KEY = "af.payReceiptFilters";

const item = {
  id: "rec-1",
  companyId: "11111111-1111-1111-1111-111111111111",
  environment: "PRODUCTION",
  transactionId: "tx-abc-12345678",
  orderReference: "PED-aabbccddeeff0011",
  processorReference: "mp-99887766",
  originalStatus: "approved",
  normalizedStatus: "CONFIRMED",
  amountMinor: "1500",
  currency: "BRL",
  amountAbsent: false,
  paidAmountMinor: null,
  paidAmountAbsent: true,
  reviewRequired: false,
  testLabeled: false,
  classification: "INDETERMINATE",
  classificationReason: "sem evidência",
  originCreatedAt: "2026-09-01T10:00:00Z",
  originUpdatedAt: "2026-09-28T12:00:00Z",
  originRevision: "rev-1",
  lastSyncRunId: "run-1",
  lastCorrelationId: "corr-1",
  updatedAt: "2026-09-28T12:00:00Z",
};

const overview = {
  environment: "PRODUCTION",
  homolog: false,
  createsFinancialMovement: false,
  latestRun: {
    id: "run-1",
    environment: "PRODUCTION",
    status: "EMPTY",
    rootCorrelationId: "corr-1",
    spiderMessageId: "msg-1",
    resumeCursor: null,
    pageCount: 1,
    importedCount: 0,
    updatedCount: 0,
    reviewCount: 1,
    lastError: null,
    startedAt: "2026-09-28T12:00:00Z",
    finishedAt: "2026-09-28T12:01:00Z",
    monitorUrl: "https://example.test/monitor",
  },
  items: [],
  reviews: [item],
};

function operator() {
  setSession({
    token: "t",
    mode: "demo",
    actorId: "a",
    displayName: "Operador",
    permissions: writePerms,
    companies: [{ id: item.companyId, tenantId: "t", name: "Loja", active: true, demo: true, permissions: writePerms }],
    companyId: item.companyId,
  });
}

describe("PayReceiptsPage", () => {
  afterEach(() => {
    setSession(null);
    sessionStorage.removeItem(FILTER_KEY);
    vi.unstubAllGlobals();
  });

  it("shows denied state without inventing success", async () => {
    operator();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        status: 403,
        json: async () => ({ code: "FORBIDDEN", message: "negado" }),
        text: async () => JSON.stringify({ code: "FORBIDDEN", message: "negado" }),
      })),
    );
    render(<PayReceiptsPage path="/pay-receipts" onNavigate={() => undefined} />);
    expect(await screen.findByText(/Acesso negado/)).toBeInTheDocument();
    expect(screen.queryByText(/apenas testes/i)).toBeNull();
    expect(screen.queryByText(/Sincronização concluída/)).toBeNull();
  });

  it("separates a finished sync from current pendings and does not treat absence as zero", async () => {
    operator();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/pay-receipts?")) {
          return { ok: true, status: 200, text: async () => JSON.stringify(overview) };
        }
        return { ok: false, status: 404, text: async () => "{}" };
      }),
    );
    render(<PayReceiptsPage path="/pay-receipts" onNavigate={() => undefined} />);
    expect(await screen.findByText(/Sincronização concluída/)).toBeInTheDocument();
    expect(screen.getByText(/nenhum item novo/)).toBeInTheDocument();
    expect(screen.getByText(/1 pendência/)).toBeInTheDocument();
    expect(screen.queryByText(/Empresa autorizada/)).not.toBeInTheDocument();
    expect(screen.queryByText(/não pagina/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/origem comercial/i)).not.toBeInTheDocument();
    expect(screen.getAllByText("Não informado").length).toBeGreaterThan(0);
    expect(screen.queryByText("R$ 0,00")).not.toBeInTheDocument();
    expect(screen.getAllByText("ActionHub Pay").length).toBeGreaterThan(0);
  });

  it("filters the returned collection by reference and opens conference detail", async () => {
    operator();
    const navigate = vi.fn();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/pay-receipts/rec-1")) {
          return {
            ok: true,
            status: 200,
            text: async () => JSON.stringify({ item, history: [], run: overview.latestRun, createsFinancialMovement: false }),
          };
        }
        if (url.includes("/pay-receipts?")) {
          return { ok: true, status: 200, text: async () => JSON.stringify(overview) };
        }
        return { ok: false, status: 404, text: async () => "{}" };
      }),
    );
    const user = userEvent.setup();
    render(<PayReceiptsPage path="/pay-receipts" onNavigate={navigate} />);
    await screen.findByText(/Sincronização concluída/);
    await user.type(screen.getByLabelText("Buscar referência"), "inexistente");
    expect(screen.getByText(/Nenhum registro corresponde/)).toBeInTheDocument();
    await user.clear(screen.getByLabelText("Buscar referência"));
    await user.type(screen.getByLabelText("Buscar referência"), "PED-");
    await user.click(screen.getAllByRole("button", { name: "Abrir" })[0]);
    expect(navigate).toHaveBeenCalledWith("/pay-receipts/rec-1");
  });

  it("shows conference detail without inventing processor or payment date", async () => {
    operator();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/pay-receipts/rec-1")) {
          return {
            ok: true,
            status: 200,
            text: async () =>
              JSON.stringify({
                item,
                history: [
                  {
                    id: "h1",
                    observedAt: "2026-09-28T12:01:00Z",
                    originalStatus: "approved",
                    normalizedStatus: "CONFIRMED",
                    amountMinor: "1500",
                    currency: "BRL",
                    reviewRequired: false,
                    originRevision: "rev-1",
                    correlationId: "corr-1",
                  },
                ],
                run: overview.latestRun,
                createsFinancialMovement: false,
              }),
          };
        }
        if (url.includes("/pay-receipts?")) {
          return { ok: true, status: 200, text: async () => JSON.stringify(overview) };
        }
        return { ok: false, status: 404, text: async () => "{}" };
      }),
    );
    render(<PayReceiptsPage path="/pay-receipts/rec-1" onNavigate={() => undefined} />);
    expect(await screen.findByRole("heading", { name: "Recebimento observado" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Atualizar da origem" })).toBeInTheDocument();
    expect(screen.getByText(/Valor pago não informado/)).toBeInTheDocument();
    expect(screen.getByText(/não este item sozinho/)).toBeInTheDocument();
    expect(screen.queryByText("Mercado Pago")).not.toBeInTheDocument();
    const processor = screen.getByText("Nome do processador").closest("div");
    expect(processor).not.toBeNull();
    expect(within(processor as HTMLElement).getByText("Não informado")).toBeInTheDocument();
    expect(screen.getByText("Loja")).toBeInTheDocument();
  });
});
