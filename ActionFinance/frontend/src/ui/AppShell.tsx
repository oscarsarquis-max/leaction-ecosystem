import { useEffect, useState, type ReactNode } from "react";
import { loadPayReceiptsVisible } from "../api";
import type { Session } from "../session";
import { BrandLogo } from "./BrandLogo";

type Area = "tesouraria" | "recebimentos" | "pagamentos" | "cadastros";

function areaOf(path: string): Area | null {
  if (path.startsWith("/financial-accounts")) return "tesouraria";
  if (path.startsWith("/pay-receipts") || path.startsWith("/receivables")) return "recebimentos";
  if (path.startsWith("/payables")) return "pagamentos";
  if (path.startsWith("/catalogs")) return "cadastros";
  return null;
}

export function AppShell({
  session,
  path,
  onNavigate,
  onSignOut,
  onSwitchCompany,
  signingOut = false,
  children,
}: {
  session: Session;
  path: string;
  onNavigate: (to: string) => boolean;
  onSignOut: () => void;
  onSwitchCompany: (companyId: string) => void;
  signingOut?: boolean;
  children: ReactNode;
}) {
  const [payVisible, setPayVisible] = useState(false);
  useEffect(() => {
    void loadPayReceiptsVisible().then(setPayVisible);
  }, []);

  useEffect(() => {
    document
      .querySelectorAll<HTMLElement>(".primary-nav .nav-item.active, .area-subnav .nav-item.active")
      .forEach((node) => {
        if (typeof node.scrollIntoView === "function") {
          node.scrollIntoView({ inline: "nearest", block: "nearest" });
        }
      });
  }, [path, payVisible]);

  const go = (to: string) => {
    onNavigate(to);
  };

  const area = areaOf(path);
  const canAccounts = session.permissions.includes("financial-accounts:read");
  const onReceivables = path.startsWith("/receivables");
  const onImported = path.startsWith("/pay-receipts");
  const onCounterparties = path.startsWith("/catalogs") && !path.includes("categories");
  const onCategories = path.startsWith("/catalogs") && path.includes("categories");

  return (
    <div className="shell">
      <header className="top">
        <div className="top-brand">
          <BrandLogo variant="blue" width={200} to="/receivables" onNavigate={go} />
        </div>
        <div className="top-company">
          <span className="top-label">Empresa</span>
          {session.companies.length > 1 ? (
            <select
              value={session.companyId}
              title={session.companies.find((company) => company.id === session.companyId)?.name}
              onChange={(event) => onSwitchCompany(event.target.value)}
              aria-label="Empresa ativa"
            >
              {session.companies.map((company) => (
                <option key={company.id} value={company.id}>
                  {company.name}
                </option>
              ))}
            </select>
          ) : (
            <span className="top-company-name" title={session.companies[0]?.name}>
              {session.companies[0]?.name ?? "Empresa"}
            </span>
          )}
        </div>
        <div className="top-meta">
          {session.mode === "demo" ? <span className="badge">Demonstração local</span> : null}
          <div className="top-user">
            <span className="top-user-name">{session.displayName}</span>
            <button
              type="button"
              className="btn-link"
              onClick={onSignOut}
              disabled={signingOut}
              aria-busy={signingOut || undefined}
            >
              {signingOut ? "Saindo…" : "Sair"}
            </button>
          </div>
        </div>
      </header>
      <nav className="primary-nav nav-scroll" aria-label="Áreas">
        <NavButton label="Tesouraria" current={area === "tesouraria"} onClick={() => go("/financial-accounts/summary")} hidden={!canAccounts} />
        <NavButton label="Recebimentos" shortLabel="Receber" current={area === "recebimentos"} onClick={() => go("/receivables")} />
        <NavButton label="Pagamentos" shortLabel="Pagar" current={area === "pagamentos"} onClick={() => go("/payables")} />
        <NavButton label="Cadastros" current={area === "cadastros"} onClick={() => go("/catalogs/counterparties")} />
      </nav>
      {area ? (
        <nav className="area-subnav nav-scroll" aria-label="Nesta área">
          {area === "recebimentos" ? (
            <>
              <NavButton label="A receber" current={onReceivables} onClick={() => go("/receivables")} />
              <NavButton label="Recebimentos integrados" shortLabel="Integrados" current={onImported} onClick={() => go("/pay-receipts")} hidden={!payVisible} />
            </>
          ) : null}
          {area === "pagamentos" ? <NavButton label="A pagar" current={path.startsWith("/payables")} onClick={() => go("/payables")} /> : null}
          {area === "tesouraria" ? (
            <>
              <NavButton label="Resumo" current={path.startsWith("/financial-accounts/summary")} onClick={() => go("/financial-accounts/summary")} />
              <NavButton label="Contas" current={(path === "/financial-accounts" || /^\/financial-accounts\/[^/]+$/.test(path)) && !path.startsWith("/financial-accounts/summary") && !path.startsWith("/financial-accounts/agenda") && !path.startsWith("/financial-accounts/statement") && !path.startsWith("/financial-accounts/reconciliation")} onClick={() => go("/financial-accounts")} />
              <NavButton label="Extratos" current={path.startsWith("/financial-accounts/statement")} onClick={() => go("/financial-accounts/statement")} />
              <NavButton label="Conciliação" current={path.startsWith("/financial-accounts/reconciliation")} onClick={() => go("/financial-accounts/reconciliation")} />
              <NavButton label="Agenda" current={path.startsWith("/financial-accounts/agenda")} onClick={() => go("/financial-accounts/agenda")} />
            </>
          ) : null}
          {area === "cadastros" ? (
            <>
              <NavButton label="Clientes e fornecedores" current={onCounterparties} onClick={() => go("/catalogs/counterparties")} />
              <NavButton label="Categorias" current={onCategories} onClick={() => go("/catalogs/categories")} />
              <NavButton label="Iniciativas" current={path.startsWith("/catalogs/initiatives")} onClick={() => go("/catalogs/initiatives")} />
              <NavButton label="Regras de rateio" shortLabel="Rateios" current={path.startsWith("/catalogs/allocation-rules")} onClick={() => go("/catalogs/allocation-rules")} />
            </>
          ) : null}
        </nav>
      ) : null}
      <main className="content">{children}</main>
    </div>
  );
}

function NavButton({
  label,
  shortLabel,
  current,
  onClick,
  hidden = false,
}: {
  label: string;
  shortLabel?: string;
  current: boolean;
  onClick: () => void;
  hidden?: boolean;
}) {
  if (hidden) {
    return null;
  }
  return (
    <button
      type="button"
      className={current ? "nav-item active" : "nav-item"}
      aria-label={label}
      aria-current={current ? "page" : undefined}
      onClick={onClick}
    >
      <span className="nav-full">{label}</span>
      <span className="nav-short">{shortLabel ?? label}</span>
    </button>
  );
}
