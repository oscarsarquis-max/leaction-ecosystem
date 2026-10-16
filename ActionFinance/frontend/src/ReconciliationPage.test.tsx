import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ReconciliationPage } from "./ReconciliationPage";
import { setSession } from "./session";

const line = {
  lineId: "line-1",
  description: "Rateio de ensaio",
  effectiveOn: "2026-10-02",
  dateLabel: "Data de aprovação",
  direction: "IN",
  eventKind: "SETTLEMENT",
  grossMinor: 1001,
  feeMinor: 0,
  netMinor: 1001,
  category: "Sem categoria",
  initiative: "Não atribuída",
  situation: "SEM_CORRESPONDENCIA",
  version: 0,
  eligible: true,
  reviewRequired: false,
};

function session() {
  setSession({
    token: "operator-demo-token",
    mode: "demo",
    actorId: "actor",
    displayName: "Operador",
    permissions: ["financial-accounts:read", "financial-accounts:write"],
    companies: [{ id: "company-a", tenantId: "t", name: "Empresa A", active: true, demo: true, permissions: ["financial-accounts:write"] }],
    companyId: "company-a",
  });
}

describe("Reconciliation controls", () => {
  afterEach(() => {
    setSession(null);
    vi.unstubAllGlobals();
  });

  it("applies a rateio rule and shows the split without asking for cents", async () => {
    session();
    window.matchMedia = (query: string) => ({ matches: false, media: query, addEventListener: () => undefined, removeEventListener: () => undefined }) as unknown as MediaQueryList;
    const posts: { url: string; body: string }[] = [];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (init?.method === "POST") {
        posts.push({ url, body: String(init.body) });
        return { ok: true, status: 200, text: async () => JSON.stringify({ saved: 1, applicable: 1, fullyReconciled: false }) };
      }
      if (url.includes("/financial-accounts?")) {
        return { ok: true, status: 200, text: async () => JSON.stringify([{ id: "cash", name: "Caixa físico" }]) };
      }
      if (url.includes("/catalogs/categories")) {
        return { ok: true, status: 200, text: async () => JSON.stringify([{ id: "cat-venda", name: "Vendas" }]) };
      }
      if (url.includes("/catalogs/initiatives")) {
        return { ok: true, status: 200, text: async () => JSON.stringify([{ id: "alfa", name: "Ensaio Alfa", code: "ALFA" }, { id: "beta", name: "Ensaio Beta", code: "BETA" }]) };
      }
      if (url.includes("/catalogs/allocation-rules")) {
        return { ok: true, status: 200, text: async () => JSON.stringify([{ id: "rule-1", name: "Meio a meio", versions: [{ id: "version-1", validFrom: "2026-10-01", shares: [{ code: "ALFA", basisPoints: 5000 }, { code: "BETA", basisPoints: 5000 }] }] }]) };
      }
      if (url.includes("/reconciliation/lines/")) {
        return { ok: true, status: 200, text: async () => JSON.stringify({ ...line, shares: [{ name: "Ensaio Alfa", amountMinor: 501, criterion: "Fração inteira em centavos; o resíduo vai para a maior parcela e, no empate, para o menor código." }, { name: "Ensaio Beta", amountMinor: 500, criterion: "Fração inteira em centavos; o resíduo vai para a maior parcela e, no empate, para o menor código." }], decisions: [{ version: 1, reason: "Classificação confirmada pelo operador." }], book: [], history: [], suggestions: [], references: [] }) };
      }
      return { ok: true, status: 200, text: async () => JSON.stringify({ page: 0, size: 8, total: 1, items: [line], coverage: { eligibleCount: 1, documentaryCount: 0, classifiedCount: 0, inBaseMinor: 1001, outBaseMinor: 0, inBookMinor: 0, outBookMinor: 0, inPendingMinor: 1001, outPendingMinor: 0, note: "Cobertura do livro." } }) };
    }));
    const user = userEvent.setup();
    render(<ReconciliationPage />);
    const boxes = await screen.findAllByRole("checkbox", { name: "Selecionar Rateio de ensaio" });
    await user.click(boxes[0]);
    await user.selectOptions(screen.getByLabelText("Categoria"), "cat-venda");
    await user.selectOptions(screen.getByLabelText("Atribuição"), "ALLOCATED");
    await user.selectOptions(screen.getByLabelText("Regra"), "version-1");
    await user.click(screen.getByRole("button", { name: "Confirmar classificação" }));
    await waitFor(() => expect(posts.some((post) => post.body.includes("\"assignment\":\"ALLOCATED\"") && post.body.includes("version-1"))).toBe(true));
    await user.click(screen.getAllByRole("button", { name: "Rateio de ensaio" })[0]);
    expect(await screen.findByText("Ensaio Alfa: R$ 5,01")).toBeTruthy();
    expect(screen.getByText("Ensaio Beta: R$ 5,00")).toBeTruthy();
    expect(screen.getByText("Versão 1. Classificação confirmada pelo operador.")).toBeTruthy();
    expect(screen.getByLabelText("Valor comparado")).toBeTruthy();
    expect(screen.queryByText("Valor em centavos")).toBeNull();
  });
});
