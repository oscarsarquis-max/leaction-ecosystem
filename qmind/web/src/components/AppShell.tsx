import { Suspense } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/auth/AuthProvider";
import { useOrganization } from "@/org/OrganizationProvider";
import { OrgSelector } from "@/components/OrgSelector";
import { AccessGate } from "@/components/AccessGate";
import { BrandLogo } from "@/components/BrandLogo";
import { GuidedTourReturnBanner } from "@/components/GuidedTourReturnBanner";
import {
  AccessDeniedPanel,
  ErrorPanel,
  LoadingPanel,
} from "@/components/StatePanels";
import { AssistantProvider } from "@/assistant/AssistantProvider";
import { QmindAssistant } from "@/assistant/QmindAssistant";
import { writeReturnUrl } from "@/lib/returnUrl";
import { clearGuidedTour } from "@/lib/guidedTour";

export function AppShell() {
  const auth = useAuth();
  const org = useOrganization();
  const location = useLocation();

  if (auth.status === "loading") {
    return (
      <div className="mx-auto max-w-5xl px-4 py-16">
        <LoadingPanel title="Validando sua sessão…" />
      </div>
    );
  }

  if (auth.status === "anonymous" || auth.status === "invalid_session") {
    // Deep links / testes: AccessGate como fallback do shell.
    // Fluxo público usa /login; hotpage permanece fora deste shell.
    const returnPath = `${location.pathname}${location.search}${location.hash}`;
    return (
      <AccessGate
        status={auth.status}
        onLogin={() => {
          writeReturnUrl(
            returnPath.startsWith("/login") ? "/assessments" : returnPath,
          );
          void auth.login();
        }}
      />
    );
  }

  return (
    <AssistantProvider>
      <div className="min-h-screen">
        <header className="qm-shell-header">
          <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4 px-4 py-2.5">
            <div className="flex items-center gap-6">
              <NavLink
                to="/assessments"
                className="block shrink-0"
                aria-label="QMind — início"
              >
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
                <NavLink
                  to="/guided-tour"
                  data-testid="nav-guided-tour"
                  className={({ isActive }) =>
                    isActive
                      ? "text-[var(--qm-ink)] underline decoration-2 underline-offset-4"
                      : "text-[var(--qm-muted)] hover:text-[var(--qm-ink)]"
                  }
                >
                  Apresentação
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
                onClick={() => {
                  clearGuidedTour();
                  void auth.logout();
                }}
                className="qm-btn-secondary !px-3 !py-1.5"
                data-testid="logout-cta"
              >
                Sair
              </button>
            </div>
          </div>
        </header>

        <main className="mx-auto max-w-5xl px-4 py-8 pb-24">
          <GuidedTourReturnBanner />
          {org.accessDenied ? (
            <AccessDeniedPanel message={org.error ?? undefined} />
          ) : org.loading && !org.currentOrganizationId ? (
            <LoadingPanel title="Carregando suas organizações…" />
          ) : org.error && !org.currentOrganizationId ? (
            <ErrorPanel
              title="Não foi possível carregar organizações"
              message={org.error}
              action={{
                label: "Tentar de novo",
                onClick: () => void org.refreshMemberships(),
              }}
            />
          ) : (
            <Suspense
              fallback={<LoadingPanel title="Carregando…" />}
            >
              <Outlet />
            </Suspense>
          )}
        </main>

        {org.currentOrganizationId ? <QmindAssistant /> : null}
      </div>
    </AssistantProvider>
  );
}
