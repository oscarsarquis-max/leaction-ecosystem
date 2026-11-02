import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Login } from "./Login";

function responder(status: number, corpo: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => corpo,
  });
}

afterEach(() => vi.unstubAllGlobals());

describe("Login", () => {
  it("entra com usuário e senha e entrega a sessão", async () => {
    const sessao = { usuario: "ana", nome: "Ana", papel: "dono", permissoes: [], csrf: "c", fuso: "America/Sao_Paulo" };
    const fetchMock = responder(200, sessao);
    vi.stubGlobal("fetch", fetchMock);
    const aoEntrar = vi.fn();
    render(<Login onEntrou={aoEntrar} />);
    await userEvent.type(screen.getByLabelText("Usuário"), "ana");
    await userEvent.type(screen.getByLabelText("Senha"), "senha-bem-longa");
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
    await waitFor(() => expect(aoEntrar).toHaveBeenCalledWith(sessao));
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/v1/auth/entrar");
    expect(JSON.parse(init.body)).toEqual({ usuario: "ana", senha: "senha-bem-longa" });
    expect(init.credentials).toBe("same-origin");
  });

  it("mostra mensagem clara quando a senha está errada e limpa o campo", async () => {
    vi.stubGlobal("fetch", responder(401, { detail: "usuário ou senha inválidos" }));
    render(<Login onEntrou={vi.fn()} />);
    await userEvent.type(screen.getByLabelText("Usuário"), "ana");
    await userEvent.type(screen.getByLabelText("Senha"), "errada-errada");
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Usuário ou senha inválidos.");
    expect(screen.getByLabelText("Senha")).toHaveValue("");
  });

  it("explica o bloqueio depois de muitas tentativas", async () => {
    vi.stubGlobal("fetch", responder(429, { detail: "muitas tentativas; aguarde alguns minutos" }));
    render(<Login onEntrou={vi.fn()} />);
    await userEvent.type(screen.getByLabelText("Usuário"), "ana");
    await userEvent.type(screen.getByLabelText("Senha"), "errada-errada");
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Muitas tentativas. Aguarde alguns minutos");
  });

  it("não envia com campos vazios", () => {
    render(<Login onEntrou={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Entrar" })).toBeDisabled();
  });
});
