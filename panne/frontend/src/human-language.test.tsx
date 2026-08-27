import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ORDER_ID, ISSUE_ID, ordersFixture } from "./api/fixtures";
import { eventLabel, UNKNOWN_EVENT_LABEL } from "./language/events";
import { formatExactQuantity, formatOperationalQuantity } from "./language/quantities";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});

describe("R026-004 linguagem humana", () => {
  it("traduz eventos conhecidos e usa fallback humano", () => {
    expect(eventLabel("order.created")).toBe("Ordem criada");
    expect(eventLabel("order.scheduled")).toBe("Ordem programada");
    expect(eventLabel("execution.policy_set")).toBe("Política de execução definida");
    expect(eventLabel("batch.split")).toBe("Batelada criada ou dividida");
    expect(eventLabel("order.released")).toBe("Ordem liberada");
    expect(eventLabel("weighing.session_opened")).toBe("Pesagem iniciada");
    expect(eventLabel("evento.invalido.xyz")).toBe(UNKNOWN_EVENT_LABEL);
  });

  it("apresenta massa com precisão operacional e preserva valor integral", () => {
    expect(formatOperationalQuantity("1958.456973", "g")).toBe("1.958,5 g");
    expect(formatExactQuantity("1958.456973", "g")).toBe("1.958,456973 g");
    expect(formatOperationalQuantity("12", "units")).toBe("12 un");
  });

  it("detalhe da ordem: hashes recolhidos, eventos traduzidos, código público preservado", async () => {
    const hash = ordersFixture.items[0].materials_hash!;
    installApiMock({
      "/events": () =>
        json({
          items: [
            { id: "e1", type: "order.created", occurred_at: "2026-08-24T10:00:00+00:00" },
            { id: "e2", type: "order.released", occurred_at: "2026-08-24T11:00:00+00:00" },
            { id: "e3", type: "weighing.session_opened", occurred_at: "2026-08-24T12:00:00+00:00" },
          ],
          next_cursor: null,
        }),
    });
    await renderApp(`/ordens/${ORDER_ID}`);
    const user = userEvent.setup();

    expect(await screen.findByRole("heading", { name: "OP-2026-0001" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Integridade da ficha" })).toBeInTheDocument();
    expect(screen.getByText(/Materiais: versão registrada/)).toBeInTheDocument();
    expect(screen.getByText(/Registro da ordem: preservado/)).toBeInTheDocument();
    expect(screen.getByText("OP-2026-0001")).toBeInTheDocument();

    const audit = screen.getByText("Detalhes técnicos de auditoria").closest("details");
    expect(audit).toBeTruthy();
    expect(audit).not.toHaveAttribute("open");

    const history = screen.getByRole("heading", { name: "Histórico e emissões" }).closest("section");
    expect(history).toBeTruthy();
    const historyParas = [...(history as HTMLElement).querySelectorAll(":scope > p")].map((node) => node.textContent || "");
    expect(historyParas.join("\n")).toMatch(/Ordem criada/);
    expect(historyParas.join("\n")).toMatch(/Ordem liberada/);
    expect(historyParas.join("\n")).toMatch(/Pesagem iniciada/);
    expect(historyParas.join("\n")).not.toMatch(/order\.created|order\.released|weighing\.session_opened/);

    const hashNode = screen.getByText(hash);
    expect(hashNode.closest("details")).not.toHaveAttribute("open");

    await user.click(screen.getByText("Detalhes técnicos de auditoria"));
    expect(audit).toHaveAttribute("open");
    expect(within(audit as HTMLElement).getByText(hash)).toBeInTheDocument();
  });

  it("login não expõe jargão OIDC/PKCE", async () => {
    installApiMock();
    await renderApp("/entrar", { signedIn: false });
    expect(await screen.findByRole("heading", { name: "Entrar na Panne" })).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/OIDC|PKCE/i);
  });
});

describe("R026-004 regressão ficha", () => {
  it("ficha não abre hashes por padrão", async () => {
    installApiMock();
    await renderApp(`/ordens/${ORDER_ID}/fichas/${ISSUE_ID}`);
    expect(await screen.findByRole("heading", { name: /Ficha de produção/ })).toBeInTheDocument();
    expect(screen.getByText(/Integridade da ficha/)).toBeInTheDocument();
    const audit = screen.getByText("Detalhes técnicos de auditoria").closest("details");
    expect(audit).not.toHaveAttribute("open");
    expect(screen.queryByRole("heading", { name: "Hashes e versões" })).not.toBeInTheDocument();
  });
});
