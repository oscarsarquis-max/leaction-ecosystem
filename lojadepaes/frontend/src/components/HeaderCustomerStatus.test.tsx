import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { HeaderCustomerStatus } from "./HeaderCustomerStatus";
import { identifyLibrary, verifyLibrary } from "../features/baker-library/libraryApi";
import { logoutHouseFidelity } from "../shop/houseFidelityApi";

vi.mock("../features/baker-library/libraryApi", () => ({
  identifyLibrary: vi.fn(),
  verifyLibrary: vi.fn(),
  cancelLibrarySubscription: vi.fn(),
}));

vi.mock("../shop/houseFidelityApi", () => ({
  fetchHouseFidelity: vi.fn(async () => null),
  logoutHouseFidelity: vi.fn(),
}));

function unidentifiedFetch() {
  return vi.fn(async (input: RequestInfo) => {
    if (String(input).includes("/api/v1/conta/situacao")) {
      return { ok: true, json: async () => ({ identified: false }) };
    }
    return { ok: false, status: 404, json: async () => ({}) };
  });
}

describe("HeaderCustomerStatus", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.mocked(identifyLibrary).mockReset();
    vi.mocked(verifyLibrary).mockReset();
    vi.mocked(logoutHouseFidelity).mockReset();
  });

  it("mostra Entrar e Receber código juntos, sem enviar código ao abrir", async () => {
    vi.stubGlobal("fetch", unidentifiedFetch());
    const user = userEvent.setup();
    render(<HeaderCustomerStatus />);
    await user.click(await screen.findByRole("button", { name: "Identifique-se" }));
    expect(screen.getByLabelText("E-mail cadastrado")).toBeInTheDocument();
    expect(screen.queryByLabelText("CPF do cadastro")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Código de acesso")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Entrar" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Receber código" })).toBeEnabled();
    expect(screen.getByRole("link", { name: "Acesso administrativo" })).toHaveAttribute("href", "#acesso");
    expect(identifyLibrary).not.toHaveBeenCalled();
    expect(verifyLibrary).not.toHaveBeenCalled();
  });

  it("entra com código já disponível sem pedir outro", async () => {
    vi.stubGlobal("fetch", unidentifiedFetch());
    vi.mocked(verifyLibrary).mockResolvedValue({ ok: true, identified: true } as never);
    const user = userEvent.setup();
    render(<HeaderCustomerStatus />);
    await user.click(await screen.findByRole("button", { name: "Identifique-se" }));
    await user.type(screen.getByLabelText("E-mail cadastrado"), "ana@example.com");
    await user.type(screen.getByLabelText("Código de acesso"), "123456");
    await user.click(screen.getByRole("button", { name: "Entrar" }));
    await waitFor(() => {
      expect(verifyLibrary).toHaveBeenCalledWith({ email: "ana@example.com", code: "123456" });
    });
    expect(identifyLibrary).not.toHaveBeenCalled();
  });

  it("entra pelo CPF sem exigir e-mail e sem enviar código", async () => {
    vi.stubGlobal("fetch", unidentifiedFetch());
    vi.mocked(verifyLibrary).mockResolvedValue({ ok: true, identified: true } as never);
    const user = userEvent.setup();
    render(<HeaderCustomerStatus />);
    await user.click(await screen.findByRole("button", { name: "Identifique-se" }));
    await user.click(screen.getByRole("radio", { name: "CPF" }));
    expect(screen.queryByLabelText("E-mail cadastrado")).not.toBeInTheDocument();
    await user.type(screen.getByLabelText("CPF do cadastro"), "39053344705");
    await user.type(screen.getByLabelText("Código de acesso"), "654321");
    await user.click(screen.getByRole("button", { name: "Entrar" }));
    await waitFor(() => {
      expect(verifyLibrary).toHaveBeenCalledWith({ cpf: "39053344705", code: "654321" });
    });
    expect(identifyLibrary).not.toHaveBeenCalled();
  });

  it("recusa CPF inválido como se fosse senha e não envia código", async () => {
    vi.stubGlobal("fetch", unidentifiedFetch());
    const user = userEvent.setup();
    render(<HeaderCustomerStatus />);
    await user.click(await screen.findByRole("button", { name: "Identifique-se" }));
    await user.click(screen.getByRole("radio", { name: "CPF" }));
    await user.type(screen.getByLabelText("CPF do cadastro"), "senha123");
    await user.click(screen.getByRole("button", { name: "Receber código" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Informe um CPF válido");
    expect(identifyLibrary).not.toHaveBeenCalled();
  });

  it("Receber código pelo CPF não manda e-mail digitado", async () => {
    vi.stubGlobal("fetch", unidentifiedFetch());
    vi.mocked(identifyLibrary).mockResolvedValue({ ok: true, email_masked: "a***@example.com" });
    const user = userEvent.setup();
    render(<HeaderCustomerStatus />);
    await user.click(await screen.findByRole("button", { name: "Identifique-se" }));
    await user.type(screen.getByLabelText("E-mail cadastrado"), "outro@example.com");
    await user.click(screen.getByRole("radio", { name: "CPF" }));
    await user.type(screen.getByLabelText("CPF do cadastro"), "39053344705");
    await user.click(screen.getByRole("button", { name: "Receber código" }));
    await waitFor(() => {
      expect(identifyLibrary).toHaveBeenCalledWith({ cpf: "39053344705" });
    });
    expect(identifyLibrary).not.toHaveBeenCalledWith(expect.objectContaining({ email: "outro@example.com" }));
  });

  it("código inválido oferece Receber código sem disparar envio e preserva o e-mail", async () => {
    vi.stubGlobal("fetch", unidentifiedFetch());
    vi.mocked(verifyLibrary).mockRejectedValue(new Error("código inválido"));
    const user = userEvent.setup();
    render(<HeaderCustomerStatus />);
    await user.click(await screen.findByRole("button", { name: "Identifique-se" }));
    await user.type(screen.getByLabelText("E-mail cadastrado"), "ana@example.com");
    await user.type(screen.getByLabelText("Código de acesso"), "000000");
    await user.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Código inválido, expirado ou já usado");
    expect(screen.getByLabelText("E-mail cadastrado")).toHaveValue("ana@example.com");
    expect(identifyLibrary).not.toHaveBeenCalled();
  });

  it("visitante autenticado sem assinatura não vê benefício inventado e pode sair", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo) => {
        if (String(input).includes("/api/v1/conta/situacao")) {
          return {
            ok: true,
            json: async () => ({
              identified: true,
              assinatura: { status: "none", status_label: "Sem assinatura", authorized: false },
              consultas_ia: { monthly_credits: 0, pack_credits: 0 },
              fidelidade: { enrolled: false, bread_credits: 0 },
            }),
          };
        }
        return { ok: false, status: 404, json: async () => ({}) };
      }),
    );
    vi.mocked(logoutHouseFidelity).mockResolvedValue({ ok: true });
    const user = userEvent.setup();
    render(<HeaderCustomerStatus />);
    await user.click(await screen.findByRole("button", { name: /Assinatura Sem assinatura/i }));
    expect(screen.getByRole("dialog", { name: "Situação da conta" })).toHaveTextContent(
      /Assinatura:\s*Sem assinatura/,
    );
    expect(screen.queryByText(/Assinatura ativa/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Sair" }));
    await waitFor(() => {
      expect(logoutHouseFidelity).toHaveBeenCalled();
    });
  });
});
