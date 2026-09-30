import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { FornadaPanel } from "./FornadaPanel";

function json(data: unknown, status = 200) {
  return {
    ok: status < 400,
    status,
    json: async () => data,
    text: async () => JSON.stringify(data),
  };
}

describe("painel da fornada", () => {
  it("mostra sugestões sem o formulário de outra data", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo) => {
        const url = String(input);
        if (url.includes("/schedule/suggestions")) {
          return json({
            context_date: "2026-09-26",
            context_source: "next_eligible",
            context_label: "sábado, 26/09",
            mode: "new_types",
            title: "Sugestões para sua fornada",
            message: "Ideias para sábado, 26/09. Incluir um pão ainda não reserva a data.",
            items: [
              {
                name: "Pão de casa",
                slug: "pao-de-casa",
                presentation: "500 g",
                image_url: "/api/v1/catalog/media/demo",
                image_alt: "Pão",
                price: { cents: 2490, currency: "BRL" },
                price_is_from: false,
                href: "/paes/pao-de-casa?data=2026-09-26",
              },
            ],
          });
        }
        return json({ detail: "não encontrado" }, 404);
      }),
    );
    render(<FornadaPanel selectedDate={null} lines={[]} />);
    expect(await screen.findByRole("heading", { name: "Sugestões para sua fornada" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Escolher este pão" })).toHaveAttribute(
      "href",
      "/paes/pao-de-casa?data=2026-09-26",
    );
    expect(screen.queryByRole("button", { name: "Sugerir uma data" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Data desejada")).not.toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("descarta a sugestão antiga quando a data muda", async () => {
    let releaseFirst: () => void = () => {};
    const gate = new Promise<void>((resolve) => {
      releaseFirst = resolve;
    });
    let suggestionCalls = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        suggestionCalls += 1;
        if (suggestionCalls === 1) {
          await gate;
          return json({
            context_date: "2026-09-23",
            context_source: "selected",
            context_label: "quarta, 23/09",
            mode: "already_programmed",
            title: "Resposta antiga",
            message: "velha",
            items: [],
          });
        }
        return json({
          context_date: "2026-09-27",
          context_source: "selected",
          context_label: "domingo, 27/09",
          mode: "empty",
          title: "Resposta nova",
          message: "nova",
          items: [],
        });
      }),
    );
    const view = render(<FornadaPanel selectedDate="2026-09-23" lines={[]} />);
    view.rerender(<FornadaPanel selectedDate="2026-09-27" lines={[]} />);
    expect(await screen.findByRole("heading", { name: "Resposta nova" })).toBeInTheDocument();
    releaseFirst();
    await waitFor(() => {
      expect(screen.queryByRole("heading", { name: "Resposta antiga" })).not.toBeInTheDocument();
    });
    vi.unstubAllGlobals();
  });
});
