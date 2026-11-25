import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Partner } from "../admin/marketplace/types";
import { PartnerOrders } from "./PartnerOrders";
import { PartnerPayout } from "./PartnerPayout";
import { partnerApi, type PartnerOrder } from "./partnerApi";

const partner: Partner = {
  id: "p1",
  partner_type: "producer",
  brand_name: "Queijaria Serra Clara",
  brand_slug: "queijaria-serra-clara",
  logo_url: "",
  photo_url: "",
  story: "",
  city: "Guaramiranga",
  region: "Ceará",
  highlight_hex: "#2F5D3A",
  document: "00",
  contact: "Ana",
  status: "active",
  fee_cents: 250,
  mp_connected: false,
};

const assign = vi.fn();

beforeEach(() => {
  Object.defineProperty(window, "location", {
    value: { ...window.location, assign, search: "", pathname: "/parceiro/recebimento" },
    writable: true,
  });
});
afterEach(() => {
  vi.restoreAllMocks();
  assign.mockReset();
});

describe("recebimento do parceiro", () => {
  it("sem conta: explica e leva ao Mercado Pago", async () => {
    const user = userEvent.setup();
    vi.spyOn(partnerApi, "mpStatus").mockResolvedValue({ available: true, connected: false, status: null });
    vi.spyOn(partnerApi, "mpConnect").mockResolvedValue({ url: "https://auth.mercadopago.com.br/authorization?x=1" });
    const onChanged = vi.fn();
    render(<PartnerPayout partner={partner} onBack={vi.fn()} onChanged={onChanged} />);
    expect(await screen.findByText("Nenhuma conta conectada")).toBeInTheDocument();
    expect(onChanged).toHaveBeenCalledWith({ mp_connected: false, mp_nickname: null });
    await user.click(screen.getByRole("button", { name: "Conectar ao Mercado Pago" }));
    expect(assign).toHaveBeenCalledWith("https://auth.mercadopago.com.br/authorization?x=1");
  });

  it("conectada: mostra a conta e pede confirmação para desconectar", async () => {
    const user = userEvent.setup();
    const status = vi
      .spyOn(partnerApi, "mpStatus")
      .mockResolvedValue({ available: true, connected: true, nickname: "SERRACLARA", connected_at: "2026-11-25T15:00:00Z" });
    const off = vi.spyOn(partnerApi, "mpDisconnect").mockResolvedValue(undefined);
    render(<PartnerPayout partner={partner} onBack={vi.fn()} onChanged={vi.fn()} />);
    expect(await screen.findByText("Conta conectada")).toBeInTheDocument();
    expect(screen.getByText(/Mercado Pago: SERRACLARA/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Desconectar" }));
    expect(off).not.toHaveBeenCalled();
    status.mockResolvedValue({ available: true, connected: false });
    await user.click(screen.getByRole("button", { name: "Sim, desconectar" }));
    expect(off).toHaveBeenCalled();
    expect(await screen.findByText("Nenhuma conta conectada")).toBeInTheDocument();
  });

  it("recebimento ainda desligado: avisa que abre em breve, sem botão", async () => {
    vi.spyOn(partnerApi, "mpStatus").mockResolvedValue({ available: false, connected: false });
    const onChanged = vi.fn();
    render(<PartnerPayout partner={partner} onBack={vi.fn()} onChanged={onChanged} />);
    expect(await screen.findByText("O recebimento pelo Mercado Pago abre em breve.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Conectar ao Mercado Pago" })).toBeNull();
    expect(onChanged).toHaveBeenCalledWith({ mp_connected: null, mp_nickname: null });
  });

  it("volta do Mercado Pago com erro: mensagem clara, sem código", async () => {
    window.location.search = "?mp=erro&motivo=negado";
    vi.spyOn(partnerApi, "mpStatus").mockResolvedValue({ available: true, connected: false });
    render(<PartnerPayout partner={partner} onBack={vi.fn()} onChanged={vi.fn()} />);
    expect(await screen.findByText(/Você não autorizou a conexão/)).toBeInTheDocument();
  });
});

describe("pedidos sem conta conectada", () => {
  it("confirmar fica bloqueado e o aviso leva ao recebimento", async () => {
    const user = userEvent.setup();
    const order: PartnerOrder = {
      id: "o1",
      public_reference: "PC-1",
      combo_ref: "CB-1",
      product_name: "Queijo meia cura 500 g",
      house_product_name: "Fermentação natural",
      requested_date: "2030-01-15",
      customer_name: "Ana Souza",
      address_line: "Rua A, 10",
      item_quantity: 1,
      item_cents: 5800,
      freight_cents: 1200,
      fee_cents: 250,
      status: "submitted",
    };
    vi.spyOn(partnerApi, "orders").mockResolvedValue([order]);
    const onPayout = vi.fn();
    render(<PartnerOrders partner={partner} onBack={vi.fn()} onPayout={onPayout} />);
    expect(await screen.findByRole("button", { name: "Confirmar entrega nesta data" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Conectar agora" }));
    expect(onPayout).toHaveBeenCalled();
  });
});
