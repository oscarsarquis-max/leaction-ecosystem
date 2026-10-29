import type { RefObject } from "react";
import { HeaderAccount } from "../../components/HeaderAccount";
import { PushNotices } from "../PushNotices";
import type { SessionInfo } from "../types";
import { Button } from "./Button";
import { Card } from "./Card";
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

function ExternalIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M14 5h5v5M19 5 10 14"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M19 13v5a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
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
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M10 21h4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
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
  return (
    <header className="admin-topbar">
      <div className="admin-topbar-lead">
        {narrow ? (
          <Button
            ref={menuButtonRef}
            className="admin-menu-button"
            aria-expanded={menuOpen}
            aria-controls="admin-menu"
            onClick={onToggleMenu}
          >
            Menu
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
        <button
          type="button"
          className="admin-notices-toggle admin-topbar-bell"
          aria-label="Notificações neste aparelho"
          aria-expanded={noticesOpen}
          aria-controls="admin-notices-panel"
          onClick={onToggleNotices}
        >
          <BellIcon />
        </button>
        <div className="admin-topbar-account admin-top-account">
          <HeaderAccount afterLogin="stay" initialSession={session} />
        </div>
        {noticesOpen ? (
          <Card className="admin-notices-pop">
            <div id="admin-notices-panel">
              <PushNotices />
            </div>
          </Card>
        ) : null}
      </div>
    </header>
  );
}
