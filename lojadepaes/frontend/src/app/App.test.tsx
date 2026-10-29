import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("vitrine", () => {
  it("mantém mural, biblioteca e logo oficial", async () => {
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
        expect(
          decoded.includes("internal") ||
            decoded.includes("/api/v1/catalog/media/") ||
            decoded.includes("vitrine da loja"),
        ).toBe(true);
      }
    }

    expect(screen.getByRole("link", { name: "Nossos pães" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Crie seu pão" })).toBeInTheDocument();
    expect(await screen.findByLabelText("Usuário")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Avançar" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "O pão aproxima." })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Um mundo para descobrir/ })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Fale com A Loja" })).toBeInTheDocument();
    const whatsapp = screen.getByRole("link", { name: /Converse pelo WhatsApp/ });
    expect(whatsapp).toHaveAttribute("href", "https://wa.me/5585999831861");
    expect(whatsapp).toHaveAttribute("target", "_blank");
    expect(whatsapp).toHaveAttribute("rel", "noopener noreferrer");
    expect(whatsapp).toHaveTextContent("(85) 99983-1861");
    expect(whatsapp.getAttribute("href")).not.toMatch(/[?&]text=/);
    const instagram = screen.getByRole("link", { name: /Acompanhe no Instagram/ });
    expect(instagram).toHaveAttribute("href", "https://www.instagram.com/loja.de.paes/");
    expect(instagram).toHaveAttribute("target", "_blank");
    expect(instagram).toHaveAttribute("rel", "noopener noreferrer");
    expect(instagram).toHaveTextContent("@loja.de.paes");
    expect(document.querySelector(".home-contact")?.nextElementSibling).toBeNull();
    expect(decodeURIComponent(document.querySelector(".intro-photo")?.getAttribute("src") ?? "")).toContain(
      "vitrine da loja",
    );
    expect(screen.getByRole("img", { name: "Vitrine com pães artesanais" })).toBeInTheDocument();
    expect(screen.getByText("O DESPERTAR DO LEVAIN")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Todo pão tem uma história/ })).toBeInTheDocument();
    expect(document.querySelector(".intro-aside .seal")).toBeNull();
    expect(decodeURIComponent(document.querySelector(".preview-photo img")?.getAttribute("src") ?? "")).toContain(
      "internal 10 bread",
    );
    expect(document.querySelector(".preview-board")?.getAttribute("style") ?? "").toContain("internal%20texture%202%20bread");
    expect(document.querySelectorAll(".story-media").length).toBe(3);
    expect(decodeURIComponent(document.querySelector(".library-banner")?.getAttribute("src") ?? "")).toContain(
      "internal work 1 bread",
    );
    expect(screen.getByRole("link", { name: /Levain e a porcentagem de padeiro/i })).toHaveAttribute(
      "href",
      "/biblioteca/o-comeco",
    );
    expect(screen.getByRole("link", { name: /Dobras, hidratação e o ponto da massa/i })).toHaveAttribute(
      "href",
      "/biblioteca/as-maos-na-massa",
    );
    expect(screen.getByRole("link", { name: /Guardar, fatiar e aproveitar o pão/i })).toHaveAttribute(
      "href",
      "/biblioteca/a-mesa",
    );
    expect(screen.getByRole("link", { name: /Abrir a calculadora de porcentagem de padeiro/i })).toHaveAttribute(
      "href",
      "/biblioteca/calculadora",
    );
  });
});
