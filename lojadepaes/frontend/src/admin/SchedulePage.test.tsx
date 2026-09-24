import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SchedulePage } from "./SchedulePage";

const calls: Array<{ url: string; method: string; body: unknown }> = [];

function json(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(body),
  };
}

beforeEach(() => {
  calls.length = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();
      const body = init?.body ? JSON.parse(String(init.body)) : null;
      calls.push({ url, method, body });
      if (url.endsWith("/api/v1/admin/schedule") && method === "GET") {
        return json({
          production_weekdays: [1, 5],
          daily_physical_limit: 40,
          daily_base_limit: 3,
          horizon_days: 21,
          min_advance_hours: 36,
          eligibility_mode: "inherit",
          eligible_base_ids: [],
          reservation_policy: "admin_accept",
        });
      }
      if (url.endsWith("/api/v1/admin/recipe-bases")) {
        return json([]);
      }
      if (url.endsWith("/api/v1/admin/dough-types")) {
        return json([]);
      }
      if (url.endsWith("/api/v1/admin/date-requests")) {
        return json({ items: [] });
      }
      if (url.endsWith("/api/v1/admin/schedule") && method === "PUT") {
        return json({ status: 409, detail: "capacidade abaixo do já comprometido" }, 409);
      }
      if (url.includes("/api/v1/admin/schedule/weeks") && method === "PUT") {
        return json({ ok: true });
      }
      if (url.includes("/weeks/preview")) {
        return json({ week_start: "2026-09-21", week_end: "2026-09-27", conflicts: [], dates: [] });
      }
      return json({ detail: "não esperado" }, 500);
    }),
  );
});

describe("agenda administrativa", () => {
  it("carrega os dias do servidor e não trata lista vazia da semana como rotina", async () => {
    const user = userEvent.setup();
    render(<SchedulePage />);

    const mondays = await screen.findAllByRole("checkbox", { name: "Segunda-feira" });
    const wednesdays = screen.getAllByRole("checkbox", { name: "Quarta-feira" });
    const fridays = screen.getAllByRole("checkbox", { name: "Sexta-feira" });
    expect(mondays[0]).toBeChecked();
    expect(wednesdays[0]).not.toBeChecked();
    expect(fridays[0]).toBeChecked();
    expect(screen.getByRole("heading", { name: "Rotina da padaria" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Ajustar uma semana" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Ajustar uma data" })).toBeInTheDocument();
    expect(screen.getByText("Nenhum cliente solicitou outra data até agora.")).toBeInTheDocument();
    expect(screen.getByText("Segue a rotina: 40 pães")).toBeInTheDocument();
    expect(screen.getByText("Segue a rotina: 3 tipos")).toBeInTheDocument();
    expect(screen.queryByPlaceholderText("Usar configuração herdada")).not.toBeInTheDocument();
    expect(screen.queryByPlaceholderText("Usar a rotina")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Tipos de pão para organizar as fornadas" })).toBeInTheDocument();
    expect(screen.getByText("Nenhum tipo cadastrado.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Massas do assistente" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Gerenciar tipos de pão" }));
    expect(screen.getByLabelText("Nome do tipo de pão")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Início da semana"), { target: { value: "2026-09-21" } });
    await user.click(screen.getByRole("button", { name: "Salvar semana" }));
    const inherited = calls.find((call) => call.method === "PUT" && call.url.includes("/weeks"));
    expect(inherited?.body).toMatchObject({ production_weekdays: null, daily_physical_limit: null });

    await user.click(screen.getByRole("button", { name: "Escolher os dias" }));
    await user.click(screen.getByRole("button", { name: "Salvar semana" }));
    const explicit = calls.filter((call) => call.method === "PUT" && call.url.includes("/weeks"));
    expect(explicit.at(-1)?.body).toMatchObject({ production_weekdays: [] });
  });

  it("mantém o valor digitado quando a rotina é recusada", async () => {
    const user = userEvent.setup();
    render(<SchedulePage />);
    const breads = await screen.findAllByLabelText("Pães por dia");
    expect(breads[0]).toHaveValue("40");
    await user.click(screen.getByRole("button", { name: "Salvar rotina" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("capacidade abaixo do já comprometido");
    expect(screen.getAllByLabelText("Pães por dia")[0]).toHaveValue("40");
  });
});
