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

function atForm() {
  window.history.replaceState(null, "", "/b2b#parceiro");
}

afterEach(() => {
  window.history.replaceState(null, "", "/b2b");
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
  await user.click(screen.getByLabelText(/Li os termos e autorizo a Loja de Pães a vincular a minha marca/));
}

describe("página /b2b", () => {
  it("apresenta a proposta, não indexa e não mostra a taxa como cobrança do cliente", () => {
    render(<B2BPage />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Seu produto à mesa");
    expect(document.head.querySelector('meta[name="robots"]')?.getAttribute("content")).toBe("noindex, nofollow");
    expect(screen.getByText(/O cliente não vê essa taxa/)).toBeInTheDocument();
  });

  it("abas: começa em Como funciona e mostra cada assunto ao clicar; nunca promete taxa zero", async () => {
    const user = userEvent.setup();
    render(<B2BPage />);
    expect(screen.getByRole("tab", { name: "Como funciona" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("heading", { name: "Você se apresenta" })).toBeVisible();
    expect(screen.getByText("Adesão e mensalidade")).toBeInTheDocument();
    expect(screen.queryByText(/sem taxa|taxa zero|nenhuma taxa/i)).toBeNull();

    await user.click(screen.getByRole("tab", { name: "Vantagens" }));
    expect(screen.getByRole("heading", { name: "Zero custo fixo" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Exclusividade possível" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Você se apresenta" })).toBeNull();
    expect(window.location.hash).toBe("#vantagens");

    await user.click(screen.getByRole("tab", { name: "Faça a conta" }));
    const table = screen.getByRole("table", { name: "Quanto você recebe em cada pedido" });
    expect(table).toHaveTextContent("R$ 67,50");
    expect(table).toHaveTextContent("R$ 241,50");

    await user.click(screen.getByRole("tab", { name: "Perguntas" }));
    expect(screen.getByText("O cliente paga mais caro por causa da taxa?")).toBeVisible();
    expect(screen.getByText("Preciso assinar contrato ou garantir volume?")).toBeVisible();

    await user.click(screen.getByRole("tab", { name: "Termos de parceria" }));
    const terms = screen.getByRole("list", { name: "Texto dos termos de parceria" });
    expect(terms).toHaveTextContent("Ações promocionais");
    expect(terms).toHaveTextContent("blog LePain");
  });

  it("setas do teclado trocam de aba", async () => {
    const user = userEvent.setup();
    render(<B2BPage />);
    screen.getByRole("tab", { name: "Como funciona" }).focus();
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Vantagens" })).toHaveFocus();
    expect(screen.getByRole("tab", { name: "Vantagens" })).toHaveAttribute("aria-selected", "true");
    await user.keyboard("{End}");
    expect(screen.getByRole("tab", { name: "Quero ser parceiro" })).toHaveAttribute("aria-selected", "true");
  });

  it("ler os termos e voltar não perde o que foi digitado", async () => {
    const user = userEvent.setup();
    atForm();
    render(<B2BPage />);
    await user.type(screen.getByLabelText("Marca ou empresa"), "Queijaria Serra Clara");
    await user.click(screen.getByRole("button", { name: /Ler os termos de parceria/ }));
    expect(screen.getByRole("tab", { name: "Termos de parceria" })).toHaveAttribute("aria-selected", "true");
    await user.click(screen.getByRole("button", { name: "Voltar ao formulário de adesão" }));
    expect(screen.getByLabelText("Marca ou empresa")).toHaveValue("Queijaria Serra Clara");
  });

  it("valida os campos e leva o foco ao primeiro erro", async () => {
    const user = userEvent.setup();
    atForm();
    render(<B2BPage />);
    await user.click(screen.getByRole("button", { name: "Enviar apresentação" }));
    expect(screen.getByLabelText("Seu nome")).toHaveFocus();
    expect(screen.getByText("Informe o seu nome.")).toBeInTheDocument();
    expect(screen.getByText("Precisamos da sua autorização para entrar em contato.")).toBeInTheDocument();
    expect(screen.getByText("Para enviar, aceite os termos de parceria.")).toBeInTheDocument();
    expect(submitPartnerLead).not.toHaveBeenCalled();
  });

  it("envia a apresentação e confirma", async () => {
    const user = userEvent.setup();
    vi.mocked(submitPartnerLead).mockResolvedValue({ ok: true });
    atForm();
    render(<B2BPage />);
    await fill(user);
    await user.click(screen.getByLabelText("Autorizo a Loja de Pães a entrar em contato sobre a parceria."));
    await user.click(screen.getByRole("button", { name: "Enviar apresentação" }));
    expect(await screen.findByText("Recebemos a sua apresentação.")).toBeInTheDocument();
    expect(submitPartnerLead).toHaveBeenCalledWith(
      expect.objectContaining({ brand: "Queijaria Serra Clara", category: "queijos", consent: true, terms: true, website: "" }),
    );
  });

  it("inscrições fechadas (404) avisam sem perder o que foi digitado", async () => {
    const user = userEvent.setup();
    vi.mocked(submitPartnerLead).mockRejectedValue(new ApiError(404, "não encontrado"));
    atForm();
    render(<B2BPage />);
    await fill(user);
    await user.click(screen.getByLabelText("Autorizo a Loja de Pães a entrar em contato sobre a parceria."));
    await user.click(screen.getByRole("button", { name: "Enviar apresentação" }));
    expect(await screen.findByText("As inscrições de parceiros estão fechadas no momento.")).toBeInTheDocument();
    expect(screen.getByLabelText("Marca ou empresa")).toHaveValue("Queijaria Serra Clara");
  });
});

describe("termos no envio", () => {
  it("sem aceitar os termos não envia, mesmo com o resto preenchido", async () => {
    const user = userEvent.setup();
    atForm();
    render(<B2BPage />);
    await fill(user);
    await user.click(screen.getByLabelText(/Li os termos e autorizo/));
    await user.click(screen.getByLabelText("Autorizo a Loja de Pães a entrar em contato sobre a parceria."));
    await user.click(screen.getByRole("button", { name: "Enviar apresentação" }));
    expect(screen.getByText("Para enviar, aceite os termos de parceria.")).toBeInTheDocument();
    expect(screen.getByLabelText(/Li os termos e autorizo/)).toHaveFocus();
    expect(submitPartnerLead).not.toHaveBeenCalled();
  });
});

describe("validWhatsapp", () => {
  it("aceita DDD com 10 ou 11 dígitos e o +55", () => {
    expect(validWhatsapp("(85) 99999-0000")).toBe(true);
    expect(validWhatsapp("+55 85 3333-4444")).toBe(true);
    expect(validWhatsapp("99999-0000")).toBe(false);
  });
});
