import { describe, it, expect, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import ExperienceHub, { INFOGRAPHIC_ALT, INFOGRAPHIC_SRC } from "./ExperienceHub.jsx";
import { CAMPOABERTO_ARTICLE_URL } from "./urls.js";

afterEach(() => cleanup());

const FORBIDDEN = /mock|laboratório|demo técnica|prompt|bean|provider scripted|Passo 1|Roteiro da experiência/i;
const CHAPTERS = [
  "hub-hero",
  "hub-problem",
  "hub-context-model",
  "hub-how",
  "hub-capabilities",
  "hub-integration",
  "hub-experiences",
  "hub-governance",
  "hub-architecture",
  "hub-closing",
];

describe("Spider Experience", () => {
  it("answers what Spider is on the first fold", () => {
    render(<ExperienceHub />);
    const hero = screen.getByTestId("hub-hero");
    expect(screen.getByTestId("hub-brand")).toHaveTextContent("SPIDER");
    expect(screen.getByTestId("hub-brand")).toHaveTextContent("Plataforma Contextual");
    expect(hero).toHaveTextContent(/Transformamos objetivos/i);
    expect(hero).toHaveTextContent(/caminhos executáveis/i);
    expect(screen.getByTestId("hub-cta-try")).toHaveTextContent(/^Experimentar$/);
    expect(hero).not.toHaveTextContent(/Sobre o Spider/i);
    expect(hero.textContent).not.toMatch(FORBIDDEN);
  });

  it("tells the product story across ten chapters", () => {
    render(<ExperienceHub />);
    CHAPTERS.forEach((id) => expect(screen.getByTestId(id)).toBeInTheDocument());
    expect(screen.getByTestId("hub-problem")).toHaveTextContent(/trabalhar juntos/i);
    expect(screen.getByTestId("hub-context-model")).toHaveTextContent(/objetivo continua pertencendo/i);
    expect(screen.getByTestId("hub-how")).toHaveTextContent(/Intent Contract/i);
    expect(screen.getByTestId("hub-ai-principle")).toHaveTextContent(/IA interpreta/i);
    expect(screen.getByTestId("hub-capabilities")).toHaveTextContent(/capacidade empresarial permanece/i);
    expect(screen.getByTestId("hub-integration")).toHaveTextContent(/não exige que todo o ambiente seja modernizado/i);
    expect(screen.getByTestId("hub-experiences")).toHaveTextContent(/contexto é criado depois do clique/i);
    expect(screen.getByTestId("hub-governance")).toHaveTextContent(/Arquitetura preparada/i);
    expect(screen.getByTestId("hub-architecture")).toHaveTextContent(/Fontes e canais/i);
    expect(screen.getByTestId("hub-closing")).toHaveTextContent(/Comece pelo objetivo/i);
  });

  it("starts CampoAberto from the product CTAs and keeps Console separate", () => {
    render(<ExperienceHub />);
    expect(screen.getByTestId("hub-cta-try")).toHaveAttribute("href", CAMPOABERTO_ARTICLE_URL);
    expect(screen.getByTestId("open-partner")).toHaveAttribute("href", CAMPOABERTO_ARTICLE_URL);
    expect(screen.getByTestId("open-partner")).toHaveTextContent(/Experimentar essa jornada/i);
    expect(screen.getByTestId("open-console")).toHaveAttribute("href", "/console");
    expect(screen.getByTestId("open-spiderbank")).toHaveAttribute("href", "/spiderbank");
    expect(screen.queryByTestId("spider-console")).not.toBeInTheDocument();
    expect(screen.queryByTestId("spiderbank-entry")).not.toBeInTheDocument();
  });

  it("introduces architecture before expanding the infographic", () => {
    render(<ExperienceHub />);
    expect(screen.getByAltText(INFOGRAPHIC_ALT)).toHaveAttribute("src", INFOGRAPHIC_SRC);
    expect(screen.queryByTestId("hub-lightbox")).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId("hub-expand-architecture"));
    expect(screen.getByTestId("hub-lightbox")).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByTestId("hub-lightbox")).not.toBeInTheDocument();
  });

  it("lets the visitor explore pipeline, capabilities and governance", () => {
    render(<ExperienceHub />);
    fireEvent.click(screen.getByRole("tab", { name: "Plano" }));
    expect(screen.getByTestId("pipeline-detail")).toHaveTextContent(/Execution Plan/i);
    expect(screen.getByTestId("hub-ai-principle")).toHaveTextContent(/Spider decide/i);
    fireEvent.click(screen.getByRole("tab", { name: "Simular" }));
    expect(screen.getByTestId("capability-panel")).toHaveTextContent(/Exemplo de jornada/i);
    fireEvent.click(screen.getByRole("tab", { name: "Resilience" }));
    expect(screen.getByTestId("governance-panel")).toHaveTextContent(/Wait\/Resume/i);
    fireEvent.click(screen.getByTestId("experience-walkthrough"));
    expect(screen.getByTestId("experience-walk-panel")).toHaveTextContent(/Origem/i);
  });

  it("keeps the demonstration footer and does not leak a script", () => {
    render(<ExperienceHub />);
    expect(screen.getByTestId("experience-hub")).toHaveTextContent(/Ambiente de demonstração/i);
    expect(screen.getByTestId("experience-hub").textContent).not.toMatch(/Passo \d/);
    expect(screen.queryByRole("heading", { name: "Sobre o Spider" })).not.toBeInTheDocument();
  });
});
