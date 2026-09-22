import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import { ACCESS_EXPLANATION } from "./emailCode";
import { EmailCodeForm } from "./EmailCodeForm";

function Harness() {
  const [entered, setEntered] = useState("");
  return (
    <>
      <EmailCodeForm
        signIn={async (email, code) => {
          setEntered(`${email}:${code}`);
        }}
        requestChange={async () => undefined}
        confirmChange={async () => undefined}
      />
      <output>{entered}</output>
    </>
  );
}

describe("formulário de código", () => {
  it("pede e-mail e código reutilizável, com a ação Entrar", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    expect(screen.getByText(ACCESS_EXPLANATION)).toBeInTheDocument();
    expect(screen.queryByText(/vale uma vez/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Receber código" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Código")).toHaveAttribute("autocomplete", "off");
    await user.type(screen.getByLabelText("E-mail"), "pessoa@example.invalid");
    await user.type(screen.getByLabelText("Código"), "Codigo-teste-1");
    await user.click(screen.getByRole("button", { name: "Entrar" }));
    expect(screen.getByText("pessoa@example.invalid:Codigo-teste-1")).toBeInTheDocument();
    expect(screen.getByLabelText("Código")).toHaveValue("");
    expect(screen.getByRole("button", { name: "Solicitar alteração do código" })).toBeInTheDocument();
  });
});
