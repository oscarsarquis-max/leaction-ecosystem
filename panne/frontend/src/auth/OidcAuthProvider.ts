import { config } from "../config";
import { createPkce, randomState } from "./pkce";
import type { AuthProvider, AuthSession } from "./types";

const STATE_KEY = "panne.oidc.state";
const VERIFIER_KEY = "panne.oidc.verifier";

type StoredFlow = { state: string; verifier: string };

export class OidcAuthProvider implements AuthProvider {
  readonly name = "oidc" as const;
  private session: AuthSession | null = null;

  async login(): Promise<void> {
    if (!config.oidcIssuer || !config.oidcClientId) {
      throw new Error("OIDC não configurado. Informe emissor e client ID.");
    }
    const { verifier, challenge } = await createPkce();
    const state = randomState();
    sessionStorage.setItem(STATE_KEY, JSON.stringify({ state, verifier } satisfies StoredFlow));
    const redirect = config.oidcRedirectUri || `${window.location.origin}/callback`;
    const authorize = new URL(`${config.oidcIssuer.replace(/\/$/, "")}/oauth2/authorize`);
    authorize.searchParams.set("response_type", "code");
    authorize.searchParams.set("client_id", config.oidcClientId);
    authorize.searchParams.set("redirect_uri", redirect);
    authorize.searchParams.set("scope", config.oidcScopes);
    authorize.searchParams.set("state", state);
    authorize.searchParams.set("code_challenge", challenge);
    authorize.searchParams.set("code_challenge_method", "S256");
    window.location.assign(authorize.toString());
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
    const response = await fetch(`${config.oidcIssuer.replace(/\/$/, "")}/oauth2/token`, {
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
      displayHint: "oidc",
    };
    return this.session;
  }

  async logout(): Promise<void> {
    this.session = null;
    sessionStorage.removeItem(STATE_KEY);
    sessionStorage.removeItem(VERIFIER_KEY);
    if (config.oidcLogoutUri) {
      const target = new URL(config.oidcLogoutUri);
      target.searchParams.set("client_id", config.oidcClientId);
      target.searchParams.set("logout_uri", window.location.origin);
      window.location.assign(target.toString());
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
