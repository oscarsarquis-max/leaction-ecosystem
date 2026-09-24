import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ShowcasePanel, type ShowcaseSlot } from "./ShowcasePanel";

function json(data: unknown, status = 200) {
  return {
    ok: status < 400,
    status,
    text: async () => JSON.stringify(data),
  };
}

describe("posições da vitrine", () => {
  it("mostra dez posições e permite escolher sem arrastar", async () => {
    const user = userEvent.setup();
    const slots: ShowcaseSlot[] = Array.from({ length: 10 }, (_, index) => ({
      position: index + 1,
      product_id: null,
      product: null,
    }));
    const fetchMock = vi.fn(async (input: RequestInfo, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/admin/showcase") && (!init || !init.method || init.method === "GET")) {
        return json({ slots });
      }
      if (url.includes("/admin/products")) {
        return json({
          items: [
            {
              id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
              name: "Pão da casa",
              slug: "pao-da-casa",
              editorial_status: "published",
              is_available: true,
              updated_at: "2026-09-20T00:00:00Z",
              thumbnail_url: "/api/v1/admin/media/1",
              from_price: { cents: 2490, currency: "BRL" },
            },
          ],
          page: 1,
          page_size: 50,
          total: 1,
        });
      }
      if (url.includes("/admin/showcase/slots/1") && init?.method === "PUT") {
        const assigned: ShowcaseSlot[] = slots.map((slot) =>
          slot.position === 1
            ? {
                position: 1,
                product_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                product: {
                  id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                  name: "Pão da casa",
                  slug: "pao-da-casa",
                  editorial_status: "published",
                  is_available: true,
                  thumbnail_url: "/api/v1/admin/media/1",
                },
              }
            : slot,
        );
        return json({ slots: assigned });
      }
      return json({ detail: "não autenticado" }, 401);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<ShowcasePanel />);
    expect(await screen.findByRole("heading", { name: "Vitrine (10 posições)" })).toBeInTheDocument();
    expect(screen.getAllByText(/Posição/).length).toBe(10);
    expect(screen.getAllByRole("button", { name: "Subir" }).length).toBe(10);
    expect(screen.getAllByRole("button", { name: "Descer" }).length).toBe(10);
    const firstSelect = screen.getAllByLabelText("Produto")[0];
    await user.selectOptions(firstSelect, "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa");
    expect(fetchMock).toHaveBeenCalled();
    vi.unstubAllGlobals();
  });
});
