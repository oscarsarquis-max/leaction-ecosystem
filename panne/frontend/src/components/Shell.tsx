import { useEffect, useId, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import logoCompacto from "../../images/aprovados/compacto-escuro.png";
import logoHorizontal from "../../images/aprovados/horizontal-escuro.png";
import { AssistantAvatar } from "../assistant/AssistantAvatar";
import { GlobalAssistant } from "../assistant/GlobalAssistant";
import { useAssistant } from "../assistant/AssistantContext";
import { config } from "../config";
import { useAuth } from "../auth/AuthContext";
import { FlowTrailFromLocation } from "../fluxo/FlowTrail";
import { roleLabel } from "../language/roles";
import { brandHomeForRoles } from "../navigation/landing";
import { FISCAL_READ_CODES } from "../session/fiscalAccess";
import { useOrganization } from "../session/OrganizationContext";

const PRODUCTION = [
  { to: "/producao", label: "Quadro", permission: "production.board.read", end: true },
  { to: "/planejamento", label: "Planejamento", permission: "production.plan.read", end: false },
  { to: "/ordens", label: "Ordens", permission: "production.order.read", end: false },
  { to: "/rastreabilidade", label: "Rastreabilidade", permission: "production.traceability.read", end: false },
];

const COMPONENTS = [
  { to: "/componentes/ingredientes", label: "Ingredientes", permission: "ingredient.read", end: false },
  { to: "/componentes/estoque", label: "Estoque", permission: "inventory.read", end: false },
  { to: "/componentes/lotes", label: "Lotes e validade", permission: "inventory.read", end: false },
  { to: "/componentes/fornecedores", label: "Fornecedores e itens", permission: "supplier.read", end: false },
  { to: "/componentes/catalogos", label: "Fontes técnicas", permission: "ingredient.read", end: false },
];

const INVENTORY = [
  { to: "/componentes/estoque", label: "Visão geral", permission: "inventory.read", end: true },
  { to: "/componentes/estoque/posicao", label: "Posição", permission: "inventory.read", end: false },
  { to: "/componentes/estoque/reservas", label: "Reservas", permission: "inventory.read", end: false },
  { to: "/componentes/estoque/movimentacoes", label: "Movimentações", permission: "inventory.read", end: false },
  { to: "/componentes/lotes", label: "Validades", permission: "inventory.read", end: false },
  { to: "/componentes/estoque/separacao", label: "Separação", permission: "inventory.separate", end: false },
];

const PROCUREMENT = [
  { to: "/gestao/compras/necessidades", label: "Necessidades", permission: "procurement.read", end: false },
  { to: "/gestao/compras/requisicoes", label: "Requisições", permission: "procurement.read", end: false },
  { to: "/gestao/compras/cotacoes", label: "Cotações", permission: "procurement.read", end: false },
  { to: "/gestao/compras/pedidos", label: "Pedidos", permission: "procurement.read", end: false },
  {
    to: "/gestao/compras/entradas",
    label: "Entradas fiscais",
    permission: "fiscal.document.read",
    anyOf: FISCAL_READ_CODES,
    end: false,
  },
  { to: "/gestao/compras/recebimentos", label: "Recebimentos", permission: "procurement.read", end: false },
  { to: "/gestao/compras/devolucoes", label: "Devoluções", permission: "procurement.read", end: false },
];

const COUNTS = [
  { to: "/gestao/inventarios", label: "Sessões", permission: "inventory.count", end: true },
];

const CATALOG = [
  { to: "/produtos", label: "Produtos", permission: "product.read", end: true },
  { to: "/componentes/ingredientes", label: "Ingredientes e componentes", permission: "ingredient.read", end: false },
  { to: "/receitas", label: "Receitas técnicas", permission: "recipe.read", end: false },
];

/** Submenu Gestao quando fora de custos; custos usam ECONOMIC_NAV no layout + espelho abaixo. */
const MANAGEMENT = [
  { to: "/gestao/custos", label: "Custos, preços e margem", permission: "costing.read", end: false },
  { to: "/gestao/compras/necessidades", label: "Compras", permission: "procurement.read", end: false },
  { to: "/gestao/inventarios", label: "Inventários", permission: "inventory.count", end: false },
];

const COSTING_SUBMENU = [
  { to: "/gestao/custos", label: "Visão geral", permission: "costing.read", end: true },
  { to: "/gestao/custos/formacao", label: "Formação do custo", permission: "costing.read", end: false },
  { to: "/gestao/custos/variacao", label: "Previsto vs realizado", permission: "costing.read", end: false },
  { to: "/gestao/custos/precos", label: "Preços e histórico", permission: "costing.read", end: false },
  { to: "/gestao/custos/politicas", label: "Políticas e premissas", permission: "costing.read", end: false },
  { to: "/gestao/custos/calculadora", label: "Calculadora", permission: "costing.read", end: false },
];

const REPORTING = [
  { to: "/gestao/relatorios/executivo", label: "Visão executiva", permission: "reporting.dashboard.read", end: false },
  { to: "/gestao/relatorios/producao", label: "Produção", permission: "reporting.production.read", end: false },
  { to: "/gestao/relatorios/componentes", label: "Componentes e perdas", permission: "reporting.production.read", end: false },
  { to: "/gestao/relatorios/custos", label: "Custos e preços", permission: "reporting.costing.read", end: false },
  { to: "/gestao/relatorios/conformidade", label: "Conformidade", permission: "reporting.compliance.read", end: false },
  { to: "/gestao/relatorios/rastreabilidade", label: "Rastreabilidade", permission: "reporting.traceability.read", end: false },
  { to: "/gestao/relatorios/estoque", label: "Estoque e compras", permission: "reporting.inventory.read", end: false },
  { to: "/gestao/relatorios/qualidade", label: "Qualidade dos dados", permission: "reporting.data_quality.read", end: false },
  { to: "/gestao/relatorios/salvos", label: "Relatórios salvos", permission: "reporting.saved_view.manage", end: false },
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
  const { open } = useAssistant();
  const [menuOpen, setMenuOpen] = useState(false);
  const [navOpen, setNavOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const menuId = useId();
  const navId = useId();
  const menuRef = useRef<HTMLDivElement>(null);
  const menuButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    setNavOpen(false);
    setMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!menuOpen) return;
    function onPointerDown(event: MouseEvent) {
      if (!menuRef.current?.contains(event.target as Node)) setMenuOpen(false);
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setMenuOpen(false);
        menuButtonRef.current?.focus();
      }
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [menuOpen]);

  async function handleLogout() {
    setMenuOpen(false);
    await logout();
    navigate("/entrar", { replace: true });
  }

  const profileLabel = me?.display_name ?? session?.displayHint ?? "Conta";
  const roleName = roleLabel(active?.roles?.[0] || me?.roles?.[0]);
  // Alguns destinos aceitam mais de um código enquanto papéis antigos não recebem o novo.
  const visible = (item: { permission: string; anyOf?: string[] }) =>
    item.anyOf ? item.anyOf.some((code) => hasPermission(code)) : hasPermission(item.permission);
  const showProduction = PRODUCTION.some(visible);
  const showComponents = COMPONENTS.filter((item) => item.to !== "/componentes/ingredientes").some(visible);
  const showCatalog = CATALOG.some(visible);
  const componentsHome = hasPermission("inventory.read")
    ? "/componentes/estoque"
    : "/componentes/fornecedores";
  const showCompliance = COMPLIANCE.some(visible);
  const showManagement =
    MANAGEMENT.some(visible)
    || PROCUREMENT.some(visible)
    || COUNTS.some(visible);
  const showReporting = REPORTING.some(visible);
  const gestaoHome = hasPermission("costing.read")
    ? "/gestao/custos"
    : hasPermission("procurement.read")
      ? "/gestao/compras/necessidades"
      : "/gestao/inventarios";
  const brandHome = brandHomeForRoles(active?.roles ?? me?.roles);
  const inicioActive = location.pathname === "/inicio";
  const fluxoActive = location.pathname === "/fluxo" || location.pathname.startsWith("/fluxo/");
  const productionActive = location.pathname.startsWith("/producao")
    || location.pathname.startsWith("/planejamento")
    || location.pathname.startsWith("/ordens")
    || location.pathname.startsWith("/rastreabilidade");
  const ingredientsActive = location.pathname.startsWith("/componentes/ingredientes");
  const componentsActive = location.pathname.startsWith("/componentes") && !ingredientsActive;
  const productsActive = location.pathname.startsWith("/produtos");
  const recipesActive = location.pathname.startsWith("/receitas");
  const catalogActive = productsActive || recipesActive || ingredientsActive;
  const complianceActive = location.pathname.startsWith("/conformidade");
  const costingActive = location.pathname.startsWith("/gestao/custos");
  const procurementActive = location.pathname.startsWith("/gestao/compras");
  const countsActive = location.pathname.startsWith("/gestao/inventarios");
  const inventoryActive = location.pathname.startsWith("/componentes/estoque") || location.pathname.startsWith("/componentes/lotes");
  const reportingActive = location.pathname.startsWith("/gestao/relatorios");
  const gestaoActive = costingActive || procurementActive || countsActive;
  const operational = location.pathname.includes("/executar");
  const submenu = reportingActive
    ? REPORTING.filter(visible)
    : costingActive
    ? COSTING_SUBMENU.filter(visible)
    : procurementActive
    ? PROCUREMENT.filter(visible)
    : countsActive
    ? COUNTS.filter(visible)
    : inventoryActive
    ? INVENTORY.filter(visible)
    : complianceActive
    ? COMPLIANCE.filter(visible)
    : catalogActive
    ? CATALOG.filter(visible)
    : productionActive
      ? PRODUCTION.filter(visible)
      : componentsActive
        ? COMPONENTS.filter(visible)
        : showProduction
          ? PRODUCTION.filter(visible)
          : [];

  return (
    <div className={operational ? "shell shell-ops" : "shell"}>
      <header className="shell-header">
        <NavLink to={brandHome} className="brand" aria-label="Panne">
          <img className="horizontal" src={logoHorizontal} alt="" />
          <img className="compacto" src={logoCompacto} alt="" />
        </NavLink>
        <NavLink
          to="/fluxo"
          className="fluxo-pin"
          aria-current={fluxoActive ? "page" : undefined}
        >
          Fluxo produtivo
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
          <NavLink to="/fluxo" aria-current={fluxoActive ? "page" : undefined} className="fluxo-nav-item">
            Fluxo produtivo
          </NavLink>
          {showProduction ? (
            <NavLink to="/producao" aria-current={productionActive ? "page" : undefined}>
              Produção
            </NavLink>
          ) : null}
          {showComponents ? (
            <NavLink to={componentsHome} aria-current={componentsActive ? "page" : undefined}>
              Estoque e insumos
            </NavLink>
          ) : null}
          {showCatalog ? (
            <NavLink to="/produtos" aria-current={catalogActive ? "page" : undefined}>
              Produtos e receitas
            </NavLink>
          ) : null}
          {showCompliance ? (
            <NavLink to="/conformidade" aria-current={complianceActive ? "page" : undefined}>
              Conformidade
            </NavLink>
          ) : null}
          {showManagement ? (
            <NavLink to={gestaoHome} aria-current={gestaoActive ? "page" : undefined}>
              Gestão
            </NavLink>
          ) : null}
          {showReporting ? (
            <NavLink to="/gestao/relatorios" aria-current={reportingActive ? "page" : undefined}>
              Relatórios
            </NavLink>
          ) : null}
        </nav>
        <div className="shell-tools">
          {config.demoMode ? <span className="demo-banner">Ambiente de demonstração</span> : null}
          {config.demoMode ? (
            <span className="demo-shared-hint" title="Alterações afetam outros homologadores">
              Dados compartilhados
            </span>
          ) : null}
          {associations.length > 1 ? (
            <label className="org-picker">
              <span className="visually-hidden">Organização ativa</span>
              <span className="org-picker__current" aria-hidden="true">
                {active?.display_name || active?.slug || "Organização"}
              </span>
              <select
                className="org-select"
                aria-label="Organização ativa"
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
            <span className="org-picker__current">{active?.display_name || "Sem organização"}</span>
          )}
          <div className="account-menu" ref={menuRef}>
            <button
              type="button"
              ref={menuButtonRef}
              className="account-menu__trigger"
              aria-label="Abrir menu do usuário"
              aria-haspopup="menu"
              aria-expanded={menuOpen}
              aria-controls={menuId}
              onClick={() => setMenuOpen((open) => !open)}
            >
              <span className="account-menu__who">
                <span className="account-menu__name">{profileLabel}</span>
                {roleName ? <span className="account-menu__role">{roleName}</span> : null}
              </span>
              <span className={`account-menu__chevron${menuOpen ? " is-open" : ""}`} aria-hidden="true">
                ▾
              </span>
            </button>
            {menuOpen ? (
              <div id={menuId} className="account-panel" role="menu" aria-label="Menu do usuário">
                <p className="account-panel__name">{profileLabel}</p>
                {roleName ? <p className="meta account-panel__role">{roleName}</p> : null}
                <p className="meta">{active?.display_name}</p>
                {config.demoMode ? (
                  <Link
                    to="/demonstracao"
                    role="menuitem"
                    className="account-panel__link"
                    onClick={() => setMenuOpen(false)}
                  >
                    Guia da demonstração
                  </Link>
                ) : null}
                <button
                  type="button"
                  role="menuitem"
                  className="account-panel__logout"
                  onClick={() => void handleLogout()}
                >
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
        {inicioActive
          ? " / Hoje"
          : fluxoActive
          ? " / Fluxo produtivo"
          : reportingActive
            ? " / Gestão / Relatórios e painéis"
            : costingActive
              ? " / Gestão / Custos e preços"
              : procurementActive
                ? " / Gestão / Compras"
                : countsActive
                  ? " / Gestão / Inventários"
                  : inventoryActive
                    ? " / Componentes / Estoque"
                    : complianceActive
                      ? " / Conformidade"
                      : catalogActive
                        ? " / Produtos e receitas"
                        : componentsActive
                            ? " / Componentes"
                            : productionActive
                              ? " / Produção"
                              : ""}
      </p>
      <FlowTrailFromLocation pathname={location.pathname} />
      <main className="main">
        {status.kind === "erro" ? (
          <p role="alert">Não foi possível carregar a sessão.</p>
        ) : (
          <Outlet />
        )}
      </main>
      <AssistantAvatar />
      {open ? <GlobalAssistant /> : null}
    </div>
  );
}
