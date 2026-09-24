import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
  it("mostra sugestões e envia solicitação de data sem perder o formulário em erro", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(async (input: RequestInfo, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/operations")) {
        return json({
          preview_protection: false,
          orders_enabled: true,
          payments_enabled: true,
          date_requests_enabled: true,
          message: null,
        });
      }
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
      if (url.includes("/schedule/date-requests") && init?.method === "POST") {
        return json({ detail: "informe um e-mail válido" }, 422);
      }
      return json({ detail: "não encontrado" }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<FornadaPanel selectedDate={null} lines={[]} cartCount={0} />);
    expect(await screen.findByRole("heading", { name: "Sugestões para sua fornada" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Escolher este pão" })).toHaveAttribute(
      "href",
      "/paes/pao-de-casa?data=2026-09-26",
    );
    await user.click(screen.getByRole("button", { name: "Solicitar outra data" }));
    expect(
      screen.getByText(/Esta solicitação ainda não confirma a fornada/),
    ).toBeInTheDocument();
    await user.type(screen.getByLabelText("Data desejada"), "2026-10-03");
    await user.type(screen.getByLabelText("Nome"), "Ana");
    await user.type(screen.getByLabelText("E-mail"), "ana@example.com");
    await user.click(screen.getByRole("button", { name: "Enviar solicitação" }));
    expect(await screen.findByText("informe um e-mail válido")).toBeInTheDocument();
    expect(screen.getByLabelText("Nome")).toHaveValue("Ana");
    vi.unstubAllGlobals();
  });

  it("não diz que a loja está fechada quando só a outra data está desligada", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo) => {
        const url = String(input);
        if (url.includes("/operations")) {
          return json({
            preview_protection: false,
            orders_enabled: true,
            payments_enabled: true,
            date_requests_enabled: false,
            message: null,
          });
        }
        if (url.includes("/schedule/suggestions")) {
          return json({
            context_date: "2026-09-23",
            context_source: "selected",
            context_label: "quarta, 23/09",
            mode: "already_programmed",
            title: "Sugestões para esta fornada",
            message: "Há pedidos aguardando a avaliação da padaria nesta data.",
            items: [],
          });
        }
        return json({ detail: "não encontrado" }, 404);
      }),
    );
    render(<FornadaPanel selectedDate="2026-09-23" lines={[]} cartCount={0} />);
    expect(await screen.findByText("Solicitação de outra data indisponível no momento.")).toBeInTheDocument();
    expect(screen.queryByText(/quando a loja abrir os pedidos/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Solicitar outra data" })).not.toBeInTheDocument();
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
      vi.fn(async (input: RequestInfo) => {
        const url = String(input);
        if (url.includes("/operations")) {
          return json({
            preview_protection: false,
            orders_enabled: true,
            payments_enabled: true,
            date_requests_enabled: false,
            message: null,
          });
        }
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
    const view = render(<FornadaPanel selectedDate="2026-09-23" lines={[]} cartCount={0} />);
    view.rerender(<FornadaPanel selectedDate="2026-09-27" lines={[]} cartCount={0} />);
    expect(await screen.findByRole("heading", { name: "Resposta nova" })).toBeInTheDocument();
    releaseFirst();
    await waitFor(() => {
      expect(screen.queryByRole("heading", { name: "Resposta antiga" })).not.toBeInTheDocument();
    });
    vi.unstubAllGlobals();
  });
});
