import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../../services/http";
import { fetchProductAccompaniments } from "../../shop/accompanimentsApi";
import { BreadAccompaniments } from "./BreadAccompaniments";
import { PartnerPage } from "./PartnerPage";
import { fetchBreadPartners, fetchPartnerPage } from "./publicApi";

vi.mock("./publicApi", async () => {
  const actual = await vi.importActual<typeof import("./publicApi")>("./publicApi");
  return { ...actual, fetchBreadPartners: vi.fn(), fetchPartnerPage: vi.fn() };
});
vi.mock("../../shop/accompanimentsApi", async () => {
  const actual = await vi.importActual<typeof import("../../shop/accompanimentsApi")>("../../shop/accompanimentsApi");
  return { ...actual, fetchProductAccompaniments: vi.fn() };
});
vi.mock("../../components/StorefrontLayout", () => ({
  StorefrontLayout: ({ children }: { children: React.ReactNode }) => <div data-testid="layout">{children}</div>,
}));

const offer = (id: string, name: string, category: string) => ({
  id,
  name,
  description: "",
  image_url: null,
  occasion: "",
  story_title: "",
  story_lead: "",
  why_pairs: "",
  serving_tip: "",
  price_label: null,
  price_fresh: false,
  price_as_of: null,
  outbound_href: "https://exemplo.test/oferta",
  outbound_label: "Ver no Mercado Livre",
  story_href: `/acompanhar#${id}`,
  category,
  related_product_slugs: [],
  related_breads: [],
  related_recipes: [],
});

function externalOffers() {
  vi.mocked(fetchProductAccompaniments).mockResolvedValue({
    enabled: true,
    items: [offer("o1", "Queijo do mercado", "queijos"), offer("o2", "Azeite do mercado", "azeites")],
    commission_note: null,
  } as never);
}

const brand = { brand_name: "Queijaria Serra Clara", brand_slug: "queijaria-serra-clara", highlight_hex: "#2F5D3A", logo_url: "" };
const delivery = { cities: ["Fortaleza"], districts: [], days: 2, freight_cents: 1200, perishable: true };

afterEach(() => {
  vi.clearAllMocks();
});

describe("Para acompanhar este pão", () => {
  it("com o marketplace desligado, mostra só as ofertas de hoje, sem mudança", async () => {
    externalOffers();
    vi.mocked(fetchBreadPartners).mockRejectedValue(new ApiError(404, "não encontrado"));
    render(<BreadAccompaniments slug="fermentacao-natural" breadName="Fermentação natural" breadPriceCents={3600} />);
    expect(await screen.findByText("Queijo do mercado")).toBeInTheDocument();
    expect(screen.getByText("Azeite do mercado")).toBeInTheDocument();
    expect(screen.queryByText("Dos nossos parceiros")).not.toBeInTheDocument();
    expect(screen.queryByText(/por Queijaria/)).not.toBeInTheDocument();
  });

  it("ligado: parceiro primeiro com selo, combinação com a soma, e oferta externa some só na categoria do parceiro", async () => {
    externalOffers();
    vi.mocked(fetchBreadPartners).mockResolvedValue({
      products: [
        { id: "x1", name: "Queijo meia cura 500 g", description: "", photos: [], price_cents: 5800, category: "queijos", why_pairs: "A acidez equilibra o sal.", delivery, partner: brand },
      ],
      combos: [{ id: "c1", product_id: "x1", product_name: "Queijo meia cura 500 g", reason: "Para a mesa do domingo.", price_cents: 5800, freight_cents: 1200, partner: brand }],
      covered_categories: ["queijos"],
    });
    render(<BreadAccompaniments slug="fermentacao-natural" breadName="Fermentação natural" breadPriceCents={3600} />);
    expect(await screen.findByRole("heading", { name: "Dos nossos parceiros" })).toBeInTheDocument();
    const badges = screen.getAllByRole("link", { name: /por Queijaria Serra Clara/ });
    expect(badges[0]).toHaveAttribute("href", "/parceiros/queijaria-serra-clara");
    expect(screen.getByText("a partir de R$ 106,00")).toBeInTheDocument();
    expect(screen.getByText("Fortaleza · em até 2 dias · frete R$ 12,00")).toBeInTheDocument();
    expect(await screen.findByText("Azeite do mercado")).toBeInTheDocument();
    expect(screen.queryByText("Queijo do mercado")).not.toBeInTheDocument();
  });
});

describe("página do parceiro", () => {
  it("desligada ou inexistente, mostra o que a rota mostrava antes", async () => {
    vi.mocked(fetchPartnerPage).mockRejectedValue(new ApiError(404, "não encontrado"));
    render(<PartnerPage slug="qualquer" fallback={<p>página de antes</p>} />);
    expect(await screen.findByText("página de antes")).toBeInTheDocument();
  });

  it("mostra a marca, a entrega do parceiro e os pães que combinam", async () => {
    vi.mocked(fetchPartnerPage).mockResolvedValue({
      partner: { ...brand, photo_url: "", story: "Queijos de leite cru da serra.", city: "Guaramiranga", region: "Ceará" },
      products: [
        {
          id: "x1",
          name: "Queijo meia cura 500 g",
          description: "Maturado 30 dias.",
          photos: [],
          price_cents: 5800,
          category: "queijos",
          delivery,
          pairings: [{ house_product_slug: "fermentacao-natural", house_product_name: "Fermentação natural", reason: "a acidez equilibra o sal" }],
        },
      ],
      combos: [],
    });
    render(<PartnerPage slug="queijaria-serra-clara" fallback={<p>página de antes</p>} />);
    expect(await screen.findByRole("heading", { level: 1, name: "Queijaria Serra Clara" })).toBeInTheDocument();
    expect(screen.getByText("A Loja de Pães apresenta")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Entrega feita por Queijaria Serra Clara" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Fermentação natural" })).toHaveAttribute("href", "/paes/fermentacao-natural");
    expect(screen.queryByText("página de antes")).not.toBeInTheDocument();
  });
});
