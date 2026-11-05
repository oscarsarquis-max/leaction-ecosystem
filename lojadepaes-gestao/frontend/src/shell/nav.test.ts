import { describe, expect, it } from "vitest";
import { trailFor } from "./nav";

describe("trilha da barra de cima", () => {
  it("tela de primeiro nível mostra só o título, sem trilha", () => {
    for (const [caminho, titulo] of [
      ["/", "Hoje"],
      ["/entradas", "Entradas"],
      ["/ingredientes", "Ingredientes"],
      ["/gestao/locais", "Locais"],
      ["/gestao/usuarios", "Usuários"],
    ] as const) {
      expect(trailFor(caminho)).toMatchObject({ group: null, page: titulo });
    }
  });

  it("tela de segundo nível mostra de onde veio, e o celular continua com o nome da seção", () => {
    expect(trailFor("/entradas/sem-nota")).toEqual({ group: "Entradas", page: "Entrada sem nota", secao: "Entradas" });
  });
});
