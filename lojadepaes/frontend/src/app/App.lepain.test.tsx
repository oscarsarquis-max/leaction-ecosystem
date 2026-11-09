import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";

const LEPAIN_HERO_HREF =
  "https://lepain.lojadepaes.com.br/pt?utm_source=lojadepaes&utm_medium=hero&utm_campaign=lancamento-lepain";

describe("selo do LePain", () => {
  it("mostra o selo no hero com o link e o nome acessível", () => {
    render(<App />);
    const seal = screen.getByRole("link", { name: "Conheça o LePain, o blog da Loja de Pães" });
    expect(seal).toHaveAttribute("href", LEPAIN_HERO_HREF);
    expect(seal).not.toHaveAttribute("target");
    expect(seal).toHaveClass("lepain-seal");
    expect(seal.querySelector(".lepain-seal-mark")).toBeTruthy();
    expect(seal).toHaveTextContent("NOVO");
    expect(seal).toHaveTextContent("Histórias, viagens e memórias do pão");
    const paragraph = screen.getByText(/Um pão feito à mão, do seu jeito/);
    expect(paragraph.compareDocumentPosition(seal) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(paragraph.parentElement).toBe(seal.parentElement);
  });
});
