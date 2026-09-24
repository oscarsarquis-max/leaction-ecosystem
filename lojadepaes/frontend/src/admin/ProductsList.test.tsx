import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ProductsList } from "./ProductsList";

function json(data: unknown, status = 200) {
  return {
    ok: status < 400,
    status,
    text: async () => JSON.stringify(data),
  };
}

describe("lista de produtos", () => {
  it("permite apagar rascunho e mostra posição na vitrine", async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    const fetchMock = vi.fn(async (input: RequestInfo, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/admin/showcase") && (!init || !init.method || init.method === "GET")) {
        return json({
          slots: Array.from({ length: 10 }, (_, index) => ({
            position: index + 1,
            product_id: null,
            product: null,
          })),
        });
      }
      if (url.includes("/admin/products/") && init?.method === "DELETE") {
        return { ok: true, status: 204, text: async () => "" };
      }
      if (url.includes("/admin/products")) {
        return json({ items: [], page: 1, page_size: 50, total: 0 });
      }
      return json({ detail: "não autenticado" }, 401);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(
      <ProductsList
        filters={{ query: "", status: "", available: "" }}
        data={{
          items: [
            {
              id: "dddddddd-dddd-dddd-dddd-dddddddddddd",
              name: "Pão de Canela rascunho",
              slug: "pao-de-canela-rascunho",
              editorial_status: "draft",
              is_available: true,
              updated_at: "2026-09-21T00:00:00Z",
              thumbnail_url: null,
              from_price: { cents: 2490, currency: "BRL" },
            },
            {
              id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
              name: "Pão de Limão Siciliano",
              slug: "pao-de-limao",
              editorial_status: "published",
              is_available: true,
              updated_at: "2026-09-21T00:00:00Z",
              thumbnail_url: null,
              from_price: { cents: 2890, currency: "BRL" },
              showcase_position: 1,
            },
            {
              id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
              name: "Pão de Canela arquivado",
              slug: "pao-de-canela-arquivado",
              editorial_status: "archived",
              is_available: false,
              updated_at: "2026-09-21T00:00:00Z",
              thumbnail_url: null,
              from_price: { cents: 2490, currency: "BRL" },
            },
          ],
          page: 1,
          page_size: 20,
          total: 3,
        }}
        loading={false}
        error={null}
        onChange={() => undefined}
        onSubmit={(event) => event.preventDefault()}
        onNew={() => undefined}
        onOpen={() => undefined}
        onPage={() => undefined}
        onRefresh={onRefresh}
      />,
    );
    expect(await screen.findByRole("heading", { name: "Vitrine (10 posições)" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Posição 1" })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Apagar" })).toHaveLength(2);
    await user.click(screen.getAllByRole("button", { name: "Apagar" })[0]);
    expect(confirmSpy).toHaveBeenCalled();
    expect(onRefresh).toHaveBeenCalled();
    confirmSpy.mockRestore();
    vi.unstubAllGlobals();
  });
});
