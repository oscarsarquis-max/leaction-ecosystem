import { useEffect, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import "./tokens.css";

const FOCAVEIS =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

const pilhaModal: symbol[] = [];

/**
 * Diálogo único do sistema: sobreposição, no centro (tela cheia no celular),
 * foco preso, Esc fecha, e o tema vai junto porque o portal carrega .gestao-frame.
 */
export function Modal({
  titulo,
  subtitulo,
  onFechar,
  children,
  rodape,
}: {
  titulo: string;
  subtitulo?: string;
  onFechar: () => void;
  children: ReactNode;
  rodape?: ReactNode;
}) {
  const raiz = useRef<HTMLDivElement>(null);
  const token = useRef(Symbol("modal"));
  const fecharAtual = useRef(onFechar);
  fecharAtual.current = onFechar;

  useEffect(() => {
    const id = token.current;
    pilhaModal.push(id);
    return () => {
      const indice = pilhaModal.lastIndexOf(id);
      if (indice >= 0) pilhaModal.splice(indice, 1);
    };
  }, []);

  useEffect(() => {
    const anterior = document.activeElement as HTMLElement | null;
    raiz.current?.focus();
    return () => anterior?.focus?.();
  }, []);

  useEffect(() => {
    const aoTeclar = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        if (pilhaModal[pilhaModal.length - 1] !== token.current) return;
        event.preventDefault();
        event.stopPropagation();
        fecharAtual.current();
        return;
      }
      if (event.key !== "Tab" || !raiz.current) return;
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
    };
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [onFechar]);

  return createPortal(
    <div
      className="gestao-frame gestao-modal"
      role="dialog"
      aria-modal="true"
      aria-label={titulo}
      ref={raiz}
      tabIndex={-1}
      style={{ position: "fixed", top: 0, right: 0, bottom: 0, left: 0 }}
    >
      {/* O fundo fecha no clique. Esc e o botão Fechar cobrem o teclado. */}
      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions */}
      <div className="gestao-modal-fundo" onClick={onFechar} />
      <div className="gestao-modal-caixa">
        <header className="gestao-modal-cab">
          <div>
            <h2>{titulo}</h2>
            {subtitulo ? <p>{subtitulo}</p> : null}
          </div>
          <button type="button" className="painel-fechar" aria-label="Fechar" onClick={onFechar}>
            <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
              <path d="M5 5l10 10M15 5 5 15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </button>
        </header>
        <div className="gestao-modal-corpo">{children}</div>
        {rodape ? <footer className="gestao-modal-rodape">{rodape}</footer> : null}
      </div>
    </div>,
    document.body,
  );
}
