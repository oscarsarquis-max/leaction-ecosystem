import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import * as api from "./api";
import { App } from "./App";
import { setSession, setSessionNotice } from "./session";

const writePerms = ["titles:write", "catalogs:write", "financial-accounts:read", "financial-accounts:write", "settlements:read", "settlements:write", "settlements:reverse"];
const company = { id: "11111111-1111-1111-1111-111111111111", tenantId: "t", name: "Padaria Demo", active: true, demo: true, permissions: writePerms };
const emptyTitleList = {
  items: [],
  totalItems: 0,
  page: 0,
  size: 20,
  summary: { openCount: 0, openAmountMinor: "0", overdueCount: 0, overdueAmountMinor: "0", draftCount: 0 },
  businessDate: "2026-09-29",
};

async function chooseAccount(user: ReturnType<typeof userEvent.setup>, name = "Conta Demo") {
  await user.click(await screen.findByRole("combobox", { name: "Conta financeira" }));
  await user.click(await screen.findByRole("option", { name }));
}

function operatorSession() {
  setSession({
    token: "operator-demo-token",
    mode: "demo",
    actorId: "actor",
    displayName: "Operador A",
    permissions: ["titles:write", "catalogs:write", "financial-accounts:read", "financial-accounts:write", "settlements:read", "settlements:write", "settlements:reverse"],
    companies: [company],
    companyId: company.id,
  });
}

describe("App identification and journeys", () => {
  afterEach(() => {
    setSession(null);
    setSessionNotice(null);
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    window.history.replaceState(null, "", "/");
    sessionStorage.removeItem("af.returnPath");
    Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" });
  });

  it("opens production access without an intermediate Enter click", async () => {
    const start = vi.spyOn(api, "startOidcLogin").mockImplementation(() => undefined);
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/api/v1/system/info")) {
          return {
            ok: true,
            status: 200,
            json: async () => ({ accessMode: "OIDC" }),
            text: async () => JSON.stringify({ accessMode: "OIDC" }),
          };
        }
        return { ok: false, status: 401, text: async () => "{}", json: async () => ({}) };
      }),
    );
    render(<App />);
    expect(await screen.findByText(/Abrindo o acesso autorizado/)).toBeInTheDocument();
    expect(screen.queryByLabelText("Token local")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Entrar" })).not.toBeInTheDocument();
    await waitFor(() => expect(start).toHaveBeenCalled());
  });

  it("returns to the requested internal page after OIDC restore", async () => {
    window.history.replaceState(null, "", "/");
    sessionStorage.setItem("af.returnPath", "/pay-receipts");
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/api/v1/system/info")) {
          return {
            ok: true,
            status: 200,
            json: async () => ({ accessMode: "OIDC" }),
            text: async () => JSON.stringify({ accessMode: "OIDC" }),
          };
        }
        if (url.includes("/api/v1/access/me")) {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              actorId: "a",
              displayName: "Operador A",
              accessState: "READY",
              permissions: ["titles:read"],
              authorizedCompanies: [{ id: company.id, tenantId: "t", name: "Loja demonstração", active: true, demo: true }],
              authorizedCompanyDetails: [{ id: company.id, tenantId: "t", name: "Loja demonstração", active: true, demo: true, permissions: ["titles:read"] }],
            }),
            text: async () => "{}",
          };
        }
        if (url.includes("/csrf")) {
          return { ok: true, status: 200, json: async () => ({ token: "t", headerName: "X-XSRF-TOKEN" }), text: async () => "{}" };
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
                reviews: [],
              }),
          };
        }
        return { ok: true, status: 200, text: async () => "[]", json: async () => [] };
      }),
    );
    render(<App />);
    await waitFor(() => expect(window.location.pathname).toBe("/pay-receipts"));
    expect(sessionStorage.getItem("af.returnPath")).toBeNull();
  });

  it("shows an explicit re-enter after a failed login without looping", async () => {
    window.history.replaceState(null, "", "/?login=failed");
    const start = vi.spyOn(api, "startOidcLogin").mockImplementation(() => undefined);
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/api/v1/system/info")) {
          return {
            ok: true,
            status: 200,
            json: async () => ({ accessMode: "OIDC" }),
            text: async () => JSON.stringify({ accessMode: "OIDC" }),
          };
        }
        return { ok: false, status: 401, text: async () => "{}", json: async () => ({}) };
      }),
    );
    render(<App />);
    expect(await screen.findByRole("button", { name: "Entrar novamente" })).toBeInTheDocument();
    expect(start).not.toHaveBeenCalled();
  });

  it("sends Sair through AF logout then Cognito without an intermediate re-enter", async () => {
    const user = userEvent.setup();
    setSession({
      mode: "oidc",
      actorId: "actor",
      displayName: "Oscar Sarquis",
      accessState: "READY",
      permissions: writePerms,
      companies: [{ ...company, name: "Loja de Pães", demo: false }],
      companyId: company.id,
    });
    window.history.replaceState(null, "", "/receivables");
    sessionStorage.setItem("af.returnPath", "/receivables");
    const start = vi.spyOn(api, "startOidcLogin").mockImplementation(() => undefined);
    const provider = vi.spyOn(api, "continueToProviderLogout").mockImplementation(() => undefined);
    const logoutCalls: Array<{ method?: string; accept?: string; csrf?: boolean }> = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        const method = init?.method ?? "GET";
        const headers = (init?.headers ?? {}) as Record<string, string>;
        if (url.includes("/api/v1/system/info")) {
          return {
            ok: true,
            status: 200,
            json: async () => ({ accessMode: "OIDC", receiptSyncEnabled: true }),
            text: async () => "{}",
          };
        }
        if (url.includes("/csrf")) {
          return { ok: true, status: 200, json: async () => ({ token: "t", headerName: "X-XSRF-TOKEN" }), text: async () => "{}" };
        }
        if (url.includes("/logout")) {
          logoutCalls.push({
            method,
            accept: headers.Accept ?? headers.accept,
            csrf: Boolean(headers["X-XSRF-TOKEN"]),
          });
          return { status: 204, ok: true, text: async () => "", json: async () => ({}) };
        }
        if (url.includes("/access/me")) {
          return { ok: false, status: 401, text: async () => "{}", json: async () => ({}) };
        }
        if (url.includes("/catalogs/") || url.includes("/pay-receipts") || url.includes("/financial-accounts")) {
          return { ok: true, status: 200, text: async () => "[]", json: async () => [] };
        }
        if (url.includes("/receivables") || url.includes("/payables")) {
          return { ok: true, status: 200, text: async () => JSON.stringify(emptyTitleList), json: async () => emptyTitleList };
        }
        return { ok: true, status: 200, text: async () => "{}", json: async () => ({}) };
      }),
    );
    render(<App />);
    expect(await screen.findByText("Oscar Sarquis")).toBeInTheDocument();
    expect(screen.getByText("Loja de Pães")).toBeInTheDocument();
    const sair = screen.getByRole("button", { name: "Sair" });
    expect(sair).toHaveAttribute("type", "button");
    await user.click(sair);
    await waitFor(() => expect(provider).toHaveBeenCalled());
    expect(screen.queryByRole("button", { name: "Entrar novamente" })).not.toBeInTheDocument();
    expect(screen.queryByText(/Você saiu do ActionFinance/)).not.toBeInTheDocument();
    expect(sessionStorage.getItem("af.returnPath")).toBeNull();
    expect(logoutCalls).toEqual([{ method: "POST", accept: "application/json", csrf: true }]);
    expect(start).not.toHaveBeenCalled();
    expect(screen.queryByRole("heading", { name: "Contas a receber" })).not.toBeInTheDocument();
  });

  it("continues a logout=1 bookmark to Cognito instead of showing a local re-enter", async () => {
    window.history.replaceState(null, "", "/?logout=1");
    const start = vi.spyOn(api, "startOidcLogin").mockImplementation(() => undefined);
    const provider = vi.spyOn(api, "continueToProviderLogout").mockImplementation(() => undefined);
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/api/v1/system/info")) {
          return {
            ok: true,
            status: 200,
            json: async () => ({ accessMode: "OIDC" }),
            text: async () => JSON.stringify({ accessMode: "OIDC" }),
          };
        }
        return { ok: false, status: 401, text: async () => "{}", json: async () => ({}) };
      }),
    );
    render(<App />);
    await waitFor(() => expect(provider).toHaveBeenCalled());
    expect(screen.queryByRole("button", { name: "Entrar novamente" })).not.toBeInTheDocument();
    expect(start).not.toHaveBeenCalled();
  });

  it("keeps a dirty form when Sair is refused", async () => {
    const user = userEvent.setup();
    operatorSession();
    window.history.replaceState(null, "", "/receivables/new");
    vi.spyOn(window, "confirm").mockReturnValue(false);
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/catalogs/") || url.includes("/financial-accounts") || url.includes("/settlements")) {
          return { ok: true, status: 200, text: async () => "[]", json: async () => [] };
        }
        return { ok: true, status: 200, text: async () => "{}", json: async () => ({}) };
      }),
    );
    const signOut = vi.spyOn(api, "signOut");
    render(<App />);
    await user.type(screen.getByLabelText(/Descrição/), "Rascunho sujo");
    await user.click(screen.getByRole("button", { name: "Sair" }));
    expect(window.confirm).toHaveBeenCalled();
    expect(signOut).not.toHaveBeenCalled();
    expect(screen.getByRole("heading", { name: "Nova conta a receber" })).toBeInTheDocument();
    expect(screen.getByDisplayValue("Rascunho sujo")).toBeInTheDocument();
  });

  it("activates Sair from the keyboard and shows processing", async () => {
    const user = userEvent.setup();
    setSession({
      mode: "oidc",
      actorId: "actor",
      displayName: "Oscar Sarquis",
      accessState: "READY",
      permissions: writePerms,
      companies: [company],
      companyId: company.id,
    });
    window.history.replaceState(null, "", "/receivables");
    let releaseLogout: () => void = () => undefined;
    const logoutGate = new Promise<void>((resolve) => {
      releaseLogout = resolve;
    });
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/api/v1/system/info")) {
          return { ok: true, status: 200, json: async () => ({ accessMode: "OIDC" }), text: async () => "{}" };
        }
        if (url.includes("/csrf")) {
          return { ok: true, status: 200, json: async () => ({ token: "t", headerName: "X-XSRF-TOKEN" }), text: async () => "{}" };
        }
        if (url.includes("/logout")) {
          await logoutGate;
          return { status: 204, ok: true, text: async () => "", json: async () => ({}) };
        }
        if (url.includes("/receivables") || url.includes("/payables")) {
          return { ok: true, status: 200, text: async () => JSON.stringify(emptyTitleList), json: async () => emptyTitleList };
        }
        return { ok: true, status: 200, text: async () => "[]", json: async () => [] };
      }),
    );
    const provider = vi.spyOn(api, "continueToProviderLogout").mockImplementation(() => undefined);
    render(<App />);
    const sair = await screen.findByRole("button", { name: "Sair" });
    sair.focus();
    await user.keyboard("{Enter}");
    expect(await screen.findByRole("button", { name: "Saindo…" })).toBeDisabled();
    releaseLogout();
    await waitFor(() => expect(provider).toHaveBeenCalled());
    expect(screen.queryByRole("button", { name: "Entrar novamente" })).not.toBeInTheDocument();
  });

  it("revalidates an oidc tab and does not keep stale financial access after 401", async () => {
    setSession({
      mode: "oidc",
      actorId: "actor",
      displayName: "Oscar Sarquis",
      accessState: "READY",
      permissions: writePerms,
      companies: [company],
      companyId: company.id,
    });
    window.history.replaceState(null, "", "/receivables");
    const start = vi.spyOn(api, "startOidcLogin").mockImplementation(() => undefined);
    const provider = vi.spyOn(api, "continueToProviderLogout").mockImplementation(() => undefined);
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/api/v1/system/info")) {
          return { ok: true, status: 200, json: async () => ({ accessMode: "OIDC" }), text: async () => "{}" };
        }
        if (url.includes("/access/me")) {
          return { ok: false, status: 401, text: async () => "{}", json: async () => ({}) };
        }
        if (url.includes("/receivables") || url.includes("/payables")) {
          return { ok: true, status: 200, text: async () => JSON.stringify(emptyTitleList), json: async () => emptyTitleList };
        }
        return { ok: true, status: 200, text: async () => "[]", json: async () => [] };
      }),
    );
    render(<App />);
    expect(await screen.findByText("Oscar Sarquis")).toBeInTheDocument();
    Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" });
    document.dispatchEvent(new Event("visibilitychange"));
    await waitFor(() => expect(provider).toHaveBeenCalled());
    expect(start).not.toHaveBeenCalled();
  });

  it("asks for a local token without storing it", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn());
    render(<App />);
    expect(await screen.findByText(/Demonstração local/)).toBeInTheDocument();
    await user.type(screen.getByLabelText("Token local"), "secret-token-value");
    expect(window.localStorage.length).toBe(0);
    expect(JSON.stringify(window.sessionStorage)).not.toMatch(/secret-token-value/);
  });

  it("registers an edited draft with PATCH register=true and frozen key", async () => {
    operatorSession();
    window.history.replaceState(null, "", "/receivables/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/edit");
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/catalogs/") || url.includes("/settlements")) {
        return { ok: true, status: 200, text: async () => "[]" };
      }
      if (url.includes("/receivables/aaaaaaaa") && (!init || !init.method || init.method === "GET")) {
        return {
          ok: true,
          status: 200,
          text: async () =>
            JSON.stringify({
              id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
              reference: "REC-aaaa",
              direction: "RECEIVABLE",
              status: "DRAFT",
              description: "Rascunho incompleto",
              counterpartyId: null,
              counterpartyName: null,
              counterpartyActive: true,
              categoryId: null,
              categoryName: null,
              categoryActive: true,
              amountMinor: null,
              currency: "BRL",
              competenceDate: null,
              dueDate: null,
              overdue: false,
              originKind: "MANUAL",
              sourceReference: null,
              version: 1,
              demoCompany: true,
              businessDate: "2026-09-15",
            }),
        };
      }
      if (init?.method === "PATCH") {
        return {
          ok: true,
          status: 200,
          text: async () =>
            JSON.stringify({
              id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
              reference: "REC-aaaa",
              direction: "RECEIVABLE",
              status: "OPEN",
              description: "Rascunho completo",
              counterpartyId: null,
              counterpartyName: null,
              counterpartyActive: true,
              categoryId: null,
              categoryName: null,
              categoryActive: true,
              amountMinor: "2500",
              currency: "BRL",
              competenceDate: "2026-09-15",
              dueDate: "2026-09-20",
              overdue: false,
              originKind: "MANUAL",
              sourceReference: null,
              version: 2,
              demoCompany: true,
              businessDate: "2026-09-15",
            }),
        };
      }
      return { ok: true, status: 200, text: async () => "{}" };
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);
    const description = await screen.findByDisplayValue("Rascunho incompleto");
    await user.clear(description);
    await user.type(description, "Rascunho completo");
    await user.click(screen.getByRole("button", { name: "Registrar" }));
    await waitFor(() => {
      const patch = fetchMock.mock.calls.find((call) => String(call[1]?.method) === "PATCH");
      expect(patch).toBeDefined();
      expect(String(patch?.[0])).toContain("register=true");
      expect((patch?.[1]?.headers as Record<string, string>)["Idempotency-Key"]).toBeTruthy();
    });
  });

  it("retries a create with the same key after a lost transport response", async () => {
    operatorSession();
    window.history.replaceState(null, "", "/receivables/new");
    const created = {
      id: "bbbbbbbb-bbbb-cccc-dddd-eeeeeeeeeeee",
      reference: "REC-bbbb",
      direction: "RECEIVABLE",
      status: "DRAFT",
      description: "Único",
      counterpartyId: null,
      counterpartyName: null,
      counterpartyActive: true,
      categoryId: null,
      categoryName: null,
      categoryActive: true,
      amountMinor: null,
      currency: "BRL",
      competenceDate: null,
      dueDate: null,
      overdue: false,
      originKind: "MANUAL",
      sourceReference: null,
      version: 1,
      demoCompany: true,
      businessDate: "2026-09-15",
    };
    let posts = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/catalogs/") || url.includes("/settlements")) {
        return { ok: true, status: 200, text: async () => "[]" };
      }
      if (init?.method === "POST" && url.includes("/receivables")) {
        posts += 1;
        if (posts === 1) {
          throw new TypeError("Failed to fetch");
        }
        return { ok: true, status: 200, text: async () => JSON.stringify(created) };
      }
      if (url.includes("/history")) {
        return { ok: true, status: 200, text: async () => JSON.stringify({ items: [{ id: "h1", action: "CREATED" }] }) };
      }
      return { ok: true, status: 200, text: async () => JSON.stringify(created) };
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);
    await user.type(await screen.findByLabelText(/Descrição/), "Único");
    await user.click(screen.getByRole("button", { name: "Salvar rascunho" }));
    expect(await screen.findByText(/repetição reenvia a mesma operação/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Tentar novamente a operação pendente" }));
    await waitFor(() => expect(posts).toBe(2));
    const postCalls = fetchMock.mock.calls.filter((call) => call[1]?.method === "POST" && String(call[0]).includes("/receivables") && !String(call[0]).includes("confirm"));
    expect(postCalls).toHaveLength(2);
    expect((postCalls[0][1]?.headers as Record<string, string>)["Idempotency-Key"]).toBe(
      (postCalls[1][1]?.headers as Record<string, string>)["Idempotency-Key"],
    );
    expect(postCalls[0][1]?.body).toBe(postCalls[1][1]?.body);
    expect(await screen.findByRole("heading", { level: 1, name: "Único" })).toBeInTheDocument();
  });

  it("allows field correction after a definitive validation error", async () => {
    operatorSession();
    window.history.replaceState(null, "", "/receivables/new");
    const keys: string[] = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).includes("/catalogs/") || String(input).includes("/settlements")) {
        return { ok: true, status: 200, text: async () => "[]" };
      }
      if (init?.method === "POST") {
        keys.push((init.headers as Record<string, string>)["Idempotency-Key"]);
        if (keys.length === 1) {
          return {
            ok: false,
            status: 400,
            text: async () => JSON.stringify({ message: "Dados inválidos.", fields: { description: "Descrição é obrigatória e deve ter até 200 caracteres." } }),
          };
        }
        return {
          ok: true,
          status: 200,
          text: async () =>
            JSON.stringify({
              id: "cccccccc-cccc-dddd-eeee-ffffffffffff",
              reference: "REC-cccc",
              direction: "RECEIVABLE",
              status: "DRAFT",
              description: "Corrigido",
              version: 1,
              demoCompany: true,
              businessDate: "2026-09-15",
            }),
        };
      }
      return { ok: true, status: 200, text: async () => JSON.stringify({ items: [] }) };
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);
    const description = await screen.findByLabelText(/Descrição/);
    await user.type(description, "Primeiro");
    await user.click(screen.getByRole("button", { name: "Salvar rascunho" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Dados inválidos.");
    await user.clear(description);
    await user.type(description, "Corrigido");
    await user.click(screen.getByRole("button", { name: "Salvar rascunho" }));
    await waitFor(() => expect(keys).toHaveLength(2));
    expect(keys[0]).not.toBe(keys[1]);
  });

  it("keeps confirm and cancel keys after a lost transport response", async () => {
    operatorSession();
    window.history.replaceState(null, "", "/receivables/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee");
    const draft = {
      id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
      reference: "REC-aaaa",
      direction: "RECEIVABLE",
      status: "DRAFT",
      description: "Rascunho",
      counterpartyId: null,
      counterpartyName: null,
      counterpartyActive: true,
      categoryId: null,
      categoryName: null,
      categoryActive: true,
      amountMinor: "1000",
      currency: "BRL",
      competenceDate: "2026-09-15",
      dueDate: "2026-09-20",
      overdue: false,
      originKind: "MANUAL",
      sourceReference: null,
      version: 1,
      demoCompany: true,
      businessDate: "2026-09-15",
    };
    const confirmKeys: string[] = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/history")) {
        return { ok: true, status: 200, text: async () => JSON.stringify({ items: [] }) };
      }
      if (url.includes("/settlements")) {
        return { ok: true, status: 200, text: async () => "[]" };
      }
      if (url.includes("/confirm")) {
        confirmKeys.push((init?.headers as Record<string, string>)["Idempotency-Key"]);
        if (confirmKeys.length === 1) {
          throw new TypeError("Failed to fetch");
        }
        return { ok: true, status: 200, text: async () => JSON.stringify({ ...draft, status: "OPEN", version: 2 }) };
      }
      return { ok: true, status: 200, text: async () => JSON.stringify(draft) };
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);
    await user.click(await screen.findByRole("button", { name: "Confirmar" }));
    expect(await screen.findByText(/repetir a mesma operação/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Confirmar" }));
    await waitFor(() => expect(confirmKeys).toHaveLength(2));
    expect(confirmKeys[0]).toBe(confirmKeys[1]);
  });

  it("registers a settlement without implying money was sent", async () => {
    operatorSession();
    window.history.replaceState(null, "", "/receivables/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/settlements/new");
    const title = {
      id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
      reference: "REC-aaaa",
      direction: "RECEIVABLE",
      status: "OPEN",
      description: "Recebível 150",
      counterpartyId: "cp",
      counterpartyName: "Cliente Balcão",
      counterpartyActive: true,
      categoryId: "cat",
      categoryName: "Vendas",
      categoryActive: true,
      amountMinor: "15000",
      settledAmountMinor: "0",
      outstandingAmountMinor: "15000",
      settlementStatus: "UNSETTLED",
      currency: "BRL",
      competenceDate: "2026-09-15",
      dueDate: "2026-09-20",
      overdue: false,
      originKind: "MANUAL",
      sourceReference: null,
      version: 1,
      demoCompany: true,
      businessDate: "2026-09-15",
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/history")) {
        return { ok: true, status: 200, text: async () => JSON.stringify({ items: [] }) };
      }
      if (url.includes("/settlements") && (!init || !init.method || init.method === "GET")) {
        return { ok: true, status: 200, text: async () => "[]" };
      }
      if (url.includes("/financial-accounts") && (!init || !init.method || init.method === "GET")) {
        return {
          ok: true,
          status: 200,
          text: async () =>
            JSON.stringify([{ id: "acc-1", code: "CTA-1", name: "Conta Demo", type: "BANK", currency: "BRL", active: true, openedOn: "2026-09-01", currentBalanceMinor: "0", companyName: "Padaria", version: 1 }]),
        };
      }
      if (url.includes("/settlements") && init?.method === "POST") {
        return {
          ok: true,
          status: 200,
          text: async () => JSON.stringify({ id: "set-1", titleOutstandingAmountMinor: "10000", titleVersion: 2 }),
        };
      }
      return { ok: true, status: 200, text: async () => JSON.stringify(title) };
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);
    expect(await screen.findByText(/Não envia nem movimenta dinheiro/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Registrar recebimento" })).toBeInTheDocument();
    expect(screen.queryByText(/Pix enviado|Pagamento executado/i)).not.toBeInTheDocument();
    await chooseAccount(user);
    await user.selectOptions(screen.getByLabelText("Meio"), "PIX");
    await user.click(screen.getByRole("button", { name: "Registrar recebimento" }));
    await waitFor(() => {
      const post = fetchMock.mock.calls.find((call) => call[1]?.method === "POST" && String(call[0]).includes("/settlements"));
      expect(post).toBeDefined();
    });
  });

  it("hides write actions for a viewer without titles:write", async () => {
    setSession({
      token: "viewer-demo-token",
      mode: "demo",
      actorId: "viewer",
      displayName: "Leitor A",
      permissions: ["titles:read", "financial-accounts:read"],
      companies: [{ ...company, permissions: ["titles:read", "financial-accounts:read"] }],
      companyId: company.id,
    });
    window.history.replaceState(null, "", "/receivables");
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/receivables") && !url.includes("/new")) {
          return {
            ok: true,
            status: 200,
            text: async () =>
              JSON.stringify({
                items: [openTitle()],
                totalItems: 1,
                page: 0,
                size: 20,
                summary: { openCount: 1, openAmountMinor: "15000", overdueCount: 0, overdueAmountMinor: "0", draftCount: 0 },
                businessDate: "2026-09-15",
              }),
          };
        }
        if (url.includes("/catalogs/")) {
          return { ok: true, status: 200, text: async () => "[]" };
        }
        return { ok: true, status: 200, text: async () => "{}" };
      }),
    );
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Contas a receber" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Nova conta a receber" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Novo recebível" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Registrar recebível" })).not.toBeInTheDocument();
  });

  it("returns to identification after 401 and drops protected data", async () => {
    operatorSession();
    window.history.replaceState(null, "", "/receivables");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        text: async () => JSON.stringify({ message: "expired" }),
      }),
    );
    render(<App />);
    expect(await screen.findByLabelText("Token local")).toBeInTheDocument();
    expect(screen.queryByText("Contas a receber")).not.toBeInTheDocument();
  });

  it("retries account creation from the dialog with the same key after a lost response", async () => {
    operatorSession();
    window.history.replaceState(null, "", "/receivables/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/settlements/new");
    const title = openTitle({ outstandingAmountMinor: "15000", version: 1 });
    const created = { ...demoAccount(), id: "acc-new", name: "Conta do diálogo", currentBalanceMinor: "10000" };
    const keys: string[] = [];
    const bodies: string[] = [];
    let posts = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.includes("/financial-accounts") && init?.method === "POST") {
          posts += 1;
          keys.push((init.headers as Record<string, string>)["Idempotency-Key"]);
          bodies.push(String(init.body));
          if (posts === 1) {
            throw new TypeError("Failed to fetch");
          }
          return { ok: true, status: 200, text: async () => JSON.stringify(created) };
        }
        if (url.includes("/financial-accounts")) {
          return { ok: true, status: 200, text: async () => "[]" };
        }
        if (url.includes("/history") || url.includes("/settlements")) {
          return { ok: true, status: 200, text: async () => url.includes("/history") ? JSON.stringify({ items: [] }) : "[]" };
        }
        return { ok: true, status: 200, text: async () => JSON.stringify(title) };
      }),
    );
    const user = userEvent.setup();
    render(<App />);
    await user.click((await screen.findAllByRole("button", { name: "Criar conta" }))[0]);
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText("Banco ou instituição"), "Banco Ensaio");
    await user.type(within(dialog).getByLabelText("Número da conta"), "0012345-6");
    await user.selectOptions(within(dialog).getByLabelText("Modalidade"), "CHECKING");
    fireEvent.change(within(dialog).getByLabelText("Início do controle"), { target: { value: "2026-09-01" } });
    await user.type(within(dialog).getByLabelText("Saldo inicial"), "100,00");
    await user.click(within(dialog).getByRole("button", { name: "Salvar" }));
    expect(await screen.findByText(/repetir a mesma operação/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
    await waitFor(() => expect(posts).toBe(2));
    expect(keys[0]).toBe(keys[1]);
    expect(bodies[0]).toBe(bodies[1]);
    await waitFor(() => expect(screen.getByRole("combobox", { name: "Conta financeira" })).toHaveValue("Conta do diálogo"));
  });

  it("retries dedicated account creation and update with frozen keys, then starts a new key after validation", async () => {
    operatorSession();
    window.history.replaceState(null, "", "/financial-accounts/new");
    const created = { ...demoAccount(), id: "acc-page", name: "Conta dedicada", currentBalanceMinor: "25000" };
    const keys: string[] = [];
    let posts = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (init?.method === "POST" && url.includes("/financial-accounts")) {
          posts += 1;
          keys.push((init.headers as Record<string, string>)["Idempotency-Key"]);
          if (posts === 1) {
            throw new TypeError("Failed to fetch");
          }
          if (posts === 2) {
            return {
              ok: false,
              status: 400,
              text: async () => JSON.stringify({ message: "Dados inválidos.", fields: { name: "Nome é obrigatório e deve ter até 100 caracteres." } }),
            };
          }
          return { ok: true, status: 200, text: async () => JSON.stringify(created) };
        }
        if (url.includes("/movements")) {
          return { ok: true, status: 200, text: async () => JSON.stringify(statementPage()) };
        }
        return { ok: true, status: 200, text: async () => JSON.stringify(created) };
      }),
    );
    const user = userEvent.setup();
    render(<App />);
    await user.selectOptions(await screen.findByLabelText("Tipo"), "BANK");
    await user.type(screen.getByLabelText("Banco ou instituição"), "Banco Ensaio");
    await user.type(screen.getByLabelText("Número da conta"), "0012345-6");
    await user.selectOptions(screen.getByLabelText("Modalidade"), "CHECKING");
    fireEvent.change(screen.getByLabelText("Início do controle"), { target: { value: "2026-09-01" } });
    await user.type(screen.getByLabelText("Saldo inicial"), "250,00");
    await user.click(screen.getByRole("button", { name: "Salvar" }));
    await user.click(await screen.findByRole("button", { name: "Tentar novamente" }));
    await waitFor(() => expect(posts).toBe(2));
    expect(keys[0]).toBe(keys[1]);
    await user.click(screen.getByRole("button", { name: "Salvar" }));
    await waitFor(() => expect(posts).toBe(3));
    expect(keys[2]).not.toBe(keys[0]);
  });

  it("retries account rename with the same key after a lost response", async () => {
    operatorSession();
    window.history.replaceState(null, "", "/financial-accounts/acc-1");
    const account = demoAccount();
    const renamed = { ...account, name: "Conta renomeada", version: 2 };
    const keys: string[] = [];
    let patches = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (init?.method === "PATCH") {
          patches += 1;
          keys.push((init.headers as Record<string, string>)["Idempotency-Key"]);
          if (patches === 1) {
            throw new TypeError("Failed to fetch");
          }
          return { ok: true, status: 200, text: async () => JSON.stringify(renamed) };
        }
        if (url.includes("/movements")) {
          return { ok: true, status: 200, text: async () => JSON.stringify(statementPage()) };
        }
        return { ok: true, status: 200, text: async () => JSON.stringify(account) };
      }),
    );
    const user = userEvent.setup();
    render(<App />);
    expect(await screen.findByRole("tab", { name: "Dados da conta" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("Complete os dados desta conta")).toBeInTheDocument();
    expect(screen.queryByText("Gerenciar conta")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Editar dados" }));
    await user.click(await screen.findByText("Mais informações"));
    const name = await screen.findByLabelText("Apelido");
    await user.clear(name);
    await user.type(name, "Conta renomeada");
    await user.click(screen.getByRole("button", { name: "Salvar" }));
    await user.click(await screen.findByRole("button", { name: "Tentar novamente" }));
    await waitFor(() => expect(patches).toBe(2));
    expect(keys[0]).toBe(keys[1]);
  });

  it("refreshes title version after settlement conflict and sends a new key after review", async () => {
    operatorSession();
    window.history.replaceState(null, "", "/receivables/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/settlements/new");
    let title = openTitle({ outstandingAmountMinor: "15000", version: 1 });
    const keys: string[] = [];
    const versions: number[] = [];
    let posts = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.includes("/settlements") && init?.method === "POST") {
          posts += 1;
          keys.push((init.headers as Record<string, string>)["Idempotency-Key"]);
          versions.push(JSON.parse(String(init.body)).version);
          if (posts === 1) {
            title = openTitle({ outstandingAmountMinor: "5000", version: 2 });
            return {
              ok: false,
              status: 409,
              text: async () =>
                JSON.stringify({
                  code: "VERSION_CONFLICT",
                  message: "Este título foi alterado por outra pessoa. Revise o restante atual.",
                  fields: { outstandingAmountMinor: "5000" },
                }),
            };
          }
          return { ok: true, status: 200, text: async () => JSON.stringify({ id: "set-2", titleOutstandingAmountMinor: "0", titleVersion: 3 }) };
        }
        if (url.includes("/financial-accounts")) {
          return { ok: true, status: 200, text: async () => JSON.stringify([demoAccount()]) };
        }
        if (url.includes("/history") || (url.includes("/settlements") && (!init || !init.method || init.method === "GET"))) {
          return { ok: true, status: 200, text: async () => url.includes("/history") ? JSON.stringify({ items: [] }) : "[]" };
        }
        return { ok: true, status: 200, text: async () => JSON.stringify(title) };
      }),
    );
    const user = userEvent.setup();
    render(<App />);
    await chooseAccount(user);
    await user.selectOptions(screen.getByLabelText("Meio"), "PIX");
    const amount = screen.getByLabelText("Valor");
    await user.clear(amount);
    await user.type(amount, "100,00");
    await user.click(screen.getByRole("button", { name: "Registrar recebimento" }));
    expect(await screen.findByText(/restante atual é R\$ 50,00/)).toBeInTheDocument();
    expect(amount).toHaveValue("100,00");
    await user.clear(amount);
    await user.type(amount, "50,00");
    await user.click(screen.getByRole("button", { name: "Registrar recebimento" }));
    await waitFor(() => expect(posts).toBe(2));
    expect(keys[0]).not.toBe(keys[1]);
    expect(versions).toEqual([1, 2]);
  });

  it("unlocks the settlement form when a retry ends in a definitive conflict", async () => {
    operatorSession();
    window.history.replaceState(null, "", "/payables/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/settlements/new");
    let title = openTitle({ direction: "PAYABLE", outstandingAmountMinor: "15000", version: 1 });
    let posts = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.includes("/settlements") && init?.method === "POST") {
          posts += 1;
          if (posts === 1) {
            throw new TypeError("Failed to fetch");
          }
          title = openTitle({ direction: "PAYABLE", outstandingAmountMinor: "5000", version: 2 });
          return {
            ok: false,
            status: 409,
            text: async () =>
              JSON.stringify({
                code: "VERSION_CONFLICT",
                message: "Este título foi alterado por outra pessoa. Revise o restante atual.",
                fields: { outstandingAmountMinor: "5000" },
              }),
          };
        }
        if (url.includes("/financial-accounts")) {
          return { ok: true, status: 200, text: async () => JSON.stringify([demoAccount()]) };
        }
        if (url.includes("/history") || (url.includes("/settlements") && (!init || !init.method || init.method === "GET"))) {
          return { ok: true, status: 200, text: async () => url.includes("/history") ? JSON.stringify({ items: [] }) : "[]" };
        }
        return { ok: true, status: 200, text: async () => JSON.stringify(title) };
      }),
    );
    const user = userEvent.setup();
    render(<App />);
    await chooseAccount(user);
    await user.selectOptions(screen.getByLabelText("Meio"), "PIX");
    await user.click(screen.getByRole("button", { name: "Registrar pagamento" }));
    await user.click(await screen.findByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByText(/restante atual é R\$ 50,00/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Registrar pagamento" })).toBeEnabled();
    expect(screen.queryByRole("button", { name: "Tentar novamente" })).not.toBeInTheDocument();
  });

  it("unlocks reversal after a lost response followed by a definitive error", async () => {
    operatorSession();
    window.history.replaceState(null, "", "/settlements/set-1");
    const settlement = {
      id: "set-1",
      titleId: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
      titleReference: "REC-aaaa",
      titleDescription: "Recebível 150",
      counterpartyName: "Cliente Balcão",
      direction: "RECEIVABLE",
      accountId: "acc-1",
      accountName: "Conta Demo",
      accountActive: true,
      amountMinor: "5000",
      effectiveDate: "2026-09-15",
      method: "PIX",
      note: null,
      originKind: "MANUAL",
      recordedAt: "2026-09-15T15:00:00Z",
      actorDisplayName: "Operador A",
      reversed: false,
      reversalId: null,
      titleOutstandingAmountMinor: "10000",
      titleVersion: 2,
    };
    let posts = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        if (String(input).includes("/reversal") && init?.method === "POST") {
          posts += 1;
          if (posts === 1) {
            throw new TypeError("Failed to fetch");
          }
          return { ok: false, status: 400, text: async () => JSON.stringify({ message: "Motivo deve ter entre 3 e 500 caracteres." }) };
        }
        return { ok: true, status: 200, text: async () => JSON.stringify(settlement) };
      }),
    );
    const user = userEvent.setup();
    render(<App />);
    await user.click(await screen.findByRole("button", { name: "Estornar registro" }));
    await user.type(screen.getByLabelText("Motivo"), "Correção");
    await user.click(screen.getByRole("button", { name: "Confirmar estorno do registro" }));
    await user.click(await screen.findByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByText("Motivo deve ter entre 3 e 500 caracteres.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirmar estorno do registro" })).toBeEnabled();
  });

  it("labels statement amounts and ignores a stale period response", async () => {
    operatorSession();
    window.history.replaceState(null, "", "/financial-accounts/acc-1");
    const account = demoAccount();
    let resolveOld: ((value: unknown) => void) | undefined;
    const oldPage = statementPage({ currentBalanceMinor: "99999", periodEndBalanceMinor: "88888" });
    const newPage = statementPage();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/movements")) {
          if (url.includes("to=2026-09-10")) {
            return { ok: true, status: 200, text: async () => JSON.stringify(newPage) };
          }
          return {
            ok: true,
            status: 200,
            text: async () => {
              await new Promise((resolve) => {
                resolveOld = resolve;
              });
              return JSON.stringify(oldPage);
            },
          };
        }
        return { ok: true, status: 200, text: async () => JSON.stringify(account) };
      }),
    );
    const user = userEvent.setup();
    render(<App />);
    await user.click(await screen.findByRole("tab", { name: "Movimentações" }));
    expect(await screen.findByText("Carregando extrato…")).toBeInTheDocument();
    const until = await screen.findByLabelText("Até");
    fireEvent.change(until, { target: { value: "2026-09-10" } });
    expect(await screen.findByRole("button", { name: "Recebimento registrado" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Pagamento registrado" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Estorno do registro" })).toBeInTheDocument();
    expect(screen.getByText("Saldo inicial informado")).toBeInTheDocument();
    expect(screen.getAllByText("+ R$ 50,00").length).toBeGreaterThan(0);
    expect(screen.getAllByText("− R$ 100,00").length).toBeGreaterThan(0);
    expect(screen.getAllByText("+ R$ 250,00").length).toBeGreaterThan(0);
    expect(screen.getAllByText("R$ 150,00").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Posição")[0].closest("div")).toHaveTextContent("R$ 150,00");
    expect(screen.queryByText("R$ 999,99")).not.toBeInTheDocument();
    resolveOld?.(undefined);
  });

  it("shows an unknown balance as not measured and keeps a known zero", async () => {
    operatorSession();
    window.history.replaceState(null, "", "/financial-accounts/acc-1");
    const unknown = {
      ...demoAccount(),
      openingRecorded: false,
      currentBalanceMinor: null,
    };
    const unknownPage = statementPage({
      previousBalanceMinor: null,
      periodEndBalanceMinor: null,
      currentBalanceMinor: null,
      items: [{
        id: "m-1",
        kind: "SETTLEMENT",
        effectiveDate: "2026-10-02",
        recordedAt: "2026-10-02T12:00:00Z",
        recordedBy: "a",
        description: "Recebimento registrado",
        inflowMinor: "2500",
        outflowMinor: "0",
        balanceAfterMinor: null,
        settlementId: "set-x",
        reversalId: null,
      }],
    });
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/movements")) {
        return { ok: true, status: 200, text: async () => JSON.stringify(unknownPage) };
      }
      return { ok: true, status: 200, text: async () => JSON.stringify(unknown) };
    }));
    const user = userEvent.setup();
    const view = render(<App />);
    await user.click(await screen.findByRole("tab", { name: "Movimentações" }));
    expect(await screen.findByText("Recebimento registrado")).toBeInTheDocument();
    expect(screen.getAllByText("+ R$ 25,00").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Não apurada")).toHaveLength(1);
    expect(screen.queryByText("Não apurado")).not.toBeInTheDocument();
    expect(screen.queryByText("R$ 0,00")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ver extrato" })).toBeInTheDocument();
    view.unmount();

    const knownZero = { ...demoAccount(), openingRecorded: true, currentBalanceMinor: "0" };
    const zeroPage = statementPage({
      previousBalanceMinor: "0",
      periodEndBalanceMinor: "0",
      currentBalanceMinor: "0",
      items: [],
    });
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/movements")) {
        return { ok: true, status: 200, text: async () => JSON.stringify(zeroPage) };
      }
      return { ok: true, status: 200, text: async () => JSON.stringify(knownZero) };
    }));
    render(<App />);
    await user.click(await screen.findByRole("tab", { name: "Movimentações" }));
    expect((await screen.findAllByText("R$ 0,00")).length).toBeGreaterThan(0);
    expect(screen.getByText("Ainda não há movimentos registrados no Finance para esta conta.")).toBeInTheDocument();
    expect(screen.getByText("Você pode consultar ou importar um relatório do Mercado Pago em Ver extrato.")).toBeInTheDocument();
    expect(screen.queryByText("Não apurado")).not.toBeInTheDocument();
    expect(screen.queryByText("Não apurada")).not.toBeInTheDocument();
  });

  it("posts quick catalog from the dialog without submitting the title", async () => {
    operatorSession();
    window.history.replaceState(null, "", "/receivables/new");
    const createdCp = { id: "cp-dialog", name: "Cliente diálogo", code: "CLI-D", active: true };
    const createdCat = { id: "cat-dialog", name: "Categoria diálogo", code: "CAT-D", active: true };
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();
      if (url.includes("/catalogs/counterparties") && method === "POST") {
        return { ok: true, status: 201, text: async () => JSON.stringify(createdCp) };
      }
      if (url.includes("/catalogs/categories") && method === "POST") {
        return { ok: true, status: 201, text: async () => JSON.stringify(createdCat) };
      }
      if (url.includes("/receivables") && method === "POST") {
        throw new Error("title POST must not run while saving the catalog dialog");
      }
      if (url.includes("/catalogs/") || url.includes("/settlements")) {
        return { ok: true, status: 200, text: async () => "[]" };
      }
      return { ok: true, status: 200, text: async () => "[]" };
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);
    const description = await screen.findByLabelText(/Descrição/);
    await user.type(description, "Rascunho incompleto");
    await user.type(screen.getByLabelText("Referência informativa"), "REF-RASCUNHO");
    await user.click(screen.getByRole("button", { name: "Cadastrar contraparte" }));
    const dialog = await screen.findByRole("dialog");
    expect(document.querySelector("form.form dialog")).toBeNull();
    expect(document.body.querySelector("dialog.dialog")).not.toBeNull();
    await user.type(within(dialog).getByLabelText("Nome"), "Cliente diálogo");
    await user.click(within(dialog).getByRole("button", { name: "Salvar" }));
    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(
          (call) => String(call[0]).includes("/catalogs/counterparties") && call[1]?.method === "POST",
        ),
      ).toBe(true);
    });
    expect(
      fetchMock.mock.calls.some((call) => String(call[0]).includes("/receivables") && call[1]?.method === "POST"),
    ).toBe(false);
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    await waitFor(() => expect(screen.getByRole("combobox", { name: /Cliente/ })).toHaveValue("Cliente diálogo"));
    await user.click(screen.getByRole("button", { name: "Cadastrar categoria" }));
    const categoryDialog = await screen.findByRole("dialog");
    await user.type(within(categoryDialog).getByLabelText("Nome"), "Categoria diálogo");
    await user.click(within(categoryDialog).getByRole("button", { name: "Salvar" }));
    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(
          (call) => String(call[0]).includes("/catalogs/categories") && call[1]?.method === "POST",
        ),
      ).toBe(true);
    });
    expect(screen.getByLabelText(/Descrição/)).toHaveValue("Rascunho incompleto");
    expect(screen.getByLabelText("Referência informativa")).toHaveValue("REF-RASCUNHO");
  });

  it("keeps the title draft and returns focus when the catalog dialog is dismissed", async () => {
    operatorSession();
    window.history.replaceState(null, "", "/receivables/new");
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/catalogs/") || url.includes("/settlements")) {
          return { ok: true, status: 200, text: async () => "[]" };
        }
        return { ok: true, status: 200, text: async () => "[]" };
      }),
    );
    const user = userEvent.setup();
    render(<App />);
    await user.type(await screen.findByLabelText(/Descrição/), "Texto a preservar");
    const trigger = screen.getByRole("button", { name: "Cadastrar contraparte" });
    await user.click(trigger);
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText("Nome"), "Não gravar");
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(screen.getByLabelText(/Descrição/)).toHaveValue("Texto a preservar");
    expect(trigger).toHaveFocus();
    await user.click(screen.getByRole("button", { name: "Cadastrar categoria" }));
    await screen.findByRole("dialog");
    await user.click(screen.getByRole("button", { name: "Voltar" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(screen.getByLabelText(/Descrição/)).toHaveValue("Texto a preservar");
  });

  it("separates financial observation from last attempt and labels refund review", async () => {
    operatorSession();
    window.history.replaceState(null, "", "/receivables/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee");
    const title = openTitle();
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/api/v1/system/info")) {
        return {
          ok: true,
          status: 200,
          json: async () => ({ homologIntegration: true, accessMode: "DEMO" }),
          text: async () => JSON.stringify({ homologIntegration: true, accessMode: "DEMO" }),
        };
      }
      if (url.includes("/history")) {
        return { ok: true, status: 200, text: async () => JSON.stringify({ items: [] }) };
      }
      if (url.includes("/settlements")) {
        return { ok: true, status: 200, text: async () => "[]" };
      }
      if (url.includes("/pay-lookup") && init?.method === "POST") {
        return {
          ok: true,
          status: 200,
          text: async () =>
            JSON.stringify({
              id: "op-1",
              companyId: company.id,
              titleId: title.id,
              originSystem: "ACTIONHUB_PAY",
              externalReference: "pay-homolog-refunded",
              amountMinor: "12550",
              currency: "BRL",
              externalStatus: "REFUNDED",
              deliveryStatus: "DELIVERED",
              correlationId: "afc-1",
              spiderDecisionId: "spd-1",
              providerReference: "pay-homolog-refunded",
              providerOrigin: "SIMULATOR",
              lastError: null,
              observedAt: "2026-09-30T12:00:00Z",
              updatedAt: "2026-09-30T12:01:00Z",
              lastAttemptAt: "2026-09-30T12:01:00Z",
              lastAttemptOutcome: "DELIVERED",
              automaticSettlement: false,
              homolog: true,
            }),
        };
      }
      if (url.includes("/pay-lookup")) {
        return {
          ok: true,
          status: 200,
          text: async () =>
            JSON.stringify({
              id: "op-1",
              companyId: company.id,
              titleId: title.id,
              originSystem: "ACTIONHUB_PAY",
              externalReference: "pay-homolog-0001",
              amountMinor: "12550",
              currency: "BRL",
              externalStatus: "CONFIRMED",
              deliveryStatus: "UNAVAILABLE",
              correlationId: "afc-1",
              spiderDecisionId: "spd-1",
              providerReference: "pay-homolog-0001",
              providerOrigin: "SIMULATOR",
              lastError: "timeout",
              observedAt: "2026-09-30T12:00:00Z",
              updatedAt: "2026-09-30T12:05:00Z",
              lastAttemptAt: "2026-09-30T12:05:00Z",
              lastAttemptOutcome: "UNAVAILABLE",
              automaticSettlement: false,
              homolog: true,
            }),
        };
      }
      return { ok: true, status: 200, text: async () => JSON.stringify(title) };
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);
    expect(await screen.findByText("Acompanhamento no ActionHub Pay")).toBeInTheDocument();
    expect(screen.getByText("Observação financeira")).toBeInTheDocument();
    expect(screen.getByText("Confirmado pelo Pay")).toBeInTheDocument();
    expect(screen.getByText(/observação anterior preservada/)).toBeInTheDocument();
    expect(screen.getByText("Simulador da borda Pay")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Consultar resultado" }));
    expect(await screen.findByText(/Estornado pelo Pay/)).toBeInTheDocument();
    expect(screen.getByText(/O título não foi baixado/)).toBeInTheDocument();
  });
});

function demoAccount() {
  return {
    id: "acc-1",
    code: "CTA-1",
    name: "Conta Demo",
    type: "BANK",
    currency: "BRL",
    active: true,
    openedOn: "2026-09-01",
    currentBalanceMinor: "25000",
    companyName: "Padaria",
    version: 1,
  };
}

function openTitle(overrides: Record<string, unknown> = {}) {
  return {
    id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    reference: "REC-aaaa",
    direction: "RECEIVABLE",
    status: "OPEN",
    description: "Recebível 150",
    counterpartyId: "cp",
    counterpartyName: "Cliente Balcão",
    counterpartyActive: true,
    categoryId: "cat",
    categoryName: "Vendas",
    categoryActive: true,
    amountMinor: "15000",
    settledAmountMinor: "0",
    outstandingAmountMinor: "15000",
    settlementStatus: "UNSETTLED",
    currency: "BRL",
    competenceDate: "2026-09-15",
    dueDate: "2026-09-20",
    overdue: false,
    originKind: "MANUAL",
    sourceReference: null,
    version: 1,
    demoCompany: true,
    businessDate: "2026-09-15",
    ...overrides,
  };
}

function statementPage(overrides: Record<string, unknown> = {}) {
  return {
    items: [
      {
        id: "m-open",
        kind: "OPENING",
        effectiveDate: "2026-09-01",
        recordedAt: "2026-09-01T12:00:00Z",
        recordedBy: "a",
        description: "Saldo inicial informado",
        inflowMinor: "25000",
        outflowMinor: "0",
        balanceAfterMinor: "25000",
        settlementId: null,
        reversalId: null,
      },
      {
        id: "m-in",
        kind: "SETTLEMENT",
        effectiveDate: "2026-09-15",
        recordedAt: "2026-09-15T15:00:00Z",
        recordedBy: "a",
        description: "Recebimento registrado · REC-aaaa",
        inflowMinor: "5000",
        outflowMinor: "0",
        balanceAfterMinor: "30000",
        settlementId: "set-1",
        reversalId: null,
      },
      {
        id: "m-out",
        kind: "SETTLEMENT",
        effectiveDate: "2026-09-15",
        recordedAt: "2026-09-15T16:00:00Z",
        recordedBy: "a",
        description: "Pagamento registrado · PAG-aaaa",
        inflowMinor: "0",
        outflowMinor: "10000",
        balanceAfterMinor: "20000",
        settlementId: "set-2",
        reversalId: null,
      },
      {
        id: "m-rev",
        kind: "REVERSAL",
        effectiveDate: "2026-09-15",
        recordedAt: "2026-09-15T17:00:00Z",
        recordedBy: "a",
        description: "Estorno do registro · REC-aaaa",
        inflowMinor: "0",
        outflowMinor: "5000",
        balanceAfterMinor: "15000",
        settlementId: "set-1",
        reversalId: "rev-1",
      },
    ],
    totalItems: 4,
    page: 0,
    size: 20,
    previousBalanceMinor: "0",
    periodEndBalanceMinor: "15000",
    currentBalanceMinor: "15000",
    from: "2026-09-01",
    to: "2026-09-15",
    ...overrides,
  };
}
