import { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { WeekdayPicker } from "./WeekdayPicker";

function Harness() {
  const [selected, setSelected] = useState<number[]>([]);
  return <WeekdayPicker selected={selected} onChange={setSelected} />;
}

describe("seletor de dias", () => {
  it("marca e desmarca pelo mouse e pelo teclado sem impor quarta ou sábado", async () => {
    const user = userEvent.setup();
    render(<Harness />);

    expect(screen.getByRole("group", { name: "Dias de produção" })).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "Quarta-feira" })).not.toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Sábado" })).not.toBeChecked();

    await user.click(screen.getByRole("checkbox", { name: "Segunda-feira" }));
    expect(screen.getByRole("checkbox", { name: "Segunda-feira" })).toBeChecked();

    const friday = screen.getByRole("checkbox", { name: "Sexta-feira" });
    friday.focus();
    await user.keyboard(" ");
    expect(friday).toBeChecked();

    await user.click(screen.getByRole("checkbox", { name: "Segunda-feira" }));
    expect(screen.getByRole("checkbox", { name: "Segunda-feira" })).not.toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Sexta-feira" })).toBeChecked();
  });
});
