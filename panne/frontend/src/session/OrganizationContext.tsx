import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { ApiClient } from "../api/client";
import { ApiError } from "../api/errors";
import type { Association, Me } from "../api/types";
import { useAuth } from "../auth/AuthContext";

const PREF_KEY = "panne.activeOrganization";

type Status =
  | { kind: "carregando" }
  | { kind: "pronto"; me: Me }
  | { kind: "erro"; error: ApiError | Error };

type OrganizationContextValue = {
  me: Me | null;
  status: Status;
  associations: Association[];
  active: Association | null;
  api: ApiClient;
  selectOrganization: (organizationId: string) => Promise<void>;
  reload: () => Promise<void>;
  hasPermission: (code: string) => boolean;
};

const OrganizationContext = createContext<OrganizationContextValue | null>(null);

function readPreference(): string | null {
  try {
    return localStorage.getItem(PREF_KEY);
  } catch {
    return null;
  }
}

function writePreference(id: string | null): void {
  try {
    if (id) localStorage.setItem(PREF_KEY, id);
    else localStorage.removeItem(PREF_KEY);
  } catch {
    /* conveniência local apenas */
  }
}

export function OrganizationProvider({ children }: { children: ReactNode }) {
  const { session, provider } = useAuth();
  const api = useMemo(() => new ApiClient(() => provider.getAccessToken()), [provider]);
  const [status, setStatus] = useState<Status>({ kind: "carregando" });
  const [activeId, setActiveId] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!session) {
      api.clear();
      setStatus({ kind: "carregando" });
      setActiveId(null);
      return;
    }
    setStatus({ kind: "carregando" });
    try {
      const preferred = readPreference();
      const me = await api.me(preferred);
      const activeIds = me.associations
        .filter((item) => item.status === "active")
        .map((item) => item.organization_id);
      let next = me.selected_organization_id;
      if (preferred && activeIds.includes(preferred)) next = preferred;
      else if (activeIds.length === 1) next = activeIds[0];
      else if (next && !activeIds.includes(next)) next = null;
      api.setOrganization(next);
      setActiveId(next);
      if (next) writePreference(next);
      setStatus({ kind: "pronto", me });
    } catch (error) {
      setStatus({
        kind: "erro",
        error: error instanceof Error ? error : new Error("Falha ao carregar o perfil."),
      });
    }
  }, [api, session]);

  useEffect(() => {
    void load();
  }, [load]);

  const selectOrganization = useCallback(
    async (organizationId: string) => {
      api.clear();
      api.setOrganization(organizationId);
      setActiveId(organizationId);
      writePreference(organizationId);
      const me = await api.me(organizationId);
      setStatus({ kind: "pronto", me });
    },
    [api],
  );

  const me = status.kind === "pronto" ? status.me : null;
  const associations = useMemo(
    () => me?.associations.filter((item) => item.status === "active") ?? [],
    [me],
  );
  const active = associations.find((item) => item.organization_id === activeId) ?? null;

  const value = useMemo<OrganizationContextValue>(
    () => ({
      me,
      status,
      associations,
      active,
      api,
      selectOrganization,
      reload: load,
      hasPermission: (code: string) => Boolean(active?.permissions.includes(code)),
    }),
    [me, status, associations, active, api, selectOrganization, load],
  );

  return <OrganizationContext.Provider value={value}>{children}</OrganizationContext.Provider>;
}

export function useOrganization(): OrganizationContextValue {
  const value = useContext(OrganizationContext);
  if (!value) throw new Error("useOrganization exige OrganizationProvider.");
  return value;
}
