import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("vitrine", () => {
  it("mantém mural, biblioteca e logo oficial", async () => {
    const user = userEvent.setup();
    render(<App />);
    const images = [...document.querySelectorAll("img")];
    const logos = screen.getAllByAltText("Loja de Pães — Boulangerie");
    expect(logos.length).toBeGreaterThanOrEqual(1);
    for (const logo of logos) {
      expect(logo).toHaveAttribute("src", "/images/lojadepaeslogo.png");
    }
    for (const image of images) {
      const src = image.getAttribute("src") ?? "";
      expect(src).not.toMatch(/lojadepaeslogo[1-4]/);
      if (logos.includes(image)) {
        expect(src).toBe("/images/lojadepaeslogo.png");
      } else {
        const decoded = decodeURIComponent(src);
        expect(decoded.includes("internal") || decoded.includes("/api/v1/catalog/media/")).toBe(true);
      }
    }

    expect(screen.getByRole("link", { name: "Nossos pães" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Crie seu pão" })).toBeInTheDocument();
    expect(await screen.findByLabelText("Usuário")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Avançar" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "O pão aproxima." })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Um mundo para descobrir/ })).toBeInTheDocument();
    expect(decodeURIComponent(document.querySelector(".intro-photo")?.getAttribute("src") ?? "")).toContain(
      "internal levain 2 bread",
    );
    expect(decodeURIComponent(document.querySelector(".preview-photo img")?.getAttribute("src") ?? "")).toContain(
      "internal 10 bread",
    );
    expect(document.querySelector(".preview-board")?.getAttribute("style") ?? "").toContain("internal%20texture%202%20bread");
    expect(document.querySelectorAll(".story-media").length).toBe(3);
    expect(decodeURIComponent(document.querySelector(".library-banner")?.getAttribute("src") ?? "")).toContain(
      "internal work 1 bread",
    );
    await user.click(screen.getByRole("button", { name: /Levain: um ingrediente vivo/i }));
    expect(document.querySelector("#reading-body h2")).toHaveTextContent("Levain: um ingrediente vivo");
    await user.click(screen.getByRole("button", { name: "Fechar leitura" }));
  });
});
