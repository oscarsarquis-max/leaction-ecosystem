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
    expect(await screen.findByText("Extrato não importado.")).toBeInTheDocument();
    const file = new File(["a,b"], "extrato.csv", { type: "text/csv" });
    await userEvent.upload(screen.getByLabelText("Importar arquivo"), file);
    expect(await screen.findByText(/Moeda USD sem regra de conversão/)).toBeInTheDocument();
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
    const file = new File(["a,b"], "sem-moeda.csv", { type: "text/csv" });
    await userEvent.upload(screen.getByLabelText("Importar arquivo"), file);
    expect(await screen.findByText(/Nenhuma moeda foi presumida/)).toBeInTheDocument();
    expect(screen.getAllByText("10,00 · moeda não informada").length).toBeGreaterThan(0);
    expect(screen.queryByText("R$ 10,00")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirmar linhas selecionadas" })).toBeDisabled();
  });
});

function json(body: unknown) {
  const text = JSON.stringify(body);
  return { ok: true, status: 200, json: async () => body, text: async () => text };
}
