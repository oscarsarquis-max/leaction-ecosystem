import { describe, expect, it } from "vitest";
import { ACCESS_EXPLANATION, signInWithAccessCode } from "./emailCode";

function respond(body: unknown, status = 200): typeof fetch {
  return (async (_input, init) => {
    const sent = JSON.parse(String(init?.body));
    expect(sent.AuthFlow).toBe("USER_PASSWORD_AUTH");
    expect(JSON.stringify(sent)).not.toContain("EMAIL_OTP");
    return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
  }) as typeof fetch;
}

describe("código reutilizável", () => {
  it("explica o contrato sem prometer expiração ou uso único", () => {
    expect(ACCESS_EXPLANATION).toContain("Ele não expira");
    expect(ACCESS_EXPLANATION).not.toContain("uma vez");
  });

  it("entra com o código e guarda só o token de acesso", async () => {
    const result = await signInWithAccessCode(
      "https://idp.example",
      "client",
      "pessoa@example.invalid",
      "Codigo-teste-1",
      respond({ AuthenticationResult: { AccessToken: "token-acesso", ExpiresIn: 3600, RefreshToken: "nao-usar" } }),
    );
    expect(result).toEqual({ accessToken: "token-acesso", expiresIn: 3600 });
  });

  it("não revela se o endereço existe e não ecoa o código", async () => {
    const wrong = await signInWithAccessCode(
      "https://idp.example",
      "client",
      "pessoa@example.invalid",
      "Codigo-errado-1",
      respond({ __type: "NotAuthorizedException", message: "Incorrect username or password." }),
    );
    const missing = await signInWithAccessCode(
      "https://idp.example",
      "client",
      "ninguem@example.invalid",
      "Codigo-errado-1",
      respond({ __type: "UserNotFoundException" }),
    );
    expect(wrong).toEqual(missing);
    expect("error" in wrong && wrong.error).toBeTruthy();
    if ("error" in wrong) expect(wrong.error).not.toContain("Codigo-errado-1");
  });

  it("distingue excesso de tentativas e conta que ainda não recebeu o código permanente", async () => {
    const limited = await signInWithAccessCode(
      "https://idp.example",
      "client",
      "pessoa@example.invalid",
      "Codigo-errado-1",
      respond({ __type: "TooManyRequestsException" }),
    );
    const update = await signInWithAccessCode(
      "https://idp.example",
      "client",
      "pessoa@example.invalid",
      "Codigo-errado-1",
      respond({ ChallengeName: "NEW_PASSWORD_REQUIRED" }),
    );
    expect(limited).not.toEqual(update);
    if ("error" in limited) expect(limited.error).toContain("tentativas");
    if ("error" in update) expect(update.error).toContain("suporte da Panne");
  });
});
