import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ComboPrice } from "./ComboPrice";

let calls: Array<{ url: string; method: string; body: unknown }> = [];

beforeEach(() => {
  calls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo, init?: RequestInit) => {
      calls.push({
        url: String(input),
        method: (init?.method ?? "GET").toUpperCase(),
        body: init?.body ? JSON.parse(String(init.body)) : null,
      });
      return { ok: true, status: 200, text: async () => "{}" };
    }),
  );
});
afterEach(() => vi.unstubAllGlobals());

describe("preço do pão no acordo da combo", () => {
  it("salva o preço por pão e mostra o acordo", async () => {
    const user = userEvent.setup();
    const onSaved = vi.fn();
    render(<ComboPrice comboId="c1" value={null} onSaved={onSaved} />);
    expect(screen.getByText(/Vazio: o pão sai pelo preço da vitrine/)).toBeInTheDocument();
    await user.type(screen.getByLabelText("Preço do pão nesta combo"), "30,00");
    await user.click(screen.getByRole("button", { name: "Salvar" }));
    expect(await screen.findByText("Preço salvo.")).toBeInTheDocument();
    expect(calls[0]).toMatchObject({ method: "PATCH", body: { house_unit_price_cents: 3000 } });
    expect(calls[0].url).toMatch(/\/combos\/c1\/price$/);
    expect(onSaved).toHaveBeenCalledWith(3000);
    expect(screen.getByText(/Acordo: R\$ 30,00 por pão/)).toBeInTheDocument();
  });

  it("vazio volta ao preço da vitrine; valor inválido não chama a API", async () => {
    const user = userEvent.setup();
    render(<ComboPrice comboId="c1" value={3000} />);
    const input = screen.getByLabelText("Preço do pão nesta combo");
    await user.clear(input);
    await user.type(input, "abc");
    await user.click(screen.getByRole("button", { name: "Salvar" }));
    expect(screen.getByRole("alert")).toHaveTextContent("informe o preço como 24,90");
    expect(calls).toHaveLength(0);
    await user.clear(input);
    await user.click(screen.getByRole("button", { name: "Salvar" }));
    expect(await screen.findByText("Preço salvo.")).toBeInTheDocument();
    expect(calls[0].body).toEqual({ house_unit_price_cents: null });
  });
});
