import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CartProvider } from "./CartContext";
import { HouseFidelityPanel } from "./HouseFidelityPanel";
import { SELECTION_KEY } from "./selection";

const visitorStatus = {
  campaign_active: false,
  preview: false,
  restart_at: "2026-10-01T00:00:00-03:00",
  restart_label: "1º de outubro, às 00h (horário de Brasília)",
  stamps: "neutral",
  participant: null,
  how_it_works: "Quatro pedidos válidos no mesmo mês geram um crédito.",
  benefit: "Escolha um pão de 500 g de qualquer tipo da vitrine.",
};

const partialStatus = {
  ...visitorStatus,
  preview: true,
  stamps: "progress",
  participant: {
    kind: "partial",
    valid_orders: 2,
    cycle_size: 4,
    credits: 0,
    progress_label: "2 de 4 pedidos válidos neste mês",
    remaining_label: "Faltam 2 para conquistar seu próximo crédito.",
    restart_label: "1º de outubro, às 00h (horário de Brasília)",
    credits_label: "Créditos disponíveis: 0.",
  },
};

const creditStatus = {
  ...partialStatus,
  participant: {
    kind: "credit",
    valid_orders: 4,
    cycle_size: 4,
    credits: 1,
    progress_label: "4 pedidos válidos neste mês · 1 crédito conquistado · 0 de 4 para o próximo",
    remaining_label: "Você tem 1 crédito para escolher um pão da vitrine.",
    restart_label: "1º de outubro, às 00h (horário de Brasília)",
    credits_label: "Créditos disponíveis: 1.",
  },
};

function json(data: unknown, status = 200) {
  return {
    ok: status < 400,
    status,
    json: async () => data,
    text: async () => JSON.stringify(data),
  };
}

function mockShop(options?: { preview?: boolean; signupMessage?: string }) {
  const preview = options?.preview === true;
  return vi.fn(async (input: RequestInfo, init?: RequestInit) => {
    const url = String(input);
    if (url.includes("/operations")) {
      return json({
        preview_protection: preview,
        orders_enabled: true,
        payments_enabled: true,
        date_requests_enabled: true,
        house_fidelity_active: false,
        message: null,
      });
    }
    if (url.includes("/promotions/house-fidelity/signup") && init?.method === "POST") {
      const body = JSON.parse(String(init.body ?? "{}")) as { name?: string; email?: string; cpf?: string };
      expect(body.cpf).toBe("529.982.247-25");
      return json({
        ...visitorStatus,
        preview,
        ok: true,
        needs_verification: true,
        contact_name: body.name,
        contact_email: body.email,
        message: options?.signupMessage ?? "Se este cadastro puder ser confirmado, enviamos um código",
      });
    }
    if (url.includes("/promotions/house-fidelity/resume") && init?.method === "POST") {
      const body = JSON.parse(String(init.body ?? "{}")) as { email?: string; cpf?: string };
      expect(body.cpf).toBeUndefined();
      return json({
        ...visitorStatus,
        preview,
        ok: true,
        needs_verification: true,
        contact_email: body.email,
        message: "retomada por e-mail, sem saldo por CPF",
      });
    }
    if (url.includes("/promotions/house-fidelity")) {
      if (preview && url.includes("demo=partial")) {
        return json(partialStatus);
      }
      if (preview && url.includes("demo=credit")) {
        return json(creditStatus);
      }
      return json({ ...visitorStatus, preview });
    }
    return json({ detail: "não encontrado" }, 404);
  });
}

describe("peça fidelidade da casa", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  it("mostra a chamada aprovada, CTAs no corpo e carimbos neutros para visitante", async () => {
    vi.stubGlobal("fetch", mockShop());
    render(
      <CartProvider>
        <HouseFidelityPanel />
      </CartProvider>,
    );
    const piece = await screen.findByRole("article", { name: /Seu quarto pedido traz um pão de presente/ });
    expect(within(piece).getByText("Fidelidade da casa · participação gratuita")).toBeInTheDocument();
    expect(within(piece).getByText(/Focaccias não participam/)).toBeInTheDocument();
    const actions = piece.querySelector(".house-fidelity-actions");
    expect(actions).not.toBeNull();
    expect(within(actions as HTMLElement).getByRole("button", { name: "Quero participar" })).toBeInTheDocument();
    expect(within(actions as HTMLElement).getByRole("button", { name: "Já tenho cadastro" })).toBeInTheDocument();
    expect(piece.querySelector("details")?.textContent).not.toContain("Quero participar");
    expect(screen.getByLabelText(/não representa saldo/)).toBeInTheDocument();
    expect(screen.getByText("1º pedido")).toBeInTheDocument();
    expect(screen.getByText("4º → crédito")).toBeInTheDocument();
    await userEvent.click(screen.getByText("Como funciona"));
    expect(screen.queryByText(/ainda serão definidos/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Ainda a definir antes do lançamento/)).not.toBeInTheDocument();
    expect(screen.getByText(/créditos já conquistados continuam/i)).toBeInTheDocument();
    expect(screen.queryByText("Voltar tem outro sabor.")).not.toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("abre o cadastro no corpo, valida CPF localmente e preserva o carrinho", async () => {
    const user = userEvent.setup();
    localStorage.setItem(
      SELECTION_KEY,
      JSON.stringify([{ key: "k1", slug: "pao-da-casa", variantId: "v500", quantity: 2 }]),
    );
    const fetchMock = mockShop({ signupMessage: "sessão preservada, campanha fechada" });
    vi.stubGlobal("fetch", fetchMock);
    render(
      <CartProvider>
        <HouseFidelityPanel />
      </CartProvider>,
    );
    await user.click(await screen.findByRole("button", { name: "Quero participar" }));
    expect(screen.getByLabelText("Nome")).toBeInTheDocument();
    expect(screen.getByLabelText("CPF")).toBeInTheDocument();
    await user.type(screen.getByLabelText("Nome"), "Ana");
    await user.type(screen.getByLabelText("E-mail"), "ana@example.com");
    await user.type(screen.getByLabelText("CPF"), "11111111111");
    await user.click(screen.getByRole("button", { name: "Enviar cadastro" }));
    expect(await screen.findByText(/Informe um CPF válido/)).toBeInTheDocument();
    expect(fetchMock.mock.calls.some((call) => String(call[0]).includes("/signup"))).toBe(false);
    await user.clear(screen.getByLabelText("CPF"));
    await user.type(screen.getByLabelText("CPF"), "52998224725");
    await user.click(screen.getByRole("button", { name: "Enviar cadastro" }));
    expect(await screen.findByText("sessão preservada, campanha fechada")).toBeInTheDocument();
    expect(screen.getByLabelText("Código de verificação")).toBeInTheDocument();
    expect(screen.queryByText("Cadastro concluído")).not.toBeInTheDocument();
    expect(JSON.parse(localStorage.getItem(SELECTION_KEY) ?? "[]")).toHaveLength(1);
    expect(JSON.parse(sessionStorage.getItem("lojadepaes_contact") ?? "{}").email).toBe("ana@example.com");
    vi.unstubAllGlobals();
  });

  it("retoma por e-mail e recusa saldo só com CPF", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", mockShop());
    render(
      <CartProvider>
        <HouseFidelityPanel />
      </CartProvider>,
    );
    await user.click(await screen.findByRole("button", { name: "Já tenho cadastro" }));
    expect(screen.queryByLabelText("CPF")).not.toBeInTheDocument();
    await user.type(screen.getByLabelText("E-mail do cadastro"), "ana@example.com");
    await user.click(screen.getByRole("button", { name: "Continuar" }));
    expect(await screen.findByText(/sem saldo por CPF/)).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("mostra progresso demonstrativo só com prévia protegida", async () => {
    sessionStorage.setItem("lojadepaes_fidelity_demo", "partial");
    vi.stubGlobal("fetch", mockShop({ preview: true }));
    const { unmount } = render(
      <CartProvider>
        <HouseFidelityPanel />
      </CartProvider>,
    );
    expect(await screen.findByText("2 de 4 pedidos válidos neste mês", { exact: false })).toBeInTheDocument();
    expect(screen.getByText(/1º de outubro/)).toBeInTheDocument();
    unmount();
    sessionStorage.setItem("lojadepaes_fidelity_demo", "credit");
    vi.stubGlobal("fetch", mockShop({ preview: true }));
    render(
      <CartProvider>
        <HouseFidelityPanel />
      </CartProvider>,
    );
    expect(await screen.findByText(/1 crédito conquistado/)).toBeInTheDocument();
    expect(screen.getByText(/Créditos disponíveis: 1/)).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("ignora estado demonstrativo fora da prévia", async () => {
    sessionStorage.setItem("lojadepaes_fidelity_demo", "credit");
    vi.stubGlobal("fetch", mockShop({ preview: false }));
    render(
      <CartProvider>
        <HouseFidelityPanel />
      </CartProvider>,
    );
    await screen.findByRole("button", { name: "Quero participar" });
    await waitFor(() => {
      expect(screen.queryByText(/1 crédito conquistado/)).not.toBeInTheDocument();
    });
    expect(screen.getByLabelText(/não representa saldo/)).toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});
