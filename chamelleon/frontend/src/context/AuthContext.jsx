import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { ROLE_LABELS } from '../config/rbac';
import { getAuthMe } from '../services/api';
import { clearSession, getSession, isAuthenticated, saveSession } from '../services/session';

const AuthContext = createContext(null);

function sessionToProfile(session) {
  if (!session) return null;
  return {
    user_id: session.userId,
    user_name: session.userName,
    user_email: session.email,
    system_role: session.systemRole,
    tenant_id: session.tenantId,
    tenant_name: session.tenantName,
    framework_id: session.frameworkId,
    sector: session.sector,
  };
}

export function AuthProvider({ children }) {
  const [session, setSession] = useState(getSession);
  const [profile, setProfile] = useState(() => sessionToProfile(getSession()));
  const [loading, setLoading] = useState(true);

  const refreshProfile = useCallback(async () => {
    const current = getSession();
    if (!current?.userId) {
      setProfile(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const me = await getAuthMe();
      setProfile(me);
      if (current.tenantId && current.frameworkId !== me.framework_id) {
        saveSession({
          ...current,
          frameworkId: me.framework_id ?? null,
          tenantName: me.tenant_name ?? current.tenantName,
          sector: me.sector ?? null,
        });
        setSession(getSession());
      } else if (me.sector !== undefined && current.sector !== me.sector) {
        saveSession({
          ...current,
          sector: me.sector ?? null,
        });
        setSession(getSession());
      }
    } catch {
      setProfile(sessionToProfile(current));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshProfile();
  }, [session, refreshProfile]);

  const loginWithResponse = useCallback((data) => {
    const next = {
      userId: data.user_id,
      tenantId: data.tenant_id,
      systemRole: data.system_role,
      userName: data.user_name,
      email: data.email,
      tenantName: data.tenant_name,
      frameworkId: data.framework_id,
      sector: data.sector ?? null,
      authType: data.auth_type,
      token: data.token || null,
    };
    saveSession(next);
    setSession(next);
    setProfile(sessionToProfile(next));
    return next;
  }, []);

  const logout = useCallback(() => {
    clearSession();
    setSession(null);
    setProfile(null);
  }, []);

  const value = useMemo(() => {
    const role = profile?.system_role || session?.systemRole;
    return {
      session,
      isAuthenticated: isAuthenticated(),
      userId: profile?.user_id || session?.userId,
      userName: profile?.user_name || session?.userName,
      userEmail: profile?.user_email || session?.email,
      systemRole: role,
      roleLabel: ROLE_LABELS[role] || role,
      tenantId: profile?.tenant_id || session?.tenantId,
      tenantName: profile?.tenant_name || session?.tenantName,
      frameworkId: profile?.framework_id || session?.frameworkId,
      sector: profile?.sector || session?.sector,
      journey: profile?.journey || null,
      loading,
      loginWithResponse,
      logout,
      refreshProfile,
      isAdmin: role === 'sysadmin',
      isLead: role === 'led',
      isConsultor: role === 'consultor',
      isExecutor: role === 'executor',
    };
  }, [session, profile, loading, loginWithResponse, logout, refreshProfile]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth deve ser usado dentro de AuthProvider');
  return ctx;
}
