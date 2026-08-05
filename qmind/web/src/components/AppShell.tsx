import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "@/auth/AuthProvider";
import { useOrganization } from "@/org/OrganizationProvider";
import { OrgSelector } from "@/components/OrgSelector";
import { AccessGate } from "@/components/AccessGate";
import { BrandLogo } from "@/components/BrandLogo";
import {
  AccessDeniedPanel,
  ErrorPanel,
  LoadingPanel,
} from "@/components/StatePanels";

export function AppShell() {
  const auth = useAuth();
  const org = useOrganization();

  if (auth.status === "loading") {
    return (
      <div className="mx-auto max-w-5xl px-4 py-16">
        <LoadingPanel title="Validando sua sessão…" />
      </div>
    );
  }

  if (auth.status === "anonymous" || auth.status === "invalid_session") {
    return (
      <AccessGate
        status={auth.status}
        onLogin={() => void auth.login()}
      />
    );
  }

  return (
    <div className="min-h-screen">
      <header className="qm-shell-header">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4 px-4 py-2.5">
          <div className="flex items-center gap-6">
            <NavLink to="/assessments" className="block shrink-0" aria-label="QMind — início">
              <BrandLogo
                mode="full"
                className="h-9 w-auto max-h-9 max-w-[13rem] object-contain object-left sm:h-10 sm:max-h-10 sm:max-w-[15rem]"
                alt=""
              />
            </NavLink>
            <nav className="flex gap-3 text-sm font-semibold">
              <NavLink
                to="/assessments"
                end
                data-testid="nav-assessments"
                className={({ isActive }) =>
                  isActive
                    ? "text-[var(--qm-ink)] underline decoration-2 underline-offset-4"
                    : "text-[var(--qm-muted)] hover:text-[var(--qm-ink)]"
                }
              >
                Minhas avaliações
              </NavLink>
            </nav>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <OrgSelector />
            <span className="hidden text-sm text-[var(--qm-muted)] sm:inline">
              {auth.userEmail}
            </span>
            <button
              type="button"
              onClick={() => void auth.logout()}
              className="qm-btn-secondary !px-3 !py-1.5"
            >
              Sair
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-8">
        {org.accessDenied ? (
          <AccessDeniedPanel message={org.error ?? undefined} />
        ) : org.loading && !org.currentOrganizationId ? (
          <LoadingPanel title="Carregando suas organizações…" />
        ) : org.error && !org.currentOrganizationId ? (
          <ErrorPanel
            title="Não foi possível carregar organizações"
            message={org.error}
            action={{ label: "Tentar de novo", onClick: () => void org.refreshMemberships() }}
          />
        ) : (
          <Outlet />
        )}
      </main>
    </div>
  );
}
