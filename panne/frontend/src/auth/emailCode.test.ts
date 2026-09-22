import { describe, expect, it } from "vitest";
import { confirmEmailCode, EMAIL_CODE_COPY, requestEmailCode } from "./emailCode";

function respond(body: unknown): typeof fetch {
  return (async () =>
    new Response(JSON.stringify(body), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    })) as typeof fetch;
}

describe("código por e-mail", () => {
  it("aceita o desafio de código e não devolve a sessão na mensagem", async () => {
    const result = await requestEmailCode(
      "https://idp.example",
      "client",
      "pessoa@example.invalid",
      respond({ ChallengeName: "EMAIL_OTP", Session: "sessao-secreta" }),
    );
    expect(result.advance).toBe(true);
    expect(result.session).toBe("sessao-secreta");
    expect(result.notice).toBe(EMAIL_CODE_COPY.SENT);
    expect(result.notice).not.toContain("sessao-secreta");
  });

  it("não revela endereço inexistente", async () => {
    const result = await requestEmailCode(
      "https://idp.example",
      "client",
      "ninguem@example.invalid",
      respond({ __type: "UserNotFoundException" }),
    );
    expect(result.advance).toBe(true);
    expect(result.session).toBeNull();
    expect(result.notice).toBe(EMAIL_CODE_COPY.SENT);
  });

  it("não pede senha quando o desafio é outro", async () => {
    const result = await requestEmailCode(
      "https://idp.example",
      "client",
      "pessoa@example.invalid",
      respond({ ChallengeName: "NEW_PASSWORD_REQUIRED", Session: "x" }),
    );
    expect(result.advance).toBe(false);
    expect(result.notice).toBe(EMAIL_CODE_COPY.UPDATE);
    expect(result.notice.toLowerCase()).not.toContain("senha");
  });

  it("recusa código errado, expirado e estourado sem ecoar o código", async () => {
    const wrong = await confirmEmailCode(
      "https://idp.example",
      "client",
      "pessoa@example.invalid",
      "sessao",
      "123456",
      respond({ __type: "CodeMismatchException", Session: "seguinte" }),
    );
    expect(wrong).toEqual({ error: EMAIL_CODE_COPY.REJECTED, session: "seguinte" });
    expect("error" in wrong && wrong.error.includes("123456")).toBe(false);

    const expired = await confirmEmailCode(
      "https://idp.example",
      "client",
      "pessoa@example.invalid",
      "sessao",
      "123456",
      respond({ __type: "ExpiredCodeException" }),
    );
    expect(expired).toMatchObject({ error: EMAIL_CODE_COPY.EXPIRED });

    const limited = await confirmEmailCode(
      "https://idp.example",
      "client",
      "pessoa@example.invalid",
      "sessao",
      "123456",
      respond({ __type: "TooManyFailedAttemptsException" }),
    );
    expect(limited).toMatchObject({ error: EMAIL_CODE_COPY.LIMITED });
  });

  it("guarda só o access token quando o código confere", async () => {
    const ok = await confirmEmailCode(
      "https://idp.example",
      "client",
      "pessoa@example.invalid",
      "sessao",
      "123456",
      respond({
        AuthenticationResult: { AccessToken: "acesso", ExpiresIn: 3600, RefreshToken: "nao-guardar" },
      }),
    );
    expect(ok).toEqual({ accessToken: "acesso", expiresIn: 3600 });
    expect(JSON.stringify(ok)).not.toContain("nao-guardar");
  });
});
