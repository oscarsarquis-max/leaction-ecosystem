import { render, screen } from "@testing-library/react";
import { PayReceiptsPage } from "./PayReceiptsPage";
import { setSession } from "./session";

const writePerms = ["titles:read", "titles:write"];

describe("PayReceiptsPage", () => {
  afterEach(() => {
    setSession(null);
    vi.unstubAllGlobals();
  });

  it("shows denied state without inventing success", async () => {
    setSession({
      token: "t",
      mode: "demo",
      actorId: "a",
      displayName: "Operador",
      permissions: writePerms,
      companies: [{ id: "11111111-1111-1111-1111-111111111111", tenantId: "t", name: "Loja", active: true, demo: true, permissions: writePerms }],
      companyId: "11111111-1111-1111-1111-111111111111",
    });
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        status: 403,
        json: async () => ({ code: "FORBIDDEN", message: "negado" }),
        text: async () => JSON.stringify({ code: "FORBIDDEN", message: "negado" }),
      })),
    );
    render(<PayReceiptsPage path="/pay-receipts" onNavigate={() => undefined} />);
    expect(await screen.findByText(/Acesso negado/)).toBeInTheDocument();
    expect(screen.queryByText(/Sincronização concluída/)).toBeNull();
  });
});
