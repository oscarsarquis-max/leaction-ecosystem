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

function createUserManager(): UserManager | null {
  const cfg = getConfig();
  if (cfg.authMode !== "cognito") return null;
  // Tokens stay in memory only — never session/localStorage.
  const memory = new InMemoryWebStorage();
  return new UserManager({
    authority: cfg.cognito.authority,
    client_id: cfg.cognito.clientId,
    redirect_uri: cfg.cognito.redirectUri,
    post_logout_redirect_uri: cfg.cognito.logoutUri,
    response_type: "code",
    scope: "openid email profile",
    automaticSilentRenew: true,
    userStore: new WebStorageStateStore({ store: memory }),
  });
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const cfg = getConfig();
  const managerRef = useRef<UserManager | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");
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
    setAccessToken(null);
    setExpiresAt(null);
    setUserEmail(null);
    setUserSub(null);
    setAuthEpoch((e) => e + 1);
    setStatus(reason === "logout" ? "anonymous" : "invalid_session");
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function boot() {
      if (cfg.authMode === "dev") {
        if (cancelled) return;
        setAccessToken("dev-local-token");
        setExpiresAt(Date.now() + 8 * 60 * 60 * 1000);
        setUserEmail(cfg.devAuth.email);
        setUserSub(cfg.devAuth.sub);
        setStatus("authenticated");
        return;
      }

      const manager = createUserManager();
      managerRef.current = manager;
      if (!manager) {
        setStatus("anonymous");
        return;
      }

      manager.events.addUserLoaded((user) => {
        if (!cancelled) applyUser(user);
      });
      manager.events.addUserUnloaded(() => {
        if (!cancelled) void invalidateSession("invalid");
      });
      manager.events.addAccessTokenExpired(() => {
        if (!cancelled) void invalidateSession("invalid");
      });
      manager.events.addSilentRenewError(() => {
        if (!cancelled) void invalidateSession("invalid");
      });

      try {
        if (window.location.pathname === "/auth/callback") {
          const user = await manager.signinRedirectCallback();
          applyUser(user);
          window.history.replaceState({}, document.title, "/");
          return;
        }
        const user = await manager.getUser();
        applyUser(user);
      } catch {
        if (!cancelled) await invalidateSession("invalid");
      }
    }

    void boot();
    return () => {
      cancelled = true;
    };
  }, [applyUser, cfg.authMode, cfg.devAuth.email, cfg.devAuth.sub, invalidateSession]);

  const login = useCallback(async () => {
    if (cfg.authMode === "dev") {
      setAccessToken("dev-local-token");
      setExpiresAt(Date.now() + 8 * 60 * 60 * 1000);
      setUserEmail(cfg.devAuth.email);
      setUserSub(cfg.devAuth.sub);
      setStatus("authenticated");
      return;
    }
    const manager = managerRef.current ?? createUserManager();
    managerRef.current = manager;
    if (!manager) throw new Error("OIDC UserManager unavailable");
    await manager.signinRedirect();
  }, [cfg.authMode, cfg.devAuth.email, cfg.devAuth.sub]);

  const logout = useCallback(async () => {
    await invalidateSession("logout");
    if (cfg.authMode === "cognito") {
      const manager = managerRef.current;
      if (manager) {
        try {
          await manager.removeUser();
          await manager.signoutRedirect();
        } catch {
          // already cleared locally
        }
      }
    }
  }, [cfg.authMode, invalidateSession]);

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
