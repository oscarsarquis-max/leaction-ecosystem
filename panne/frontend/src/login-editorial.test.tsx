import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { sanitizeColumn } from "./editorial/sanitize";
import { StaticLoginEditorialProvider } from "./editorial/staticProvider";
import { installApiMock } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("tela de acesso e editorial", () => {
  it("mostra três colunas e não bloqueia o login", async () => {
    installApiMock();
    const { view } = await renderApp("/entrar", { signedIn: false });
    expect(await screen.findByRole("heading", { name: "Entrar na Panne" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "O turno cabe no quadro" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Ficha antes do palpite" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Entrar em desenvolvimento" })).toBeEnabled();
    const results = await axe(view.container);
    expect(results.violations.filter((item) => item.impact === "critical")).toEqual([]);
  });

  it("recolhe laterais quando o provider está indisponível", async () => {
    window.history.replaceState({}, "", "/entrar?editorial=indisponivel");
    installApiMock();
    await renderApp("/entrar?editorial=indisponivel", { signedIn: false });
    expect(await screen.findByRole("heading", { name: "Entrar na Panne" })).toBeInTheDocument();
    expect(await screen.findByText(/colunas editoriais são opcionais/)).toBeInTheDocument();
  });

  it("sanitiza HTML e protocolo perigoso", () => {
    expect(sanitizeColumn({ placement: "left", title: "" })).toBeNull();
    const row = sanitizeColumn({
      placement: "right",
      title: "<b>Oficina</b>",
      image: { url: "javascript:alert(1)", alt: "x" },
    });
    expect(row?.title).toBe("Oficina");
    expect(row?.image.url).toBe("");
  });

  it("segunda barreira: allowlist de host e bloqueio de auth em CTA", () => {
    const ok = sanitizeColumn({
      placement: "left",
      title: "Ok",
      image: { url: "https://paneldx-cms-assets-2026.s3.amazonaws.com/a.png", alt: "a" },
      cta: { label: "Docs", url: "https://docs.leaction.com.br/x" },
    });
    expect(ok?.image.url).toContain("s3.amazonaws.com");
    expect(ok?.cta?.url).toContain("docs.leaction.com.br");
    const bad = sanitizeColumn({
      placement: "right",
      title: "Bad",
      image: { url: "https://evil.example/a.png", alt: "x" },
      cta: { label: "Login", url: "/entrar" },
    });
    expect(bad?.image.url).toBe("");
    expect(bad?.cta).toBeUndefined();
  });

  it("provider estático e inválido", async () => {
    const ok = await new StaticLoginEditorialProvider("ok").load();
    expect(ok?.columns).toHaveLength(2);
    const bad = await new StaticLoginEditorialProvider("invalid").load();
    expect(bad).toBeNull();
    const down = await new StaticLoginEditorialProvider("unavailable").load();
    expect(down).toBeNull();
  });

  it("ajuda pública não chama rede", async () => {
    installApiMock();
    await renderApp("/entrar", { signedIn: false });
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Ajuda para entrar" }));
    expect(await screen.findByRole("heading", { name: /Ajuda para entrar/ })).toBeInTheDocument();
  });

  it("R026-005: marca fica no cabeçalho estrutural da caixa", async () => {
    installApiMock();
    const { view } = await renderApp("/entrar", { signedIn: false });
    expect(await screen.findByRole("heading", { name: "Entrar na Panne" })).toBeInTheDocument();
    const brand = screen.getByRole("img", { name: "Panne" });
    expect(brand).toHaveClass("login-center__brand");
    expect(brand.closest("header")).toHaveClass("login-center__header");
    expect(brand.closest("header")?.parentElement).toHaveClass("login-center");
    expect(view.container.querySelector(".login-center__body")).toContainElement(
      screen.getByRole("heading", { name: "Entrar na Panne" }),
    );
    expect(view.container.querySelector(".login-brand")).toBeNull();
  });

  it("R026-005: marca fica no cabeçalho estrutural da caixa", async () => {
    installApiMock();
    const { view } = await renderApp("/entrar", { signedIn: false });
    expect(await screen.findByRole("heading", { name: "Entrar na Panne" })).toBeInTheDocument();
    const brand = screen.getByRole("img", { name: "Panne" });
    expect(brand).toHaveClass("login-center__brand");
    expect(brand.closest("header")).toHaveClass("login-center__header");
    expect(brand.closest("header")?.parentElement).toHaveClass("login-center");
    expect(view.container.querySelector(".login-center__body")).toContainElement(
      screen.getByRole("heading", { name: "Entrar na Panne" }),
    );
    expect(view.container.querySelector(".login-brand")).toBeNull();
  });
});
