'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { MessageCircle, X } from 'lucide-react';
import { getHubApiBase } from '@/lib/hub-api';
import {
  ASSISTENTE_SEED_COMERCIAL_PUBLICO,
  type AssistenteTree,
  type AssistenteTreeOption,
} from '@/lib/cms-assistente-seed-comercial-publico';
import './comeco-assistente.css';

export const COMECO_OPEN_COMERCIAL_EVENT = 'comeco:open-comercial';

type TreePayload = {
  tree?: AssistenteTree;
  error?: string;
};

function isExternalHref(href: string): boolean {
  return /^https?:\/\//i.test(href);
}

/** FAB + painel — assistente comercial CMS (`comercial_publico`). Sem avatar / sem LLM. */
export function ComecoAssistenteComercial() {
  const [open, setOpen] = useState(false);
  const [tree, setTree] = useState<AssistenteTree | null>(null);
  const [nodeId, setNodeId] = useState('inicio');
  const [loadError, setLoadError] = useState('');
  const [loading, setLoading] = useState(false);

  const loadTree = useCallback(async () => {
    setLoading(true);
    setLoadError('');
    try {
      const base = getHubApiBase();
      const res = await fetch(
        `${base}/api/cms/assistente-chat?sistema_destino=comercial_publico`,
        { headers: { Accept: 'application/json' }, cache: 'no-store' }
      );
      if (res.ok) {
        const data = (await res.json()) as TreePayload;
        if (data?.tree?.nodes && data.tree.root_id) {
          setTree(data.tree);
          setNodeId(data.tree.root_id);
          return;
        }
      }
      // Fallback local se CMS ainda não publicou
      setTree(ASSISTENTE_SEED_COMERCIAL_PUBLICO);
      setNodeId(ASSISTENTE_SEED_COMERCIAL_PUBLICO.root_id);
      if (!res.ok && res.status !== 404) {
        setLoadError('Usando guia local — CMS indisponível no momento.');
      }
    } catch {
      setTree(ASSISTENTE_SEED_COMERCIAL_PUBLICO);
      setNodeId(ASSISTENTE_SEED_COMERCIAL_PUBLICO.root_id);
      setLoadError('Usando guia local — não foi possível alcançar a API.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    function onOpen() {
      setOpen(true);
    }
    window.addEventListener(COMECO_OPEN_COMERCIAL_EVENT, onOpen);
    return () => window.removeEventListener(COMECO_OPEN_COMERCIAL_EVENT, onOpen);
  }, []);

  useEffect(() => {
    if (!open) return;
    if (tree) return;
    void loadTree();
  }, [open, tree, loadTree]);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false);
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  const node = tree?.nodes?.[nodeId] || null;
  const title = tree?.avatar_name || 'Comercial';
  const tagline = tree?.avatar_tagline || 'Contratação e primeiros passos';

  function handleOption(opt: AssistenteTreeOption) {
    if (!opt) return;
    const href = String(opt.href || '').trim();
    if (href) {
      if (isExternalHref(href)) {
        window.open(href, '_blank', 'noopener,noreferrer');
        if (opt.next && tree?.nodes?.[opt.next]) setNodeId(opt.next);
        return;
      }
      if (href.startsWith('/')) {
        setOpen(false);
        window.location.assign(href);
        return;
      }
    }
    if (opt.next && tree?.nodes?.[opt.next]) {
      setNodeId(opt.next);
    }
  }

  function openPanel() {
    setOpen(true);
  }

  return (
    <>
      <button
        type="button"
        className="comeco-asst-fab"
        onClick={openPanel}
        aria-label="Abrir assistente comercial"
      >
        <MessageCircle className="size-5" aria-hidden />
        <span>Comercial</span>
      </button>

      {open ? (
        <div
          className="comeco-asst-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="comeco-asst-title"
          onClick={(e) => {
            if (e.target === e.currentTarget) setOpen(false);
          }}
        >
          <div className="comeco-asst-panel">
            <header className="comeco-asst-header">
              <div>
                <p className="comeco-asst-kicker">Pré-venda</p>
                <h2 id="comeco-asst-title">{title}</h2>
                <p className="comeco-asst-tagline">{tagline}</p>
              </div>
              <button
                type="button"
                className="comeco-asst-close"
                onClick={() => setOpen(false)}
                aria-label="Fechar"
              >
                <X className="size-4" aria-hidden />
              </button>
            </header>

            <div className="comeco-asst-body">
              {loading && !node ? (
                <p className="comeco-asst-muted">Carregando guia…</p>
              ) : null}
              {loadError ? <p className="comeco-asst-hint">{loadError}</p> : null}
              {node ? (
                <div className="comeco-asst-message">
                  <p>{node.message}</p>
                </div>
              ) : null}
            </div>

            <div className="comeco-asst-options">
              {(node?.options || []).map((opt) => {
                const key = `${opt.label}-${opt.next || ''}-${opt.href || ''}`;
                const href = String(opt.href || '').trim();
                if (href.startsWith('/') && !opt.next) {
                  return (
                    <Link
                      key={key}
                      href={href}
                      className="comeco-asst-option"
                      onClick={() => setOpen(false)}
                    >
                      {opt.label}
                    </Link>
                  );
                }
                return (
                  <button
                    key={key}
                    type="button"
                    className="comeco-asst-option"
                    onClick={() => handleOption(opt)}
                  >
                    {opt.label}
                  </button>
                );
              })}
              {tree && nodeId !== tree.root_id ? (
                <button
                  type="button"
                  className="comeco-asst-option comeco-asst-option-ghost"
                  onClick={() => setNodeId(tree.root_id)}
                >
                  Voltar ao início
                </button>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}

export function openComecoAssistenteComercial() {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new Event(COMECO_OPEN_COMERCIAL_EVENT));
}
