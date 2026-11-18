import type { RefObject } from "react";
import type { Etapa, SessaoInfo } from "../lib/api";
import { PAPEIS } from "../lib/format";
import { Button } from "./Button";
import { Marca } from "./Marca";
import { Ponto } from "./Ponto";
import { ETAPAS_BASE, GESTAO_ITENS, activeNavId } from "./nav";

type Props = {
  path: string;
  open: boolean;
  narrow?: boolean;
  etapas: Etapa[] | null;
  sessao: SessaoInfo;
  onNavigate: (href: string) => void;
  onClose?: () => void;
  onSair: () => void;
  onTrocarOrganizacao: (id: string) => void;
  sidebarRef: RefObject<HTMLElement>;
};

function CloseIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <path d="M5 5l10 10M15 5 5 15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export function Sidebar({
  path,
  open,
  narrow = false,
  etapas,
  sessao,
  onNavigate,
  onClose,
  onSair,
  onTrocarOrganizacao,
  sidebarRef,
}: Props) {
  const active = activeNavId(path);
  const lista = etapas ?? ETAPAS_BASE;
  const permissoes = sessao.permissoes;
  const brand = (
    <a
      className="gestao-brand-link"
      href="/"
      aria-label="Loja de Pães · Gestão: ir para Hoje"
      onClick={(event) => {
        event.preventDefault();
        onNavigate("/");
      }}
    >
      <Marca altura={40} />
      <span className="gestao-brand-sub">Gestão</span>
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
        <div className="gestao-side-group">
          <a
            className={active === "hoje" ? "nl on" : "nl"}
            href="/"
            aria-current={active === "hoje" ? "page" : undefined}
            onClick={(event) => {
              event.preventDefault();
              onNavigate("/");
            }}
          >
            <span className="nl-nome">Hoje</span>
          </a>
        </div>

        <div className="gestao-side-group">
          <p className="ng">Fluxo da padaria</p>
          {lista.map((etapa, indice) => {
            const conteudo = (
              <>
                <span className="etapa-num" aria-hidden="true">
                  {indice + 1}
                </span>
                <span className="etapa-txt">
                  <span className="etapa-linha">
                    <span className="etapa-nome">{etapa.nome}</span>
                    {etapa.href ? null : <span className="soon">em breve</span>}
                  </span>
                  <span className="etapa-frase">{etapa.href ? etapa.frase || etapa.pergunta : etapa.pergunta}</span>
                </span>
                <Ponto estado={etapa.estado} />
              </>
            );
            return etapa.href ? (
              <a
                key={etapa.id}
                className={active === etapa.id ? "nl etapa on" : "nl etapa"}
                href={etapa.href}
                aria-current={active === etapa.id ? "page" : undefined}
                onClick={(event) => {
                  event.preventDefault();
                  onNavigate(etapa.href!);
                }}
              >
                {conteudo}
              </a>
            ) : (
              <span key={etapa.id} className="nl etapa off" aria-disabled="true">
                {conteudo}
              </span>
            );
          })}
        </div>

        <div className="gestao-side-group">
          <p className="ng">Gestão</p>
          {GESTAO_ITENS.filter((i) => !i.permissao || permissoes.includes(i.permissao)).map((item) =>
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
                <span className="nl-nome">{item.label}</span>
              </a>
            ) : (
              <span key={item.id} className="nl off" aria-disabled="true">
                <span className="nl-nome">{item.label}</span>
                <span className="soon">em breve</span>
              </span>
            ),
          )}
        </div>
      </nav>

      {narrow ? (
        <div className="gestao-side-foot">
          <p className="foot-pessoa">
            <strong>{sessao.nome}</strong>
            <span>{sessao.papel ? (PAPEIS[sessao.papel] ?? sessao.papel) : "Admin da plataforma"}</span>
          </p>
          {sessao.organizacoes.length > 1 ? (
            <div className="foot-orgs" role="group" aria-label="Trocar de organização">
              <p className="ng">Organização</p>
              {sessao.organizacoes.map((org) => (
                <button
                  key={org.id}
                  type="button"
                  className={org.id === sessao.organizacao?.id ? "nl on" : "nl"}
                  aria-pressed={org.id === sessao.organizacao?.id}
                  onClick={() => onTrocarOrganizacao(org.id)}
                >
                  <span className="nl-nome">{org.nome}</span>
                </button>
              ))}
            </div>
          ) : null}
          <Button className="foot-sair" onClick={onSair}>
            Sair
          </Button>
        </div>
      ) : null}
    </aside>
  );
}
