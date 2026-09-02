'use client';

import { useEffect, useId, useRef, useState } from 'react';
import { MessageCircle, X } from 'lucide-react';

export const PANNE_OPEN_COMERCIAL_EVENT = 'panne:open-comercial';

/** Mesmo destino comercial já usado no Action Hub (página /inove4us). */
const CANAL_COMERCIAL = 'https://wa.me/5585999031861';

type View = 'inicio' | 'como-funciona' | 'para-quem' | 'demo' | 'comercial';

const HOME_OPTIONS: { view: Exclude<View, 'inicio'>; label: string }[] = [
  { view: 'como-funciona', label: 'Como funciona?' },
  { view: 'para-quem', label: 'Para quem é?' },
  { view: 'demo', label: 'O que consigo testar na Demo?' },
  { view: 'comercial', label: 'Como falar com o comercial?' },
];

const ANSWERS: Record<Exclude<View, 'inicio' | 'comercial'>, string> = {
  'como-funciona':
    'A Panne percorre um só caminho: compras e entradas, estoque, produtos, receitas técnicas, planejamento, preparo, acabamento e conformidade, até custos e preços. Cada etapa alimenta a seguinte — a operação deixa de ser um conjunto de planilhas soltas.',
  'para-quem':
    'Proprietário, produção, formulador, compras, regulatório e comercial usam o mesmo fluxo, cada um no recorte da sua decisão. Na página você escolhe o perfil e vê o que acompanha, o que decide e onde atua.',
  demo: 'A demonstração usa dados sintéticos, identificados como exemplo. Você percorre a jornada completa — da entrada conferida ao produto — sem documentos reais da Fazenda e sem dados de clientes.',
};

export function PanneAssistenteComercial() {
  const [open, setOpen] = useState(false);
  const [view, setView] = useState<View>('inicio');
  const [canDismiss, setCanDismiss] = useState(false);
  const fabRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useId();

  function openPanel() {
    setView('inicio');
    setCanDismiss(false);
    setOpen(true);
  }

  function close() {
    setOpen(false);
    setView('inicio');
    setCanDismiss(false);
    requestAnimationFrame(() => fabRef.current?.focus());
  }

  useEffect(() => {
    function onOpen() {
      openPanel();
    }
    window.addEventListener(PANNE_OPEN_COMERCIAL_EVENT, onOpen);
    return () => window.removeEventListener(PANNE_OPEN_COMERCIAL_EVENT, onOpen);
  }, []);

  useEffect(() => {
    if (!open) return undefined;
    panelRef.current?.focus();

    function armDismiss() {
      setCanDismiss(true);
    }
    const timer = window.setTimeout(armDismiss, 250);
    window.addEventListener('pointerup', armDismiss, { once: true });

    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        close();
      }
    }
    window.addEventListener('keydown', onKey);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener('pointerup', armDismiss);
      window.removeEventListener('keydown', onKey);
    };
  }, [open]);

  return (
    <>
      <button
        ref={fabRef}
        type="button"
        className={`panne-asst-fab${open ? ' is-hidden' : ''}`}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          openPanel();
        }}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls="panne-asst-dialog"
      >
        <MessageCircle className="size-4" aria-hidden />
        Falar sobre a Panne
      </button>

      {open ? (
        <div
          className="panne-asst-overlay"
          onPointerDown={(e) => {
            if (!canDismiss) return;
            if (e.target === e.currentTarget) close();
          }}
        >
          <div
            ref={panelRef}
            id="panne-asst-dialog"
            className="panne-asst-panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            tabIndex={-1}
            onPointerDown={(e) => e.stopPropagation()}
          >
            <header className="panne-asst-header">
              <div>
                <p className="panne-asst-kicker">Atendimento comercial</p>
                <h2 id={titleId}>Panne</h2>
              </div>
              <button type="button" className="panne-asst-close" onClick={close} aria-label="Fechar">
                <X className="size-4" aria-hidden />
              </button>
            </header>

            <div className="panne-asst-body">
              {view === 'inicio' ? (
                <p className="panne-asst-message">Olá. Posso ajudar você a entender a Panne.</p>
              ) : null}
              {view === 'como-funciona' || view === 'para-quem' || view === 'demo' ? (
                <p className="panne-asst-message">{ANSWERS[view]}</p>
              ) : null}
              {view === 'comercial' ? (
                <p className="panne-asst-message">
                  O canal comercial do Action Hub é o WhatsApp. Use o botão abaixo para continuar a
                  conversa por lá.
                </p>
              ) : null}
            </div>

            <div className="panne-asst-options">
              {view === 'inicio'
                ? HOME_OPTIONS.map((opt) => (
                    <button
                      key={opt.view}
                      type="button"
                      className="panne-asst-option"
                      onClick={() => setView(opt.view)}
                    >
                      {opt.label}
                    </button>
                  ))
                : null}

              {view === 'comercial' ? (
                <a
                  className="panne-asst-option panne-asst-option-primary"
                  href={CANAL_COMERCIAL}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Abrir canal comercial
                </a>
              ) : null}

              {view !== 'inicio' ? (
                <button
                  type="button"
                  className="panne-asst-option panne-asst-option-ghost"
                  onClick={() => setView('inicio')}
                >
                  Voltar
                </button>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}

export function openPanneAssistenteComercial() {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new Event(PANNE_OPEN_COMERCIAL_EVENT));
}
