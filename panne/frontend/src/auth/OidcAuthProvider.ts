import { config } from "../config";
import { signInWithAccessCode } from "./emailCode";
import type { AuthProvider, AuthSession } from "./types";

const STATE_KEY = "panne.oidc.state";
const VERIFIER_KEY = "panne.oidc.verifier";

type StoredFlow = { state: string; verifier: string };

export class OidcAuthProvider implements AuthProvider {
  readonly name = "oidc" as const;
  private session: AuthSession | null = null;

  private endpoint(): string {
    return new URL(config.oidcIssuer).origin;
  }

  async signIn(email: string, code: string): Promise<void> {
    if (!config.oidcIssuer || !config.oidcClientId) {
      throw new Error("A entrada da Panne ainda não está configurada.");
    }
    const result = await signInWithAccessCode(this.endpoint(), config.oidcClientId, email, code);
    if ("error" in result) throw new Error(result.error);
    this.session = {
      accessToken: result.accessToken,
      expiresAt: result.expiresIn ? Date.now() + result.expiresIn * 1000 : null,
      displayHint: "Conta",
    };
  }

  async requestChange(email: string): Promise<void> {
    await this.postChange("/api/v1/access/code-change", { email });
  }

  async confirmChange(email: string, confirmation: string): Promise<void> {
    await this.postChange("/api/v1/access/code-change/confirm", { email, confirmation });
  }

  private async postChange(path: string, body: Record<string, string>): Promise<void> {
    const response = await fetch(`${config.apiBase}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) throw new Error("Não foi possível concluir o pedido.");
  }

  async login(): Promise<void> {
    throw new Error("Informe o e-mail e o código de acesso.");
  }

  async handleCallback(): Promise<AuthSession> {
    const params = new URLSearchParams(window.location.search);
    const storedRaw = sessionStorage.getItem(STATE_KEY);
    sessionStorage.removeItem(STATE_KEY);
    if (!storedRaw) throw new Error("Retorno de autenticação incompleto.");
    const stored = JSON.parse(storedRaw) as StoredFlow;
    if (params.get("state") !== stored.state) {
      throw new Error("Estado de autenticação inválido.");
    }
    const code = params.get("code");
    if (!code) throw new Error("Código de autorização ausente.");
    const redirect = config.oidcRedirectUri || `${window.location.origin}/callback`;
    const body = new URLSearchParams({
      grant_type: "authorization_code",
      client_id: config.oidcClientId,
      code,
      redirect_uri: redirect,
      code_verifier: stored.verifier,
    });
    const response = await fetch(`${config.oidcAuthorizeBase.replace(/\/$/, "")}/oauth2/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    if (!response.ok) throw new Error("Falha ao trocar o código de autorização.");
    const payload = (await response.json()) as {
      access_token?: string;
      expires_in?: number;
    };
    if (!payload.access_token) throw new Error("A resposta OIDC não trouxe access token.");
    this.session = {
      accessToken: payload.access_token,
      expiresAt: payload.expires_in ? Date.now() + payload.expires_in * 1000 : null,
      displayHint: "Conta",
    };
    return this.session;
  }

  async logout(): Promise<void> {
    const token = this.session?.accessToken;
    this.session = null;
    sessionStorage.removeItem(STATE_KEY);
    sessionStorage.removeItem(VERIFIER_KEY);
    if (!token || !config.oidcIssuer) return;
    try {
      await fetch(this.endpoint(), {
        method: "POST",
        headers: {
          "Content-Type": "application/x-amz-json-1.1",
          "X-Amz-Target": "AWSCognitoIdentityProviderService.GlobalSignOut",
        },
        body: JSON.stringify({ AccessToken: token }),
      });
    } catch {
      /* a sessão local já foi encerrada */
    }
  }

  getSession(): AuthSession | null {
    return this.session;
  }

  getAccessToken(): string | null {
    if (!this.session) return null;
    if (this.session.expiresAt && this.session.expiresAt <= Date.now()) {
      this.session = null;
      return null;
    }
    return this.session.accessToken;
  }
}
