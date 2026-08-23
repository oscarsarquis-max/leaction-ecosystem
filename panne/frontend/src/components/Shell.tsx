import { useEffect, useId, useRef, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useOrganization } from "../session/OrganizationContext";

const LINKS = [
  { to: "/producao", label: "Produção", permission: "production.board.read" },
  { to: "/planejamento", label: "Planejamento", permission: "production.plan.read" },
  { to: "/ordens", label: "Ordens", permission: "production.order.read" },
  { to: "/rastreabilidade", label: "Rastreabilidade", permission: "production.traceability.read" },
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

  const visibleLinks = LINKS.filter((item) => hasPermission(item.permission));
  const operational = location.pathname.includes("/executar");

  return (
    <div className={operational ? "shell shell-ops" : "shell"}>
      <header className="shell-header">
        <NavLink to="/producao" className="brand">
          Panne
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
          {visibleLinks.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.to === "/producao"}>
              {item.label}
            </NavLink>
          ))}
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
