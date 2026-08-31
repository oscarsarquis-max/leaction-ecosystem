export type AuthProviderName = "oidc" | "fake";

function read(name: keyof ImportMetaEnv, fallback = ""): string {
  return (import.meta.env[name] ?? fallback).trim();
}

/** Homologação hospedada: VITE_HOMOLOG_DEMO=1 libera fake+demoMode em build PROD. */
const homologDemo = read("VITE_HOMOLOG_DEMO") === "1";

export const config = {
  authProvider: (read("VITE_AUTH_PROVIDER") ||
    (import.meta.env.PROD && !homologDemo ? "oidc" : "fake")) as AuthProviderName,
  oidcIssuer: read("VITE_OIDC_ISSUER"),
  oidcClientId: read("VITE_OIDC_CLIENT_ID"),
  oidcRedirectUri: read("VITE_OIDC_REDIRECT_URI"),
  oidcScopes: read("VITE_OIDC_SCOPES", "openid profile"),
  oidcLogoutUri: read("VITE_OIDC_LOGOUT_URI"),
  apiBase: read("VITE_API_BASE"),
  evidence: read("VITE_EVIDENCE") === "1",
  demoMode: (homologDemo || !import.meta.env.PROD) && read("VITE_DEMO_MODE") === "1",
  /** Data-âncora do cenário demo (026). Só usada quando demoMode. */
  demoAnchorDate: read("VITE_DEMO_ANCHOR_DATE", "2026-08-24") || "2026-08-24",
};

export function isFakeBlockedInProduction(
  isProd = import.meta.env.PROD,
  provider = config.authProvider,
): boolean {
  if (homologDemo && provider === "fake") return false;
  return isProd && provider === "fake";
}

export function assertAuthProviderAllowed(): void {
  if (isFakeBlockedInProduction()) {
    throw new Error("O provedor falso de autenticação não pode ser usado em produção.");
  }
  if (config.authProvider !== "oidc" && config.authProvider !== "fake") {
    throw new Error("Provedor de autenticação desconhecido.");
  }
}
