import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, getHealth, requestJson } from "./http";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("cliente HTTP", () => {
  it("devolve o JSON em resposta 200", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://127.0.0.1:5075");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ status: "ok", service: "lojadepaes" }),
      }),
    );
    await expect(getHealth()).resolves.toEqual({ status: "ok", service: "lojadepaes" });
  });

  it("trata falha de rede e HTTP de erro sem engolir o status", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://127.0.0.1:5075");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    await expect(requestJson("/api/v1/health")).rejects.toMatchObject({
      name: "ApiError",
      status: 0,
      message: "rede-indisponivel",
    } satisfies Partial<ApiError>);

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        json: async () => ({ status: "unavailable" }),
      }),
    );
    await expect(requestJson("/api/v1/ready")).rejects.toMatchObject({ status: 503 });
  });

  it("envia JSON e lê o detalhe de validação do FastAPI", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "");
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({
        detail: [{ loc: ["body", "delivery_number"], msg: "informe o número do endereço de entrega" }],
      }),
    });
    vi.stubGlobal("fetch", fetchMock);
    await expect(
      requestJson("/api/v1/storefront/orders/LP/delivery-address", {
        method: "POST",
        body: JSON.stringify({ delivery_street: "Rua" }),
      }),
    ).rejects.toMatchObject({
      status: 422,
      message: "informe o número do endereço de entrega",
    });
    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.get("Content-Type")).toBe("application/json");
  });
});
