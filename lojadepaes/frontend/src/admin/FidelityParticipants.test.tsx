import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { FidelityParticipants } from "./FidelityParticipants";
import { adminRequest } from "./api";

vi.mock("./api", () => ({
  AdminApiError: class AdminApiError extends Error {
    status = 400;
  },
  adminRequest: vi.fn(),
}));

const list = {
  items: [
    {
      id: "acc-1",
      name: "Ana",
      email: "ana@example.com",
      cpf_masked: "***.***.***-05",
      verified: true,
      valid_orders: 0,
      credits_available: 0,
    },
  ],
  page: 1,
  page_size: 20,
  total: 1,
  campaign_status: "active",
  campaign_active: true,
  gaps: [],
};

const detail = {
  id: "acc-1",
  name: "Ana",
  email: "ana@example.com",
  cpf_masked: "***.***.***-05",
  verified: true,
  valid_orders_month: 0,
  credits: { available: 0, reserved: 0, used: 0, returned: 0 },
  credits_available: 0,
  progress: { progress_label: "0 de 4 pedidos" },
  credit_rows: [],
  history: [],
  can_grant: true,
  grant_block_reason: null,
};

describe("gestão da fidelidade", () => {
  it("mostra a regra curta e o ajuste no detalhe, sem motivo global", async () => {
    vi.mocked(adminRequest).mockImplementation(async (path: string) => {
      if (path.includes("/admin/participants/acc-1")) {
        return detail;
      }
      return list;
    });
    const user = userEvent.setup();
    render(<FidelityParticipants />);
    expect(await screen.findByRole("heading", { name: "Fidelidade da casa" })).toBeInTheDocument();
    expect(screen.getByText("Acompanhe participantes, créditos e ajustes.")).toBeInTheDocument();
    expect(screen.getByText(/O crédito vale um pão de 500 g da vitrine/)).toBeInTheDocument();
    expect(screen.queryByText(/Motivo do ajuste/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Conceder" })).not.toBeInTheDocument();
    await user.click(screen.getAllByRole("button", { name: "Ver detalhes" })[0]);
    expect(await screen.findByRole("button", { name: "Conceder crédito manualmente" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Conceder crédito manualmente" }));
    expect(screen.getByLabelText("Por que está concedendo este crédito?")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Confirmar ajuste" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Informe o motivo deste ajuste.");
    expect(adminRequest).not.toHaveBeenCalledWith(
      "/api/v1/promotions/house-fidelity/admin/adjust",
      expect.anything(),
    );
  });

  it("não busca por CPF completo", async () => {
    vi.mocked(adminRequest).mockResolvedValue(list);
    const user = userEvent.setup();
    render(<FidelityParticipants />);
    await screen.findByLabelText("Buscar por nome ou e-mail");
    await user.type(screen.getByLabelText("Buscar por nome ou e-mail"), "39053344705");
    await user.keyboard("{Enter}");
    expect(screen.getByText(/O CPF não entra na busca/)).toBeInTheDocument();
    expect(vi.mocked(adminRequest).mock.calls.every(([path]) => !String(path).includes("39053344705"))).toBe(
      true,
    );
  });
});
