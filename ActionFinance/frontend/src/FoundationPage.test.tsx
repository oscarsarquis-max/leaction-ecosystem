import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FoundationPage } from "./FoundationPage";

describe("FoundationPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows a real available response and can verify again", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        name: "ActionFinance",
        stage: "FOUNDATION",
        financialOperationsAvailable: false,
        spiderIntegrationStatus: "NOT_IMPLEMENTED",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<FoundationPage />);
    expect(await screen.findByText("API local disponível.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Verificar novamente" })).toBeEnabled();
    await user.tab();
    expect(screen.getByRole("button", { name: "Verificar novamente" })).toHaveFocus();
    await user.click(screen.getByRole("button", { name: "Verificar novamente" }));
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(JSON.stringify(fetchMock.mock.calls)).not.toMatch(/Bearer|token/i);
  });

  it("shows an unavailable state without leaking internals", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("http://127.0.0.1:8091/secret")));
    render(<FoundationPage />);
    expect(await screen.findByText("API local indisponível. Tente verificar novamente.")).toBeInTheDocument();
    expect(screen.queryByText(/8091/)).not.toBeInTheDocument();
  });
});
