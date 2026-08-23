import { useEffect, useId, useRef, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import logoCompacto from "../../images/aprovados/compacto-escuro.png";
import logoHorizontal from "../../images/aprovados/horizontal-escuro.png";
import { useAuth } from "../auth/AuthContext";
import { useOrganization } from "../session/OrganizationContext";

const PRODUCTION = [
  { to: "/producao", label: "Quadro", permission: "production.board.read", end: true },
  { to: "/planejamento", label: "Planejamento", permission: "production.plan.read", end: false },
  { to: "/ordens", label: "Ordens", permission: "production.order.read", end: false },
  { to: "/rastreabilidade", label: "Rastreabilidade", permission: "production.traceability.read", end: false },
];

const COMPONENTS = [
  { to: "/componentes/ingredientes", label: "Ingredientes", permission: "ingredient.read", end: false },
  { to: "/componentes/fornecedores", label: "Fornecedores e itens", permission: "supplier.read", end: false },
  { to: "/componentes/catalogos", label: "Fontes técnicas", permission: "ingredient.read", end: false },
];

const RECIPES = [
  { to: "/receitas", label: "Minhas receitas", permission: "recipe.read", end: true },
  { to: "/receitas/assistente", label: "Assistente de receitas", permission: "recipe.read", end: false },
  { to: "/receitas/assistente/historico", label: "Histórico de propostas", permission: "recipe.ai.review", end: false },
];

const COMPLIANCE = [
  { to: "/conformidade", label: "Visão geral", permission: "labeling.read", end: true },
  { to: "/conformidade/dossies", label: "Dossiês", permission: "labeling.read", end: false },
  { to: "/conformidade/avaliacoes", label: "Avaliações", permission: "labeling.read", end: false },
  { to: "/conformidade/rotulos", label: "Rótulos candidatos", permission: "labeling.read", end: false },
  { to: "/conformidade/fontes", label: "Fontes e normas", permission: "regulatory.source.read", end: false },
];

export function Shell() {
  const { session, logout } = useAuth();
  const { me, associations, active, selectOrganization, status, hasPermission } = useOrganization();
  const [menuOpen, setMenuOpen] = useState(false);
  const [navOpen, setNavOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const menuId = useId();
  const navId = useId();
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setNavOpen(false);
    setMenuOpen(false);
  }, [location.pathname]);

  async function handleLogout() {
    await logout();
    navigate("/entrar", { replace: true });
  }

  const showProduction = PRODUCTION.some((item) => hasPermission(item.permission));
  const showComponents = COMPONENTS.some((item) => hasPermission(item.permission));
  const showRecipes = RECIPES.some((item) => hasPermission(item.permission));
  const showCompliance = COMPLIANCE.some((item) => hasPermission(item.permission));
  const productionActive = location.pathname.startsWith("/producao")
    || location.pathname.startsWith("/planejamento")
    || location.pathname.startsWith("/ordens")
    || location.pathname.startsWith("/rastreabilidade");
  const componentsActive = location.pathname.startsWith("/componentes");
  const recipesActive = location.pathname.startsWith("/receitas");
  const complianceActive = location.pathname.startsWith("/conformidade");
  const operational = location.pathname.includes("/executar");
  const submenu = complianceActive
    ? COMPLIANCE.filter((item) => hasPermission(item.permission))
    : recipesActive
    ? RECIPES.filter((item) => hasPermission(item.permission))
    : productionActive
      ? PRODUCTION.filter((item) => hasPermission(item.permission))
      : componentsActive
        ? COMPONENTS.filter((item) => hasPermission(item.permission))
        : showProduction
          ? PRODUCTION.filter((item) => hasPermission(item.permission))
          : [];

  return (
    <div className={operational ? "shell shell-ops" : "shell"}>
      <header className="shell-header">
        <NavLink to="/inicio" className="brand" aria-label="Panne">
          <img className="horizontal" src={logoHorizontal} alt="" />
          <img className="compacto" src={logoCompacto} alt="" />
        </NavLink>
        <button
          type="button"
          className="nav-toggle"
          aria-expanded={navOpen}
          aria-controls={navId}
          onClick={() => setNavOpen((open) => !open)}
        >
          Menu
        </button>
        <nav id={navId} className={`shell-nav ${navOpen ? "is-open" : ""}`} aria-label="Principal">
          {showProduction ? (
            <NavLink to="/producao" aria-current={productionActive ? "page" : undefined}>
              Produção
            </NavLink>
          ) : null}
          {showComponents ? (
            <NavLink to="/componentes/ingredientes" aria-current={componentsActive ? "page" : undefined}>
              Componentes
            </NavLink>
          ) : null}
          {showRecipes ? (
            <NavLink to="/receitas" aria-current={recipesActive ? "page" : undefined}>
              Receitas
            </NavLink>
          ) : null}
          {showCompliance ? (
            <NavLink to="/conformidade" aria-current={complianceActive ? "page" : undefined}>
              Conformidade
            </NavLink>
          ) : null}
        </nav>
        <div className="shell-tools">
          {associations.length > 1 ? (
            <label>
              <span className="visually-hidden">Organização ativa</span>
              <select
                className="org-select"
                value={active?.organization_id ?? ""}
                onChange={(event) => void selectOrganization(event.target.value)}
              >
                {associations.map((item) => (
                  <option key={item.organization_id} value={item.organization_id}>
                    {item.display_name || item.slug || item.organization_id}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <span>{active?.display_name || "Sem organização"}</span>
          )}
          <div className="account-menu" ref={menuRef}>
            <button
              type="button"
              aria-expanded={menuOpen}
              aria-controls={menuId}
              onClick={() => setMenuOpen((open) => !open)}
            >
              {me?.display_name ?? session?.displayHint ?? "Conta"}
            </button>
            {menuOpen ? (
              <div id={menuId} className="account-panel" role="menu">
                <p>{me?.display_name}</p>
                <p className="meta">{active?.display_name}</p>
                <button type="button" className="ghost" onClick={() => void handleLogout()}>
                  Sair
                </button>
              </div>
            ) : null}
          </div>
        </div>
      </header>
      {operational || submenu.length === 0 ? null : (
        <nav className="submenu" aria-label="Submenu">
          {submenu.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end}>
              {item.label}
            </NavLink>
          ))}
        </nav>
      )}
      <p className="crumb">
        Início
        {complianceActive ? " / Conformidade" : recipesActive ? " / Receitas" : componentsActive ? " / Componentes" : productionActive ? " / Produção" : ""}
      </p>
      <main className="main">
        {status.kind === "erro" ? (
          <p role="alert">Não foi possível carregar a sessão.</p>
        ) : (
          <Outlet />
        )}
      </main>
    </div>
  );
}
