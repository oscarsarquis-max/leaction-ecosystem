import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "./App";
import { setSession } from "./session";

const writePerms = ["titles:write", "catalogs:write", "financial-accounts:read", "financial-accounts:write", "settlements:read", "settlements:write", "settlements:reverse"];
const company = { id: "11111111-1111-1111-1111-111111111111", tenantId: "t", name: "Padaria Demo", active: true, demo: true, permissions: writePerms };

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
    vi.unstubAllGlobals();
    window.history.replaceState(null, "", "/");
  });

  it("shows production enter without a token field", async () => {
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
    expect(await screen.findByRole("button", { name: "Entrar" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Token local")).not.toBeInTheDocument();
    expect(screen.getByText(/Acesso restrito/)).toBeInTheDocument();
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
    expect(await screen.findByText("Único")).toBeInTheDocument();
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
    expect(await screen.findByText("Conta Demo")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Registrar recebimento" })).toBeInTheDocument();
    expect(screen.queryByText(/Pix enviado|Pagamento executado/i)).not.toBeInTheDocument();
    const accountSelect = screen.getAllByRole("combobox")[0];
    await user.selectOptions(accountSelect, "acc-1");
    await user.selectOptions(screen.getByLabelText("Meio"), "PIX");
    await user.click(screen.getByRole("button", { name: "Registrar recebimento" }));
    await waitFor(() => {
      const post = fetchMock.mock.calls.find((call) => call[1]?.method === "POST" && String(call[0]).includes("/settlements"));
      expect(post).toBeDefined();
    });
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
    await user.type(within(dialog).getByLabelText("Nome"), "Conta do diálogo");
    fireEvent.change(within(dialog).getByLabelText("Início do controle"), { target: { value: "2026-09-01" } });
    await user.type(within(dialog).getByLabelText("Saldo inicial"), "100,00");
    await user.click(within(dialog).getByRole("button", { name: "Criar conta" }));
    expect(await screen.findByText(/repetir a mesma operação/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
    await waitFor(() => expect(posts).toBe(2));
    expect(keys[0]).toBe(keys[1]);
    expect(bodies[0]).toBe(bodies[1]);
    expect(await screen.findByText("Conta do diálogo")).toBeInTheDocument();
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
    await user.type(await screen.findByLabelText("Nome"), "Conta dedicada");
    await user.selectOptions(screen.getByLabelText("Tipo"), "BANK");
    fireEvent.change(screen.getByLabelText("Início do controle"), { target: { value: "2026-09-01" } });
    await user.type(screen.getByLabelText("Saldo inicial"), "250,00");
    await user.click(screen.getByRole("button", { name: "Criar conta" }));
    await user.click(await screen.findByRole("button", { name: "Tentar novamente" }));
    await waitFor(() => expect(posts).toBe(2));
    expect(keys[0]).toBe(keys[1]);
    await user.click(screen.getByRole("button", { name: "Criar conta" }));
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
    const name = await screen.findByLabelText("Nome");
    await user.clear(name);
    await user.type(name, "Conta renomeada");
    await user.click(screen.getByRole("button", { name: "Renomear" }));
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
    await user.selectOptions((await screen.findAllByRole("combobox"))[0], "acc-1");
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
    await user.selectOptions((await screen.findAllByRole("combobox"))[0], "acc-1");
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
    render(<App />);
    expect(await screen.findByText("Carregando extrato…")).toBeInTheDocument();
    const until = await screen.findByLabelText("Até");
    fireEvent.change(until, { target: { value: "2026-09-10" } });
    expect(await screen.findByText("Entrada: R$ 50,00")).toBeInTheDocument();
    expect(screen.getByText("Saída: R$ 100,00")).toBeInTheDocument();
    expect(screen.getByText("Estorno do registro")).toBeInTheDocument();
    expect(screen.getByText("Abertura: R$ 250,00")).toBeInTheDocument();
    expect(screen.getAllByText("Saldo após: R$ 150,00").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Saldo gerencial atual")[0].closest("div")).toHaveTextContent("R$ 150,00");
    expect(screen.queryByText("R$ 999,99")).not.toBeInTheDocument();
    resolveOld?.(undefined);
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
    const counterpartySelect = document.querySelector("label.searchable select") as HTMLSelectElement;
    expect(counterpartySelect.value).toBe("cp-dialog");
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
