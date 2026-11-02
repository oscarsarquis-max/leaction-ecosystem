import type { RefObject } from "react";
import type { SessaoInfo } from "../lib/api";
import { Button } from "./Button";
import { trailFor } from "./nav";

type Props = {
  path: string;
  sessao: SessaoInfo;
  narrow: boolean;
  menuOpen: boolean;
  onToggleMenu: () => void;
  onSair: () => void;
  menuButtonRef: RefObject<HTMLButtonElement>;
};

const PAPEL: Record<string, string> = {
  dono: "Dono",
  operador: "Operador",
  somente_leitura: "Somente leitura",
};

function MenuIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <path d="M3 5h14M3 10h14M3 15h14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export function Topbar({ path, sessao, narrow, menuOpen, onToggleMenu, onSair, menuButtonRef }: Props) {
  const trail = trailFor(path);
  return (
    <header className="gestao-topbar">
      <div className="gestao-topbar-inner">
        <div className="gestao-topbar-lead">
          {narrow ? (
            <Button
              ref={menuButtonRef}
              className="gestao-menu-button"
              aria-label="Abrir menu"
              aria-expanded={menuOpen}
              aria-controls="gestao-menu"
              onClick={onToggleMenu}
            >
              <MenuIcon />
            </Button>
          ) : null}
          <p className="gestao-trail">
            {narrow ? null : (
              <>
                {trail.group} <span aria-hidden="true">/</span>{" "}
              </>
            )}
            <strong>{trail.page}</strong>
          </p>
        </div>
        <div className="gestao-topbar-actions">
          <p className="gestao-topbar-user">
            <span className="nome">{sessao.nome}</span>
            <span className="papel">{PAPEL[sessao.papel] ?? sessao.papel}</span>
          </p>
          <Button className="gestao-topbar-exit" onClick={onSair}>
            Sair
          </Button>
        </div>
      </div>
    </header>
  );
}
