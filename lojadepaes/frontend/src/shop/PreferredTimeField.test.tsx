import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PreferredTimeField } from "./PreferredTimeField";

describe("horário preferido", () => {
  it("começa sem preferência e aceita um horário de retirada", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const { rerender } = render(
      <PreferredTimeField value="" onChange={onChange} modality="pickup" />,
    );
    expect(screen.getByLabelText("Horário preferido para retirar")).toBeInTheDocument();
    expect(screen.getByText("Sem preferência")).toBeInTheDocument();
    expect(screen.getByText(/A Loja avaliará a possibilidade/)).toBeInTheDocument();
    await user.type(screen.getByLabelText("Horário preferido para retirar"), "16:30");
    expect(onChange).toHaveBeenCalled();
    rerender(<PreferredTimeField value="16:30" onChange={onChange} modality="pickup" />);
    expect(screen.getByText("Horário solicitado: 16:30")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Limpar horário" }));
    expect(onChange).toHaveBeenCalledWith("");
  });

  it("avisa quando o horário fica fora da janela, sem bloquear", () => {
    render(
      <PreferredTimeField
        value="21:00"
        onChange={() => undefined}
        modality="pickup"
        windows={[
          {
            id: "w1",
            starts_at: "2026-09-30T14:00:00-03:00",
            ends_at: "2026-09-30T18:00:00-03:00",
            modality: "pickup",
          },
        ]}
      />,
    );
    expect(screen.getByText(/Janela operacional: 14:00 às 18:00/)).toBeInTheDocument();
    expect(screen.getByText(/fora da janela operacional/)).toBeInTheDocument();
  });
});
