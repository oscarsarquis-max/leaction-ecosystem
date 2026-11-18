import { describe, expect, it } from "vitest";
import type { Catalogo } from "./api";
import { dataIso, lembrarModo, linhasDaColagem, modoLembrado, novaLinha, numero, paraEnvio, reconhecer, usarItem } from "./entradaForm";
import { custoCalculado, dinheiro, quantidadeBase } from "./format";

const CATALOGO: Catalogo = {
  ingredientes: [{ id: "ing-1", nome: "Farinha de trigo", unidade_base: "g" }],
  itens: [
    {
      id: "item-1",
      nome: "Farinha de trigo 25 kg",
      marca: "Dona Benta",
      unidade_controle: "massa",
      conteudo_embalagem: null,
      ingrediente_id: "ing-1",
      ingrediente: "Farinha de trigo",
      unidade_base: "g",
    },
    {
      id: "item-2",
      nome: "Fermento 500 g",
      marca: "",
      unidade_controle: "embalagem",
      conteudo_embalagem: 500,
      ingrediente_id: "ing-2",
      ingrediente: "Fermento",
      unidade_base: "g",
    },
  ],
  locais: [{ id: "loc", nome: "Despensa", padrao: true }],
};

describe("números e datas digitados à brasileira", () => {
  it("entende vírgula, ponto de milhar e R$", () => {
    expect(numero("12,5")).toBe(12.5);
    expect(numero("1.234,56")).toBe(1234.56);
    expect(numero("R$ 4,50")).toBe(4.5);
    expect(numero("4.5")).toBe(4.5);
    expect(numero("")).toBeNull();
    expect(numero("abc")).toBeNull();
  });

  it("converte datas de planilha para o formato do servidor", () => {
    expect(dataIso("02/11/2026")).toBe("2026-11-02");
    expect(dataIso("2/1/27")).toBe("2027-01-02");
    expect(dataIso("2026-11-02")).toBe("2026-11-02");
    expect(dataIso("amanhã")).toBe("");
  });

  it("escreve quantidades e dinheiro como a pessoa lê", () => {
    expect(quantidadeBase(25000, "g")).toBe("25 kg");
    expect(quantidadeBase(600, "g")).toBe("600 g");
    expect(quantidadeBase(1500, "ml")).toBe("1,5 L");
    expect(quantidadeBase(12, "un")).toBe("12 un");
    expect(dinheiro(112.5).replace(/\s/g, " ")).toBe("R$ 112,50");
  });
});

describe("colar de uma planilha", () => {
  it("cria uma linha por linha colada, na ordem da tela", () => {
    const texto = [
      "Açúcar cristal 5 kg\tAçúcar cristal\tUnião\t3\tkg\t\tL01\t15/03/2027\t4,20",
      "Sal\tSal\t\t2\tpacote\t1000\t\tsem validade\t",
    ].join("\n");
    const linhas = linhasDaColagem(texto, CATALOGO);
    expect(linhas).toHaveLength(2);
    expect(linhas[0]).toMatchObject({
      itemTexto: "Açúcar cristal 5 kg",
      ingredienteTexto: "Açúcar cristal",
      marca: "União",
      quantidade: "3",
      unidade: "kg",
      lote: "L01",
      validade: "2027-03-15",
      custo: "4,20",
    });
    expect(linhas[1]).toMatchObject({ unidade: "emb", conteudo: "1000", semValidade: true });
  });

  it("ignora linhas em branco e reconhece o item que já existe", () => {
    const linhas = linhasDaColagem("\nFarinha de trigo 25 kg — Dona Benta\t\t\t5\tkg\n\n", CATALOGO);
    expect(linhas).toHaveLength(1);
    expect(linhas[0].itemId).toBe("item-1");
    expect(linhas[0].ingredienteTexto).toBe("Farinha de trigo");
  });
});

describe("item que já existe trava o resto", () => {
  it("reconhece pelo nome exato e copia ingrediente, unidade e conteúdo", () => {
    const l = reconhecer({ ...novaLinha(), itemTexto: "fermento 500 g" }, CATALOGO);
    expect(l.itemId).toBe("item-2");
    expect(l.unidade).toBe("emb");
    expect(l.conteudo).toBe("500");
    expect(l.ingredienteId).toBe("ing-2");
  });

  it("mantém a unidade escolhida se ela serve ao item", () => {
    const l = usarItem({ ...novaLinha(), unidade: "g" }, "item-1", CATALOGO);
    expect(l.unidade).toBe("g");
    const outra = usarItem({ ...novaLinha(), unidade: "ml" }, "item-1", CATALOGO);
    expect(outra.unidade).toBe("kg");
  });
});

describe("envio ao servidor", () => {
  it("item novo leva o ingrediente já escolhido e nunca cria ingrediente", () => {
    const l = {
      ...novaLinha(),
      itemTexto: "Farinha integral 1 kg",
      ingredienteTexto: "Farinha integral",
      marca: "X",
      quantidade: "2",
      unidade: "kg",
      custo: "7,5",
      validade: "2027-01-10",
      ingredienteId: "ing-1",
      decisaoItem: "novo" as const,
    };
    const envio = paraEnvio(l, CATALOGO, "preco_unidade");
    expect(envio).toMatchObject({
      item_id: null,
      item_nome: "Farinha integral 1 kg",
      unidade_controle: "massa",
      ingrediente_id: "ing-1",
      decisao_item: "novo",
      quantidade: 2,
      custo: 7.5,
      validade: "2027-01-10",
      sem_validade: false,
    });
  });

  it("o valor pago vai como valor_pago e o preço por unidade vai como custo: nunca os dois", () => {
    const l = { ...novaLinha(), itemTexto: "Farinha sarraceno", quantidade: "0,5", unidade: "kg", custo: "22,99" };
    expect(paraEnvio(l, CATALOGO)).toMatchObject({ valor_pago: 22.99, custo: null }); // o padrão é o valor pago
    expect(paraEnvio(l, CATALOGO, "valor_pago")).toMatchObject({ valor_pago: 22.99, custo: null });
    expect(paraEnvio(l, CATALOGO, "preco_unidade")).toMatchObject({ valor_pago: null, custo: 22.99 });
    // "Não sei": sem custo nos dois modos
    const sem = { ...l, custo: "" };
    expect(paraEnvio(sem, CATALOGO, "valor_pago")).toMatchObject({ valor_pago: null, custo: null });
    expect(paraEnvio(sem, CATALOGO, "preco_unidade")).toMatchObject({ valor_pago: null, custo: null });
  });

  it("a colagem guarda o custo como veio; o modo só entra na hora de enviar", () => {
    const [linha] = linhasDaColagem("Farinha sarraceno\t\t\t0,5\tkg\t\t\tsem validade\t22,99", CATALOGO);
    expect(linha.custo).toBe("22,99");
    expect(paraEnvio(linha, CATALOGO, "valor_pago")).toMatchObject({ valor_pago: 22.99, custo: null });
    expect(paraEnvio(linha, CATALOGO, "preco_unidade")).toMatchObject({ valor_pago: null, custo: 22.99 });
  });

  it("o modo do custo é lembrado; sem escolha, vale o valor pago", () => {
    window.localStorage.clear();
    expect(modoLembrado()).toBe("valor_pago");
    lembrarModo("preco_unidade");
    expect(modoLembrado()).toBe("preco_unidade");
    lembrarModo("valor_pago");
    expect(modoLembrado()).toBe("valor_pago");
  });

  it("item que existe manda só o id, a quantidade e a unidade", () => {
    const l = usarItem({ ...novaLinha(), quantidade: "3", semValidade: true }, "item-1", CATALOGO);
    const envio = paraEnvio(l, CATALOGO);
    expect(envio.item_id).toBe("item-1");
    expect(envio.item_nome).toBe("");
    expect(envio.ingrediente_id).toBeNull();
    expect(envio.sem_validade).toBe(true);
    expect(envio.validade).toBeNull();
  });
});

describe("custo calculado embaixo do campo", () => {
  const sem = (s: string) => s.replace(/\s+/g, " ");
  it("0,5 kg por R$ 22,99 dá R$ 45,98/kg", () => {
    expect(sem(custoCalculado(22.99 / 500, "g"))).toBe("= R$ 45,98/kg");
  });
  it("1 embalagem de 500 g por R$ 22,99 dá R$ 22,99/emb · R$ 45,98/kg", () => {
    expect(sem(custoCalculado(22.99 / 500, "g", 22.99))).toBe("= R$ 22,99/emb · R$ 45,98/kg");
  });
  it("volume em L e unidade em un", () => {
    expect(sem(custoCalculado(0.012, "ml"))).toBe("= R$ 12,00/L");
    expect(sem(custoCalculado(1.5, "un"))).toBe("= R$ 1,50/un");
  });
});
