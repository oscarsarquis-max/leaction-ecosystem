import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { clearOperationalContext } from "../session/operationalContext";
import { createAuthProvider } from "./createAuth";
import type { AuthProvider, AuthSession } from "./types";

type AuthContextValue = {
  provider: AuthProvider;
  session: AuthSession | null;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  completeCallback: () => Promise<AuthSession>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProviderTree({
  children,
  provider: provided,
}: {
  children: ReactNode;
  provider?: AuthProvider;
}) {
  const [provider] = useState(() => provided ?? createAuthProvider());
  const [session, setSession] = useState<AuthSession | null>(() => provider.getSession());

  const login = useCallback(async () => {
    await provider.login();
    setSession(provider.getSession());
  }, [provider]);

  const logout = useCallback(async () => {
    await provider.logout();
    try {
      localStorage.removeItem("panne.activeOrganization");
    } catch {
      /* ignore */
    }
    clearOperationalContext();
    setSession(null);
  }, [provider]);

  const completeCallback = useCallback(async () => {
    const next = await provider.handleCallback();
    setSession(next);
    return next;
  }, [provider]);

  const value = useMemo(
    () => ({ provider, session, login, logout, completeCallback }),
    [provider, session, login, logout, completeCallback],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth exige AuthProviderTree.");
  return value;
}
