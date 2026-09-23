import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import { AppRoutes } from "./App";
import { meFixture } from "./api/fixtures";
import { AssistantProvider } from "./assistant/AssistantContext";
import { AuthProviderTree } from "./auth/AuthContext";
import { FakeAuthProvider } from "./auth/FakeAuthProvider";
import { OrganizationProvider } from "./session/OrganizationContext";
import { installApiMock, json } from "./test/fetchMock";

afterEach(() => {
  sessionStorage.clear();
  localStorage.clear();
});

const authorized = {
  ...meFixture,
  user_id: null,
  display_name: "",
  associations: [],
  roles: [],
  permissions: [],
  selected_organization_id: null,
  access_state: "autorizado",
  commercial_condition_label: "Acesso sem cobrança da Panne nesta etapa",
  account_email: "conta@example.com",
};

async function open(me: Record<string, unknown>, extra: Record<string, (url: URL, request: Request) => Response> = {}) {
  const provider = new FakeAuthProvider();
  await provider.login();
  installApiMock({
    "/api/v1/me": () => json(me),
    ...extra,
  });
  render(
    <AuthProviderTree provider={provider}>
      <OrganizationProvider>
        <MemoryRouter future={{ v7_relativeSplatPath: true }} initialEntries={["/"]}>
          <AssistantProvider>
            <AppRoutes />
          </AssistantProvider>
        </MemoryRouter>
      </OrganizationProvider>
    </AuthProviderTree>,
  );
}

async function fillNatural() {
  await userEvent.type(screen.getByLabelText("Nome que aparecerá na Panne"), "Oficina Norte");
  await userEvent.type(screen.getByLabelText("Seu nome"), "Ana Silva");
  await userEvent.type(screen.getByLabelText("CPF"), "52998224725");
  await userEvent.type(screen.getByLabelText("Nome do local"), "Balcão");
  await userEvent.click(screen.getByRole("checkbox", { name: /Vendas/ }));
}

describe("primeiro acesso", () => {
  it("não mostra o formulário sem autorização", async () => {
    await open({ ...authorized, access_state: "sem_autorizacao", commercial_condition_label: null });
    expect(await screen.findByRole("heading", { name: "Vamos configurar seu negócio" })).toBeTruthy();
    expect(screen.getByRole("alert").textContent).toMatch(/ainda não pode cadastrar/);
    expect(screen.getByRole("button", { name: "Sair" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Criar meu espaço na Panne" })).toBeNull();
  });

  it("explica autorização vencida sem abrir o cadastro", async () => {
    await open({ ...authorized, access_state: "autorizacao_expirada" });
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(screen.getByRole("alert").textContent).toMatch(/venceu/);
    expect(screen.queryByLabelText("Nome que aparecerá na Panne")).toBeNull();
  });

  it("mostra só os campos da pessoa física ainda sem empresa", async () => {
    await open(authorized);
    expect(await screen.findByText("conta@example.com")).toBeTruthy();
    expect(screen.getByLabelText("CPF")).toBeTruthy();
    expect(screen.getByRole("radio", { name: /Ainda sem empresa/ })).toBeTruthy();
    expect(screen.queryByLabelText("Razão social")).toBeNull();
    expect(screen.queryByLabelText("CNPJ")).toBeNull();
    expect(screen.queryByRole("checkbox", { name: /Aceito/ })).toBeNull();
    expect(screen.getByText("Acesso sem cobrança da Panne nesta etapa")).toBeTruthy();
    expect(document.body.textContent).not.toMatch(/holder_kind|slug|payload|complimentary/);
  });

  it("mostra razão social e CNPJ só para pessoa jurídica", async () => {
    await open(authorized);
    await screen.findByLabelText("CPF");
    await userEvent.click(screen.getByRole("radio", { name: /Pessoa jurídica/ }));
    expect(screen.getByLabelText("Razão social")).toBeTruthy();
    expect(screen.getByLabelText("CNPJ")).toBeTruthy();
    expect(screen.queryByLabelText("CPF")).toBeNull();
    expect(screen.queryByRole("radio", { name: /Ainda sem empresa/ })).toBeNull();
  });

  it("aponta CPF inválido e mantém o nome preenchido", async () => {
    await open(authorized);
    await screen.findByLabelText("CPF");
    await userEvent.type(screen.getByLabelText("Nome que aparecerá na Panne"), "Oficina Norte");
    await userEvent.type(screen.getByLabelText("CPF"), "11111111111");
    await userEvent.click(screen.getByRole("button", { name: "Criar meu espaço na Panne" }));
    expect(await screen.findByText("Informe um CPF válido.")).toBeTruthy();
    expect((screen.getByLabelText("Nome que aparecerá na Panne") as HTMLInputElement).value).toBe("Oficina Norte");
  });

  it("cria pessoa física sem empresa e só então oferece o painel", async () => {
    const bodies: Record<string, unknown>[] = [];
    let calls = 0;
    await open(authorized, {
      "/api/v1/onboarding": (_url, request) => {
        calls += 1;
        void request
          .clone()
          .json()
          .then((body) => bodies.push(body as Record<string, unknown>));
        return json({
          organization_id: "11111111-1111-1111-1111-111111111111",
          display_name: "Oficina Norte",
          establishment_name: "Balcão",
          created: true,
        });
      },
    });
    await screen.findByLabelText("CPF");
    await fillNatural();
    const submit = screen.getByRole("button", { name: "Criar meu espaço na Panne" });
    fireEvent.click(submit);
    fireEvent.click(submit);
    expect(calls).toBe(1);
    expect(await screen.findByRole("heading", { name: "Seu espaço está pronto" })).toBeTruthy();
    expect(screen.getByText("Oficina Norte")).toBeTruthy();
    expect(screen.getByText("Balcão")).toBeTruthy();
    expect(screen.queryByText("529.982.247-25")).toBeNull();
    expect(screen.queryByRole("link", { name: "Quadro" })).toBeNull();
    await waitFor(() => expect(bodies.length).toBe(1));
    expect(bodies[0]).toMatchObject({
      holder_kind: "natural_person",
      formalization_state: "not_formalized",
      legal_name: null,
      holder_fiscal_id: "52998224725",
      capabilities: ["sale"],
      establishment_nature: "specialized",
      accept_commercial_condition: true,
    });
  });

  it("cria pessoa jurídica formalizada com várias atividades", async () => {
    const bodies: Record<string, unknown>[] = [];
    await open(authorized, {
      "/api/v1/onboarding": (_url, request) => {
        void request
          .clone()
          .json()
          .then((body) => bodies.push(body as Record<string, unknown>));
        return json({
          organization_id: "11111111-1111-1111-1111-111111111111",
          display_name: "Moinho Sul",
          establishment_name: "Fábrica",
          created: true,
        });
      },
    });
    await screen.findByLabelText("CPF");
    await userEvent.click(screen.getByRole("radio", { name: /Pessoa jurídica/ }));
    await userEvent.type(screen.getByLabelText("Nome que aparecerá na Panne"), "Moinho Sul");
    await userEvent.type(screen.getByLabelText("Seu nome"), "Bruno Costa");
    await userEvent.type(screen.getByLabelText("Razão social"), "Moinho Sul Alimentos Ltda");
    await userEvent.type(screen.getByLabelText("CNPJ"), "11222333000181");
    await userEvent.type(screen.getByLabelText("Nome do local"), "Fábrica");
    await userEvent.click(screen.getByRole("checkbox", { name: /Estoque/ }));
    await userEvent.click(screen.getByRole("checkbox", { name: /Produção/ }));
    await userEvent.click(screen.getByRole("button", { name: "Criar meu espaço na Panne" }));
    expect(await screen.findByRole("heading", { name: "Seu espaço está pronto" })).toBeTruthy();
    await waitFor(() => expect(bodies.length).toBe(1));
    expect(bodies[0]).toMatchObject({
      holder_kind: "legal_entity",
      formalization_state: "formalized",
      legal_name: "Moinho Sul Alimentos Ltda",
      holder_fiscal_id: "11222333000181",
      capabilities: ["stock", "production"],
      establishment_nature: "integrated",
    });
    expect(bodies[0]?.legal_name).not.toBeNull();
  });

  it("mantém o cadastro quando o identificador já está em uso", async () => {
    await open(authorized, {
      "/api/v1/onboarding": () => json({ detail: "Este código de cliente já está em uso." }, 409),
    });
    await screen.findByLabelText("CPF");
    await fillNatural();
    await userEvent.click(screen.getByRole("button", { name: "Criar meu espaço na Panne" }));
    expect(await screen.findByText(/já está em uso/)).toBeTruthy();
    expect((screen.getByLabelText("Nome que aparecerá na Panne") as HTMLInputElement).value).toBe("Oficina Norte");
    expect(screen.getByLabelText("Identificador do negócio")).toBeTruthy();
  });

  it("não oferece o cadastro a uma conta convidada", async () => {
    await open({
      ...authorized,
      access_state: "convidado",
      invite_organization_name: "Cliente convidado",
      commercial_condition_label: null,
    });
    expect(await screen.findByRole("button", { name: "Entrar neste negócio" })).toBeTruthy();
    expect(screen.getByText(/Cliente convidado/)).toBeTruthy();
    expect(screen.queryByLabelText("Nome que aparecerá na Panne")).toBeNull();
  });
});
