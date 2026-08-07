import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { MembershipOut } from "@qmind/api-client";
import { useAuth } from "@/auth/AuthProvider";
import {
  readPreferredOrganizationId,
  writePreferredOrganizationId,
} from "@/auth/storage";
import { abortAllInFlight } from "@/api/abortRegistry";
import {
  bindAuthBridge,
  getQmindClient,
  withTenantGeneration,
  StaleTenantResponseError,
  QmindApiError,
} from "@/api/qmindApi";
import { isOrgScopedKey, queryKeys } from "@/api/queryKeys";
import {
  bumpRequestGeneration,
  getActiveOrganizationId,
  getRequestGeneration,
  setActiveOrganizationId,
} from "@/api/tenantContext";
import { clearGuidedTour } from "@/lib/guidedTour";

export type Membership = {
  id: string;
  organizationId: string;
  organizationName: string;
  roles: string[];
  status: string;
};

export type OrganizationContextValue = {
  memberships: Membership[];
  currentOrganizationId: string | null;
  currentOrganization: Membership | null;
  loading: boolean;
  error: string | null;
  accessDenied: boolean;
  requestGeneration: number;
  switchOrganization: (organizationId: string) => Promise<void>;
  refreshMemberships: () => Promise<void>;
};

const OrganizationContext = createContext<OrganizationContextValue | null>(null);

function mapMembership(raw: MembershipOut): Membership {
  return {
    id: raw.id,
    organizationId: raw.organization_id,
    organizationName: raw.organization_name,
    roles: raw.roles ?? [],
    status: raw.status,
  };
}

export function OrganizationProvider({ children }: { children: ReactNode }) {
  const auth = useAuth();
  const queryClient = useQueryClient();
  const [memberships, setMemberships] = useState<Membership[]>([]);
  const [currentOrganizationId, setCurrentOrganizationId] = useState<string | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [accessDenied, setAccessDenied] = useState(false);
  const [requestGeneration, setRequestGeneration] = useState(0);

  useEffect(() => {
    bindAuthBridge({
      getAccessToken: () => auth.accessToken,
    });
  }, [auth.accessToken]);

  useEffect(() => {
    setActiveOrganizationId(currentOrganizationId);
  }, [currentOrganizationId]);

  const clearOrgCaches = useCallback(async () => {
    await queryClient.cancelQueries({
      predicate: (q) => isOrgScopedKey(q.queryKey),
    });
    queryClient.removeQueries({
      predicate: (q) => isOrgScopedKey(q.queryKey),
    });
  }, [queryClient]);

  const refreshMemberships = useCallback(async () => {
    if (auth.status !== "authenticated") {
      setMemberships([]);
      setCurrentOrganizationId(null);
      setActiveOrganizationId(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    setAccessDenied(false);
    const client = getQmindClient();

    try {
      const data = await withTenantGeneration(async () => {
        const res = await client.api.listMyMemberships();
        return res.data ?? [];
      });

      const active = data
        .map(mapMembership)
        .filter((m) => m.status === "active");

      setMemberships(active);

      // Prefer the imperative active org (set synchronously on switch) over React state.
      const activeId = getActiveOrganizationId();
      const preferred = readPreferredOrganizationId();
      const nextOrg =
        activeId && active.some((m) => m.organizationId === activeId)
          ? activeId
          : preferred && active.some((m) => m.organizationId === preferred)
            ? preferred
            : (active[0]?.organizationId ?? null);

      if (nextOrg) writePreferredOrganizationId(nextOrg);
      setActiveOrganizationId(nextOrg);
      setCurrentOrganizationId(nextOrg);
    } catch (e) {
      if (e instanceof StaleTenantResponseError) return;
      if (e instanceof QmindApiError && (e.status === 401 || e.status === 403)) {
        setAccessDenied(true);
        setError(e.message);
      } else if (e instanceof DOMException && e.name === "AbortError") {
        // cancelled by tenant switch / logout
      } else {
        setError(e instanceof Error ? e.message : "Failed to load memberships");
      }
      setMemberships([]);
    } finally {
      setLoading(false);
    }
  }, [auth.status]);

  useEffect(() => {
    if (auth.status === "loading") return;
    if (auth.status !== "authenticated") {
      setMemberships([]);
      setCurrentOrganizationId(null);
      setActiveOrganizationId(null);
      setLoading(false);
      setError(null);
      return;
    }
    void refreshMemberships();
  }, [auth.status, auth.authEpoch, refreshMemberships]);

  const switchOrganization = useCallback(
    async (organizationId: string) => {
      if (!memberships.some((m) => m.organizationId === organizationId)) {
        throw new Error("Organization is not in active memberships");
      }
      if (organizationId === currentOrganizationId) return;

      // Gate: abort → invalidateTenant → clear org caches → bump generation
      abortAllInFlight("tenant_switch");
      getQmindClient().invalidateTenant();
      await clearOrgCaches();
      const gen = bumpRequestGeneration();
      setRequestGeneration(gen);

      // Tour guiado é por organização — limpa ao trocar.
      clearGuidedTour();

      writePreferredOrganizationId(organizationId);
      setActiveOrganizationId(organizationId);
      setCurrentOrganizationId(organizationId);

      await refreshMemberships();
      await queryClient.invalidateQueries({
        queryKey: queryKeys.assessments(organizationId),
      });
    },
    [
      memberships,
      currentOrganizationId,
      clearOrgCaches,
      refreshMemberships,
      queryClient,
    ],
  );

  const currentOrganization =
    memberships.find((m) => m.organizationId === currentOrganizationId) ?? null;

  const value = useMemo<OrganizationContextValue>(
    () => ({
      memberships,
      currentOrganizationId,
      currentOrganization,
      loading,
      error,
      accessDenied,
      requestGeneration: requestGeneration || getRequestGeneration(),
      switchOrganization,
      refreshMemberships,
    }),
    [
      memberships,
      currentOrganizationId,
      currentOrganization,
      loading,
      error,
      accessDenied,
      requestGeneration,
      switchOrganization,
      refreshMemberships,
    ],
  );

  return (
    <OrganizationContext.Provider value={value}>{children}</OrganizationContext.Provider>
  );
}

export function useOrganization(): OrganizationContextValue {
  const ctx = useContext(OrganizationContext);
  if (!ctx) {
    throw new Error("useOrganization must be used within OrganizationProvider");
  }
  return ctx;
}
