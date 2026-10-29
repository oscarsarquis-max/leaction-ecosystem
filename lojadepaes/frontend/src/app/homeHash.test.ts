import { afterEach, describe, expect, it, vi } from "vitest";
import { goStorefrontUnlessModified, homeSectionHref, scrollToLocationHash } from "./homeHash";

describe("âncoras da home", () => {
  afterEach(() => {
    window.history.pushState({}, "", "/");
    document.body.replaceChildren();
  });

  it("fora da home prefixa a rota da vitrine", () => {
    expect(homeSectionHref("#paes", "/")).toBe("#paes");
    expect(homeSectionHref("#paes", "/receitas/sardinhas-e-homus")).toBe("/#paes");
    expect(homeSectionHref("#criacao", "/paes/pao-da-casa")).toBe("/#criacao");
    expect(homeSectionHref("#mural", "/pedido/novo")).toBe("/#mural");
    expect(homeSectionHref("#biblioteca", "/admin/produtos")).toBe("/#biblioteca");
  });

  it("navega pela vitrine sem recarregar quando o clique é primário", () => {
    const push = vi.spyOn(window.history, "pushState");
    window.history.pushState({}, "", "/receitas/sardinhas-e-homus");
    const event = { preventDefault: vi.fn(), button: 0 };
    goStorefrontUnlessModified(event, "/#paes");
    expect(event.preventDefault).toHaveBeenCalled();
    expect(push).toHaveBeenCalledWith({}, "", "/#paes");
    push.mockRestore();
  });

  it("não intercepta clique modificado nem âncora já na home", () => {
    const event = { preventDefault: vi.fn(), button: 0, ctrlKey: true };
    goStorefrontUnlessModified(event, "/#paes");
    expect(event.preventDefault).not.toHaveBeenCalled();

    window.history.pushState({}, "", "/");
    const samePage = { preventDefault: vi.fn(), button: 0 };
    goStorefrontUnlessModified(samePage, "#paes");
    expect(samePage.preventDefault).not.toHaveBeenCalled();
  });

  it("rola até a seção quando o alvo já está no documento", async () => {
    const target = document.createElement("section");
    target.id = "paes";
    document.body.append(target);
    const scrollTo = vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    window.history.pushState({}, "", "/#paes");
    const stop = scrollToLocationHash();
    await vi.waitFor(() => expect(scrollTo).toHaveBeenCalled());
    stop();
    scrollTo.mockRestore();
  });

  it("espera o alvo aparecer sem temporizador", async () => {
    window.history.pushState({}, "", "/#criacao");
    const scrollTo = vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    const stop = scrollToLocationHash();
    const target = document.createElement("section");
    target.id = "criacao";
    document.body.append(target);
    await vi.waitFor(() => expect(scrollTo).toHaveBeenCalled());
    stop();
    scrollTo.mockRestore();
  });
});
