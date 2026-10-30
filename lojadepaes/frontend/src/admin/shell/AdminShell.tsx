import { useEffect, useRef, useState, type ReactNode, type RefObject } from "react";
import type { SessionInfo } from "../types";
import { AdminSidebar } from "./AdminSidebar";
import { AdminTopbar } from "./AdminTopbar";
import "./shell.css";
import "./tokens.css";

type Props = {
  path: string;
  onNavigate: (to: string) => void;
  session: SessionInfo;
  noticesOpen: boolean;
  onToggleNotices: () => void;
  trailDetail?: string | null;
  children: ReactNode;
};

function useNarrow(): boolean {
  const query = "(max-width: 959px)";
  const [narrow, setNarrow] = useState(() =>
    typeof window.matchMedia === "function" ? window.matchMedia(query).matches : false,
  );
  useEffect(() => {
    if (typeof window.matchMedia !== "function") {
      return;
    }
    const media = window.matchMedia(query);
    const apply = () => setNarrow(media.matches);
    apply();
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, []);
  return narrow;
}

function focusable(root: HTMLElement): HTMLElement[] {
  return [
    ...root.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  ].filter((node) => !node.hasAttribute("disabled") && node.tabIndex !== -1);
}

function trapTab(event: KeyboardEvent, root: HTMLElement) {
  if (event.key !== "Tab") {
    return;
  }
  const items = focusable(root);
  if (items.length === 0) {
    return;
  }
  const first = items[0];
  const last = items[items.length - 1];
  const active = document.activeElement;
  if (event.shiftKey && (active === first || !root.contains(active))) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && active === last) {
    event.preventDefault();
    first.focus();
  }
}

export function AdminShell({
  path,
  onNavigate,
  session,
  noticesOpen,
  onToggleNotices,
  trailDetail,
  children,
}: Props) {
  const narrow = useNarrow();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const sidebarRef = useRef<HTMLElement>(null);
  const drawerOpen = !narrow || menuOpen;

  function closeDrawer(restoreFocus: boolean) {
    setMenuOpen(false);
    if (restoreFocus) {
      menuButtonRef.current?.focus();
    }
  }

  function navigate(href: string) {
    onNavigate(href);
    if (narrow) {
      closeDrawer(true);
    }
  }

  useEffect(() => {
    if (!narrow || !menuOpen) {
      return;
    }
    const root = sidebarRef.current;
    if (!root) {
      return;
    }
    const close = root.querySelector<HTMLElement>(".admin-drawer-close");
    (close ?? focusable(root)[0])?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setMenuOpen(false);
        menuButtonRef.current?.focus();
        return;
      }
      trapTab(event, root);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [narrow, menuOpen]);

  return (
    <div className="admin-frame">
      <a className="admin-skip" href="#admin-conteudo">
        Pular para o conteúdo
      </a>
      <div className="admin-frame-body">
        {narrow && menuOpen ? (
          <button type="button" className="admin-backdrop" aria-label="Fechar menu" onClick={() => closeDrawer(true)} />
        ) : null}
        <AdminSidebar
          path={path}
          open={drawerOpen}
          narrow={narrow}
          onNavigate={navigate}
          onClose={() => closeDrawer(true)}
          sidebarRef={sidebarRef as RefObject<HTMLElement>}
        />
        <div className="admin-frame-main">
          <AdminTopbar
            path={path}
            session={session}
            trailDetail={trailDetail}
            narrow={narrow}
            menuOpen={menuOpen}
            noticesOpen={noticesOpen}
            onToggleMenu={() => setMenuOpen((open) => !open)}
            onToggleNotices={onToggleNotices}
            onNavigate={navigate}
            menuButtonRef={menuButtonRef as RefObject<HTMLButtonElement>}
          />
          <div id="admin-conteudo" className="admin-page admin-frame-content" tabIndex={-1}>
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}
