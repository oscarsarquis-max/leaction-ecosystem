import { describe, expect, it, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AccessGate } from "@/components/AccessGate";
import { resetConfigCache } from "@/config/env";

describe("AccessGate login explícito", () => {
  beforeEach(() => {
    resetConfigCache();
    vi.stubEnv("VITE_AUTH_MODE", "dev");
    vi.stubEnv("VITE_ENVIRONMENT", "local");
  });

  it("exige clique no CTA de desenvolvimento e não autentica sozinho", async () => {
    const user = userEvent.setup();
    const onLogin = vi.fn();
    render(<AccessGate status="anonymous" onLogin={onLogin} />);

    expect(
      screen.getByRole("button", {
        name: /Entrar como usuário de desenvolvimento/i,
      }),
    ).toBeInTheDocument();
    expect(onLogin).not.toHaveBeenCalled();

    await user.click(screen.getByTestId("login-cta"));
    expect(onLogin).toHaveBeenCalledTimes(1);
  });
});
