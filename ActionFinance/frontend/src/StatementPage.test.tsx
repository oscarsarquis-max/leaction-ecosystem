import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StatementPage } from "./StatementPage";
import { setSession } from "./session";

const companyId = "11111111-1111-4111-a111-111111111111";
const perms = ["financial-accounts:read", "financial-accounts:write"];

function operator() {
  setSession({
    token: "t",
    mode: "demo",
    actorId: "a",
    displayName: "Operador",
    permissions: perms,
    companies: [{ id: companyId, tenantId: "t", name: "Loja de Pães", active: true, demo: true, permissions: perms }],
    companyId,
  });
}

describe("StatementPage", () => {
  afterEach(() => {
    setSession(null);
    vi.unstubAllGlobals();
  });

  it("shows an empty statement, a partial preview and a long description without turning absence into zero", async () => {
    operator();
    const longText = "Descrição muito longa ".repeat(12);
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/financial-accounts")) {
        return json([{ id: "acc-1", name: "Conta laboratório" }]);
      }
      if (url.includes("/statement-previews") && init?.method === "POST") {
        return json({
          id: "prev-1",
          previewToken: "a".repeat(64),
          profileId: "mp-account-money-csv-1",
          recognized: true,
          fileDiagnostic: null,
          blockReason: null,
          confirmBlocked: false,
          accountEvidenceRequired: false,
          currencyAssumed: false,
          periodFrom: "2026-10-01",
          periodTo: "2026-10-01",
          rows: [
            {
              lineNumber: 2,
              description: longText,
              effectiveOn: "2026-10-01",
              direction: "IN",
              eventKind: "SETTLEMENT",
              netMinor: 8500,
              netAbsent: false,
              eligible: true,
            },
            {
              lineNumber: 3,
              description: "Sem líquido",
              effectiveOn: "2026-10-01",
              direction: "NONE",
              eventKind: "SETTLEMENT",
              netMinor: null,
              netAbsent: true,
              eligible: false,
            },
          ],
          issues: [{ lineNumber: 4, code: "UNSUPPORTED_CURRENCY", message: "Moeda USD sem regra de conversão. Nenhuma conversão foi feita." }],
        });
      }
      if (url.includes("/statement-lines")) {
        return json({
          page: 0, size: 20, total: 0, creditMinor: "0", creditCount: 0, debitMinor: "0", debitCount: 0,
          availabilityCount: 0, amountAbsentCount: 0, items: [], imported: 0,
        });
      }
      if (url.includes("/statement-batches") || url.includes("/statement-links")) {
        return json([]);
      }
      return json({});
    }));

    render(<StatementPage path="/financial-accounts/statement" />);
    expect(await screen.findByRole("heading", { name: "Importe seu primeiro relatório" })).toBeInTheDocument();
    expect(screen.getByText("Conta laboratório")).toBeInTheDocument();
    expect(screen.queryByText("CSV da conta, com vírgula ou ponto e vírgula.")).not.toBeInTheDocument();
    expect(screen.queryByText("Nenhum lote nesta conta.")).not.toBeInTheDocument();
    const file = new File(["a,b"], "extrato.csv", { type: "text/csv" });
    await userEvent.upload(screen.getByLabelText("Importar relatório"), file);
    expect(await screen.findByText(/Preparando prévia|Moeda USD sem regra de conversão/)).toBeInTheDocument();
    expect(screen.queryByText(/CSV de laboratório/)).not.toBeInTheDocument();
    expect(await screen.findByText(/Moeda USD sem regra de conversão/)).toBeInTheDocument();
    expect(screen.getByText(/Todas as linhas são preservadas/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Resolvidas/ })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Identificadas/ })).toBeInTheDocument();
    expect(screen.getAllByText(/Descrição muito longa/).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Não informado").length).toBeGreaterThan(0);
    expect(screen.getAllByText("R$ 85,00").length).toBeGreaterThan(0);
  });

  it("shows a preview without currency as an unconfirmed amount and keeps confirmation blocked", async () => {
    operator();
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/financial-accounts")) {
        return json([{ id: "acc-1", name: "Conta laboratório" }]);
      }
      if (url.includes("/statement-previews") && init?.method === "POST") {
        return json({
          id: "prev-2",
          previewToken: "b".repeat(64),
          profileId: "mp-account-money-csv-1",
          recognized: true,
          fileDiagnostic: "O arquivo não informa a moeda. A prévia permanece disponível, mas a confirmação e a soma financeira ficam bloqueadas. Nenhuma moeda foi presumida.",
          blockReason: null,
          confirmBlocked: true,
          accountEvidenceRequired: false,
          currencyAssumed: true,
          periodFrom: "2026-10-02",
          periodTo: "2026-10-02",
          rows: [{
            lineNumber: 2,
            description: "Sem moeda",
            effectiveOn: "2026-10-02",
            direction: "IN",
            eventKind: "SETTLEMENT",
            netMinor: 1000,
            netAbsent: false,
            eligible: false,
          }],
          issues: [],
        });
      }
      if (url.includes("/statement-lines")) {
        return json({
          page: 0, size: 20, total: 0, creditMinor: "0", creditCount: 0, debitMinor: "0", debitCount: 0,
          availabilityCount: 0, amountAbsentCount: 0, items: [], imported: 0,
        });
      }
      if (url.includes("/statement-batches") || url.includes("/statement-links")) {
        return json([]);
      }
      return json({});
    }));

    render(<StatementPage path="/financial-accounts/statement" />);
    expect(await screen.findByText("Conta laboratório")).toBeInTheDocument();
    const file = new File(["a,b"], "sem-moeda.csv", { type: "text/csv" });
    await userEvent.upload(screen.getByLabelText("Importar relatório"), file);
    expect(await screen.findByText(/Nenhuma moeda foi presumida/)).toBeInTheDocument();
    expect(screen.getAllByText("10,00 · moeda não informada").length).toBeGreaterThan(0);
    expect(screen.queryByText("R$ 10,00")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Importar este relatório" })).toBeDisabled();
  });

  it("explains an empty account list and keeps the file input disabled", async () => {
    operator();
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/financial-accounts")) {
        return json([]);
      }
      return json([]);
    }));
    render(<StatementPage path="/financial-accounts/statement" />);
    expect(await screen.findByRole("heading", { name: "Vamos cadastrar suas contas financeiras" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cadastrar primeira conta" })).toBeInTheDocument();
    expect(screen.getByLabelText("Importar relatório")).toBeDisabled();
    expect(screen.getByText("Cadastre uma conta para importar o relatório.")).toBeInTheDocument();
    expect(screen.queryByText("Nenhum lote nesta conta.")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Data inicial")).not.toBeInTheDocument();
  });

  it("shows a load failure instead of inviting a new account", async () => {
    operator();
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: false,
      status: 500,
      json: async () => ({ message: "Falha ao consultar contas." }),
      text: async () => JSON.stringify({ message: "Falha ao consultar contas." }),
    })));
    render(<StatementPage path="/financial-accounts/statement" />);
    expect(await screen.findByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
    expect(screen.getByText("Falha ao consultar contas.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cadastrar primeira conta" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Importar relatório")).toBeDisabled();
  });

  it("asks which account when there is more than one and does not import without a choice", async () => {
    operator();
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/financial-accounts")) {
        return json([
          { id: "acc-1", name: "Conta Mercado Pago", active: true },
          { id: "acc-2", name: "Caixa", active: true },
        ]);
      }
      return json([]);
    }));
    render(<StatementPage path="/financial-accounts/statement" />);
    expect(await screen.findByText("De qual conta é este relatório?")).toBeInTheDocument();
    expect(screen.getByRole("combobox")).toHaveValue("");
    expect(screen.getByLabelText("Importar relatório")).toBeDisabled();
    expect(screen.getByText("Selecione a conta deste relatório.")).toBeInTheDocument();
  });

  it("does not offer account creation without permission", async () => {
    setSession({
      token: "t",
      mode: "demo",
      actorId: "a",
      displayName: "Consulta",
      permissions: ["financial-accounts:read"],
      companies: [{ id: companyId, tenantId: "t", name: "Loja de Pães", active: true, demo: true, permissions: ["financial-accounts:read"] }],
      companyId,
    });
    vi.stubGlobal("fetch", vi.fn(async () => json([])));
    render(<StatementPage path="/financial-accounts/statement" />);
    expect(await screen.findByText("O cadastro de contas não está disponível para o seu acesso nesta empresa.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cadastrar primeira conta" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Importar relatório")).toBeDisabled();
  });

  it("keeps a failed file selectable again and does not drop a later preview", async () => {
    operator();
    let uploads = 0;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/financial-accounts")) {
        return json([{ id: "acc-1", name: "Conta laboratório", active: true }]);
      }
      if (url.includes("/statement-previews") && init?.method === "POST") {
        uploads += 1;
        if (uploads === 1) {
          return {
            ok: false,
            status: 400,
            json: async () => ({ message: "Arquivo incompatível." }),
            text: async () => JSON.stringify({ message: "Arquivo incompatível." }),
          };
        }
        return json({
          id: "prev-3",
          previewToken: "c".repeat(64),
          profileId: "mp-settlement-v2-csv-1",
          recognized: true,
          fileDiagnostic: null,
          blockReason: null,
          confirmBlocked: false,
          accountEvidenceRequired: false,
          currencyAssumed: false,
          periodFrom: "2026-10-01",
          periodTo: "2026-10-01",
          rows: [],
          issues: [],
        });
      }
      if (url.includes("/statement-lines")) {
        return json({
          page: 0, size: 20, total: 0, creditMinor: "0", creditCount: 0, debitMinor: "0", debitCount: 0,
          availabilityCount: 0, amountAbsentCount: 0, items: [], imported: 0,
        });
      }
      return json([]);
    }));
    render(<StatementPage path="/financial-accounts/statement" />);
    expect(await screen.findByText("Conta laboratório")).toBeInTheDocument();
    const input = screen.getByLabelText("Importar relatório");
    const file = new File(["a,b"], "mesmo.csv", { type: "text/csv" });
    await userEvent.upload(input, file);
    expect(await screen.findByText("Arquivo incompatível.")).toBeInTheDocument();
    await userEvent.upload(input, file);
    expect(await screen.findByRole("heading", { name: "Prévia" })).toBeInTheDocument();
    expect(uploads).toBe(2);
  });

  it("ignores a late account response from the previous company", async () => {
    operator();
    let releaseFirst: (value: unknown) => void = () => undefined;
    const first = new Promise((resolve) => {
      releaseFirst = resolve;
    });
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (!url.includes("/financial-accounts")) {
        return json([]);
      }
      if (url.includes(companyId)) {
        return first;
      }
      return json([{ id: "acc-b", name: "Conta da outra empresa", active: true }]);
    }));
    const view = render(<StatementPage path="/financial-accounts/statement" />);
    const otherId = "22222222-2222-4222-a222-222222222222";
    setSession({
      token: "t",
      mode: "demo",
      actorId: "a",
      displayName: "Operador",
      permissions: perms,
      companies: [
        { id: companyId, tenantId: "t", name: "Loja de Pães", active: true, demo: true, permissions: perms },
        { id: otherId, tenantId: "t", name: "Outra", active: true, demo: true, permissions: perms },
      ],
      companyId: otherId,
    });
    view.rerender(<StatementPage path="/financial-accounts/statement" />);
    expect(await screen.findByText("Conta da outra empresa")).toBeInTheDocument();
    releaseFirst(json([{ id: "acc-a", name: "Conta da empresa anterior", active: true }]));
    await new Promise((resolve) => setTimeout(resolve, 30));
    expect(screen.getByText("Conta da outra empresa")).toBeInTheDocument();
    expect(screen.queryByText("Conta da empresa anterior")).not.toBeInTheDocument();
  });

  it("reads the file before asking which account it belongs to", async () => {
    operator();
    const calls: string[] = [];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      calls.push(`${init?.method ?? "GET"} ${url}`);
      if (url.includes("/financial-accounts")) {
        return json([{ id: "acc-1", name: "Conta Mercado Pago", active: true }]);
      }
      if (url.includes("/identify")) {
        return json({
          id: "prev-1",
          previewToken: "b".repeat(64),
          profileId: "mp-settlement-v2-csv-1",
          recognized: true,
          fileDiagnostic: null,
          blockReason: null,
          confirmBlocked: false,
          accountEvidenceRequired: false,
          currencyAssumed: false,
          periodFrom: "2026-10-01",
          periodTo: "2026-10-14",
          identityConfirmationRequired: false,
          fileAccountRef: "conta-mp-1",
          rows: [{
            lineNumber: 2, description: "Venda", effectiveOn: "2026-10-02", direction: "IN",
            eventKind: "SETTLEMENT", netMinor: 1000, netAbsent: false, eligible: true,
          }],
          issues: [],
        });
      }
      if (url.includes("/statement-previews") && init?.method === "POST") {
        return json({
          id: "prev-1",
          previewToken: "a".repeat(64),
          profileId: "mp-settlement-v2-csv-1",
          recognized: true,
          confirmBlocked: true,
          accountEvidenceRequired: false,
          currencyAssumed: false,
          periodFrom: "2026-10-01",
          periodTo: "2026-10-14",
          identityConfirmationRequired: true,
          fileAccountRef: "conta-mp-1",
          rows: [],
          issues: [],
        });
      }
      if (url.includes("/statement-lines")) {
        return json({
          page: 0, size: 20, total: 0, creditMinor: "0", creditCount: 0, debitMinor: "0", debitCount: 0,
          availabilityCount: 0, amountAbsentCount: 0, items: [], imported: 0, days: [], reviews: [],
        });
      }
      return json([]);
    }));
    render(<StatementPage path="/financial-accounts/statement" />);
    expect(await screen.findByText("Conta Mercado Pago")).toBeInTheDocument();
    expect(screen.queryByText("Referência no relatório")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Gravar vínculo" })).not.toBeInTheDocument();
    const input = screen.getByLabelText("Importar relatório");
    await userEvent.upload(input, new File(["a,b"], "relatorio.csv", { type: "text/csv" }));
    expect(await screen.findByRole("button", { name: "Sim, é esta conta" })).toBeInTheDocument();
    expect(screen.getByText(/Instituição do relatório: Mercado Pago/)).toBeInTheDocument();
    expect(screen.getByText(/Identificação encontrada: conta-mp-1/)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Prévia" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Sim, é esta conta" }));
    expect(await screen.findByRole("heading", { name: "Prévia" })).toBeInTheDocument();
    expect(calls.some((call) => call.includes("/identify"))).toBe(true);
    expect(calls.some((call) => call.includes("/confirm"))).toBe(false);
  });

  it("does not replace an existing link when the file identifies another account", async () => {
    operator();
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/financial-accounts")) {
        return json([
          { id: "acc-1", name: "Conta Mercado Pago", active: true },
          { id: "acc-2", name: "Conta caixa", active: true },
        ]);
      }
      if (url.includes("/statement-previews") && init?.method === "POST") {
        return json({
          id: null,
          previewToken: "",
          recognized: true,
          confirmBlocked: true,
          identityMismatch: true,
          identityConfirmationRequired: false,
          fileAccountRef: "outra-conta",
          periodFrom: "2026-10-01",
          periodTo: "2026-10-02",
          rows: [],
          issues: [],
          accountEvidenceRequired: false,
          currencyAssumed: false,
        });
      }
      if (url.includes("/statement-lines")) {
        return json({
          page: 0, size: 20, total: 0, creditMinor: "0", creditCount: 0, debitMinor: "0", debitCount: 0,
          availabilityCount: 0, amountAbsentCount: 0, items: [], imported: 0,
        });
      }
      return json([]);
    }));
    render(<StatementPage path="/financial-accounts/statement" />);
    const select = await screen.findByLabelText("De qual conta é este relatório?");
    await userEvent.selectOptions(select, "acc-1");
    await userEvent.upload(screen.getByLabelText("Importar relatório"), new File(["a"], "outro.csv", { type: "text/csv" }));
    expect(await screen.findByRole("heading", { name: "Este relatório parece ser de outra conta." })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sim, é esta conta" })).not.toBeInTheDocument();
  });
});

function json(body: unknown) {
  const text = JSON.stringify(body);
  return { ok: true, status: 200, json: async () => body, text: async () => text };
}
