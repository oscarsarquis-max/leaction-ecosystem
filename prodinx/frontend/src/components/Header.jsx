import AppNavbar from "./AppNavbar";
import { getOrganizacaoNome } from "../config/organizacao";

function Header({ metricCount, loading }) {
  const organizacaoNome = getOrganizacaoNome();
  return (
    <header className="bg-brand-verde text-white shadow-md">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
        <div className="flex items-center gap-4">
          <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-brand-laranja font-bold text-white">
            P
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-widest text-white/70">
              {organizacaoNome}
            </p>
            <h1 className="text-xl font-bold leading-tight">Prodinx</h1>
          </div>
        </div>

        <AppNavbar />

        <div className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-1.5 text-sm font-medium">
          <span className="h-2 w-2 rounded-full bg-brand-laranja" />
          {loading ? "A carregar..." : `${metricCount} métricas · 12 meses`}
        </div>
      </div>
    </header>
  );
}

export default Header;
