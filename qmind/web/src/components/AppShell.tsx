import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "@/auth/AuthProvider";
import { useOrganization } from "@/org/OrganizationProvider";
import { OrgSelector } from "@/components/OrgSelector";
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
        <LoadingPanel title="Validando sessão…" />
      </div>
    );
  }

  if (auth.status === "anonymous" || auth.status === "invalid_session") {
    return (
      <div className="mx-auto flex min-h-screen max-w-lg flex-col justify-center px-4 py-16">
        <p className="font-display text-4xl tracking-tight text-teal-950">QMind</p>
        <p className="mt-3 text-teal-950/70">
          {auth.status === "invalid_session"
            ? "Sessão inválida ou expirada. Entre novamente."
            : "Entre para acessar avaliações da sua organização."}
        </p>
        <button
          type="button"
          onClick={() => void auth.login()}
          className="mt-8 w-fit rounded-md bg-teal-900 px-4 py-2 text-sm font-semibold text-white"
        >
          Entrar
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-teal-900/10 bg-white/70 backdrop-blur">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4 px-4 py-3">
          <div className="flex items-center gap-6">
            <NavLink
              to="/"
              className="font-display text-2xl tracking-tight text-teal-950"
            >
              QMind
            </NavLink>
            <nav className="flex gap-3 text-sm font-semibold">
              <NavLink
                to="/assessments"
                end
                data-testid="nav-assessments"
                className={({ isActive }) =>
                  isActive
                    ? "text-teal-900 underline decoration-2 underline-offset-4"
                    : "text-teal-950/60 hover:text-teal-900"
                }
              >
                Avaliações
              </NavLink>
            </nav>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            <OrgSelector />
            <span className="hidden text-sm text-teal-950/60 sm:inline">
              {auth.userEmail}
            </span>
            <button
              type="button"
              onClick={() => void auth.logout()}
              className="rounded-md border border-teal-900/20 bg-white px-3 py-1.5 text-sm font-semibold text-teal-950"
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
          <LoadingPanel title="Carregando organizações…" />
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
