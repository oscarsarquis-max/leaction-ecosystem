import { render, screen } from "@testing-library/react";
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

async function open(me: Record<string, unknown>) {
  const provider = new FakeAuthProvider();
  await provider.login();
  installApiMock({
    "/api/v1/me": () => json(me),
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

describe("primeiro acesso", () => {
  it("mostra autorização ausente, saída e suporte", async () => {
    await open({
      ...meFixture,
      user_id: null,
      associations: [],
      roles: [],
      permissions: [],
      access_state: "sem_autorizacao",
    });
    expect(await screen.findByRole("heading", { name: "Primeiro acesso" })).toBeTruthy();
    expect(screen.getByText(/não tem autorização da Panne/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Sair" })).toBeTruthy();
    expect(screen.getByText(/suporte da Panne/)).toBeTruthy();
    expect(screen.queryByText("Acesso negado")).toBeNull();
  });

  it("adapta o formulário à pessoa física e à pessoa jurídica", async () => {
    await open({
      ...meFixture,
      associations: [],
      roles: [],
      permissions: [],
      access_state: "autorizado",
      commercial_condition_label: "Acesso sem cobrança da Panne nesta etapa",
    });
    expect(await screen.findByLabelText("CPF do titular")).toBeTruthy();
    expect(screen.queryByLabelText("Razão social")).toBeNull();
    await userEvent.click(screen.getByLabelText("Pessoa jurídica"));
    expect(screen.getByLabelText("Razão social")).toBeTruthy();
    expect(screen.getByLabelText("CNPJ")).toBeTruthy();
    expect(screen.queryByText("Loja de Pães")).toBeNull();
  });

  it("oferece continuar um convite", async () => {
    await open({
      ...meFixture,
      associations: [],
      roles: [],
      permissions: [],
      access_state: "convidado",
      invite_organization_name: "Cliente convidado",
    });
    expect(await screen.findByRole("button", { name: "Continuar convite" })).toBeTruthy();
    expect(screen.getByText(/Cliente convidado/)).toBeTruthy();
  });
});
