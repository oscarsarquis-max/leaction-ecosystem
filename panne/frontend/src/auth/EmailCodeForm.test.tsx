import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { EmailCodeForm } from "./EmailCodeForm";

describe("formulário de código", () => {
  it("pede e-mail, não pede senha e avança para o código", async () => {
    const requestCode = vi.fn(async () => ({ notice: "Se este endereço puder entrar na Panne, enviamos um código.", advance: true }));
    render(
      <EmailCodeForm
        requestCode={requestCode}
        confirmCode={vi.fn()}
        resendCode={vi.fn()}
      />,
    );
    expect(screen.queryByLabelText(/senha/i)).toBeNull();
    await userEvent.type(screen.getByLabelText("E-mail"), "pessoa@example.invalid");
    await userEvent.click(screen.getByRole("button", { name: "Receber código" }));
    expect(await screen.findByLabelText("Código")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Enviar outro código/ })).toBeDisabled();
  });
});