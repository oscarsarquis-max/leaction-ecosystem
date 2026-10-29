import type { RefObject } from "react";
import { NAV_GROUPS, activeNavId } from "./nav";

type Props = {
  path: string;
  open: boolean;
  narrow?: boolean;
  onNavigate: (href: string) => void;
  sidebarRef: RefObject<HTMLElement>;
};

export function AdminSidebar({ path, open, narrow = false, onNavigate, sidebarRef }: Props) {
  const active = activeNavId(path);
  return (
    <aside id="admin-menu" className={open ? "admin-side is-open" : "admin-side"} ref={sidebarRef} hidden={!open}>
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
      {narrow ? (
        <a
          className="nl admin-drawer-store"
          href="/"
          onClick={(event) => {
            event.preventDefault();
            onNavigate("/");
          }}
        >
          Ver a loja
        </a>
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
