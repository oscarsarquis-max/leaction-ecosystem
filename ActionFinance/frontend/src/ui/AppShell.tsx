import { useEffect, useRef, useState, type ReactNode } from "react";
import { loadPayReceiptsVisible } from "../api";
import type { Session } from "../session";
import { BrandLogo } from "./BrandLogo";

type Area = "recebimentos" | "pagamentos" | "contas" | "mais" | "other";

function areaOf(path: string): Area {
  if (path.startsWith("/pay-receipts") || path.startsWith("/receivables")) return "recebimentos";
  if (path.startsWith("/payables")) return "pagamentos";
  if (path.startsWith("/financial-accounts")) return "contas";
  if (path.startsWith("/catalogs")) return "mais";
  return "other";
}

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
  const moreDesktopRef = useRef<HTMLButtonElement>(null);
  const moreMobileRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLElement>(null);
  const [payVisible, setPayVisible] = useState(false);
  useEffect(() => {
    void loadPayReceiptsVisible().then(setPayVisible);
  }, []);
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
    const node = panelRef.current;
    if (!node) {
      return;
    }
    if (!navOpen) {
      node.setAttribute("inert", "");
    } else {
      node.removeAttribute("inert");
    }
  }, [navOpen]);

  useEffect(() => {
    if (!navOpen) {
      return;
    }
    const node = panelRef.current;
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
        (compact ? moreMobileRef.current : moreDesktopRef.current)?.focus();
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

  const closeMore = () => {
    setNavOpen(false);
    (compact ? moreMobileRef.current : moreDesktopRef.current)?.focus();
  };

  const go = (to: string) => {
    if (onNavigate(to)) {
      setNavOpen(false);
    }
  };

  const area = areaOf(path);
  const canAccounts = session.permissions.includes("financial-accounts:read");
  const canWriteTitles = session.permissions.includes("titles:write");

  const moreLinks = (
    <>
      <NavButton label="A receber" current={path.startsWith("/receivables") && !path.includes("/new")} onClick={() => go("/receivables")} />
      <NavButton
        label="Registrar recebível"
        current={path === "/receivables/new"}
        onClick={() => go("/receivables/new")}
        hidden={!canWriteTitles}
      />
      <NavButton
        label="Recebimentos ActionHub Pay"
        current={path.startsWith("/pay-receipts")}
        onClick={() => go("/pay-receipts")}
        hidden={!payVisible}
      />
      <NavButton label="A pagar" current={path.startsWith("/payables") && !path.includes("/new")} onClick={() => go("/payables")} />
      <NavButton
        label="Registrar pagável"
        current={path === "/payables/new"}
        onClick={() => go("/payables/new")}
        hidden={!canWriteTitles}
      />
      <NavButton
        label="Contas financeiras"
        current={path.startsWith("/financial-accounts")}
        onClick={() => go("/financial-accounts")}
        hidden={!canAccounts}
      />
      <NavButton label="Cadastros" current={path.startsWith("/catalogs")} onClick={() => go("/catalogs/counterparties")} />
    </>
  );

  return (
    <div className="shell">
      {navOpen ? <button type="button" className="nav-backdrop" aria-label="Fechar menu" onClick={closeMore} /> : null}
      <header className="top">
        <div className="top-brand">
          <BrandLogo variant="blue" width={200} to="/receivables" onNavigate={go} />
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
      <nav className="primary-nav" aria-label="Áreas">
        <NavButton label="Recebimentos" current={area === "recebimentos"} onClick={() => go("/receivables")} />
        <NavButton label="Pagamentos" current={area === "pagamentos"} onClick={() => go("/payables")} />
        <NavButton
          label="Contas e caixa"
          current={area === "contas"}
          onClick={() => go("/financial-accounts")}
          hidden={!canAccounts}
        />
        <button
          ref={moreDesktopRef}
          type="button"
          className={navOpen || area === "mais" ? "nav-item active" : "nav-item"}
          aria-expanded={navOpen}
          aria-controls="main-nav"
          onClick={() => setNavOpen(!navOpen)}
        >
          Mais
        </button>
      </nav>
      <nav
        ref={panelRef}
        id="main-nav"
        className={navOpen ? "more-panel more-panel--open" : "more-panel"}
        aria-label="Principal"
        aria-hidden={!navOpen}
      >
        <p className="more-panel-title">Destinos disponíveis</p>
        {moreLinks}
      </nav>
      {area === "recebimentos" || area === "pagamentos" ? (
        <nav className="area-subnav" aria-label="Nesta área">
          {area === "recebimentos" ? (
            <>
              <NavButton label="A receber" current={path.startsWith("/receivables") && !path.startsWith("/pay-receipts")} onClick={() => go("/receivables")} />
              <NavButton
                label="Recebimentos ActionHub Pay"
                current={path.startsWith("/pay-receipts")}
                onClick={() => go("/pay-receipts")}
                hidden={!payVisible}
              />
            </>
          ) : (
            <NavButton label="A pagar" current={path.startsWith("/payables")} onClick={() => go("/payables")} />
          )}
        </nav>
      ) : null}
      <main className="content">{children}</main>
      <nav className="bottom-nav" aria-label="Principal móvel">
        <NavButton icon="receber" label="Receber" current={area === "recebimentos"} onClick={() => go("/receivables")} />
        <NavButton icon="pagar" label="Pagar" current={area === "pagamentos"} onClick={() => go("/payables")} />
        <NavButton icon="contas" label="Contas" current={area === "contas"} onClick={() => go("/financial-accounts")} hidden={!canAccounts} />
        <button
          ref={moreMobileRef}
          type="button"
          className={navOpen || area === "mais" ? "nav-item active" : "nav-item"}
          aria-expanded={navOpen}
          aria-controls="main-nav"
          onClick={() => setNavOpen(!navOpen)}
        >
          <NavIcon name="mais" />
          Mais
        </button>
      </nav>
    </div>
  );
}

function NavButton({
  label,
  current,
  onClick,
  hidden = false,
  icon,
}: {
  label: string;
  current: boolean;
  onClick: () => void;
  hidden?: boolean;
  icon?: "receber" | "pagar" | "contas" | "mais";
}) {
  if (hidden) {
    return null;
  }
  return (
    <button type="button" className={current ? "nav-item active" : "nav-item"} aria-current={current ? "page" : undefined} onClick={onClick}>
      {icon ? <NavIcon name={icon} /> : null}
      {label}
    </button>
  );
}

function NavIcon({ name }: { name: "receber" | "pagar" | "contas" | "mais" }) {
  return (
    <svg className="nav-icon" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
      {name === "receber" ? <path fill="currentColor" d="M12 3v12l4-4 1.4 1.4L12 18.8 6.6 12.4 8 11l4 4V3h0Zm-7 16h14v2H5v-2Z" /> : null}
      {name === "pagar" ? <path fill="currentColor" d="M12 21V9l4 4 1.4-1.4L12 5.2 6.6 11.6 8 13l4-4v12h0Zm-7-16h14V3H5v2Z" /> : null}
      {name === "contas" ? <path fill="currentColor" d="M4 6h16v12H4V6Zm2 2v8h12V8H6Zm2 2h8v2H8v-2Zm0 4h5v2H8v-2Z" /> : null}
      {name === "mais" ? <path fill="currentColor" d="M11 5h2v6h6v2h-6v6h-2v-6H5v-2h6V5Z" /> : null}
    </svg>
  );
}
