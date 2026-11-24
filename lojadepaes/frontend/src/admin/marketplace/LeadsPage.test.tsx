import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LeadsPage, safeLink, whatsappHref, type Lead } from "./LeadsPage";
import { INVITE_PREFILL_KEY } from "./labels";

const lead: Lead = {
  id: "l1",
  created_at: "2026-11-24T13:00:00Z",
  name: "Ana Souza",
  brand: "Queijaria Serra Clara",
  category: "queijos",
  city: "Guaramiranga",
  whatsapp: "(85) 99999-0000",
  email: "ana@serra.test",
  link: "@serraclara",
  message: "Queijos de leite cru.",
  status: "new",
};

let calls: Array<{ url: string; method: string; body: unknown }> = [];

function stub(reply: (url: string, method: string) => { body: unknown; status?: number }) {
  calls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo, init?: RequestInit) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();
      calls.push({ url, method, body: init?.body ? JSON.parse(String(init.body)) : null });
      const { body, status = 200 } = reply(url, method);
      return { ok: status >= 200 && status < 300, status, text: async () => JSON.stringify(body) };
    }),
  );
}

beforeEach(() => {
  stub((url, method) => (url.endsWith("/leads") && method === "GET" ? { body: [lead, { ...lead, id: "l2", brand: "Adega", status: "discarded" }] } : { body: {} }));
});

afterEach(() => {
  vi.unstubAllGlobals();
  sessionStorage.clear();
});

describe("Interessados", () => {
  it("lista os novos, abre o detalhe com contatos seguros e marca em conversa", async () => {
    const user = userEvent.setup();
    render(<LeadsPage marketplaceOn={false} onNavigate={vi.fn()} />);
    const card = (await screen.findByText("Queijaria Serra Clara")).closest("li") as HTMLElement;
    expect(screen.queryByText("Adega")).toBeNull();
    await user.click(within(card).getByRole("button", { name: "Abrir" }));
    expect(within(card).getByRole("link", { name: "(85) 99999-0000" })).toHaveAttribute("href", "https://wa.me/5585999990000");
    expect(within(card).getByRole("link", { name: "@serraclara" })).toHaveAttribute("href", "https://instagram.com/serraclara");
    expect(within(card).getByText("O convite de parceiro abre quando o marketplace for ligado.")).toBeInTheDocument();
    await user.click(within(card).getByRole("button", { name: "Marcar em conversa" }));
    expect(calls.find((call) => call.method === "PATCH")).toEqual(
      expect.objectContaining({ url: expect.stringContaining("/marketplace/leads/l1"), body: { status: "contacting" } }),
    );
  });

  it("com o marketplace ligado, convida e leva os dados ao convite", async () => {
    const user = userEvent.setup();
    const go = vi.fn();
    render(<LeadsPage marketplaceOn onNavigate={go} />);
    const card = (await screen.findByText("Queijaria Serra Clara")).closest("li") as HTMLElement;
    await user.click(within(card).getByRole("button", { name: "Abrir" }));
    await user.click(within(card).getByRole("button", { name: "Convidar como parceiro" }));
    expect(go).toHaveBeenCalledWith("/admin/marketplace/parceiros/novo");
    expect(JSON.parse(sessionStorage.getItem(INVITE_PREFILL_KEY) ?? "{}")).toEqual({
      brand_name: "Queijaria Serra Clara",
      city: "Guaramiranga",
      contact: "Ana Souza",
      email: "ana@serra.test",
    });
  });

  it("formulário desligado (404) avisa", async () => {
    stub(() => ({ body: { detail: "não encontrado" }, status: 404 }));
    render(<LeadsPage marketplaceOn={false} onNavigate={vi.fn()} />);
    expect(await screen.findByText("O formulário de parceiros está desligado neste ambiente.")).toBeInTheDocument();
  });
});

describe("links do interessado", () => {
  it("só gera links http(s), wa.me e Instagram", () => {
    expect(safeLink("javascript:alert(1)")).toBeNull();
    expect(safeLink("www.serra.com.br")).toBe("https://www.serra.com.br");
    expect(safeLink("https://serra.com.br/x")).toBe("https://serra.com.br/x");
    expect(whatsappHref("85 3333-4444")).toBe("https://wa.me/558533334444");
    expect(whatsappHref("123")).toBeNull();
  });
});

describe("convite com dados do interessado", () => {
  it("preenche marca, cidade, contato e e-mail uma vez", async () => {
    const { InvitePartner } = await import("./InvitePartner");
    sessionStorage.setItem(
      INVITE_PREFILL_KEY,
      JSON.stringify({ brand_name: "Queijaria Serra Clara", city: "Guaramiranga", contact: "Ana Souza", email: "ana@serra.test" }),
    );
    render(<InvitePartner onBack={vi.fn()} onCreated={vi.fn()} onOpen={vi.fn()} />);
    expect(screen.getByDisplayValue("Queijaria Serra Clara")).toBeInTheDocument();
    expect(screen.getByDisplayValue("queijaria-serra-clara")).toBeInTheDocument();
    expect(screen.getByDisplayValue("ana@serra.test")).toBeInTheDocument();
    expect(sessionStorage.getItem(INVITE_PREFILL_KEY)).toBeNull();
  });
});
