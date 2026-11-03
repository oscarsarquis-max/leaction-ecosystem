import { useEffect, useRef, useState, type RefObject } from "react";
import type { Etapa, SessaoInfo } from "../lib/api";
import { PAPEIS } from "../lib/format";
import { Button } from "./Button";
import { Marca } from "./Marca";
import { Ponto } from "./Ponto";
import { ETAPAS_BASE, activeNavId, trailFor } from "./nav";

type Props = {
  path: string;
  sessao: SessaoInfo;
  etapas: Etapa[] | null;
  narrow: boolean;
  menuOpen: boolean;
  onToggleMenu: () => void;
  onSair: () => void;
  onTrocarOrganizacao: (id: string) => void;
  menuButtonRef: RefObject<HTMLButtonElement>;
};

function Chevron() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      <path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

/** Nome da organização e CNPJ lado a lado (no celular, o CNPJ vai para uma segunda linha e nunca é cortado). */
export function OrganizacaoNaBarra({ sessao }: { sessao: SessaoInfo }) {
  const org = sessao.organizacao;
  if (!org) return null;
  return (
    <p className="gestao-topbar-org" aria-label="Organização atual">
      <span className="org-nome">{org.nome}</span>
      <span className="org-sep" aria-hidden="true">
        ·
      </span>
      <span className="org-cnpj">CNPJ {org.cnpj_formatado}</span>
    </p>
  );
}

export function MenuDaPessoa({
  sessao,
  onSair,
  onTrocarOrganizacao,
}: Pick<Props, "sessao" | "onSair" | "onTrocarOrganizacao">) {
  const [aberto, setAberto] = useState(false);
  const raiz = useRef<HTMLDivElement>(null);
  const botao = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!aberto) return;
    const fora = (event: MouseEvent) => {
      if (raiz.current && !raiz.current.contains(event.target as Node)) setAberto(false);
    };
    const tecla = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setAberto(false);
        botao.current?.focus();
      }
    };
    document.addEventListener("mousedown", fora);
    document.addEventListener("keydown", tecla);
    return () => {
      document.removeEventListener("mousedown", fora);
      document.removeEventListener("keydown", tecla);
    };
  }, [aberto]);

  const papel = sessao.papel ? (PAPEIS[sessao.papel] ?? sessao.papel) : "Admin da plataforma";
  return (
    <div className="gestao-pessoa" ref={raiz}>
      <button
        ref={botao}
        type="button"
        className="gestao-pessoa-botao"
        aria-haspopup="menu"
        aria-expanded={aberto}
        onClick={() => setAberto((v) => !v)}
      >
        <span className="gestao-topbar-user">
          <span className="nome">{sessao.nome}</span>
          <span className="papel">{papel}</span>
        </span>
        <Chevron />
      </button>
      {aberto ? (
        <div className="gestao-pessoa-menu" role="menu" aria-label="Menu da pessoa">
          {sessao.organizacoes.length > 1 ? (
            <>
              <p className="ng">Trocar de organização</p>
              {sessao.organizacoes.map((org) => (
                <button
                  key={org.id}
                  type="button"
                  role="menuitemradio"
                  aria-checked={org.id === sessao.organizacao?.id}
                  className="item"
                  onClick={() => {
                    setAberto(false);
                    if (org.id !== sessao.organizacao?.id) onTrocarOrganizacao(org.id);
                  }}
                >
                  <span>{org.nome}</span>
                  <span className="sub">CNPJ {org.cnpj_formatado}</span>
                </button>
              ))}
              <hr />
            </>
          ) : null}
          <button type="button" role="menuitem" className="item" onClick={onSair}>
            Sair
          </button>
        </div>
      ) : null}
    </div>
  );
}

export function Topbar({
  path,
  sessao,
  etapas,
  narrow,
  menuOpen,
  onToggleMenu,
  onSair,
  onTrocarOrganizacao,
  menuButtonRef,
}: Props) {
  const trail = trailFor(path);
  const id = activeNavId(path);
  const etapa = (etapas ?? ETAPAS_BASE).find((e) => e.id === id) ?? null;

  if (narrow) {
    return (
      <header className="gestao-topbar is-narrow">
        <div className="gestao-topbar-inner">
          <div className="gestao-topbar-lead">
            <Marca altura={32} className="gestao-logo-topbar" />
            <Button
              ref={menuButtonRef}
              className="gestao-etapa-botao"
              aria-label={`${trail.page}. Abrir a lista de etapas`}
              aria-expanded={menuOpen}
              aria-controls="gestao-menu"
              onClick={onToggleMenu}
            >
              {etapa ? <Ponto estado={etapa.estado} /> : null}
              <span className="etapa-botao-nome">{trail.page}</span>
              <Chevron />
            </Button>
          </div>
        </div>
        <OrganizacaoNaBarra sessao={sessao} />
      </header>
    );
  }

  return (
    <header className="gestao-topbar">
      <div className="gestao-topbar-inner">
        <div className="gestao-topbar-lead">
          <p className="gestao-trail">
            {trail.group} <span aria-hidden="true">/</span> <strong>{trail.page}</strong>
          </p>
        </div>
        <div className="gestao-topbar-actions">
          <OrganizacaoNaBarra sessao={sessao} />
          <MenuDaPessoa sessao={sessao} onSair={onSair} onTrocarOrganizacao={onTrocarOrganizacao} />
        </div>
      </div>
    </header>
  );
}
