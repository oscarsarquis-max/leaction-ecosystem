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

function CloseIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <path d="M5 5l10 10M15 5 5 15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export function Sidebar({ path, open, narrow = false, onNavigate, onClose, sidebarRef }: Props) {
  const active = activeNavId(path);
  const brand = (
    <a
      className="gestao-brand-link"
      href="/"
      onClick={(event) => {
        event.preventDefault();
        onNavigate("/");
      }}
    >
      <span className="gestao-brand-name">Gestão</span>
      <span className="gestao-brand-mark">Loja de Pães</span>
    </a>
  );
  return (
    <aside id="gestao-menu" className={open ? "gestao-side is-open" : "gestao-side"} ref={sidebarRef} hidden={!open}>
      {narrow ? (
        <div className="gestao-drawer-head">
          {brand}
          <button type="button" className="gestao-drawer-close" aria-label="Fechar menu" onClick={onClose}>
            <CloseIcon />
          </button>
        </div>
      ) : (
        brand
      )}
      <nav className="gestao-side-nav" aria-label="Menu da Gestão">
        {NAV_GROUPS.map((group) => (
          <div key={group.label} className="gestao-side-group">
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
                <span key={item.id} className="nl off" aria-disabled="true">
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
