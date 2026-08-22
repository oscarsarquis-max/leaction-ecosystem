export type AuthSession = {
  accessToken: string;
  expiresAt: number | null;
  displayHint: string;
};

export type AuthProvider = {
  readonly name: "oidc" | "fake";
  login(): Promise<void>;
  handleCallback(): Promise<AuthSession>;
  logout(): Promise<void>;
  getSession(): AuthSession | null;
  getAccessToken(): string | null;
};
