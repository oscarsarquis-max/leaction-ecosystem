import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../../services/http";
import { B2BPage } from "./B2BPage";
import { submitPartnerLead, validWhatsapp } from "./b2bApi";

vi.mock("./b2bApi", async () => {
  const actual = await vi.importActual<typeof import("./b2bApi")>("./b2bApi");
  return { ...actual, submitPartnerLead: vi.fn() };
});

afterEach(() => {
  vi.mocked(submitPartnerLead).mockReset();
  document.head.querySelectorAll('meta[name="robots"]').forEach((node) => node.remove());
});

async function fill(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("Seu nome"), "Ana Souza");
  await user.type(screen.getByLabelText("Marca ou empresa"), "Queijaria Serra Clara");
  await user.selectOptions(screen.getByLabelText("Categoria principal"), "queijos");
  await user.type(screen.getByLabelText("Cidade"), "Guaramiranga");
  await user.type(screen.getByLabelText("WhatsApp"), "(85) 99999-0000");
  await user.type(screen.getByLabelText("E-mail"), "ana@serra.test");
  await user.type(screen.getByLabelText("Conte sobre os seus produtos"), "Queijos de leite cru.");
}

describe("página /b2b", () => {
  it("apresenta a proposta, não indexa e não mostra a taxa como cobrança do cliente", () => {
    render(<B2BPage />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Seu produto à mesa");
    expect(document.head.querySelector('meta[name="robots"]')?.getAttribute("content")).toBe("noindex, nofollow");
    expect(screen.getByText(/O cliente não vê essa taxa/)).toBeInTheDocument();
  });

  it("valida os campos e leva o foco ao primeiro erro", async () => {
    const user = userEvent.setup();
    render(<B2BPage />);
    await user.click(screen.getByRole("button", { name: "Enviar apresentação" }));
    expect(screen.getByLabelText("Seu nome")).toHaveFocus();
    expect(screen.getByText("Informe o seu nome.")).toBeInTheDocument();
    expect(screen.getByText("Precisamos da sua autorização para entrar em contato.")).toBeInTheDocument();
    expect(submitPartnerLead).not.toHaveBeenCalled();
  });

  it("envia a apresentação e confirma", async () => {
    const user = userEvent.setup();
    vi.mocked(submitPartnerLead).mockResolvedValue({ ok: true });
    render(<B2BPage />);
    await fill(user);
    await user.click(screen.getByLabelText("Autorizo a Loja de Pães a entrar em contato sobre a parceria."));
    await user.click(screen.getByRole("button", { name: "Enviar apresentação" }));
    expect(await screen.findByText("Recebemos a sua apresentação.")).toBeInTheDocument();
    expect(submitPartnerLead).toHaveBeenCalledWith(
      expect.objectContaining({ brand: "Queijaria Serra Clara", category: "queijos", consent: true, website: "" }),
    );
  });

  it("inscrições fechadas (404) avisam sem perder o que foi digitado", async () => {
    const user = userEvent.setup();
    vi.mocked(submitPartnerLead).mockRejectedValue(new ApiError(404, "não encontrado"));
    render(<B2BPage />);
    await fill(user);
    await user.click(screen.getByLabelText("Autorizo a Loja de Pães a entrar em contato sobre a parceria."));
    await user.click(screen.getByRole("button", { name: "Enviar apresentação" }));
    expect(await screen.findByText("As inscrições de parceiros estão fechadas no momento.")).toBeInTheDocument();
    expect(screen.getByLabelText("Marca ou empresa")).toHaveValue("Queijaria Serra Clara");
  });
});

describe("validWhatsapp", () => {
  it("aceita DDD com 10 ou 11 dígitos e o +55", () => {
    expect(validWhatsapp("(85) 99999-0000")).toBe(true);
    expect(validWhatsapp("+55 85 3333-4444")).toBe(true);
    expect(validWhatsapp("99999-0000")).toBe(false);
  });
});
