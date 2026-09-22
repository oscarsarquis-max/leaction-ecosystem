/** Entrada com o código pessoal. O valor não é gravado nem devolvido em mensagem. */

const REJECTED = "O acesso não foi aceito. Confira o e-mail e o código.";
const LIMITED = "Houve tentativas demais. Espere um pouco antes de tentar de novo.";
const UPDATE = "Esta conta ainda precisa de uma atualização de acesso. Fale com o suporte da Panne.";
const UNAVAILABLE = "Não foi possível entrar agora. Tente de novo em instantes.";

export const ACCESS_EXPLANATION =
  "Para o primeiro uso, o identificador do usuário é o e-mail cadastrado na contratação pela organização. O acesso é por um código enviado a este e-mail. Ele não expira, vale sempre exceto quando solicitada a sua alteração ou por descontinuidade da relação contratual.";

type FetchLike = (input: string, init: RequestInit) => Promise<Response>;

export type AccessSignIn =
  | { accessToken: string; expiresIn: number | null }
  | { error: string };

function headers(): HeadersInit {
  return {
    "Content-Type": "application/x-amz-json-1.1",
    "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
  };
}

export async function signInWithAccessCode(
  endpoint: string,
  clientId: string,
  email: string,
  code: string,
  fetchImpl: FetchLike = fetch,
): Promise<AccessSignIn> {
  try {
    const response = await fetchImpl(endpoint, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({
        AuthFlow: "USER_PASSWORD_AUTH",
        ClientId: clientId,
        AuthParameters: { USERNAME: email.trim().toLowerCase(), PASSWORD: code },
      }),
    });
    const payload = (await response.json()) as {
      AuthenticationResult?: { AccessToken?: string; ExpiresIn?: number };
      ChallengeName?: string;
      __type?: string;
      message?: string;
    };
    const token = payload.AuthenticationResult?.AccessToken;
    if (token) {
      return { accessToken: token, expiresIn: payload.AuthenticationResult?.ExpiresIn ?? null };
    }
    if (payload.ChallengeName === "NEW_PASSWORD_REQUIRED") return { error: UPDATE };
    const kind = `${payload.__type ?? ""} ${payload.message ?? ""}`;
    if (kind.includes("TooMany") || kind.includes("LimitExceeded") || kind.includes("attempts")) {
      return { error: LIMITED };
    }
    return { error: REJECTED };
  } catch {
    return { error: UNAVAILABLE };
  }
}
