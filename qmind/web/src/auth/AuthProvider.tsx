import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  UserManager,
  WebStorageStateStore,
  InMemoryWebStorage,
  type User,
} from "oidc-client-ts";
import { getConfig } from "@/config/env";
import { clearAllLocalPersistence } from "@/auth/storage";
import { abortAllInFlight } from "@/api/abortRegistry";
import { getQmindClient } from "@/api/qmindApi";
import { setActiveOrganizationId } from "@/api/tenantContext";

export type AuthStatus = "loading" | "authenticated" | "anonymous" | "invalid_session";

export type AuthContextValue = {
  status: AuthStatus;
  accessToken: string | null;
  expiresAt: number | null;
  userEmail: string | null;
  userSub: string | null;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  /** Bumped on logout / session invalidation so consumers drop in-flight work. */
  authEpoch: number;
};

const AuthContext = createContext<AuthContextValue | null>(null);

/** Singleton — StrictMode remount não pode recriar InMemoryWebStorage vazio. */
let sharedManager: UserManager | null = null;
/** Dedup do callback OIDC (código de autorização é one-shot). */
let callbackInFlight: Promise<User> | null = null;

function getOrCreateUserManager(): UserManager | null {
  const cfg = getConfig();
  if (cfg.authMode !== "cognito") return null;
  if (!sharedManager) {
    // Tokens em memória; state/PKCE do redirect fica no sessionStorage (default do oidc-client-ts).
    const memory = new InMemoryWebStorage();
    sharedManager = new UserManager({
      authority: cfg.cognito.authority,
      client_id: cfg.cognito.clientId,
      redirect_uri: cfg.cognito.redirectUri,
      post_logout_redirect_uri: cfg.cognito.logoutUri,
      response_type: "code",
      scope: "openid email profile",
      automaticSilentRenew: true,
      userStore: new WebStorageStateStore({ store: memory }),
      // Cognito Managed Login localization (pt-BR).
      extraQueryParams: { lang: "pt-BR" },
    });
  }
  return sharedManager;
}

/** Test helper — reset module singletons between Vitest cases if needed. */
export function __resetAuthManagerForTests(): void {
  sharedManager = null;
  callbackInFlight = null;
}

async function completeRedirectCallback(manager: UserManager): Promise<User> {
  if (!callbackInFlight) {
    callbackInFlight = manager.signinRedirectCallback().finally(() => {
      // Mantém a promise resolvida para remounts StrictMode na mesma URL.
    });
  }
  return callbackInFlight;
}

function isAuthCallbackPath(): boolean {
  return window.location.pathname === "/auth/callback";
}

/** Força AccessGate: /?sair=1 ou /?login=1 (útil quando o browser restaura sessão/BFCache). */
function wantsForcedLoginScreen(): boolean {
  try {
    const q = new URLSearchParams(window.location.search);
    return q.get("sair") === "1" || q.get("login") === "1";
  } catch {
    return false;
  }
}

function stripForcedLoginParams(): void {
  try {
    const url = new URL(window.location.href);
    if (!url.searchParams.has("sair") && !url.searchParams.has("login")) return;
    url.searchParams.delete("sair");
    url.searchParams.delete("login");
    const next = `${url.pathname}${url.search}${url.hash}`;
    window.history.replaceState(null, "", next || "/");
  } catch {
    /* ignore */
  }
}

/** Remove resíduos de builds antigos que gravavam o user OIDC no sessionStorage. */
function clearStaleOidcUserStorage(): void {
  if (isAuthCallbackPath()) return;
  try {
    for (const k of Object.keys(sessionStorage)) {
      if (
        k.startsWith("oidc.user:") ||
        k.startsWith("qmind.dev.authenticated")
      ) {
        sessionStorage.removeItem(k);
      }
    }
  } catch {
    /* ignore */
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const cfg = getConfig();
  const managerRef = useRef<UserManager | null>(null);
  /**
   * AUTH_MODE=dev: sempre começa anônimo (AccessGate).
   * Sessão só em memória após "Entrar" — F5 volta ao login (evita ficar preso autenticado).
   */
  const [status, setStatus] = useState<AuthStatus>(() =>
    cfg.authMode === "dev" ? "anonymous" : "loading",
  );
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [expiresAt, setExpiresAt] = useState<number | null>(null);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [userSub, setUserSub] = useState<string | null>(null);
  const [authEpoch, setAuthEpoch] = useState(0);

  const applyUser = useCallback((user: User | null) => {
    if (!user || user.expired) {
      setAccessToken(null);
      setExpiresAt(null);
      setUserEmail(null);
      setUserSub(null);
      setStatus(user?.expired ? "invalid_session" : "anonymous");
      return;
    }
    setAccessToken(user.access_token);
    setExpiresAt(user.expires_at ? user.expires_at * 1000 : null);
    setUserEmail((user.profile.email as string | undefined) ?? null);
    setUserSub(user.profile.sub ?? null);
    setStatus("authenticated");
  }, []);

  const invalidateSession = useCallback(async (reason: "logout" | "invalid") => {
    abortAllInFlight(reason);
    getQmindClient().invalidateTenant();
    setActiveOrganizationId(null);
    clearAllLocalPersistence();
    clearStaleOidcUserStorage();
    setAccessToken(null);
    setExpiresAt(null);
    setUserEmail(null);
    setUserSub(null);
    setAuthEpoch((e) => e + 1);
    setStatus(reason === "logout" ? "anonymous" : "invalid_session");
  }, []);

  const dropUserManager = useCallback(() => {
    sharedManager = null;
    managerRef.current = null;
    callbackInFlight = null;
  }, []);

  useEffect(() => {
    let cancelled = false;

    clearStaleOidcUserStorage();

    if (wantsForcedLoginScreen()) {
      stripForcedLoginParams();
      dropUserManager();
      void invalidateSession("logout");
      return () => {
        cancelled = true;
      };
    }

    if (cfg.authMode === "dev") {
      // Sessão só em memória; documento novo = AccessGate.
      // BFCache/HMR: pageshow abaixo também revalida.
      return () => {
        cancelled = true;
      };
    }

    const manager = getOrCreateUserManager();
    managerRef.current = manager;
    if (!manager) {
      setStatus("anonymous");
      return () => {
        cancelled = true;
      };
    }

    const onLoaded = (user: User) => {
      if (!cancelled) applyUser(user);
    };
    const onUnloaded = () => {
      if (!cancelled) void invalidateSession("invalid");
    };
    const onExpired = () => {
      if (!cancelled) void invalidateSession("invalid");
    };
    const onRenewError = () => {
      if (!cancelled) void invalidateSession("invalid");
    };
    manager.events.addUserLoaded(onLoaded);
    manager.events.addUserUnloaded(onUnloaded);
    manager.events.addAccessTokenExpired(onExpired);
    manager.events.addSilentRenewError(onRenewError);

    void (async () => {
      try {
        if (isAuthCallbackPath()) {
          const user = await completeRedirectCallback(manager);
          if (cancelled) return;
          applyUser(user);
          // Navegação para /assessments fica a cargo de AuthCallbackPage (React Router).
          return;
        }
        const user = await manager.getUser();
        if (!cancelled) applyUser(user);
      } catch {
        if (!cancelled) await invalidateSession("invalid");
      }
    })();

    return () => {
      cancelled = true;
      manager.events.removeUserLoaded(onLoaded);
      manager.events.removeUserUnloaded(onUnloaded);
      manager.events.removeAccessTokenExpired(onExpired);
      manager.events.removeSilentRenewError(onRenewError);
    };
  }, [
    applyUser,
    cfg.authMode,
    cfg.devAuth.email,
    cfg.devAuth.sub,
    dropUserManager,
    invalidateSession,
  ]);

  // BFCache: o browser pode restaurar JS+React já autenticados sem remount.
  useEffect(() => {
    const onPageShow = (event: PageTransitionEvent) => {
      if (!event.persisted) return;
      if (cfg.authMode === "dev" || wantsForcedLoginScreen()) {
        dropUserManager();
        void invalidateSession("logout");
        stripForcedLoginParams();
        return;
      }
      const manager = managerRef.current ?? getOrCreateUserManager();
      if (!manager) {
        void invalidateSession("logout");
        return;
      }
      void manager.getUser().then((user) => {
        if (!user || user.expired) {
          dropUserManager();
          void invalidateSession("logout");
        } else applyUser(user);
      });
    };
    window.addEventListener("pageshow", onPageShow);
    return () => window.removeEventListener("pageshow", onPageShow);
  }, [applyUser, cfg.authMode, dropUserManager, invalidateSession]);

  const login = useCallback(async () => {
    if (cfg.authMode === "dev") {
      setAccessToken("dev-local-token");
      setExpiresAt(Date.now() + 8 * 60 * 60 * 1000);
      setUserEmail(cfg.devAuth.email);
      setUserSub(cfg.devAuth.sub);
      setStatus("authenticated");
      return;
    }
    const manager = getOrCreateUserManager();
    managerRef.current = manager;
    if (!manager) throw new Error("OIDC UserManager unavailable");
    await manager.signinRedirect();
  }, [cfg.authMode, cfg.devAuth.email, cfg.devAuth.sub]);

  const logout = useCallback(async () => {
    if (cfg.authMode === "cognito") {
      const manager = managerRef.current ?? getOrCreateUserManager();
      await invalidateSession("logout");
      if (manager) {
        try {
          await manager.removeUser();
          await manager.signoutRedirect();
        } catch {
          // already cleared locally — AccessGate permanece via status anonymous
        }
      }
      dropUserManager();
      return;
    }
    await invalidateSession("logout");
    dropUserManager();
    // AUTH_MODE=dev: garante AccessGate visível sem depender de F5 / HMR.
    if (typeof window !== "undefined" && window.location.pathname !== "/") {
      window.history.replaceState(null, "", "/");
    }
  }, [cfg.authMode, dropUserManager, invalidateSession]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      accessToken,
      expiresAt,
      userEmail,
      userSub,
      login,
      logout,
      authEpoch,
    }),
    [status, accessToken, expiresAt, userEmail, userSub, login, logout, authEpoch],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
