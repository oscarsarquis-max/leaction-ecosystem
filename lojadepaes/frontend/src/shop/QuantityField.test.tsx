import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { QuantityField } from "./QuantityField";

function Harness({ initial = 1 }: { initial?: number }) {
  const [value, setValue] = useState(initial);
  return <QuantityField value={value} onChange={setValue} />;
}

describe("QuantityField", () => {
  it("substitui a quantidade com mais, menos e digitação, inclusive campo vazio", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    const input = screen.getByLabelText("Quantidade");
    expect(input).toHaveValue(1);
    await user.click(screen.getByRole("button", { name: "Aumentar quantidade" }));
    expect(input).toHaveValue(2);
    await user.click(screen.getByRole("button", { name: "Diminuir quantidade" }));
    expect(input).toHaveValue(1);
    await user.clear(input);
    expect(input).toHaveValue(null);
    await user.type(input, "2");
    expect(input).toHaveValue(2);
    await user.clear(input);
    await user.tab();
    expect(input).toHaveValue(1);
  });
});
