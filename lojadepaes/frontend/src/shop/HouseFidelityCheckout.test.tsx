import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { HouseFidelityCheckout } from "./HouseFidelityCheckout";
import type { HouseFidelityStatus } from "./houseFidelity";
import { fetchHouseFidelity } from "./houseFidelityApi";

vi.mock("./houseFidelityApi", () => ({
  fetchHouseFidelity: vi.fn(),
}));

const creditStatus: HouseFidelityStatus = {
  campaign_active: true,
  preview: false,
  restart_at: "2026-10-01T00:00:00-03:00",
  restart_label: "1º de outubro",
  stamps: "progress" as const,
  verified: true,
  name: "Ana",
  cpf_masked: "***.***.***-05",
  participant: {
    kind: "credit" as const,
    valid_orders: 0,
    cycle_size: 4,
    credits: 1,
    progress_label: "1 crédito disponível",
    remaining_label: "",
    restart_label: "1º de outubro",
    credits_label: "1 crédito disponível",
  },
};

describe("oferta de crédito no fechamento", () => {
  it("pede consentimento e não aplica sozinha", async () => {
    vi.mocked(fetchHouseFidelity).mockResolvedValue(creditStatus);
    const onApply = vi.fn();
    const user = userEvent.setup();
    render(
      <HouseFidelityCheckout
        optIn={false}
        onOptIn={vi.fn()}
        applyCredit={false}
        onApplyCredit={onApply}
        creditVariantId=""
        onCreditVariantId={vi.fn()}
        eligibleItems={[
          { variant_id: "v1", product_name: "Pão de fermentação", variant_name: "500 g", unit_cents: 2490 },
        ]}
        creditNotice={null}
        creditLabel={null}
        quoteReady
      />,
    );
    expect(await screen.findByText(/Você tem 1 crédito disponível/)).toBeInTheDocument();
    expect(screen.getByText(/Vale um pão de 500 g da vitrine/)).toBeInTheDocument();
    expect(screen.getByText(/O benefício cobre 1 unidade de Pão de fermentação/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Usar meu crédito" }));
    expect(onApply).toHaveBeenCalledWith(true);
    await user.click(screen.getByRole("button", { name: "Guardar para depois" }));
    expect(onApply).toHaveBeenCalledWith(false);
  });

  it("explica quando não há pão elegível e não escolhe no silêncio", async () => {
    vi.mocked(fetchHouseFidelity).mockResolvedValue(creditStatus);
    render(
      <HouseFidelityCheckout
        optIn={false}
        onOptIn={vi.fn()}
        applyCredit={false}
        onApplyCredit={vi.fn()}
        creditVariantId=""
        onCreditVariantId={vi.fn()}
        eligibleItems={[]}
        creditNotice={null}
        creditLabel={null}
        quoteReady
      />,
    );
    expect(await screen.findByText(/Este item não participa da fidelidade/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Escolher um pão da vitrine" })).toHaveAttribute("href", "/");
    expect(screen.queryByRole("button", { name: "Usar meu crédito" })).not.toBeInTheDocument();
  });

  it("exige escolher o pão quando há mais de um elegível", async () => {
    vi.mocked(fetchHouseFidelity).mockResolvedValue({
      ...creditStatus,
      participant: {
        ...creditStatus.participant!,
        credits: 2,
        credits_label: "2 créditos disponíveis",
      },
    });
    const onApply = vi.fn();
    const user = userEvent.setup();
    render(
      <HouseFidelityCheckout
        optIn={false}
        onOptIn={vi.fn()}
        applyCredit={false}
        onApplyCredit={onApply}
        creditVariantId=""
        onCreditVariantId={vi.fn()}
        eligibleItems={[
          { variant_id: "v1", product_name: "Pão claro", variant_name: "500 g", unit_cents: 2490 },
          { variant_id: "v2", product_name: "Pão escuro", variant_name: "500 g", unit_cents: 2890 },
        ]}
        creditNotice={null}
        creditLabel={null}
        quoteReady
      />,
    );
    expect(await screen.findByText(/Você tem 2 créditos disponíveis. Quer usar 1 neste pedido/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Usar meu crédito" }));
    expect(onApply).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("Escolha qual pão de 500 g receberá o crédito.");
  });
});
