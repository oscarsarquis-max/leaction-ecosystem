import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, definirCsrf, lancarEntrada, listarEntradas, textoDoErro } from "./api";

function resposta(status: number, corpo: unknown) {
  return { ok: status >= 200 && status < 300, status, json: async () => corpo };
}

afterEach(() => vi.unstubAllGlobals());

describe("erros do servidor", () => {
  it("lê detail em texto, em objeto {codigo, mensagem} e em lista do Pydantic", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(resposta(409, { detail: { codigo: "ultimo_dono", mensagem: "Precisa de um dono." } })));
    const erro = (await listarEntradas("todas").catch((e) => e)) as ApiError;
    expect(erro).toBeInstanceOf(ApiError);
    expect(erro.status).toBe(409);
    expect(erro.codigo).toBe("ultimo_dono");
    expect(textoDoErro(erro)).toBe("Precisa de um dono.");

    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(resposta(422, { detail: [{ loc: ["body"], msg: "x" }] })));
    const lista = (await listarEntradas("todas").catch((e) => e)) as ApiError;
    expect(lista.codigo).toBe("dados_invalidos");
    expect(textoDoErro(lista)).toBe("Confira os dados informados.");

    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(resposta(500, {})));
    expect(textoDoErro(await listarEntradas("todas").catch((e) => e))).toContain("Não foi possível");
  });

  it("403 de regra (sem_organizacao) não tenta renovar o CSRF; 403 sem código tenta uma vez", async () => {
    definirCsrf("velho");
    const regra = vi.fn().mockResolvedValue(resposta(403, { detail: { codigo: "sem_organizacao", mensagem: "Sem org." } }));
    vi.stubGlobal("fetch", regra);
    const erro = (await lancarEntrada({} as never).catch((e) => e)) as ApiError;
    expect(erro.codigo).toBe("sem_organizacao");
    expect(regra).toHaveBeenCalledTimes(1);

    const chamadas: string[] = [];
    const csrf = vi.fn(async (url: string, init: { method: string; headers: Record<string, string> }) => {
      chamadas.push(`${init.method} ${url} ${init.headers["X-CSRF-Token"] ?? ""}`);
      if (url.includes("/auth/sessao")) return resposta(200, { csrf: "novo" });
      return chamadas.length === 1 ? resposta(403, { detail: "requisição recusada" }) : resposta(200, { id: "e1" });
    });
    vi.stubGlobal("fetch", csrf);
    const gravada = await lancarEntrada({} as never);
    expect(gravada).toEqual({ id: "e1" });
    expect(chamadas[0]).toBe("POST /api/v1/entradas velho");
    expect(chamadas[2]).toBe("POST /api/v1/entradas novo");
  });
});
