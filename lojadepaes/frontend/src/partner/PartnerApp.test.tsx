import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Photo } from "../admin/marketplace/Photo";
import type { Partner, PartnerProduct } from "../admin/marketplace/types";
import { PartnerApp, partnerRoute } from "./PartnerApp";

const partner: Partner = {
  id: "p1",
  partner_type: "producer",
  brand_name: "Queijaria Serra Clara",
  brand_slug: "queijaria-serra-clara",
  logo_url: "",
  photo_url: "",
  story: "",
  city: "Guaramiranga",
  region: "Ceará",
  highlight_hex: "#2F5D3A",
  document: "00",
  contact: "Ana",
  status: "active",
  fee_cents: 250,
  email: "contato@serra.test",
};

const returned: PartnerProduct = {
  id: "x1",
  partner_id: "p1",
  category: "queijos",
  name: "Queijo de casca florida 250 g",
  description: "",
  photos: ["https://exemplo.test/queijo.jpg"],
  price_cents: 4600,
  is_available: true,
  delivery_cities: ["Fortaleza"],
  delivery_districts: [],
  delivery_cep_prefixes: [],
  delivery_days: 2,
  freight_cents: 1200,
  perishable: true,
  status: "returned",
  pairings: [{ id: "a", house_product_slug: "fermentacao-natural", house_product_name: "Fermentação natural", reason: "Acidez." }],
};

type Call = { url: string; method: string; body: unknown; headers: Record<string, string> };
let calls: Call[] = [];
let signedIn = true;

function json(body: unknown, status = 200) {
  return { ok: status >= 200 && status < 300, status, text: async () => (body === undefined ? "" : JSON.stringify(body)) };
}

type Routes = (url: string, method: string, body: unknown) => { body?: unknown; status?: number } | undefined;

function stub(extra?: Routes) {
  calls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo, init?: RequestInit) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();
      const body = init?.body && !(init.body instanceof FormData) ? JSON.parse(String(init.body)) : null;
      calls.push({ url, method, body, headers: (init?.headers ?? {}) as Record<string, string> });
      const custom = extra?.(url, method, body);
      if (custom) {
        return json(custom.body, custom.status ?? 200);
      }
      if (url.endsWith("/partner/me")) {
        return signedIn
          ? json({ csrf_token: "csrf-1", email: partner.email, partner })
          : json({ detail: "não autenticado" }, 401);
      }
      if (url.endsWith("/partner/products") && method === "GET") {
        return json([returned]);
      }
      if (url.endsWith("/partner/products/x1/reviews")) {
        return json([
          { id: "r1", quality: 4, visual: 2, complementarity: 4, note: "Fotos escuras.", decision: "return", reviewer_ref: "admin", reviewed_at: "2026-11-10T19:20:00Z" },
        ]);
      }
      if (url.includes("/api/v1/catalog/products")) {
        return json({ items: [{ slug: "fermentacao-natural", name: "Fermentação natural" }, { slug: "rustico-centeio", name: "Rústico de centeio" }], page: 1, page_size: 50, total: 2 });
      }
      return json({});
    }),
  );
}

function at(path: string) {
  window.history.pushState({}, "", path);
}

beforeEach(() => {
  signedIn = true;
  stub();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("rotas do portal", () => {
  it("lê as rotas do parceiro", () => {
    expect(partnerRoute("/parceiro")).toEqual({ view: "home" });
    expect(partnerRoute("/parceiro/convite")).toEqual({ view: "invite" });
    expect(partnerRoute("/parceiro/entrar")).toEqual({ view: "login" });
    expect(partnerRoute("/parceiro/marca")).toEqual({ view: "brand" });
    expect(partnerRoute("/parceiro/produtos/novo")).toEqual({ view: "product", id: null });
    expect(partnerRoute("/parceiro/produtos/x1")).toEqual({ view: "product", id: "x1" });
  });
});

describe("portal do parceiro", () => {
  it("avisa quando o marketplace está desligado", async () => {
    stub(() => ({ body: { detail: "não encontrado" }, status: 404 }));
    at("/parceiro");
    render(<PartnerApp />);
    expect(await screen.findByRole("heading", { name: "Portal indisponível" })).toBeInTheDocument();
  });

  it("aceita o convite: confere a senha, envia o token e abre os produtos", async () => {
    const user = userEvent.setup();
    signedIn = false;
    stub((url, method) => {
      if (url.endsWith("/partner/invite/accept") && method === "POST") {
        signedIn = true;
        return { body: { csrf_token: "csrf-2", email: partner.email, partner } };
      }
      return undefined;
    });
    at("/parceiro/convite?token=tok-123");
    render(<PartnerApp />);
    await user.type(await screen.findByLabelText("Senha (mínimo de 8 caracteres)"), "segredo123");
    await user.type(screen.getByLabelText("Repita a senha"), "segredo12");
    await user.click(screen.getByRole("button", { name: "Criar senha e entrar" }));
    expect(screen.getByRole("alert")).toHaveTextContent("As duas senhas não são iguais.");
    await user.type(screen.getByLabelText("Repita a senha"), "3");
    await user.click(screen.getByRole("button", { name: "Criar senha e entrar" }));
    const accept = calls.find((call) => call.url.endsWith("/invite/accept"));
    expect(accept?.body).toEqual({ token: "tok-123", password: "segredo123" });
    expect(await screen.findByRole("heading", { name: "Meus produtos" })).toBeInTheDocument();
    expect(window.location.search).toBe("");
  });

  it("lista os produtos com a observação da Loja e manda o CSRF ao sair", async () => {
    const user = userEvent.setup();
    at("/parceiro");
    render(<PartnerApp />);
    const card = (await screen.findByText("Queijo de casca florida 250 g")).closest("button") as HTMLElement;
    expect(within(card).getByText("Devolvido")).toBeInTheDocument();
    expect(await within(card).findByText("Loja: Fotos escuras.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Sair" }));
    const logout = calls.find((call) => call.url.endsWith("/partner/logout"));
    expect(logout?.headers["X-CSRF-Token"]).toBe("csrf-1");
  });

  it("novo produto: só envia com o checklist completo e manda os valores em centavos", async () => {
    const user = userEvent.setup();
    stub((url, method, body) => {
      if (url.endsWith("/partner/products") && method === "POST") {
        return { status: 201, body: { ...returned, ...(body as object), id: "x9", status: "draft", pairings: [] } };
      }
      if (url.endsWith("/partner/products/x9/submit")) {
        return { body: { ...returned, id: "x9", status: "pending" } };
      }
      if (url.endsWith("/partner/media") && method === "POST") {
        return { status: 201, body: { id: "m1", url: "/api/v1/marketplace/media/m1" } };
      }
      return undefined;
    });
    at("/parceiro/produtos/novo");
    render(<PartnerApp />);
    const send = await screen.findByRole("button", { name: "Enviar para avaliação" });
    expect(send).toBeDisabled();
    await user.selectOptions(screen.getByLabelText("Categoria"), "queijos");
    await user.type(screen.getByLabelText("Nome"), "Ricota fresca 300 g");
    await user.upload(screen.getByLabelText(/Adicionar foto/), new File(["x"], "ricota.jpg", { type: "image/jpeg" }));
    expect(await screen.findByRole("button", { name: "Remover a foto 1" })).toBeInTheDocument();
    const media = calls.find((call) => call.url.endsWith("/partner/media"));
    expect(media?.method).toBe("POST");
    expect(media?.headers["X-CSRF-Token"]).toBe("csrf-1");
    expect(media?.headers["Content-Type"]).toBeUndefined();
    await screen.findByRole("option", { name: "Rústico de centeio" });
    await user.selectOptions(screen.getByLabelText("Pão"), "rustico-centeio");
    await user.type(screen.getByLabelText("Por que combina"), "Leve com o centeio.");
    await user.type(screen.getByLabelText("Preço (R$)"), "24,00");
    await user.type(screen.getByLabelText("Prazo (dias após o pedido)"), "2");
    await user.type(screen.getByLabelText("Frete (R$)"), "12,00");
    expect(send).toBeDisabled();
    await user.type(screen.getByLabelText("Cidades atendidas"), "Fortaleza, Eusébio");
    expect(send).toBeEnabled();
    await user.click(send);
    const create = calls.find((call) => call.url.endsWith("/partner/products") && call.method === "POST");
    expect(create?.body).toMatchObject({
      category: "queijos",
      name: "Ricota fresca 300 g",
      photos: ["/api/v1/marketplace/media/m1"],
      price_cents: 2400,
      freight_cents: 1200,
      delivery_days: 2,
      delivery_cities: ["Fortaleza", "Eusébio"],
      pairings: [{ house_product_slug: "rustico-centeio", reason: "Leve com o centeio." }],
    });
    expect(calls.some((call) => call.url.endsWith("/partner/products/x9/submit"))).toBe(true);
    expect(await screen.findByText("Enviado para avaliação. A Loja de Pães avisa quando decidir.")).toBeInTheDocument();
  });

  it("produto devolvido mostra a observação e reenvia", async () => {
    at("/parceiro/produtos/x1");
    render(<PartnerApp />);
    expect(await screen.findByText("Loja: “Fotos escuras.”")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Enviar para avaliação" })).toBeEnabled();
  });
});

describe("fotos do produto", () => {
  it("recusa arquivo grande ou de outro tipo e aceita endereço da internet", async () => {
    const user = userEvent.setup({ applyAccept: false });
    at("/parceiro/produtos/novo");
    render(<PartnerApp />);
    const input = await screen.findByLabelText(/Adicionar foto/);
    await user.upload(input, new File(["x"], "nota.pdf", { type: "application/pdf" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Envie a foto em JPEG, PNG ou WebP.");
    const big = new File([new Uint8Array(8 * 1024 * 1024 + 1)], "grande.jpg", { type: "image/jpeg" });
    await user.upload(input, big);
    expect(screen.getByRole("alert")).toHaveTextContent("A foto passa de 8 MB.");
    expect(calls.some((call) => call.url.endsWith("/partner/media"))).toBe(false);
    await user.click(screen.getByRole("button", { name: "A foto já está na internet? Colar o endereço" }));
    await user.type(screen.getByLabelText("Endereço da imagem"), "https://exemplo.test/q.jpg");
    await user.click(screen.getByRole("button", { name: "Usar este endereço" }));
    expect(screen.getByRole("button", { name: "Remover a foto 1" })).toBeInTheDocument();
  });
});

describe("foto indisponível", () => {
  it("troca a imagem quebrada por um aviso", () => {
    render(<Photo src="https://exemplo.test/quebrada.jpg" alt="Queijo" />);
    fireEvent.error(screen.getByRole("img", { name: "Queijo" }));
    expect(screen.getByRole("img", { name: "Queijo: foto indisponível" })).toHaveTextContent("Foto indisponível");
  });
});
