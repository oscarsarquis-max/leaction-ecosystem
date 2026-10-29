import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Root } from "../../app/Root";
import type { SessionInfo } from "../types";
import { AdminShell } from "./AdminShell";
import { AdminSidebar } from "./AdminSidebar";
import { PageHeader } from "./PageHeader";
import { StatusChip } from "./StatusChip";
import { NAV_GROUPS } from "./nav";

const session: SessionInfo = {
  username: "admin",
  csrf_token: "csrf-teste",
  bakery_timezone: "America/Sao_Paulo",
};

const routes: Array<[string, string]> = [
  ["/admin", "Pedidos"],
  ["/admin/pedidos", "Pedidos"],
  ["/admin/pedidos/pedido-1", "Pedidos"],
  ["/admin/pedidos/solicitacao/sol-1", "Pedidos"],
  ["/admin/agenda", "Dias, tetos e fechamentos"],
  ["/admin/produtos", "Produtos"],
  ["/admin/produtos/novo", "Produtos"],
  ["/admin/produtos/prod-1", "Produtos"],
  ["/admin/produtos/receitas", "Receitas da semana"],
  ["/admin/produtos/receitas/nova", "Receitas da semana"],
  ["/admin/produtos/receitas/rec-1", "Receitas da semana"],
  ["/admin/produtos/gigio", "Gigio"],
  ["/admin/produtos/gigio/harmonizacoes", "Harmonizações"],
  ["/admin/produtos/complementos", "Complementos"],
  ["/admin/fidelidade", "Fidelidade"],
];

function sidebar(path: string) {
  return (
    <AdminSidebar
      path={path}
      open
      onNavigate={() => {}}
      sidebarRef={{ current: null }}
    />
  );
}

function shell(path: string) {
  return (
    <AdminShell path={path} onNavigate={() => {}} session={session} noticesOpen={false} onToggleNotices={() => {}}>
      <p>conteúdo</p>
    </AdminShell>
  );
}

describe("menu do backoffice", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it("mostra os itens com rota e deixa Parceiros e Repasses fora da tabulação", () => {
    render(sidebar("/admin/pedidos"));
    for (const group of NAV_GROUPS) {
      expect(screen.getByText(group.label)).toBeInTheDocument();
      for (const item of group.items) {
        if (item.href) {
          expect(screen.getByRole("link", { name: item.label })).toHaveAttribute("href", item.href);
        } else {
          expect(screen.getByText(item.label).closest("a")).toBeNull();
          expect(screen.getByText(item.label).closest("[tabindex]")).toBeNull();
        }
      }
    }
    expect(screen.getAllByText("em breve")).toHaveLength(2);
  });

  it.each(routes)("em %s acende %s", (path, label) => {
    render(sidebar(path));
    const nav = screen.getByRole("navigation", { name: "Gestão" });
    expect(within(nav).getByRole("link", { name: label })).toHaveAttribute("aria-current", "page");
  });

  it("não dispara requisição ao montar a casca em produtos", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(shell("/admin/produtos"));
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("abre a gaveta no celular, fecha com Esc e ao escolher item, e devolve o foco", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("matchMedia", () => ({
      matches: true,
      media: "(max-width: 959px)",
      addEventListener() {},
      removeEventListener() {},
      dispatchEvent() {
        return false;
      },
    }));
    render(shell("/admin/produtos"));
    const menu = screen.getByRole("button", { name: "Menu" });
    expect(menu).toHaveAttribute("aria-expanded", "false");
    await user.click(menu);
    expect(menu).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("link", { name: "Pedidos" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Ver a loja" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("banner").querySelector("a.admin-topbar-store")).toBeNull();
    await user.keyboard("{Escape}");
    expect(menu).toHaveFocus();
    expect(menu).toHaveAttribute("aria-expanded", "false");
    await user.click(menu);
    await user.click(screen.getByRole("link", { name: "Pedidos" }));
    expect(menu).toHaveFocus();
    expect(menu).toHaveAttribute("aria-expanded", "false");
  });

  it("coloca a barra fora do recipiente de largura máxima", () => {
    render(shell("/admin/pedidos"));
    const bar = screen.getByRole("banner");
    expect(bar.parentElement).toHaveClass("admin-frame-main");
    expect(bar.closest(".admin-frame-content")).toBeNull();
    expect(bar.parentElement?.querySelector(":scope > .admin-frame-content")).not.toBeNull();
    expect(within(bar).getByText("Operação")).toBeInTheDocument();
    expect(bar.querySelector(".admin-trail strong")).toHaveTextContent("Pedidos");
    expect(within(bar).getByRole("button", { name: "admin" })).toBeInTheDocument();
    expect(within(bar).getByRole("link", { name: "Ver a loja" })).toHaveAttribute("href", "/");
    expect(within(bar).getByRole("button", { name: "Notificações neste aparelho" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });

  it("no celular mostra Menu e só o nome da página na barra", () => {
    vi.stubGlobal("matchMedia", () => ({
      matches: true,
      media: "(max-width: 959px)",
      addEventListener() {},
      removeEventListener() {},
      dispatchEvent() {
        return false;
      },
    }));
    render(shell("/admin/agenda"));
    const bar = screen.getByRole("banner");
    expect(within(bar).getByRole("button", { name: "Menu" })).toBeInTheDocument();
    expect(within(bar).getByText("Dias, tetos e fechamentos")).toBeInTheDocument();
    expect(within(bar).queryByText("Produção")).toBeNull();
    expect(within(bar).getByRole("button", { name: "admin" })).toBeInTheDocument();
    expect(within(bar).queryByRole("link", { name: "Ver a loja" })).toBeNull();
  });

  it("mostra título e a etapa visível sem escolher outra", () => {
    render(
      <>
        <PageHeader title="Pedidos" description="Fila única." />
        <StatusChip stage="paid" label="Pago" />
      </>,
    );
    expect(screen.getByRole("heading", { name: "Pedidos" })).toBeInTheDocument();
    expect(screen.getByText("Pago")).toBeInTheDocument();
  });
});

describe("Gigio fora do admin", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo) => {
        const url = String(input);
        if (url.includes("/api/v1/gigio/status")) {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              enabled: true,
              ready: true,
              live: false,
              welcome: "Olá",
              starters: [],
              culinary: [],
            }),
            text: async () => "",
          };
        }
        return {
          ok: false,
          status: 404,
          text: async () => "",
          json: async () => ({}),
        };
      }),
    );
  });

  it("não aparece em /admin e continua na vitrine", async () => {
    window.history.pushState({}, "", "/admin/pedidos");
    const admin = render(<Root />);
    expect(screen.getByText("Verificando sessão…")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Conversar com Gigio" })).not.toBeInTheDocument();
    expect(document.querySelector(".gigio-host")).toBeNull();
    admin.unmount();
    window.history.pushState({}, "", "/");
    render(<Root />);
    expect(await screen.findByRole("button", { name: "Conversar com Gigio" })).toBeInTheDocument();
  });
});
