import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../App";
import { setSession } from "../session";

const emptyList = {
  items: [],
  totalItems: 0,
  page: 0,
  size: 20,
  summary: { openCount: 0, openAmountMinor: "0", overdueCount: 0, overdueAmountMinor: "0", draftCount: 0 },
  businessDate: "2026-09-29",
};

function longSession() {
  setSession({
    token: "operator-demo-token",
    mode: "demo",
    actorId: "actor",
    displayName: "Operadora com nome bastante extenso da demonstração local",
    permissions: ["titles:write", "catalogs:write", "financial-accounts:read", "financial-accounts:write", "settlements:read", "settlements:write", "settlements:reverse"],
    companies: [
      {
        id: "11111111-1111-1111-1111-111111111111",
        tenantId: "t",
        name: "Empresa Cooperativa Agroindustrial do Vale do Rio Longo Ltda",
        active: true,
        demo: true,
        permissions: ["titles:write", "catalogs:write", "financial-accounts:read", "financial-accounts:write", "settlements:read", "settlements:write", "settlements:reverse"],
      },
    ],
    companyId: "11111111-1111-1111-1111-111111111111",
  });
}

function installMatchMedia(initial: boolean) {
  const listeners = new Set<(event: { matches: boolean }) => void>();
  const mql = {
    matches: initial,
    media: "(max-width: 1023px)",
    addEventListener: (_event: string, fn: (event: { matches: boolean }) => void) => {
      listeners.add(fn);
    },
    removeEventListener: (_event: string, fn: (event: { matches: boolean }) => void) => {
      listeners.delete(fn);
    },
    dispatch(matches: boolean) {
      mql.matches = matches;
      listeners.forEach((fn) => fn({ matches }));
    },
  };
  window.matchMedia = ((query: string) => {
    if (String(query).includes("1023")) {
      return mql as unknown as MediaQueryList;
    }
    return {
      matches: false,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
    } as unknown as MediaQueryList;
  }) as typeof window.matchMedia;
  return mql;
}

function stubLists() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/catalogs/")) {
        return { ok: true, status: 200, text: async () => "[]" };
      }
      return { ok: true, status: 200, text: async () => JSON.stringify(emptyList) };
    }),
  );
}

describe("AppShell compact header and drawer focus", () => {
  afterEach(() => {
    setSession(null);
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    window.history.replaceState(null, "", "/");
  });

  it("keeps long company and user names out of the brand region", async () => {
    installMatchMedia(true);
    longSession();
    stubLists();
    render(<App />);
    const header = document.querySelector("header.top");
    expect(header).not.toBeNull();
    const brand = header?.querySelector(".top-brand");
    const company = screen.getByText("Empresa Cooperativa Agroindustrial do Vale do Rio Longo Ltda");
    const user = screen.getByText("Operadora com nome bastante extenso da demonstração local");
    expect(brand).not.toBeNull();
    expect(brand).not.toContainElement(company);
    expect(brand).not.toContainElement(user);
    expect(screen.getByRole("button", { name: "Sair" })).toBeVisible();
    expect(screen.getByText("Empresa")).toBeVisible();
    expect(header?.querySelector(".top-company")).toContainElement(company);
    expect(header?.querySelector(".top-meta")).toContainElement(user);
  });

  it("traps tab in the open drawer, returns to Menu on Escape, and focuses the page title after a destination", async () => {
    installMatchMedia(true);
    longSession();
    stubLists();
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: "Menu" }));
    const nav = screen.getByRole("navigation", { name: "Principal" });
    expect(nav).toHaveClass("side--open");
    expect(document.activeElement).toHaveAttribute("aria-label", "Action Finance Capital — início");

    await user.tab({ shift: true });
    expect(within(nav).getByRole("button", { name: "Cadastros" })).toHaveFocus();
    await user.tab();
    expect(document.activeElement).toHaveAttribute("aria-label", "Action Finance Capital — início");

    await user.keyboard("{Escape}");
    expect(screen.getByRole("button", { name: "Menu" })).toHaveFocus();
    expect(nav).not.toHaveClass("side--open");

    await user.click(screen.getByRole("button", { name: "Menu" }));
    await user.click(within(nav).getByRole("button", { name: "A pagar" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "Contas a pagar" })).toHaveFocus());
    expect(document.getElementById("main-nav")).not.toHaveClass("side--open");
  });

  it("closes the drawer on desktop resize without focusing the hidden Menu", async () => {
    const media = installMatchMedia(true);
    longSession();
    stubLists();
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: "Menu" }));
    expect(screen.getByRole("navigation", { name: "Principal" })).toHaveClass("side--open");
    media.dispatch(false);
    await waitFor(() => expect(screen.getByRole("navigation", { name: "Principal" })).not.toHaveClass("side--open"));
    expect(screen.queryByRole("button", { name: "Fechar menu" })).not.toBeInTheDocument();
    expect(document.activeElement).not.toBe(document.querySelector(".menu-toggle"));
  });

  it("keeps the form and useful focus when dirty navigation is refused", async () => {
    installMatchMedia(true);
    longSession();
    stubLists();
    vi.spyOn(window, "confirm").mockReturnValue(false);
    window.history.replaceState(null, "", "/receivables/new");
    const user = userEvent.setup();
    render(<App />);
    await user.type(screen.getByLabelText(/Descrição/), "Rascunho sujo");
    await user.click(screen.getByRole("button", { name: "Menu" }));
    const nav = screen.getByRole("navigation", { name: "Principal" });
    await user.click(within(nav).getByRole("button", { name: "A pagar" }));
    expect(screen.getByRole("heading", { name: "Novo recebível" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Contas a pagar" })).not.toBeInTheDocument();
    expect(nav).toHaveClass("side--open");
    expect(document.activeElement).not.toBe(screen.getByRole("heading", { name: "Novo recebível" }));
  });
});
