import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { HeaderAccount } from "../components/HeaderAccount";

afterEach(() => {
  vi.unstubAllGlobals();
  sessionStorage.clear();
});

describe("acesso no cabeçalho", () => {
  it("no modo local entra sem senha e abre o editor", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/access")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          text: async () => JSON.stringify({ local_passwordless: true }),
        });
      }
      if (url.includes("/local-login")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          text: async () =>
            JSON.stringify({
              username: "desenvolvimento",
              csrf_token: "csrf-local",
              bakery_timezone: "America/Sao_Paulo",
            }),
        });
      }
      return Promise.resolve({
        ok: false,
        status: 401,
        text: async () => JSON.stringify({ detail: "não autenticado" }),
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    const push = vi.spyOn(window.history, "pushState");
    render(<HeaderAccount />);
    const enter = await screen.findByRole("button", { name: "Entrar como administrador" });
    expect(screen.queryByLabelText("Usuário")).not.toBeInTheDocument();
    await user.click(enter);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Admin" })).toBeInTheDocument();
    });
    expect(push).toHaveBeenCalled();
    expect(String(push.mock.calls.at(-1)?.[2])).toBe("/admin/produtos");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/local-login"),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("não mostra mensagem de infraestrutura ao carregar a vitrine", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        text: async () => JSON.stringify({ detail: "Gestão indisponível" }),
      }),
    );
    render(<HeaderAccount />);
    await screen.findByLabelText("Usuário");
    await waitFor(() => {
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });
    expect(screen.queryByText(/Gestão indisponível/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/configuração local/i)).not.toBeInTheDocument();
  });

  it("mostra só o usuário e avança para a senha no mesmo controle", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      text: async () => JSON.stringify({ detail: "credenciais inválidas" }),
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<HeaderAccount />);
    const login = await screen.findByLabelText("Usuário");
    expect(login).toHaveClass("is-active");
    expect(screen.getByLabelText("Senha")).toHaveClass("is-idle");
    await user.type(login, "padaria");
    await user.click(screen.getByRole("button", { name: "Avançar" }));
    expect(screen.getByLabelText("Senha")).toHaveClass("is-active");
    expect(screen.getByLabelText("Usuário")).toHaveClass("is-idle");
    await user.type(screen.getByLabelText("Senha"), "secreta");
    await user.click(screen.getByRole("button", { name: "Entrar" }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Usuário ou senha inválidos");
    });
    const loginCall = fetchMock.mock.calls.find((call) => String(call[0]).includes("/login"));
    expect(loginCall).toBeTruthy();
    expect(String(loginCall?.[1]?.body)).toContain("padaria");
    expect(window.location.href).not.toContain("secreta");
    expect(screen.getByLabelText("Senha")).toHaveValue("");
  });

  it("volta para editar o usuário e limpa a senha", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        text: async () => JSON.stringify({ detail: "não autenticado" }),
      }),
    );
    render(<HeaderAccount />);
    await user.type(await screen.findByLabelText("Usuário"), "padaria");
    await user.keyboard("{Enter}");
    await user.type(screen.getByLabelText("Senha"), "secreta");
    await user.click(screen.getByRole("button", { name: "Editar usuário" }));
    expect(screen.getByLabelText("Usuário")).toHaveClass("is-active");
    expect(screen.getByLabelText("Usuário")).toHaveValue("padaria");
    expect(screen.getByLabelText("Senha")).toHaveValue("");
  });

  it("após login válido vai ao editor de produtos", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/login")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          text: async () =>
            JSON.stringify({
              username: "padaria",
              csrf_token: "csrf-test",
              bakery_timezone: "America/Sao_Paulo",
            }),
        });
      }
      return Promise.resolve({
        ok: false,
        status: 401,
        text: async () => JSON.stringify({ detail: "não autenticado" }),
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    const push = vi.spyOn(window.history, "pushState");
    render(<HeaderAccount />);
    await user.type(await screen.findByLabelText("Usuário"), "padaria");
    await user.keyboard("{Enter}");
    await user.type(screen.getByLabelText("Senha"), "secreta");
    await user.keyboard("{Enter}");
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "padaria" })).toBeInTheDocument();
    });
    expect(push).toHaveBeenCalled();
    expect(String(push.mock.calls.at(-1)?.[2])).toBe("/admin/produtos");
    await user.click(screen.getByRole("button", { name: "padaria" }));
    expect(screen.getByRole("menuitem", { name: "Produtos" })).toHaveAttribute("href", "/admin/produtos");
    expect(screen.getByRole("menuitem", { name: "Pedidos" })).toHaveAttribute("href", "/admin/pedidos");
    expect(screen.getByRole("menuitem", { name: "Sair" })).toBeInTheDocument();
  });
});
