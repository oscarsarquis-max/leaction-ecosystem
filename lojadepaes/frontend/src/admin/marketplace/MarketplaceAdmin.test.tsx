import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AdminSidebar } from "../shell/AdminSidebar";
import { activeNavId } from "../shell/nav";
import { MarketplaceAdmin, marketplaceRoute } from "./MarketplaceAdmin";
import type { Partner, PartnerProduct } from "./types";

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
  document: "00.000.000/0001-00",
  contact: "Ana · 85 90000-0000",
  status: "active",
  fee_cents: 250,
  email: "contato@serraclara.test",
  links: [{ id: "l1", partner_id: "p1", category: "queijos", link_type: "exclusive", starts_on: "2026-01-01", ends_on: null }],
};

const pending: PartnerProduct = {
  id: "prod1",
  partner_id: "p1",
  category: "queijos",
  name: "Queijo de casca florida 250 g",
  description: "Leite cru, 30 dias.",
  photos: [],
  price_cents: 4600,
  is_available: true,
  delivery_cities: ["Fortaleza"],
  delivery_districts: [],
  delivery_cep_prefixes: [],
  delivery_days: 2,
  freight_cents: 1200,
  perishable: true,
  status: "pending",
  pairings: [{ id: "x1", house_product_slug: "fermentacao-natural-de-trigo", house_product_name: "Fermentação natural de trigo", reason: "A acidez corta a gordura." }],
};

type Call = { url: string; method: string; body: unknown };
let calls: Call[] = [];

function json(body: unknown, status = 200) {
  return { ok: status >= 200 && status < 300, status, text: async () => JSON.stringify(body) };
}

function stubApi(routes: (url: string, method: string) => { body: unknown; status?: number }) {
  calls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo, init?: RequestInit) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();
      calls.push({ url, method, body: init?.body ? JSON.parse(String(init.body)) : null });
      const reply = routes(url, method);
      return json(reply.body, reply.status ?? 200);
    }),
  );
}

function defaultRoutes(url: string, method: string) {
  if (url.endsWith("/marketplace/partners") && method === "GET") {
    return { body: [partner] };
  }
  if (url.endsWith("/marketplace/products") && method === "GET") {
    return { body: [pending] };
  }
  if (url.endsWith("/reviews")) {
    return { body: [] };
  }
  return { body: {} };
}

beforeEach(() => {
  stubApi(defaultRoutes);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("rotas do marketplace", () => {
  it("lê abas, convite, parceiro e avaliação", () => {
    expect(marketplaceRoute("/admin/marketplace")).toEqual({ view: "tab", tab: "parceiros" });
    expect(marketplaceRoute("/admin/marketplace/avaliacao")).toEqual({ view: "tab", tab: "avaliacao" });
    expect(marketplaceRoute("/admin/marketplace/vinculos/")).toEqual({ view: "tab", tab: "vinculos" });
    expect(marketplaceRoute("/admin/marketplace/parceiros/novo")).toEqual({ view: "invite" });
    expect(marketplaceRoute("/admin/marketplace/parceiros/p1")).toEqual({ view: "partner", id: "p1" });
    expect(marketplaceRoute("/admin/marketplace/avaliacao/prod1")).toEqual({ view: "review", id: "prod1" });
    expect(activeNavId("/admin/marketplace/avaliacao/prod1")).toBe("parceiros");
  });

  it("menu: desligado fica em breve; ligado vira link", () => {
    const { rerender } = render(
      <AdminSidebar path="/admin/pedidos" open onNavigate={() => {}} sidebarRef={{ current: null }} />,
    );
    expect(screen.queryByRole("link", { name: "Parceiros" })).toBeNull();
    expect(screen.getAllByText("em breve")).toHaveLength(2);
    rerender(
      <AdminSidebar path="/admin/marketplace/parceiros" open marketplace onNavigate={() => {}} sidebarRef={{ current: null }} />,
    );
    const link = screen.getByRole("link", { name: "Parceiros" });
    expect(link).toHaveAttribute("href", "/admin/marketplace/parceiros");
    expect(link).toHaveAttribute("aria-current", "page");
    expect(screen.getAllByText("em breve")).toHaveLength(1);
  });
});

describe("Marketplace › Parceiros", () => {
  it("avisa quando o marketplace está desligado no servidor", async () => {
    stubApi(() => ({ body: { detail: "não encontrado" }, status: 404 }));
    render(<MarketplaceAdmin path="/admin/marketplace/parceiros" onNavigate={() => {}} />);
    expect(await screen.findByText("O marketplace está desligado neste ambiente.")).toBeInTheDocument();
  });

  it("lista parceiros com taxa por pedido, vínculo e produtos", async () => {
    render(<MarketplaceAdmin path="/admin/marketplace/parceiros" onNavigate={() => {}} />);
    const row = (await screen.findByText("Queijaria Serra Clara")).closest("tr") as HTMLElement;
    expect(within(row).getByText("R$ 2,50")).toBeInTheDocument();
    expect(within(row).getByText("Exclusivo")).toBeInTheDocument();
    expect(within(row).getByText("Queijos")).toBeInTheDocument();
    expect(within(row).getByText("0 publicados")).toBeInTheDocument();
    expect(within(row).getByText("1 em avaliação")).toBeInTheDocument();
    expect(within(row).getByText("Ativo")).toBeInTheDocument();
    const tabs = screen.getByRole("navigation", { name: "Seções do marketplace" });
    expect(within(tabs).getByRole("link", { name: /Parceiros/ })).toHaveAttribute("aria-current", "page");
    expect(within(tabs).getByRole("link", { name: /Avaliação/ })).toHaveTextContent("1");
    expect(screen.queryByText(/comiss/i)).toBeNull();
  });

  it("vínculos mostram categorias sem parceiro", async () => {
    render(<MarketplaceAdmin path="/admin/marketplace/vinculos" onNavigate={() => {}} />);
    expect(await screen.findByRole("rowheader", { name: "Queijos" })).toBeInTheDocument();
    expect(screen.getAllByText("Sem parceiro · ofertas externas, quando houver")).toHaveLength(8);
  });
});

describe("avaliação de produto", () => {
  it("só aprova com as três notas e só devolve com observação", async () => {
    const user = userEvent.setup();
    render(<MarketplaceAdmin path="/admin/marketplace/avaliacao/prod1" onNavigate={() => {}} />);
    expect(await screen.findByRole("heading", { name: "Queijo de casca florida 250 g" })).toBeInTheDocument();
    expect(screen.getByText("Fermentação natural de trigo")).toBeInTheDocument();
    const approve = screen.getByRole("button", { name: "Aprovar e publicar" });
    const giveBack = screen.getByRole("button", { name: "Devolver com observação" });
    expect(approve).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Qualidade: nota 4" }));
    await user.click(screen.getByRole("button", { name: "Visual: nota 2" }));
    expect(approve).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Complementaridade: nota 5" }));
    expect(approve).toBeEnabled();
    expect(giveBack).toBeDisabled();
    await user.type(screen.getByLabelText(/Observação ao parceiro/), "Fotos escuras.");
    expect(giveBack).toBeEnabled();
    await user.click(giveBack);
    const post = calls.find((call) => call.method === "POST");
    expect(post?.url).toBe("/api/v1/admin/marketplace/products/prod1/review");
    expect(post?.body).toEqual({ quality: 4, visual: 2, complementarity: 5, decision: "return", note: "Fotos escuras." });
    expect(await screen.findByText("Devolvido ao parceiro.")).toBeInTheDocument();
  });
});

describe("acesso e reativação", () => {
  it("gera novo link de acesso e reativa parceiro pausado", async () => {
    const user = userEvent.setup();
    let status = "paused";
    stubApi((url, method) => {
      if (url.endsWith("/partners/p1") && method === "GET") {
        return { body: { ...partner, status } };
      }
      if (url.endsWith("/partners/p1/activate") && method === "POST") {
        status = "active";
        return { body: { ...partner, status } };
      }
      if (url.endsWith("/partners/p1/access-link") && method === "POST") {
        return { body: { invite_link: "/parceiro/convite?token=novo", invite_expires_at: "2026-11-20T15:00:00Z" } };
      }
      return defaultRoutes(url, method);
    });
    render(<MarketplaceAdmin path="/admin/marketplace/parceiros/p1" onNavigate={() => {}} />);
    expect(await screen.findByRole("button", { name: "Gerar novo link de acesso" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Reativar parceiro" }));
    expect(await screen.findByRole("button", { name: "Pausar parceiro" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Gerar novo link de acesso" }));
    expect(await screen.findByLabelText("Link de acesso")).toHaveValue(`${window.location.origin}/parceiro/convite?token=novo`);
    expect(calls.filter((call) => call.method === "POST").map((call) => call.url)).toEqual([
      "/api/v1/admin/marketplace/partners/p1/activate",
      "/api/v1/admin/marketplace/partners/p1/access-link",
    ]);
  });
});

describe("convite de parceiro", () => {
  it("envia a taxa em centavos e mostra o link uma vez", async () => {
    const user = userEvent.setup();
    stubApi((url, method) => {
      if (url.endsWith("/marketplace/partners") && method === "POST") {
        return {
          status: 201,
          body: { ...partner, id: "p2", status: "invited", invite_link: "/parceiro/convite?token=abc", invite_expires_at: "2026-11-20T15:00:00Z" },
        };
      }
      return defaultRoutes(url, method);
    });
    render(<MarketplaceAdmin path="/admin/marketplace/parceiros/novo" onNavigate={() => {}} />);
    await user.type(await screen.findByLabelText("Nome da marca"), "Queijaria Serra Clara");
    expect(screen.getByLabelText("Endereço na loja")).toHaveValue("queijaria-serra-clara");
    await user.type(screen.getByLabelText("Cidade"), "Guaramiranga");
    await user.type(screen.getByLabelText("Região"), "Ceará");
    await user.type(screen.getByLabelText("E-mail de acesso"), "contato@serraclara.test");
    await user.type(screen.getByLabelText("CNPJ ou CPF"), "00.000.000/0001-00");
    await user.type(screen.getByLabelText("Contato (nome e telefone)"), "Ana");
    expect(screen.getByLabelText("Taxa por pedido (R$)")).toHaveValue("2,50");
    await user.click(screen.getByRole("button", { name: "Criar convite" }));
    const post = calls.find((call) => call.method === "POST");
    expect(post?.body).toMatchObject({ brand_slug: "queijaria-serra-clara", fee_cents: 250, highlight_hex: "#2F5D3A" });
    expect(post?.body).not.toHaveProperty("commission_percent");
    expect(await screen.findByLabelText("Link do convite")).toHaveValue(`${window.location.origin}/parceiro/convite?token=abc`);
  });
});
