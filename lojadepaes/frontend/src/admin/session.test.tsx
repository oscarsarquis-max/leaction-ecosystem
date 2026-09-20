import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AdminApp } from "./AdminApp";

afterEach(() => {
  vi.unstubAllGlobals();
  sessionStorage.clear();
});

describe("AdminApp", () => {
  it("sem sessão redireciona para o acesso do cabeçalho", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        text: async () => JSON.stringify({ detail: "não autenticado" }),
      }),
    );
    const replace = vi.spyOn(window.history, "replaceState");
    render(<AdminApp />);
    expect(await screen.findByText("Redirecionando ao acesso do cabeçalho…")).toBeInTheDocument();
    expect(replace).toHaveBeenCalled();
    const url = String(replace.mock.calls.at(-1)?.[2] ?? "");
    expect(url).toContain("next=");
    expect(url).toContain("#acesso");
    expect(url).not.toContain("/admin/login");
  });
});
