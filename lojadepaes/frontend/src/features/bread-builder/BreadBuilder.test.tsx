import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { BreadBuilder } from "./BreadBuilder";

describe("BreadBuilder", () => {
  it("preserva escolhas ao voltar e exige data e horário para concluir", async () => {
    const user = userEvent.setup();
    render(<BreadBuilder />);

    expect(decodeURIComponent(document.querySelector(".preview-photo img")?.getAttribute("src") ?? "")).toContain(
      "internal 10 bread",
    );
    expect(document.querySelector(".preview-board")?.getAttribute("style") ?? "").toContain("internal%20texture%202%20bread");

    await user.click(screen.getByRole("button", { name: /integral/i }));
    await user.click(screen.getByRole("button", { name: /escolher os sabores/i }));
    expect(decodeURIComponent(document.querySelector(".preview-photo img")?.getAttribute("src") ?? "")).toContain(
      "internal 10 bread",
    );
    expect(document.querySelector(".preview-board")?.getAttribute("style") ?? "").toContain("internal%20texture%202%20bread");
    await user.click(screen.getByRole("button", { name: /nozes/i }));
    await user.click(screen.getByRole("button", { name: /escolher a forma/i }));
    await user.click(screen.getByRole("button", { name: /pão de forma/i }));
    await user.click(screen.getByRole("button", { name: /combinar o encontro/i }));

    const conclude = screen.getByRole("button", { name: /concluir minha criação/i });
    expect(conclude).toBeDisabled();

    const enabledDay = screen.getAllByRole("button").find((button) => {
      return button.classList.contains("day") && !button.hasAttribute("disabled");
    });
    expect(enabledDay).toBeTruthy();
    await user.click(enabledDay!);
    expect(conclude).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "14h–16h" }));
    expect(conclude).toBeEnabled();

    await user.click(screen.getByRole("button", { name: /voltar/i }));
    expect(screen.getByRole("button", { name: /pão de forma/i })).toHaveAttribute("aria-pressed", "true");
    await user.click(screen.getByRole("button", { name: /voltar/i }));
    expect(screen.getByRole("button", { name: /nozes/i })).toHaveAttribute("aria-pressed", "true");
    await user.click(screen.getByRole("button", { name: /voltar/i }));
    expect(screen.getByRole("button", { name: /integral/i })).toHaveAttribute("aria-pressed", "true");

    await user.click(screen.getByRole("button", { name: /escolher os sabores/i }));
    await user.click(screen.getByRole("button", { name: /escolher a forma/i }));
    await user.click(screen.getByRole("button", { name: /combinar o encontro/i }));
    await user.click(screen.getByRole("button", { name: /concluir minha criação/i }));

    expect(screen.getByText("SUA COMBINAÇÃO ESTÁ PRONTA")).toBeInTheDocument();
    const receipt = document.querySelector(".receipt");
    expect(receipt).toHaveTextContent("Integral");
    expect(receipt).toHaveTextContent("Nozes");
    expect(receipt).toHaveTextContent("Pão de forma");
    expect(receipt).toHaveTextContent("14h–16h");
    expect(screen.getByText(/simulação/i)).toBeInTheDocument();
  });
});
