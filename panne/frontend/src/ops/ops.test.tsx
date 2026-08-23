import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { ORDER_ID, executionFixture, operatorMeFixture } from "../api/fixtures";
import { json, installApiMock } from "../test/fetchMock";
import { renderApp } from "../test/renderApp";
import { parseQuantityInput } from "./parseQuantity";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("modo operacional", () => {
  it("protege a rota e mostra o fluxo sem custos", async () => {
    installApiMock({
      "/api/v1/me": () => json(operatorMeFixture),
    });
    const { view } = await renderApp(`/producao/ordens/${ORDER_ID}/executar`);
    expect(await screen.findByRole("heading", { name: /Executar OP-2026-0001/ })).toBeInTheDocument();
    expect(screen.getAllByText(/Farinha de trigo/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/ocorrência bloqueante/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Encerramento parcial não é conclusão normal/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Concluir ordem" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Encerrar parcialmente" })).toBeInTheDocument();
    expect(document.body.textContent?.toLowerCase()).not.toContain("preço");
    const results = await axe(view.container);
    expect(results.violations.filter((item) => item.impact === "critical")).toEqual([]);
  });

  it("nega a rota operacional sem leitura de ordem", async () => {
    installApiMock({
      "/api/v1/me": () =>
        json({
          ...operatorMeFixture,
          associations: operatorMeFixture.associations.map((item) => ({
            ...item,
            permissions: item.permissions.filter((code) => code !== "production.order.read"),
          })),
          permissions: operatorMeFixture.permissions.filter((code) => code !== "production.order.read"),
        }),
    });
    await renderApp(`/producao/ordens/${ORDER_ID}/executar`);
    expect(await screen.findByRole("alert")).toHaveTextContent("permissão");
    expect(screen.queryByRole("heading", { name: /Executar/ })).not.toBeInTheDocument();
  });

  it("reusa Idempotency-Key no retry e bloqueia duplo clique", async () => {
    let writes = 0;
    installApiMock({
      "/api/v1/me": () => json(operatorMeFixture),
      "/entries": () => {
        writes += 1;
        if (writes === 1) return json({ code: "indisponivel", message: "tente de novo" }, 503);
        return json({ data: { id: "cmd-1" } });
      },
    });
    await renderApp(`/producao/ordens/${ORDER_ID}/executar`);
    const user = userEvent.setup();
    const quantity = await screen.findByLabelText("Quantidade pesada");
    await user.type(quantity, "7,250");
    const submit = screen.getByRole("button", { name: "Registrar pesagem" });
    await user.click(submit);
    await screen.findByRole("alert");
    await user.click(submit);
    await waitFor(() => expect(writes).toBe(2));
    const keys = vi.mocked(fetch).mock.calls
      .map(([input, init]) => {
        const method = input instanceof Request ? input.method : init?.method ?? "GET";
        if (method === "GET") return null;
        const headers = input instanceof Request ? input.headers : init?.headers;
        return headers instanceof Headers
          ? headers.get("Idempotency-Key")
          : (headers as Record<string, string> | undefined)?.["Idempotency-Key"];
      })
      .filter((value): value is string => Boolean(value));
    expect(new Set(keys).size).toBe(1);
  });

  it("explica conflito 409 e oferece recarregar", async () => {
    installApiMock({
      "/api/v1/me": () => json(operatorMeFixture),
      "/entries": () => json({ code: "conflito", message: "O estado mudou." }, 409),
    });
    await renderApp(`/producao/ordens/${ORDER_ID}/executar`);
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Quantidade pesada"), "1,5");
    await user.click(screen.getByRole("button", { name: "Registrar pesagem" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("estado mudou");
    expect(screen.getByRole("button", { name: "Recarregar" })).toBeInTheDocument();
  });

  it("trata gramas, quilogramas e vírgula como string", () => {
    expect(parseQuantityInput("7,250")).toBe("7.250");
    expect(parseQuantityInput("1.234,5")).toBe("1234.5");
    expect(parseQuantityInput("7000")).toBe("7000");
    expect(parseQuantityInput("abc")).toBeNull();
  });

  it("mostra pesagem fora da tolerância e segunda conferência por outro usuário", async () => {
    installApiMock({
      "/api/v1/me": () => json(operatorMeFixture),
    });
    await renderApp(`/producao/ordens/${ORDER_ID}/executar`);
    expect(await screen.findByText(/fora da tolerância/)).toBeInTheDocument();
    expect(screen.getByText(/Aguardando conferência por outro usuário/)).toBeInTheDocument();
    expect(screen.getByText(/Saia e entre com outro usuário/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Aceitar" })).not.toBeInTheDocument();
  });

  it("apresenta conferência quando o visualizador não é o operador", async () => {
    installApiMock({
      "/api/v1/me": () => json(operatorMeFixture),
      "/execution": () =>
        json({
          data: {
            ...executionFixture.data,
            viewer: { ...executionFixture.data.viewer, user_id: "outro-usuario" },
          },
        }),
    });
    await renderApp(`/producao/ordens/${ORDER_ID}/executar`);
    expect(await screen.findByRole("button", { name: "Aceitar" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Rejeitar" })).toBeInTheDocument();
  });

  it("oferece reversão, correção, consumo e etapas", async () => {
    installApiMock({
      "/api/v1/me": () => json(operatorMeFixture),
    });
    await renderApp(`/producao/ordens/${ORDER_ID}/executar`);
    expect(await screen.findByRole("button", { name: "Reverter" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Corrigir" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Registrar consumo" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Concluir" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancelar etapa" })).toBeInTheDocument();
    expect(screen.getAllByText(/cronômetro/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Massa final/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reemitir ficha" })).toBeInTheDocument();
  });

  it("mostra estabelecimento e responsável na ficha e imprime o payload já carregado", async () => {
    const print = vi.fn();
    vi.stubGlobal("print", print);
    installApiMock();
    await renderApp(`/ordens/${ORDER_ID}/fichas/cccccccc-cccc-cccc-cccc-cccccccccccc`);
    expect(await screen.findByText(/Estabelecimento:/)).toBeInTheDocument();
    expect(screen.getAllByText(/Padaria Central/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Ana Padeiro/).length).toBeGreaterThan(0);
    const fetchCount = vi.mocked(fetch).mock.calls.length;
    await userEvent.setup().click(screen.getByRole("button", { name: "Imprimir" }));
    expect(print).toHaveBeenCalled();
    expect(vi.mocked(fetch).mock.calls.length).toBe(fetchCount);
  });

  it("mostra não informado quando a emissão antiga não tem snapshot", async () => {
    installApiMock({
      "/sheets/cccccccc-cccc-cccc-cccc-cccccccccccc": () =>
        json({
          data: {
            id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
            issue_number: 1,
            purpose: "operational",
            order_status_at_issue: "released",
            previous_issue_id: null,
            payload_sha256: "old",
            canonical_payload: { schema_version: "1", order: { public_code: "OP-2026-0001" } },
          },
        }),
    });
    await renderApp(`/ordens/${ORDER_ID}/fichas/cccccccc-cccc-cccc-cccc-cccccccccccc`);
    expect(await screen.findByText(/Estabelecimento:/)).toHaveTextContent("não informado");
    expect(screen.getByText(/Responsável, data e hora/i).closest("section")).toHaveTextContent("não informado");
  });

  it("limpa rascunho operacional na troca de organização", async () => {
    installApiMock();
    await renderApp(`/producao/ordens/${ORDER_ID}/executar`);
    const user = userEvent.setup();
    const quantity = await screen.findByLabelText("Quantidade pesada");
    await user.type(quantity, "1,2");
    expect(quantity).toHaveValue("1,2");
    await user.selectOptions(
      screen.getByLabelText("Organização ativa"),
      operatorMeFixture.associations[1].organization_id,
    );
    await waitFor(() => {
      expect(screen.getByLabelText("Quantidade pesada")).toHaveValue("");
    });
  });
});
