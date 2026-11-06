import { useEffect, useRef, type ReactNode } from "react";

type Props = {
  titulo: string;
  subtitulo?: string;
  onFechar: () => void;
  children: ReactNode;
  rodape?: ReactNode;
  largo?: boolean;
};

const FOCAVEIS =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Painel de detalhe: ao lado da lista no computador, tela cheia no celular.
 * Foco vai para o painel ao abrir, Esc fecha, e o foco volta para quem abriu.
 */
export function SidePanel({ titulo, subtitulo, onFechar, children, rodape, largo = false }: Props) {
  const raiz = useRef<HTMLElement>(null);
  const fechar = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const anterior = document.activeElement as HTMLElement | null;
    fechar.current?.focus();
    return () => anterior?.focus?.();
  }, []);

  useEffect(() => {
    const aoTeclar = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        onFechar();
        return;
      }
      if (event.key === "Tab" && raiz.current && window.matchMedia?.("(max-width: 959px)").matches) {
        const itens = [...raiz.current.querySelectorAll<HTMLElement>(FOCAVEIS)];
        if (itens.length === 0) return;
        const primeiro = itens[0];
        const ultimo = itens[itens.length - 1];
        const ativo = document.activeElement;
        if (event.shiftKey && (ativo === primeiro || !raiz.current.contains(ativo))) {
          event.preventDefault();
          ultimo.focus();
        } else if (!event.shiftKey && ativo === ultimo) {
          event.preventDefault();
          primeiro.focus();
        }
      }
    };
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [onFechar]);

  return (
    <aside className={largo ? "gestao-painel gigio-largo" : "gestao-painel"} role="dialog" aria-modal="true" aria-label={titulo} ref={raiz}>
      <header className="painel-cab">
        <div className="painel-titulos">
          <h2>{titulo}</h2>
          {subtitulo ? <p>{subtitulo}</p> : null}
        </div>
        <button ref={fechar} type="button" className="painel-fechar" aria-label="Fechar" onClick={onFechar}>
          <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
            <path d="M5 5l10 10M15 5 5 15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </button>
      </header>
      <div className="painel-corpo">{children}</div>
      {rodape ? <footer className="painel-rodape">{rodape}</footer> : null}
    </aside>
  );
}
