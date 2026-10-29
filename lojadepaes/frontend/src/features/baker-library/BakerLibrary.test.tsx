import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ArticlePage } from "./ArticlePage";
import { CalculatorPage } from "./CalculatorPage";
import { Root } from "../../app/Root";

describe("Biblioteca do padeiro", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo, init?: RequestInit) => {
        const url = String(input);
        const method = String(init?.method || "GET").toUpperCase();
        if (url.includes("/api/v1/biblioteca/artigos/o-comeco")) {
          return {
            ok: true,
            json: async () => ({
              slug: "o-comeco",
              kicker: "01 / O começo",
              title: "Levain e a porcentagem de padeiro",
              summary: "Cultura e fórmula.",
              reading_label: "Leitura · 8 min",
              href: "/biblioteca/o-comeco",
              photo: { src: "/images/internal%20levain%201%20bread.png", alt: "Levain" },
              calculator_href: "/biblioteca/calculadora",
              version: 1,
              body_markdown: "Texto livre.\n\nUse a [calculadora](/biblioteca/calculadora).",
              sources: [{ label: "Hamelman, Bread", detail: "Porcentagem de padeiro." }],
            }),
          };
        }
        if (url.includes("/api/v1/biblioteca/plano")) {
          return {
            ok: true,
            json: async () => ({
              configured: false,
              checkout_ready: false,
              source: "hub",
              period: "mensal",
              message: "Os planos da Biblioteca ainda não estão publicados no editor do ActionHub.",
              authorized_initial_brl: 19,
              authorized_complementary_brl: 10,
              principal: { price: 19, credits: 20, period: "mês" },
              complementary: { price: 10, credits: 10, period: "avulso" },
              pack: { price: 10, credits: 10, period: "avulso" },
              plans_href: "http://127.0.0.1:4000/loja?return_origin=http://127.0.0.1:5175&return_to=%2F%23biblioteca",
              benefits: ["Aprofundamento personalizado com o Gigio na Biblioteca."],
            }),
          };
        }
        if (url.includes("/api/v1/biblioteca/acesso") || url.includes("/api/v1/conta/situacao")) {
          return { ok: true, json: async () => ({ identified: false, authorized: false, subscription_status: "none" }) };
        }
        if (url.includes("/api/v1/biblioteca/calculadora") && method === "POST") {
          return {
            ok: true,
            json: async () => ({
              mode: "from_flour",
              flour_g: 1000,
              hydration_pct: 70,
              salt_pct: 2,
              preferment_flour_pct: 20,
              levain_hydration_pct: 100,
              levain_mode: "pff",
              final_mix: { flour_g: 800, water_g: 500, salt_g: 20, levain_g: 400, extras: [] },
              levain: { flour_g: 200, water_g: 200, weight_g: 400 },
              totals: { flour_g: 1000, water_g: 700, salt_g: 20, levain_g: 400, dough_g: 1720 },
              notes: ["A farinha do levain já está na farinha total."],
            }),
          };
        }
        return { ok: false, status: 404, json: async () => ({}) };
      }),
    );
  });

  afterEach(() => {
    window.history.pushState({}, "", "/");
    vi.unstubAllGlobals();
  });

  it("abre o artigo com calculadora e oferta sem checkout ambíguo", async () => {
    render(<ArticlePage slug="o-comeco" />);
    expect(await screen.findByRole("heading", { name: "Levain e a porcentagem de padeiro" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Abrir a calculadora" })).toHaveAttribute("href", "/biblioteca/calculadora");
    expect(screen.getByText(/Hamelman/)).toBeInTheDocument();
    expect(await screen.findByText(/ainda não estão publicados/i)).toBeInTheDocument();
    expect(screen.getByText(/R\$ 19,00 \/ mês/)).toBeInTheDocument();
    expect(screen.getByText(/R\$ 10,00 \/ avulso/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Assinar pelo ActionHub/ })).toBeNull();
    expect(screen.queryByLabelText(/E-mail/i)).toBeNull();
    expect(screen.getByRole("link", { name: "Ver planos" })).toHaveAttribute("href", expect.stringContaining("/loja"));
  });

  it("calcula 1720 g sem contar o levain duas vezes", async () => {
    const user = userEvent.setup();
    render(<CalculatorPage />);
    await user.click(screen.getByRole("button", { name: "Calcular" }));
    expect(await screen.findByText(/Massa final:/)).toHaveTextContent("1720 g");
    expect(screen.getByText(/800 g de farinha/)).toBeInTheDocument();
  });

  it("rota da calculadora não mistura com o checkout de pão", () => {
    window.history.pushState({}, "", "/biblioteca/calculadora");
    render(<Root />);
    expect(screen.getByRole("heading", { name: "Porcentagem de padeiro" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /Revisar pedido/ })).toBeNull();
  });
});
