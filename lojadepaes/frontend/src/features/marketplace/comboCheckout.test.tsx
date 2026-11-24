import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../../services/http";
import { ComboCheckoutPage } from "./ComboCheckoutPage";
import { ComboOrderPage } from "./ComboOrderPage";
import { fetchCombo, fetchComboOrder, partnerDelivers, partnerEarliestDate, submitComboOrder, type ComboSummary } from "./comboApi";

vi.mock("./comboApi", async () => {
  const actual = await vi.importActual<typeof import("./comboApi")>("./comboApi");
  return { ...actual, fetchCombo: vi.fn(), submitComboOrder: vi.fn(), fetchComboOrder: vi.fn() };
});
vi.mock("../../components/StorefrontLayout", () => ({
  StorefrontLayout: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
vi.mock("../../shop/BakeCalendar", () => ({
  BakeCalendar: ({ onSelectDate }: { onSelectDate: (date: string) => void }) => (
    <button type="button" onClick={() => onSelectDate("2030-01-15")}>
      escolher 15/01
    </button>
  ),
}));

const brand = { brand_name: "Queijaria Serra Clara", brand_slug: "queijaria-serra-clara", highlight_hex: "#2F5D3A", logo_url: "" };
const combo: ComboSummary = {
  id: "c1",
  reason: "Para a mesa do domingo.",
  bread: { slug: "fermentacao-natural", name: "Fermentação natural", variants: [{ id: "v1", name: "800 g", price_cents: 3600 }] },
  product: { id: "x1", name: "Queijo meia cura 500 g", description: "", photos: [], price_cents: 5800 },
  partner: brand,
  delivery: { cities: ["Fortaleza"], districts: [], days: 2, freight_cents: 1200, perishable: true },
};

const assign = vi.fn();

beforeEach(() => {
  vi.mocked(fetchCombo).mockResolvedValue(combo);
  Object.defineProperty(window, "location", { value: { ...window.location, assign, search: "" }, writable: true });
});

afterEach(() => {
  vi.mocked(fetchCombo).mockReset();
  vi.mocked(submitComboOrder).mockReset();
  assign.mockReset();
  sessionStorage.clear();
});

async function fillAll(user: ReturnType<typeof userEvent.setup>, city = "Fortaleza") {
  await user.click(screen.getByRole("button", { name: "escolher 15/01" }));
  await user.type(screen.getByLabelText(/Rua/), "Rua A");
  await user.type(screen.getByLabelText(/Número/), "10");
  await user.type(screen.getByLabelText(/Bairro/), "Centro");
  await user.type(screen.getByLabelText(/Cidade/), city);
  await user.selectOptions(screen.getByLabelText(/Estado/), "CE");
  await user.type(screen.getByLabelText(/CEP/), "60000000");
  await user.type(screen.getByLabelText("Nome de quem pede"), "Ana Souza");
  await user.type(screen.getByLabelText("E-mail para acompanhar o pedido"), "ana@exemplo.test");
}

describe("checkout da combo", () => {
  it("mostra o resumo pelos preços de face, sem taxa, e avisa que nada é cobrado agora", async () => {
    render(<ComboCheckoutPage comboId="c1" />);
    const summary = await screen.findByRole("complementary", { name: "Sua combo" });
    expect(within(summary).getByText("R$ 114,00")).toBeInTheDocument();
    expect(within(summary).getByText("R$ 8,00")).toBeInTheDocument();
    expect(within(summary).getByText("R$ 12,00")).toBeInTheDocument();
    expect(screen.queryByText(/taxa|2,50|acordo/i)).toBeNull();
    expect(screen.getByText(/Nada é cobrado agora/)).toBeInTheDocument();
  });

  it("valida data, endereço e cidade atendida pelo parceiro", async () => {
    const user = userEvent.setup();
    render(<ComboCheckoutPage comboId="c1" />);
    await screen.findByRole("complementary", { name: "Sua combo" });
    await user.click(screen.getByRole("button", { name: "Enviar pedido da combo" }));
    expect(screen.getByText("Escolha a data da fornada no calendário.")).toBeInTheDocument();
    await fillAll(user, "Recife");
    await user.click(screen.getByRole("button", { name: "Enviar pedido da combo" }));
    expect(screen.getByText("Queijaria Serra Clara entrega em Fortaleza.")).toBeInTheDocument();
    expect(submitComboOrder).not.toHaveBeenCalled();
  });

  it("envia com o total visto e vai para o acompanhamento", async () => {
    const user = userEvent.setup();
    vi.mocked(submitComboOrder).mockResolvedValue({ combo_ref: "CB-1", token: "tok" });
    render(<ComboCheckoutPage comboId="c1" />);
    await screen.findByRole("complementary", { name: "Sua combo" });
    await fillAll(user);
    await user.click(screen.getByRole("button", { name: "Enviar pedido da combo" }));
    expect(submitComboOrder).toHaveBeenCalledWith(
      "c1",
      expect.objectContaining({ variant_id: "v1", bread_quantity: 1, item_quantity: 1, requested_date: "2030-01-15", quoted_cents: 11400, delivery_city: "Fortaleza" }),
    );
    expect(assign).toHaveBeenCalledWith("/combo/pedido/CB-1?t=tok");
  });

  it("preço do acordo por pão e quantidades entram no total e no envio", async () => {
    const user = userEvent.setup();
    vi.mocked(fetchCombo).mockResolvedValue({ ...combo, house_unit_price_cents: 3000 });
    vi.mocked(submitComboOrder).mockResolvedValue({ combo_ref: "CB-2", token: "tok" });
    render(<ComboCheckoutPage comboId="c1" />);
    const summary = await screen.findByRole("complementary", { name: "Sua combo" });
    expect(within(summary).getByText("R$ 30,00 cada")).toBeInTheDocument();
    await user.click(within(summary).getByRole("button", { name: "Aumentar quantidade de pães" }));
    await user.click(within(summary).getByRole("button", { name: "Aumentar quantidade de pães" }));
    await user.click(within(summary).getByRole("button", { name: "Aumentar quantidade de queijo meia cura 500 g" }));
    // 3 × 30 + 8 (frete Loja) + 2 × 58 + 12 (frete parceiro) = 226
    expect(within(summary).getByText("R$ 226,00")).toBeInTheDocument();
    expect(within(summary).getByText("R$ 90,00")).toBeInTheDocument();
    expect(within(summary).getByText("R$ 116,00")).toBeInTheDocument();
    expect(screen.queryByText(/taxa|2,50|acordo/i)).toBeNull();
    await fillAll(user);
    await user.click(screen.getByRole("button", { name: "Enviar pedido da combo" }));
    expect(submitComboOrder).toHaveBeenCalledWith(
      "c1",
      expect.objectContaining({ bread_quantity: 3, item_quantity: 2, quoted_cents: 22600 }),
    );
  });

  it("quantidade fica entre 1 e o máximo da combo", async () => {
    const user = userEvent.setup();
    render(<ComboCheckoutPage comboId="c1" />);
    const summary = await screen.findByRole("complementary", { name: "Sua combo" });
    expect(within(summary).getByRole("button", { name: "Diminuir quantidade de pães" })).toBeDisabled();
    const more = within(summary).getByRole("button", { name: "Aumentar quantidade de pães" });
    for (let i = 0; i < 12; i += 1) await user.click(more);
    expect(more).toBeDisabled();
    expect(within(within(summary).getByRole("group", { name: "Quantidade de pães" })).getByText("10")).toBeInTheDocument();
  });

  it("preço mudou (409) avisa e não sai da página", async () => {
    const user = userEvent.setup();
    vi.mocked(submitComboOrder).mockRejectedValue(new ApiError(409, "preço mudou"));
    render(<ComboCheckoutPage comboId="c1" />);
    await screen.findByRole("complementary", { name: "Sua combo" });
    await fillAll(user);
    await user.click(screen.getByRole("button", { name: "Enviar pedido da combo" }));
    expect(await screen.findByText(/O preço ou a data mudaram/)).toBeInTheDocument();
    expect(assign).not.toHaveBeenCalled();
  });

  it("combo indisponível (404) mostra a saída para a loja", async () => {
    vi.mocked(fetchCombo).mockRejectedValue(new ApiError(404, "não encontrado"));
    render(<ComboCheckoutPage comboId="c9" />);
    expect(await screen.findByText("Esta combo não está disponível")).toBeInTheDocument();
  });
});

describe("acompanhamento da combo", () => {
  it("mostra cada parte com o seu status e o total", async () => {
    vi.mocked(fetchComboOrder).mockResolvedValue({
      combo_ref: "CB-1",
      requested_date: "2030-01-15",
      total_cents: 11400,
      house: { public_reference: "LP-100", status: "submitted", status_label: "Em avaliação pela Loja", amount_cents: 4650, order_url: "/pedido/LP-100?t=a" },
      partners: [
        { id: "p1", public_reference: "PC-1", brand, product_name: "Queijo meia cura 500 g", status: "refused", amount_cents: 6750, refuse_reason: "Sem estoque" },
      ],
    });
    render(<ComboOrderPage reference="CB-1" token="tok" />);
    expect(await screen.findByText("Pedido recebido")).toBeInTheDocument();
    expect(screen.getByText("Em avaliação pela Loja")).toBeInTheDocument();
    expect(screen.getByText("Recusado")).toBeInTheDocument();
    expect(screen.getByText(/Sem estoque\. Este item não vai sair/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Acompanhar o pedido do pão" })).toHaveAttribute("href", "/pedido/LP-100?t=a");
    expect(screen.getByText("R$ 114,00")).toBeInTheDocument();
  });
});

describe("regras de entrega do parceiro", () => {
  it("cidade sem acento e prazo mínimo", () => {
    expect(partnerDelivers(combo.delivery, "fortaleza ", "")).toBe(true);
    expect(partnerDelivers({ ...combo.delivery, cities: [] }, "Recife", "")).toBe(true);
    expect(partnerDelivers({ ...combo.delivery, cities: ["Eusébio"] }, "Eusebio", "")).toBe(true);
    expect(partnerEarliestDate(combo.delivery, "2030-01-30")).toBe("2030-02-01");
  });
});
