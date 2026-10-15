import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "./App";
import { setSession, setSessionNotice } from "./session";

const writePerms = ["titles:write", "catalogs:write", "financial-accounts:read", "financial-accounts:write"];
const company = {
  id: "11111111-1111-1111-1111-111111111111",
  tenantId: "t",
  name: "Padaria Demo",
  active: true,
  demo: true,
  permissions: writePerms,
};

const emptyPage = { items: [], totalItems: 0, page: 0, size: 20 };

function operatorSession() {
  setSession({
    token: "operator-demo-token",
    mode: "demo",
    actorId: "actor",
    displayName: "Operador A",
    permissions: writePerms,
    companies: [company],
    companyId: company.id,
  });
}

describe("Counterparties directory", () => {
  afterEach(() => {
    setSession(null);
    setSessionNotice(null);
    vi.unstubAllGlobals();
    sessionStorage.clear();
    window.history.replaceState(null, "", "/");
  });

  it("opens cadastro from empty search and does not treat list as a submit form", async () => {
    operatorSession();
    window.history.replaceState(null, "", "/catalogs/counterparties");
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/catalogs/parties?") || url.endsWith("/catalogs/parties")) {
        return { ok: true, status: 200, text: async () => JSON.stringify(emptyPage) };
      }
      return { ok: true, status: 200, text: async () => "[]" };
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Clientes e fornecedores" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Criar" })).not.toBeInTheDocument();
    expect(screen.getByText(/Nenhum cliente ou fornecedor cadastrado/)).toBeInTheDocument();
    await user.click(screen.getAllByRole("button", { name: "Cadastrar" })[0]);
    expect(await screen.findByRole("group", { name: "Identificação" })).toBeInTheDocument();
    expect(screen.getByText(/Documento opcional/)).toBeInTheDocument();
    expect(screen.queryByText(/Não invente número/)).not.toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "Cliente" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Fornecedor" })).not.toBeChecked();
    expect(screen.queryByRole("radio")).not.toBeInTheDocument();
  });

  it("distinguishes empty search results and keeps import as preview", async () => {
    operatorSession();
    window.history.replaceState(null, "", "/catalogs/counterparties");
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();
      if (url.includes("/catalogs/parties")) {
        return {
          ok: true,
          status: 200,
          text: async () => JSON.stringify({ items: [], totalItems: 0, page: 0, size: 20 }),
        };
      }
      if (url.includes("/party-imports") && method === "POST" && !url.includes("confirm")) {
        return {
          ok: true,
          status: 200,
          text: async () =>
            JSON.stringify({
              id: "batch-1",
              filename: "modelo.csv",
              status: "PREVIEW",
              totalLines: 1,
              newCount: 1,
              duplicateCount: 0,
              conflictCount: 0,
              invalidCount: 0,
              atomicity: "PER_LINE",
              lines: [
                {
                  id: "line-1",
                  lineNo: 1,
                  classification: "NEW",
                  selected: true,
                  name: "Padaria Modelo",
                  role: "SUPPLIER",
                },
              ],
            }),
        };
      }
      return { ok: true, status: 200, text: async () => "[]" };
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("heading", { name: "Clientes e fornecedores" });
    await user.type(screen.getByLabelText("Buscar"), "xyz-inexistente");
    await user.click(screen.getByRole("button", { name: "Buscar" }));
    expect(await screen.findByText(/Nenhum resultado para esta busca/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Importar arquivo" }));
    expect(await screen.findByText(/O envio só gera prévia/)).toBeInTheDocument();
    expect(screen.queryByText(/Importar do Panne/)).not.toBeInTheDocument();
    const csv = "nome;relacao\nPadaria Modelo;FORNECEDOR\n";
    const file = new File([csv], "modelo.csv", { type: "text/csv" });
    Object.defineProperty(file, "text", { value: async () => csv });
    await user.upload(screen.getByLabelText("Arquivo CSV"), file);
    await user.click(screen.getByRole("button", { name: "Validar arquivo" }));
    await waitFor(() => expect(screen.getByText(/1 linha/)).toBeInTheDocument());
    expect(screen.getAllByText("Padaria Modelo").length).toBeGreaterThan(0);
    expect(screen.getAllByRole("checkbox", { name: "Incluir linha 1" }).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Confirmar linhas selecionadas" })).toBeEnabled();
    expect(fetchMock.mock.calls.some((call) => String(call[0]).includes("/confirm"))).toBe(false);
  });

  it("translates invalid import lines and disables confirm without eligible selection", async () => {
    operatorSession();
    window.history.replaceState(null, "", "/catalogs/counterparties/import");
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();
      if (url.includes("/party-imports") && method === "POST" && !url.includes("confirm")) {
        return {
          ok: true,
          status: 200,
          text: async () =>
            JSON.stringify({
              id: "batch-invalid",
              filename: "invalido.csv",
              status: "PREVIEW",
              totalLines: 1,
              newCount: 0,
              duplicateCount: 0,
              conflictCount: 0,
              invalidCount: 1,
              atomicity: "PER_LINE",
              lines: [
                {
                  id: "line-invalid",
                  lineNo: 1,
                  classification: "INVALID",
                  selected: false,
                  name: "Linha invalida",
                  errorMessage: "Documento inválido",
                },
              ],
            }),
        };
      }
      return { ok: true, status: 200, text: async () => "[]" };
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Importar arquivo CSV" })).toBeInTheDocument();
    expect(screen.queryByText(/Não invente número/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Nenhum campo é inventado/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Isto não é conector Panne/)).not.toBeInTheDocument();
    const csv = "nome;relacao;documento\nLinha invalida;FORNECEDOR;00\n";
    const file = new File([csv], "invalido.csv", { type: "text/csv" });
    Object.defineProperty(file, "text", { value: async () => csv });
    await user.upload(screen.getByLabelText("Arquivo CSV"), file);
    await user.click(screen.getByRole("button", { name: "Validar arquivo" }));
    expect((await screen.findAllByText("Inválido")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Linha invalida").length).toBeGreaterThan(0);
    expect(screen.getByText(/1 inválido/)).toBeInTheDocument();
    expect(screen.getByText(/Selecione ao menos uma linha válida/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirmar linhas selecionadas" })).toBeDisabled();
  });
});
