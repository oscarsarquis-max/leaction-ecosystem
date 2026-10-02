import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SearchableSelect } from "./SearchableSelect";

const options = [
  { id: "cat-1", code: "C1", name: "Insumos", active: true, version: 1 },
  { id: "cat-2", code: "C2", name: "Embalagem", active: true, version: 1 },
];

describe("SearchableSelect", () => {
  it("searches, selects with keyboard, and shows no results", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<SearchableSelect label="Categoria" value="" onChange={onChange} options={options} emptyLabel="Todas" />);
    const combo = screen.getByRole("combobox", { name: "Categoria" });
    expect(combo).toHaveValue("Todas");
    await user.click(combo);
    expect(screen.getByRole("listbox", { name: "Categoria" })).toBeInTheDocument();
    await user.type(combo, "emb");
    expect(screen.getByRole("option", { name: "Embalagem" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "Insumos" })).not.toBeInTheDocument();
    await user.keyboard("{ArrowDown}{Enter}");
    expect(onChange).toHaveBeenCalledWith("cat-2");
    await user.click(screen.getByRole("combobox", { name: "Categoria" }));
    await user.clear(screen.getByRole("combobox", { name: "Categoria" }));
    await user.type(screen.getByRole("combobox", { name: "Categoria" }), "xyz");
    expect(screen.getByText("Nenhum resultado")).toBeInTheDocument();
  });
});
