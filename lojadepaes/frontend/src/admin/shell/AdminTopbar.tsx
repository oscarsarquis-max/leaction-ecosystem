import type { RefObject } from "react";
import { HeaderAccount } from "../../components/HeaderAccount";
import type { SessionInfo } from "../types";
import { Button } from "./Button";
import { trailFor } from "./nav";

type Props = {
  path: string;
  session: SessionInfo;
  trailDetail?: string | null;
  narrow: boolean;
  menuOpen: boolean;
  onToggleMenu: () => void;
  menuButtonRef: RefObject<HTMLButtonElement>;
};

export function AdminTopbar({ path, session, trailDetail, narrow, menuOpen, onToggleMenu, menuButtonRef }: Props) {
  const trail = trailFor(path);
  return (
    <header className="admin-topbar">
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
        {trail.group} <span aria-hidden="true">/</span> <strong>{trail.page}</strong>
        {trailDetail ? (
          <>
            {" "}
            <span aria-hidden="true">/</span> <span className="admin-trail-ref">{trailDetail}</span>
          </>
        ) : null}
      </p>
      <div className="admin-topbar-account admin-top-account">
        <HeaderAccount afterLogin="stay" initialSession={session} />
      </div>
    </header>
  );
}
