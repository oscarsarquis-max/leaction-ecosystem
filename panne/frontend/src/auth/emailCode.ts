/** Troca de código com o Cognito. O código e a sessão ficam só na memória de quem chama. */

const SENT =
  "Se este endereço puder entrar na Panne, enviamos um código. Ele expira e só pode ser usado uma vez.";
const UNAVAILABLE = "Não foi possível enviar o código agora. Tente de novo em instantes.";
const REJECTED = "O código não foi aceito. Confira e tente de novo, ou peça outro.";
const EXPIRED = "Esse código expirou. Peça outro.";
const LIMITED = "Houve tentativas demais. Espere um pouco antes de pedir outro código.";
const UPDATE =
  "Esta conta ainda precisa de uma atualização de acesso. Fale com o suporte da Panne.";

export type CodeRequest = {
  session: string | null;
  notice: string;
  advance: boolean;
};

export type CodeConfirmation =
  | { accessToken: string; expiresIn: number | null }
  | { error: string; session: string | null };

type FetchLike = (input: string, init: RequestInit) => Promise<Response>;

function idpHeaders(target: string): HeadersInit {
  return {
    "Content-Type": "application/x-amz-json-1.1",
    "X-Amz-Target": `AWSCognitoIdentityProviderService.${target}`,
  };
}

function emailLooksUsable(value: string): boolean {
  return value.includes("@") && !value.startsWith("@") && !value.endsWith("@") && !value.includes(" ");
}

export async function requestEmailCode(
  endpoint: string,
  clientId: string,
  email: string,
  fetchImpl: FetchLike = fetch,
): Promise<CodeRequest> {
  const username = email.trim().toLowerCase();
  if (!emailLooksUsable(username)) {
    return { session: null, notice: "Informe o e-mail usado na Panne.", advance: false };
  }
  try {
    const response = await fetchImpl(endpoint, {
      method: "POST",
      headers: idpHeaders("InitiateAuth"),
      body: JSON.stringify({
        AuthFlow: "USER_AUTH",
        ClientId: clientId,
        AuthParameters: { USERNAME: username, PREFERRED_CHALLENGE: "EMAIL_OTP" },
      }),
    });
    const payload = (await response.json()) as {
      ChallengeName?: string;
      Session?: string;
      __type?: string;
    };
    if (payload.ChallengeName === "EMAIL_OTP" && payload.Session) {
      return { session: payload.Session, notice: SENT, advance: true };
    }
    if (payload.ChallengeName && payload.ChallengeName !== "EMAIL_OTP") {
      return { session: null, notice: UPDATE, advance: false };
    }
    return { session: null, notice: SENT, advance: true };
  } catch {
    return { session: null, notice: UNAVAILABLE, advance: false };
  }
}

export async function confirmEmailCode(
  endpoint: string,
  clientId: string,
  email: string,
  session: string | null,
  code: string,
  fetchImpl: FetchLike = fetch,
): Promise<CodeConfirmation> {
  const digits = code.replace(/\s/g, "");
  if (!session || !/^[0-9]{4,8}$/.test(digits)) {
    return { error: REJECTED, session };
  }
  try {
    const response = await fetchImpl(endpoint, {
      method: "POST",
      headers: idpHeaders("RespondToAuthChallenge"),
      body: JSON.stringify({
        ChallengeName: "EMAIL_OTP",
        ClientId: clientId,
        Session: session,
        ChallengeResponses: {
          USERNAME: email.trim().toLowerCase(),
          EMAIL_OTP_CODE: digits,
        },
      }),
    });
    const payload = (await response.json()) as {
      AuthenticationResult?: { AccessToken?: string; ExpiresIn?: number };
      Session?: string;
      __type?: string;
    };
    const token = payload.AuthenticationResult?.AccessToken;
    if (token) {
      return { accessToken: token, expiresIn: payload.AuthenticationResult?.ExpiresIn ?? null };
    }
    const nextSession = payload.Session ?? null;
    const kind = payload.__type ?? "";
    if (kind.includes("ExpiredCode")) return { error: EXPIRED, session: nextSession };
    if (kind.includes("LimitExceeded") || kind.includes("TooMany")) return { error: LIMITED, session: nextSession };
    return { error: REJECTED, session: nextSession };
  } catch {
    return { error: UNAVAILABLE, session: null };
  }
}

export const EMAIL_CODE_COPY = { SENT, UNAVAILABLE, REJECTED, EXPIRED, LIMITED, UPDATE };
