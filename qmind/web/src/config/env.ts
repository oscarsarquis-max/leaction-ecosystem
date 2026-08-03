/**
 * Runtime env for the QMind web shell.
 * Dev auth is blocked when VITE_ENVIRONMENT=prod (mirrors backend Settings).
 */

export type AppEnvironment = "local" | "dev" | "prod";
export type AuthMode = "cognito" | "dev";

export type AppConfig = {
  environment: AppEnvironment;
  apiBaseUrl: string;
  authMode: AuthMode;
  cognito: {
    authority: string;
    clientId: string;
    redirectUri: string;
    logoutUri: string;
  };
  devAuth: {
    sub: string;
    email: string;
  };
};

function readEnv(name: string, fallback = ""): string {
  const v = import.meta.env[name];
  return typeof v === "string" ? v.trim() : fallback;
}

function assertConfig(): AppConfig {
  const environment = (readEnv("VITE_ENVIRONMENT", "local") || "local") as AppEnvironment;
  if (!["local", "dev", "prod"].includes(environment)) {
    throw new Error(`Invalid VITE_ENVIRONMENT=${environment}`);
  }

  const authMode = (readEnv("VITE_AUTH_MODE", "dev") || "dev") as AuthMode;
  if (!["cognito", "dev"].includes(authMode)) {
    throw new Error(`Invalid VITE_AUTH_MODE=${authMode}`);
  }

  if (environment === "prod" && authMode === "dev") {
    throw new Error("VITE_AUTH_MODE=dev is forbidden when VITE_ENVIRONMENT=prod.");
  }

  // Empty base URL → same-origin (Vite proxy in local).
  const apiBaseUrl = readEnv("VITE_API_BASE_URL", "").replace(/\/$/, "");

  const config: AppConfig = {
    environment,
    apiBaseUrl,
    authMode,
    cognito: {
      authority: readEnv("VITE_COGNITO_AUTHORITY"),
      clientId: readEnv("VITE_COGNITO_CLIENT_ID"),
      redirectUri: readEnv("VITE_COGNITO_REDIRECT_URI", `${window.location.origin}/auth/callback`),
      logoutUri: readEnv("VITE_COGNITO_LOGOUT_URI", window.location.origin),
    },
    devAuth: {
      sub: readEnv("VITE_DEV_USER_SUB", "dev-local-user"),
      email: readEnv("VITE_DEV_USER_EMAIL", "dev@example.com"),
    },
  };

  if (authMode === "cognito") {
    if (!config.cognito.authority || !config.cognito.clientId) {
      throw new Error("Cognito requires VITE_COGNITO_AUTHORITY and VITE_COGNITO_CLIENT_ID.");
    }
  }

  return config;
}

let cached: AppConfig | null = null;

export function getConfig(): AppConfig {
  if (!cached) cached = assertConfig();
  return cached;
}

/** Test helper — reset cached config. */
export function resetConfigCache(): void {
  cached = null;
}
