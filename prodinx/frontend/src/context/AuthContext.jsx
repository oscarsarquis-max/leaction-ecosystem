import { createContext, useCallback, useContext, useMemo, useState } from "react";
import {
  clearAuthentication,
  isAuthenticated as readIsAuthenticated,
  setAuthenticated,
} from "../utils/auth";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [autenticado, setAutenticado] = useState(() => readIsAuthenticated());

  const login = useCallback(() => {
    setAuthenticated(true);
    setAutenticado(true);
  }, []);

  const logout = useCallback(() => {
    clearAuthentication();
    setAutenticado(false);
  }, []);

  const value = useMemo(
    () => ({
      autenticado,
      login,
      logout,
    }),
    [autenticado, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth deve ser usado dentro de AuthProvider");
  }

  return context;
}
