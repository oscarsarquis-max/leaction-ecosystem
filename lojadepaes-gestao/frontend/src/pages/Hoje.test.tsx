import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Hoje as HojeDados } from "../lib/api";
import { dataLonga, quando } from "../lib/format";
import { Hoje } from "./Hoje";

function base(sobrescrever: Partial<HojeDados> = {}): HojeDados {
  return {
    hoje: "2026-11-02",
    ate: "2026-11-15",
    dias: 14,
    compatibilidade: { ok: true, versao_loja: "e7b3c9a41d06", versao_conhecida: true, mensagem: null },
    fornadas: [],
    total_paes_fisicos: 0,
    ...sobrescrever,
  };
}

function servir(dados: HojeDados) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => dados }));
}

afterEach(() => vi.unstubAllGlobals());

describe("formatação de datas", () => {
  it("não volta um dia por causa do fuso", () => {
    expect(dataLonga("2026-11-03")).toBe("terça-feira, 3 de novembro");
    expect(quando("2026-11-02", "2026-11-02")).toBe("Hoje");
    expect(quando("2026-11-02", "2026-11-03")).toBe("Amanhã");
    expect(quando("2026-11-02", "2026-11-06")).toBe("Em 4 dias");
  });
});

describe("tela Hoje", () => {
  it("mostra a demanda por fornada, com totais", async () => {
    servir(
      base({
        total_paes_fisicos: 12,
        fornadas: [
          {
            data: "2026-11-03",
            paes_fisicos: 5,
            quantidade: 3,
            unidades_pendentes: 0,
            itens: [
              {
                origem: "catalogo",
                produto_ou_massa: "Pão de Fermentação Natural",
                variante_ou_forma: "Unidade",
                receita_base: "TRAD",
                quantidade: 3,
                paes_fisicos: 5,
                linhas_unidades_pendentes: 0,
              },
            ],
          },
          {
            data: "2026-11-06",
            paes_fisicos: 7,
            quantidade: 7,
            unidades_pendentes: 0,
            itens: [
              {
                origem: "criador",
                produto_ou_massa: "Massa Integral",
                variante_ou_forma: "Bola",
                receita_base: null,
                quantidade: 7,
                paes_fisicos: 7,
                linhas_unidades_pendentes: 0,
              },
            ],
          },
        ],
      }),
    );
    render(<Hoje />);
    expect(await screen.findByRole("heading", { name: "terça-feira, 3 de novembro" })).toBeInTheDocument();
    expect(screen.getByText("Amanhã")).toBeInTheDocument();
    expect(screen.getByText("Em 4 dias")).toBeInTheDocument();
    const resumo = screen.getByRole("region", { name: "Resumo do período" });
    expect(within(resumo).getByText("12")).toBeInTheDocument();
    expect(screen.getByText("Pão de Fermentação Natural")).toBeInTheDocument();
    expect(screen.getByText("Criador de pães")).toBeInTheDocument();
  });

  it("avisa quando há linhas sem quantidade de pães, em vez de mostrar zero em silêncio", async () => {
    servir(
      base({
        total_paes_fisicos: 2,
        fornadas: [
          {
            data: "2026-11-03",
            paes_fisicos: 2,
            quantidade: 5,
            unidades_pendentes: 1,
            itens: [
              {
                origem: "catalogo",
                produto_ou_massa: "Kit surpresa",
                variante_ou_forma: "Kit",
                receita_base: "TRAD",
                quantidade: 3,
                paes_fisicos: 3,
                linhas_unidades_pendentes: 1,
              },
            ],
          },
        ],
      }),
    );
    render(<Hoje />);
    expect(await screen.findByText("Unidades a confirmar")).toBeInTheDocument();
    expect(screen.getByText(/a confirmar/, { selector: ".hoje-pendente" })).toBeInTheDocument();
  });

  it("explica quando não há demanda", async () => {
    servir(base());
    render(<Hoje />);
    expect(await screen.findByText("Nenhuma demanda confirmada nos próximos 14 dias.")).toBeInTheDocument();
  });

  it("não inventa número quando a Loja não pôde ser lida", async () => {
    servir(
      base({
        compatibilidade: { ok: false, versao_loja: null, versao_conhecida: null, mensagem: "Não consegui ler os dados da Loja agora." },
      }),
    );
    render(<Hoje />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Não consegui ler os dados da Loja agora.");
    expect(screen.queryByText("Pães confirmados")).not.toBeInTheDocument();
  });

  it("mostra erro com botão de tentar de novo quando a API falha", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500, json: async () => ({}) }));
    render(<Hoje />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível carregar a demanda agora.");
    expect(screen.getByRole("button", { name: "Tentar de novo" })).toBeInTheDocument();
  });
});
