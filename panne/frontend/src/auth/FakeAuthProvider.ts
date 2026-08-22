import type { AuthProvider, AuthSession } from "./types";

const FAKE_TOKEN = "panne-fake-access-token";

export class FakeAuthProvider implements AuthProvider {
  readonly name = "fake" as const;
  private session: AuthSession | null = null;

  constructor() {
    if (import.meta.env.PROD) {
      throw new Error("O provedor falso de autenticação não pode ser usado em produção.");
    }
  }

  async login(): Promise<void> {
    this.session = {
      accessToken: FAKE_TOKEN,
      expiresAt: Date.now() + 60 * 60 * 1000,
      displayHint: "desenvolvimento",
    };
  }

  async handleCallback(): Promise<AuthSession> {
    await this.login();
    if (!this.session) throw new Error("Falha no retorno de autenticação falsa.");
    return this.session;
  }

  async logout(): Promise<void> {
    this.session = null;
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
