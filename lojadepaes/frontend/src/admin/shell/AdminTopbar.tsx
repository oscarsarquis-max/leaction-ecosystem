import { useEffect, useRef, useState, type RefObject } from "react";
import { HeaderAccount } from "../../components/HeaderAccount";
import { PushNotices } from "../PushNotices";
import type { SessionInfo } from "../types";
import { Button } from "./Button";
import { trailFor } from "./nav";

type Props = {
  path: string;
  session: SessionInfo;
  trailDetail?: string | null;
  narrow: boolean;
  menuOpen: boolean;
  noticesOpen: boolean;
  onToggleMenu: () => void;
  onToggleNotices: () => void;
  onNavigate: (href: string) => void;
  menuButtonRef: RefObject<HTMLButtonElement>;
};

function useMaxWidth(max: number): boolean {
  const query = `(max-width: ${max}px)`;
  const [matches, setMatches] = useState(() =>
    typeof window.matchMedia === "function" ? window.matchMedia(query).matches : false,
  );
  useEffect(() => {
    if (typeof window.matchMedia !== "function") {
      return;
    }
    const media = window.matchMedia(query);
    const apply = () => setMatches(media.matches);
    apply();
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, [query]);
  return matches;
}

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

function BellIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M10 21h4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function MenuIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <path d="M3 5h14M3 10h14M3 15h14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export function AdminTopbar({
  path,
  session,
  trailDetail,
  narrow,
  menuOpen,
  noticesOpen,
  onToggleMenu,
  onToggleNotices,
  onNavigate,
  menuButtonRef,
}: Props) {
  const trail = trailFor(path);
  const compactAccount = useMaxWidth(599);
  const bellRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!noticesOpen || menuOpen) {
      return;
    }
    function close() {
      onToggleNotices();
      bellRef.current?.focus();
    }
    function onKey(event: KeyboardEvent) {
      if (event.key !== "Escape") {
        return;
      }
      event.preventDefault();
      close();
    }
    function onPointer(event: MouseEvent) {
      const target = event.target;
      if (!(target instanceof Node)) {
        return;
      }
      if (panelRef.current?.contains(target) || bellRef.current?.contains(target)) {
        return;
      }
      close();
    }
    window.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onPointer);
    return () => {
      window.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onPointer);
    };
  }, [menuOpen, noticesOpen, onToggleNotices]);

  return (
    <header className="admin-topbar">
      <div className="admin-topbar-inner">
        <div className="admin-topbar-lead">
          {narrow ? (
            <Button
              ref={menuButtonRef}
              className="admin-menu-button"
              aria-label="Abrir menu"
              aria-expanded={menuOpen}
              aria-controls="admin-menu"
              onClick={onToggleMenu}
            >
              <MenuIcon />
            </Button>
          ) : null}
          <p className="admin-trail">
            {narrow ? null : (
              <>
                {trail.group} <span aria-hidden="true">/</span>{" "}
              </>
            )}
            <strong>{trail.page}</strong>
            {!narrow && trailDetail ? (
              <>
                {" "}
                <span aria-hidden="true">/</span> <span className="admin-trail-ref">{trailDetail}</span>
              </>
            ) : null}
          </p>
        </div>
        <div className="admin-topbar-actions">
          {narrow ? null : (
            <a
              className="admin-topbar-store"
              href="/"
              onClick={(event) => {
                event.preventDefault();
                onNavigate("/");
              }}
            >
              <ExternalIcon />
              Ver a loja
            </a>
          )}
          <div className="admin-topbar-bell-anchor">
            <button
              ref={bellRef}
              type="button"
              className="admin-notices-toggle admin-topbar-bell"
              aria-label="Notificações neste aparelho"
              aria-expanded={noticesOpen}
              aria-controls="admin-notices-panel"
              onClick={onToggleNotices}
            >
              <BellIcon />
            </button>
            {noticesOpen ? (
              <div ref={panelRef} id="admin-notices-panel" className="admin-notices-pop">
                <PushNotices />
              </div>
            ) : null}
          </div>
          <div className="admin-topbar-account admin-top-account">
            <HeaderAccount afterLogin="stay" initialSession={session} iconOnly={compactAccount} />
          </div>
        </div>
      </div>
    </header>
  );
}
