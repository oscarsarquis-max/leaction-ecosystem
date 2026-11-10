import { useEffect, useRef, useState, type ReactNode } from "react";
import { loadPayReceiptsVisible } from "../api";
import logo from "../assets/brand/af-logo-vazado-branco.png";
import type { Session } from "../session";

type Area = "inicio" | "caixa" | "vendas" | "pagamentos" | "bancos" | "cadastros";

function formatCnpj(value: string | null | undefined): string {
  const digits = (value ?? "").replace(/\D/g, "");
  if (digits.length !== 14) {
    return "CNPJ não informado";
  }
  return `CNPJ ${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5, 8)}/${digits.slice(8, 12)}-${digits.slice(12)}`;
}

function areaOf(path: string): Area | null {
  if (path === "/" || path === "") return "inicio";
  if (path.startsWith("/financial-accounts/summary") || path.startsWith("/financial-accounts/agenda")) return "caixa";
  if (path.startsWith("/pay-receipts") || path.startsWith("/receivables")) return "vendas";
  if (path.startsWith("/payables")) return "pagamentos";
  if (path.startsWith("/financial-accounts")) return "bancos";
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
  const onAccounts =
    path.startsWith("/financial-accounts") &&
    !path.startsWith("/financial-accounts/summary") &&
    !path.startsWith("/financial-accounts/agenda") &&
    !path.startsWith("/financial-accounts/statement") &&
    !path.startsWith("/financial-accounts/reconciliation");
  const activeCompany = session.companies.find((company) => company.id === session.companyId) ?? session.companies[0];

  return (
    <div className="shell">
      <header className="top">
        <div className="top-brand">
          <a
            className="brand-logo-link"
            href="/"
            onClick={(event) => {
              event.preventDefault();
              go("/");
            }}
          >
            <img className="brand-mark-logo" src={logo} alt="Action Finance Capital" />
          </a>
        </div>
        <div className="top-side">
          <div className="top-company">
            {session.companies.length > 1 ? (
              <select
                value={session.companyId}
                title={activeCompany?.name}
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
              <span className="top-company-name" title={activeCompany?.name}>
                {activeCompany?.name ?? "Empresa"}
              </span>
            )}
            <span className="top-cnpj">{formatCnpj(activeCompany?.cnpj)}</span>
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
        </div>
      </header>
      <nav className="primary-nav nav-scroll" aria-label="Áreas">
        <NavButton label="Início" current={area === "inicio"} onClick={() => go("/")} />
        <NavButton label="Caixa" current={area === "caixa"} onClick={() => go("/financial-accounts/summary")} hidden={!canAccounts} />
        <NavButton label="Vendas" current={area === "vendas"} onClick={() => go("/receivables")} />
        <NavButton label="Pagamentos" shortLabel="Pagar" current={area === "pagamentos"} onClick={() => go("/payables")} />
        <NavButton label="Bancos" current={area === "bancos"} onClick={() => go("/financial-accounts")} hidden={!canAccounts} />
        <NavButton label="Cadastros" current={area === "cadastros"} onClick={() => go("/catalogs/counterparties")} />
      </nav>
      {area && area !== "inicio" ? (
        <nav className="area-subnav nav-scroll" aria-label="Nesta área">
          {area === "caixa" ? (
            <>
              <NavButton label="Resumo" current={path.startsWith("/financial-accounts/summary")} onClick={() => go("/financial-accounts/summary")} />
              <NavButton label="Agenda" current={path.startsWith("/financial-accounts/agenda")} onClick={() => go("/financial-accounts/agenda")} />
            </>
          ) : null}
          {area === "vendas" ? (
            <>
              <NavButton label="A receber" current={path.startsWith("/receivables")} onClick={() => go("/receivables")} />
              <NavButton label="Recebimentos integrados" shortLabel="Integrados" current={path.startsWith("/pay-receipts")} onClick={() => go("/pay-receipts")} hidden={!payVisible} />
            </>
          ) : null}
          {area === "pagamentos" ? <NavButton label="A pagar" current={path.startsWith("/payables")} onClick={() => go("/payables")} /> : null}
          {area === "bancos" ? (
            <>
              <NavButton label="Contas" current={onAccounts} onClick={() => go("/financial-accounts")} />
              <NavButton label="Extratos" current={path.startsWith("/financial-accounts/statement")} onClick={() => go("/financial-accounts/statement")} />
              <NavButton label="Conciliação" current={path.startsWith("/financial-accounts/reconciliation")} onClick={() => go("/financial-accounts/reconciliation")} />
            </>
          ) : null}
          {area === "cadastros" ? (
            <>
              <NavButton label="Clientes e fornecedores" current={path.startsWith("/catalogs") && !path.includes("categories") && !path.includes("initiatives") && !path.includes("allocation-rules")} onClick={() => go("/catalogs/counterparties")} />
              <NavButton label="Categorias" current={path.includes("/catalogs/categories")} onClick={() => go("/catalogs/categories")} />
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
  const ref = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (current && typeof ref.current?.scrollIntoView === "function") {
      ref.current.scrollIntoView({ inline: "nearest", block: "nearest" });
    }
  }, [current]);
  if (hidden) {
    return null;
  }
  return (
    <button
      ref={ref}
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
