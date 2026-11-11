import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { GestaoContext } from "../contexto";
import type { Comanda as Folha, SessaoInfo } from "../lib/api";
import { Comanda } from "./Comanda";

vi.mock("../lib/api", async () => {
  const atual = await vi.importActual<typeof import("../lib/api")>("../lib/api");
  return { ...atual, carregarComanda: vi.fn(), imprimirComanda: vi.fn() };
});

import { carregarComanda } from "../lib/api";

const SESSAO: SessaoInfo = {
  usuario: "ana",
  nome: "Ana",
  admin_plataforma: false,
  papel: "dono",
  permissoes: ["ver_estoque", "lancar"],
  csrf: "c",
  fuso: "America/Sao_Paulo",
  organizacao: null,
  organizacoes: [],
  precisa_escolher_organizacao: false,
};

describe("comanda 014B", () => {
  it("lista as referências da Loja e não mostra nome nem e-mail", async () => {
    const folha: Folha = {
      data: "2026-11-11",
      fornada: { id: "f", nome: "Manhã", horario: "05:00", ordem: 1, ativa: true },
      numero: 1,
      via: 0,
      via_rotulo: null,
      impressa_em: null,
      impressa_por: null,
      produtos: [
        {
          ordem_id: "o",
          produto: "Pão country",
          unidades: 112,
          origens: "100 programadas + 12 da Loja",
          loja: [
            { referencia: "LPA39746B92A", unidades: 2 },
            { referencia: "SD10X9", unidades: 10 },
          ],
          por_unidade: true,
          pecas: "Peças de 568 g",
          massa: "36,65 kg",
          sem_receita: false,
          aviso: null,
          modo_fazer: [],
          observacao: null,
          customer_name: "NOME-SINTETICO",
          customer_email: "sintetico@example.invalid",
          linhas: [
            {
              nome: "Farinha de trigo",
              funcao: "massa",
              funcao_rotulo: "Massa",
              quantidade_g: "11200",
              texto: "11,20 kg",
              componente: false,
              filhos: [],
            },
          ],
        },
      ],
      pesagem: [{ nome: "Levain · inóculo", quantidade_g: "50", texto: "50 g" }],
    };
    vi.mocked(carregarComanda).mockResolvedValue(folha as Folha);
    render(
      <GestaoContext.Provider
        value={{
          sessao: SESSAO,
          search: "?data=2026-11-11&fornada=f",
          navegar: vi.fn(),
          atualizarFluxo: () => {},
          pode: () => true,
        }}
      >
        <Comanda />
      </GestaoContext.Provider>,
    );
    expect(await screen.findByText("112 un")).toBeInTheDocument();
    expect(screen.getByText("(100 programadas + 12 da Loja)")).toBeInTheDocument();
    expect(screen.getByText("Loja: LPA39746B92A (2), SD10X9 (10)")).toBeInTheDocument();
    const html = document.body.innerHTML;
    expect(html).not.toContain("NOME-SINTETICO");
    expect(html).not.toContain("sintetico@example.invalid");
    expect(html).not.toMatch(/customer_name|customer_email|@example/);
  });
});
