import type { AuthProvider, AuthSession } from "./types";

const FAKE_TOKEN = "panne-fake-access-token";
const SUBJECT_KEY = "panne.demoSubject";
/** Flag de sessão fake na aba (sem token). Permite refresh/rota direta. */
const SESSION_FLAG = "panne.fakeSession";

export class FakeAuthProvider implements AuthProvider {
  readonly name = "fake" as const;
  private session: AuthSession | null = null;

  constructor() {
    const homolog = (import.meta.env.VITE_HOMOLOG_DEMO ?? "").trim() === "1";
    if (import.meta.env.PROD && !homolog) {
      throw new Error("O provedor falso de autenticação não pode ser usado em produção.");
    }
    this.hydrateFromSessionStorage();
  }

  async login(): Promise<void> {
    const subject =
      typeof sessionStorage !== "undefined" ? sessionStorage.getItem(SUBJECT_KEY) : null;
    this.session = {
      accessToken: subject ? `panne-demo:${subject}` : FAKE_TOKEN,
      expiresAt: Date.now() + 60 * 60 * 1000,
      displayHint: subject ? `demonstração:${subject}` : "desenvolvimento",
    };
    try {
      sessionStorage.setItem(SESSION_FLAG, "1");
    } catch {
      /* sessão de aba indisponível */
    }
  }

  async handleCallback(): Promise<AuthSession> {
    await this.login();
    if (!this.session) throw new Error("Falha no retorno de autenticação falsa.");
    return this.session;
  }

  async logout(): Promise<void> {
    this.session = null;
    try {
      sessionStorage.removeItem(SESSION_FLAG);
      sessionStorage.removeItem(SUBJECT_KEY);
    } catch {
      /* ignore */
    }
  }

  getSession(): AuthSession | null {
    this.hydrateFromSessionStorage();
    return this.session;
  }

  getAccessToken(): string | null {
    this.hydrateFromSessionStorage();
    if (!this.session) return null;
    if (this.session.expiresAt && this.session.expiresAt <= Date.now()) {
      this.session = null;
      try {
        sessionStorage.removeItem(SESSION_FLAG);
      } catch {
        /* ignore */
      }
      return null;
    }
    return this.session.accessToken;
  }

  private hydrateFromSessionStorage(): void {
    if (this.session) return;
    if (typeof sessionStorage === "undefined") return;
    let flag: string | null = null;
    let subject: string | null = null;
    try {
      flag = sessionStorage.getItem(SESSION_FLAG);
      subject = sessionStorage.getItem(SUBJECT_KEY);
    } catch {
      return;
    }
    if (flag !== "1" && !subject) return;
    this.session = {
      accessToken: subject ? `panne-demo:${subject}` : FAKE_TOKEN,
      expiresAt: Date.now() + 60 * 60 * 1000,
      displayHint: subject ? `demonstração:${subject}` : "desenvolvimento",
    };
  }
}
