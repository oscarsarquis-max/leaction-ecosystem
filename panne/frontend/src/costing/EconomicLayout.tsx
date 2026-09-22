/**
 * Casca do módulo econômico: nav interna persistente + breadcrumb + retorno ao painel.
 */
import { Link, NavLink, Outlet, useLocation, useSearchParams } from "react-router-dom";
import { useOrganization } from "../session/OrganizationContext";
import { ECONOMIC_NAV, economicCrumbLabel, matchEconomicNav } from "./nav";

export function EconomicLayout() {
  const { hasPermission } = useOrganization();
  const location = useLocation();
  const [params] = useSearchParams();
  const current = matchEconomicNav(location.pathname);
  const fromFlow = params.get("origem") === "fluxo" || location.search.includes("etapa=");
  const productQ = params.get("produto");

  const items = ECONOMIC_NAV.filter((item) =>
    item.permission ? hasPermission(item.permission) : true,
  );

  return (
    <div className="econ-module">
      <header className="econ-module__head">
        <nav className="econ-breadcrumb" aria-label="Trilha econômica">
          <Link to="/gestao/custos">Custos, preços e margem</Link>
          {current && current !== "visao" ? (
            <>
              <span aria-hidden="true"> / </span>
              <span>{economicCrumbLabel(current)}</span>
            </>
          ) : null}
          {productQ ? (
            <>
              <span aria-hidden="true"> · </span>
              <span className="meta">Produto {productQ}</span>
            </>
          ) : null}
        </nav>
        <div className="econ-module__returns">
          {current !== "visao" ? (
            <Link className="ghost" to="/gestao/custos">
              Voltar ao painel de custos
            </Link>
          ) : null}
          {fromFlow ? (
            <Link className="ghost" to="/fluxo?etapa=8">
              Voltar ao fluxo
            </Link>
          ) : null}
        </div>
      </header>

      <nav className="econ-nav" aria-label="Área econômica">
        {items.map((item) => (
          <NavLink
            key={item.id}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              isActive || current === item.id ? "econ-nav__link is-active" : "econ-nav__link"
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="econ-module__body">
        <Outlet />
      </div>
    </div>
  );
}
