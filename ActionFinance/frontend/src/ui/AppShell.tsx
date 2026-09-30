import { useEffect, useRef, useState, type ReactNode } from "react";
import type { Session } from "../session";
import { BrandLogo } from "./BrandLogo";

export function AppShell({
  session,
  path,
  navOpen,
  setNavOpen,
  onNavigate,
  onSignOut,
  onSwitchCompany,
  children,
}: {
  session: Session;
  path: string;
  navOpen: boolean;
  setNavOpen: (open: boolean) => void;
  onNavigate: (to: string) => boolean;
  onSignOut: () => void;
  onSwitchCompany: (companyId: string) => void;
  children: ReactNode;
}) {
  const menuRef = useRef<HTMLButtonElement>(null);
  const navRef = useRef<HTMLElement>(null);
  const [compact, setCompact] = useState(() =>
    typeof window !== "undefined" && typeof window.matchMedia === "function"
      ? window.matchMedia("(max-width: 1023px)").matches
      : false,
  );

  useEffect(() => {
    if (typeof window.matchMedia !== "function") {
      return;
    }
    const mq = window.matchMedia("(max-width: 1023px)");
    const sync = () => {
      const next = mq.matches;
      setCompact(next);
      if (!next) {
        setNavOpen(false);
      }
    };
    sync();
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, [setNavOpen]);

  useEffect(() => {
    const node = navRef.current;
    if (!node) {
      return;
    }
    if (compact && !navOpen) {
      node.setAttribute("inert", "");
    } else {
      node.removeAttribute("inert");
    }
  }, [compact, navOpen]);

  useEffect(() => {
    if (!compact || !navOpen) {
      return;
    }
    const node = navRef.current;
    if (!node) {
      return;
    }
    const focusables = () =>
      Array.from(
        node.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      );
    focusables()[0]?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setNavOpen(false);
        menuRef.current?.focus();
        return;
      }
      if (event.key !== "Tab") {
        return;
      }
      const items = focusables();
      if (items.length === 0) {
        return;
      }
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [compact, navOpen, setNavOpen]);

  const closeDrawer = () => {
    setNavOpen(false);
    if (compact) {
      menuRef.current?.focus();
    }
  };

  const go = (to: string) => {
    if (onNavigate(to)) {
      setNavOpen(false);
    }
  };

  const nav = (
    <nav
      ref={navRef}
      id="main-nav"
      className={navOpen ? "side side--open" : "side"}
      aria-label="Principal"
      aria-hidden={compact && !navOpen}
    >
      <div className="side-brand">
        <BrandLogo variant="yellow" width={212} to="/receivables" onNavigate={go} />
      </div>
      <NavButton label="A receber" current={path.startsWith("/receivables")} onClick={() => go("/receivables")} />
      <NavButton label="A pagar" current={path.startsWith("/payables")} onClick={() => go("/payables")} />
      <NavButton
        label="Contas financeiras"
        current={path.startsWith("/financial-accounts")}
        onClick={() => go("/financial-accounts")}
        hidden={!session.permissions.includes("financial-accounts:read")}
      />
      <NavButton label="Cadastros" current={path.startsWith("/catalogs")} onClick={() => go("/catalogs/counterparties")} />
    </nav>
  );

  return (
    <div className="shell">
      {compact && navOpen ? (
        <button type="button" className="nav-backdrop" aria-label="Fechar menu" onClick={closeDrawer} />
      ) : null}
      {nav}
      <div className="workspace">
        <header className="top">
          <button
            ref={menuRef}
            type="button"
            className="menu-toggle"
            aria-expanded={navOpen}
            aria-controls="main-nav"
            onClick={() => setNavOpen(!navOpen)}
          >
            Menu
          </button>
          <div className="top-brand">
            <BrandLogo variant="yellow" width={144} to="/receivables" onNavigate={go} />
          </div>
          <div className="top-company">
            <span className="top-label">Empresa</span>
            {session.companies.length > 1 ? (
              <select value={session.companyId} onChange={(event) => onSwitchCompany(event.target.value)} aria-label="Empresa ativa">
                {session.companies.map((company) => (
                  <option key={company.id} value={company.id}>
                    {company.name}
                  </option>
                ))}
              </select>
            ) : (
              <span className="top-company-name">{session.companies[0]?.name ?? "Empresa"}</span>
            )}
          </div>
          <div className="top-meta">
            {session.mode === "demo" ? <span className="badge">Demonstração local</span> : null}
            <div className="top-user">
              <span className="top-user-name">{session.displayName}</span>
              <button type="button" className="btn-link" onClick={onSignOut}>
                Sair
              </button>
            </div>
          </div>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  );
}

function NavButton({
  label,
  current,
  onClick,
  hidden = false,
}: {
  label: string;
  current: boolean;
  onClick: () => void;
  hidden?: boolean;
}) {
  if (hidden) {
    return null;
  }
  return (
    <button type="button" className={current ? "nav-item active" : "nav-item"} aria-current={current ? "page" : undefined} onClick={onClick}>
      {label}
    </button>
  );
}
