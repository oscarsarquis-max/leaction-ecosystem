import type { RefObject } from "react";
import { NAV_GROUPS, activeNavId } from "./nav";

type Props = {
  path: string;
  open: boolean;
  narrow?: boolean;
  onNavigate: (href: string) => void;
  onClose?: () => void;
  sidebarRef: RefObject<HTMLElement>;
};

function ExternalIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M14 5h5v5M19 5 10 14"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M19 13v5a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <path d="M5 5l10 10M15 5 5 15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export function AdminSidebar({ path, open, narrow = false, onNavigate, onClose, sidebarRef }: Props) {
  const active = activeNavId(path);
  const brand = (
    <a
      className="admin-brand-link"
      href="/admin/pedidos"
      onClick={(event) => {
        event.preventDefault();
        onNavigate("/admin/pedidos");
      }}
    >
      <span className="admin-brand-name">Loja de Pães</span>
      <span className="admin-brand-mark">Gestão</span>
    </a>
  );
  return (
    <aside id="admin-menu" className={open ? "admin-side is-open" : "admin-side"} ref={sidebarRef} hidden={!open}>
      {narrow ? (
        <div className="admin-drawer-head">
          {brand}
          <button type="button" className="admin-drawer-close" aria-label="Fechar menu" onClick={onClose}>
            <CloseIcon />
          </button>
        </div>
      ) : (
        brand
      )}
      {narrow ? (
        <>
          <a
            className="admin-drawer-store"
            href="/"
            onClick={(event) => {
              event.preventDefault();
              onNavigate("/");
            }}
          >
            <ExternalIcon />
            Ver a loja
          </a>
          <div className="admin-drawer-rule" />
        </>
      ) : null}
      <nav className="admin-side-nav" aria-label="Gestão">
        {NAV_GROUPS.map((group) => (
          <div key={group.label} className="admin-side-group">
            <p className="ng">{group.label}</p>
            {group.items.map((item) =>
              item.href ? (
                <a
                  key={item.id}
                  className={active === item.id ? "nl on" : "nl"}
                  href={item.href}
                  aria-current={active === item.id ? "page" : undefined}
                  onClick={(event) => {
                    event.preventDefault();
                    onNavigate(item.href!);
                  }}
                >
                  {item.label}
                </a>
              ) : (
                <span key={item.id} className="nl off">
                  {item.label}
                  <span className="soon">em breve</span>
                </span>
              ),
            )}
          </div>
        ))}
      </nav>
    </aside>
  );
}
