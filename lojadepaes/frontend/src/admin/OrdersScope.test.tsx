import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AdminApp } from "./AdminApp";
import { ProductsList } from "./ProductsList";
import { WeekRecipesList } from "./WeekRecipesList";
import type { AdminProductList } from "./productTypes";
import type { WeekRecipeAdmin } from "../shop/weekRecipe";

const calls: string[] = [];
const requestPermission = vi.fn(async () => "granted" as NotificationPermission);

function json(body: unknown, status = 200) {
  return {
    ok: status < 400,
    status,
    text: async () => JSON.stringify(body),
  };
}

function payloadFor(url: string): { body: unknown; status?: number } {
  if (url.includes("/api/v1/admin/session")) {
    return {
      body: { username: "admin", csrf_token: "csrf-teste", bakery_timezone: "America/Sao_Paulo" },
    };
  }
  if (url.includes("/api/v1/admin/schedule/closures")) {
    return { body: { items: [], history: [] } };
  }
  if (url.includes("/recipe-bases") || url.includes("/dough-types")) {
    return { body: [] };
  }
  if (url.includes("/custom-loaf")) {
    return { body: { price_cents: 7000, weight_grams: 500, ingredients: [] } };
  }
  if (/\/api\/v1\/admin\/schedule(?:\?|$)/.test(url)) {
    return {
      body: {
        production_weekdays: [2, 5],
        daily_physical_limit: 8,
        daily_base_limit: 4,
        horizon_days: 14,
        min_advance_hours: 24,
        eligibility_mode: "inherit",
        eligible_base_ids: [],
        reservation_policy: "hold",
      },
    };
  }
  if (/\/api\/v1\/admin\/orders\/[^/?]+$/.test(url)) {
    return { body: { detail: "ausente" }, status: 404 };
  }
  if (url.includes("/ops/push/devices")) {
    return { body: { devices: [] } };
  }
  if (url.includes("/ops/push")) {
    return { body: { configured: true, public_key: "chave-publica", receipt_confirmed: false } };
  }
  if (url.includes("attendance-summary")) {
    return {
      body: {
        date_requests_awaiting: 0,
        orders_awaiting_evaluation: 0,
        orders_awaiting_adaptation: 0,
        paid_awaiting_accept: 0,
        confirmed_awaiting_delivery: 0,
        overdue_dates: 0,
        unique_records: 0,
        counts_are_subsets: true,
        priority: [],
        updated_at: "2026-10-26T12:00:00+00:00",
        board: {
          scope: "Situação atual.",
          timezone: "America/Sao_Paulo",
          updated_label: "26/10/2026 09:00",
          operational_total: 0,
          stages: [],
          history: [],
          payments: [],
          payment_other: [],
          payment_orders: 0,
          pending_note: "Nota.",
          pendings: [],
          not_tracked: [],
          payment_note: "Nota.",
        },
      },
    };
  }
  if (url.includes("production-agenda")) {
    return {
      body: {
        timezone: "America/Sao_Paulo",
        year: 2026,
        month: 10,
        today: "2026-10-26",
        days: [],
        undated: [],
      },
    };
  }
  return {
    body: {
      items: [],
      page: 1,
      page_size: 20,
      total: 0,
      slots: [],
      hub_items: [],
      hub_ok: false,
      devices: [],
      gaps: [],
    },
  };
}

beforeEach(() => {
  calls.length = 0;
  requestPermission.mockClear();
  vi.stubGlobal("Notification", { permission: "default", requestPermission });
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo) => {
      const url = String(input);
      calls.push(url);
      const payload = payloadFor(url);
      return json(payload.body, payload.status ?? 200);
    }),
  );
});

function opsCalls(): string[] {
  return calls.filter(
    (url) => url.includes("attendance-summary") || url.includes("production-agenda"),
  );
}

async function openAdmin(path: string) {
  window.history.pushState({}, "", path);
  render(<AdminApp />);
  await screen.findByRole("navigation", { name: "Gestão" });
}

describe("resumo só na lista de pedidos", () => {
  it.each([
    ["/admin/produtos/receitas", "Receitas da semana"],
    ["/admin/produtos", "Produtos"],
    ["/admin/produtos/gigio", "Explicações aprovadas"],
    ["/admin/produtos/gigio/harmonizacoes", "Referências de harmonização"],
    ["/admin/produtos/complementos", "Para acompanhar seu pão"],
    ["/admin/agenda", "Agenda de fornadas"],
    ["/admin/fidelidade", "Fidelidade da casa"],
    ["/admin/pedidos/pedido-1", ""],
  ])("não monta o resumo em %s", async (path, heading) => {
    await openAdmin(path);
    expect(screen.queryByRole("heading", { name: "Ciclo dos pedidos" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Agenda de produção" })).not.toBeInTheDocument();
    expect(opsCalls()).toEqual([]);
    expect(calls.some((url) => url.includes("/ops/push"))).toBe(false);
    if (heading) {
      expect(await screen.findByRole("heading", { name: heading })).toBeInTheDocument();
    }
  });

  it("monta agenda e resumo em /admin e desmonta ao sair", async () => {
    const user = userEvent.setup();
    await openAdmin("/admin");
    expect(await screen.findByRole("heading", { name: "Ciclo dos pedidos" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Agenda de produção" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Pedidos" })).toBeInTheDocument();
    await waitFor(() => expect(opsCalls().length).toBeGreaterThan(0));
    const before = opsCalls().length;
    await user.click(within(screen.getByRole("navigation", { name: "Gestão" })).getByRole("link", { name: "Produtos" }));
    await screen.findByRole("heading", { name: "Produtos" });
    expect(screen.queryByRole("heading", { name: "Ciclo dos pedidos" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Agenda de produção" })).not.toBeInTheDocument();
    expect(opsCalls()).toHaveLength(before);
  });

  it("em /admin/pedidos mostra só a fila", async () => {
    await openAdmin("/admin/pedidos");
    expect(await screen.findByRole("heading", { name: "Pedidos" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Ciclo dos pedidos" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Agenda de produção" })).not.toBeInTheDocument();
    await waitFor(() => expect(opsCalls().some((url) => url.includes("attendance-summary"))).toBe(true));
  });

  it("abre notificações sob ação, sem pedir permissão", async () => {
    const user = userEvent.setup();
    await openAdmin("/admin/produtos/receitas");
    expect(calls.some((url) => url.includes("/ops/push"))).toBe(false);
    await user.click(screen.getByRole("button", { name: "Notificações neste aparelho" }));
    expect(await screen.findByRole("heading", { name: "Notificações neste aparelho" })).toBeInTheDocument();
    await waitFor(() => expect(calls.some((url) => url.includes("/ops/push"))).toBe(true));
    expect(requestPermission).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Notificações neste aparelho" }));
    expect(screen.queryByRole("heading", { name: "Notificações neste aparelho" })).not.toBeInTheDocument();
    expect(requestPermission).not.toHaveBeenCalled();
  });
});

describe("tabela de receitas", () => {
  const longTitle =
    "Bocadillo de calamares, pimentão e maionese de açafrão com pão crocante da semana";

  function recipe(partial: Partial<WeekRecipeAdmin>): WeekRecipeAdmin {
    return {
      id: "rec-1",
      title: longTitle,
      editorial_status: "published",
      is_featured: true,
      slug: "bocadillo",
      summary: "",
      ...partial,
    } as WeekRecipeAdmin;
  }

  it("mostra o título longo e separa destacar de arquivar", async () => {
    const user = userEvent.setup();
    const onFeature = vi.fn();
    const onUnfeature = vi.fn();
    const onArchive = vi.fn();
    const onOpen = vi.fn();
    render(
      <WeekRecipesList
        items={[
          recipe({ id: "bocadillo", title: longTitle, is_featured: true }),
          recipe({
            id: "sopa",
            title: "Sopa de tomate assado com manjericão e azeite",
            is_featured: false,
          }),
          recipe({
            id: "sardinhas",
            title: "Sardinhas grelhadas com homus e limão",
            is_featured: false,
          }),
          recipe({
            id: "tomate",
            title: "Pan con Tomate",
            is_featured: false,
          }),
        ]}
        loading={false}
        error={null}
        busyId={null}
        onNew={() => undefined}
        onOpen={onOpen}
        onPublish={() => undefined}
        onFeature={onFeature}
        onUnfeature={onUnfeature}
        onArchive={onArchive}
      />,
    );
    expect(screen.getByRole("heading", { name: "Receitas da semana" })).toBeInTheDocument();
    expect(screen.getByText(longTitle)).toBeInTheDocument();
    expect(screen.getByText("Pan con Tomate")).toBeInTheDocument();
    const featuredRow = screen.getByText(longTitle).closest("tr");
    if (!featuredRow) {
      throw new Error("linha do Bocadillo ausente");
    }
    await user.click(within(featuredRow).getByRole("button", { name: "Retirar destaque" }));
    expect(onUnfeature).toHaveBeenCalledWith("bocadillo");
    expect(onArchive).not.toHaveBeenCalled();
    expect(onFeature).not.toHaveBeenCalled();
    await user.click(within(featuredRow).getByRole("button", { name: "Arquivar" }));
    expect(onArchive).toHaveBeenCalledWith("bocadillo");
    expect(onUnfeature).toHaveBeenCalledTimes(1);
    await user.click(within(featuredRow).getByRole("button", { name: "Editar" }));
    expect(onOpen).toHaveBeenCalledWith("bocadillo");
  });
});

describe("tabela de produtos permanece a de produtos", () => {
  it("mantém as colunas de produto", async () => {
    const data: AdminProductList = {
      items: [
        {
          id: "p1",
          name: "Focaccia",
          slug: "focaccia",
          editorial_status: "published",
          is_available: true,
          updated_at: "2026-10-26T12:00:00Z",
          thumbnail_url: null,
          from_price: { cents: 1800, currency: "BRL" },
        },
      ],
      page: 1,
      page_size: 20,
      total: 1,
    } as AdminProductList;
    render(
      <ProductsList
        filters={{ query: "", status: "", available: "" }}
        data={data}
        loading={false}
        error={null}
        onChange={() => undefined}
        onSubmit={(event) => event.preventDefault()}
        onNew={() => undefined}
        onOpen={() => undefined}
        onPage={() => undefined}
        onRefresh={() => undefined}
      />,
    );
    expect(await screen.findByRole("heading", { name: "Vitrine (10 posições)" })).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText("Carregando a vitrine…")).not.toBeInTheDocument());
    expect(screen.getByRole("columnheader", { name: "Foto" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Preço" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Disponibilidade" })).toBeInTheDocument();
    expect(document.querySelector(".admin-recipes-table")).toBeNull();
  });
});
