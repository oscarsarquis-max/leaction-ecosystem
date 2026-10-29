import { useEffect, useRef, useState } from "react";
import { fetchBuilderTip, type BuilderTip } from "./builderApi";
import { compositionReady, describeTipChanges, openGigioWithBuilder, tipCacheKey } from "./proposal";
import type { BreadBuilderState } from "./state";

type Props = {
  state: BreadBuilderState;
  enabled: boolean;
  onApply: (tip: BuilderTip) => void;
};

const cache = new Map<string, BuilderTip>();

export function clearGigioTipCache(): void {
  cache.clear();
}

export function GigioLoafTip({ state, enabled, onApply }: Props) {
  const [tip, setTip] = useState<BuilderTip | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const requestRef = useRef(0);
  const key = tipCacheKey(state);
  const canAnalyze = enabled && compositionReady(state) && Boolean(state.shapeId) && !state.finished;
  const visible = enabled && compositionReady(state) && !state.finished;
  const boxRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!canAnalyze) {
      return;
    }
    const cached = cache.get(key);
    if (cached) {
      setTip(cached);
      setError(null);
      setBusy(false);
      return;
    }
    setTip(null);
    setError(null);
    const requestId = ++requestRef.current;
    const timer = window.setTimeout(() => {
      setBusy(true);
      setError(null);
      fetchBuilderTip({
        flour_id: state.flourId,
        dough_id: state.massId,
        ingredient_ids: state.extraIds,
        shape_id: state.shapeId,
        free_text: state.freeText,
      })
        .then((payload) => {
          if (requestRef.current !== requestId) return;
          cache.set(key, payload);
          setTip(payload);
          setBusy(false);
        })
        .catch(() => {
          if (requestRef.current !== requestId) return;
          setTip(null);
          setBusy(false);
          setError("Não consegui montar a dica agora.");
        });
    }, 700);
    return () => window.clearTimeout(timer);
  }, [canAnalyze, key, state.flourId, state.massId, state.shapeId, state.extraIds, state.freeText]);

  useEffect(() => {
    if (!tip || !boxRef.current) {
      return;
    }
    boxRef.current.scrollIntoView?.({ block: "nearest", inline: "nearest" });
  }, [tip]);

  if (!visible) {
    return null;
  }

  if (!state.shapeId) {
    return (
      <aside className="gigio-loaf-tip" aria-live="polite">
        <p className="gigio-loaf-tip-kicker">Uma dica do Gigio para o seu pão</p>
        <p>Escolha o formato acima para o Gigio comentar a combinação que você montou.</p>
      </aside>
    );
  }

  function refresh() {
    cache.delete(key);
    setTip(null);
    setError(null);
    const requestId = ++requestRef.current;
    setBusy(true);
    fetchBuilderTip({
      flour_id: state.flourId,
      dough_id: state.massId,
      ingredient_ids: state.extraIds,
      shape_id: state.shapeId,
      free_text: state.freeText,
    })
      .then((payload) => {
        if (requestRef.current !== requestId) return;
        cache.set(key, payload);
        setTip(payload);
        setBusy(false);
      })
      .catch(() => {
        if (requestRef.current !== requestId) return;
        setBusy(false);
        setError("Não consegui montar a dica agora.");
      });
  }

  return (
    <aside ref={boxRef} className="gigio-loaf-tip" aria-live="polite">
      <p className="gigio-loaf-tip-kicker">Uma dica do Gigio para o seu pão</p>
      {busy && !tip ? <p>Gigio está olhando a sua massa…</p> : null}
      {error ? (
        <p>
          {error} Você pode continuar com o seu pão.
          <button type="button" className="text-button" onClick={refresh}>
            Tentar novamente
          </button>
        </p>
      ) : null}
      {tip ? (
        <>
          <p>{tip.observation}</p>
          <p>{tip.serving}</p>
          {tip.suggestion ? (
            <div className="gigio-loaf-tip-apply">
              <p>
                <strong>{tip.suggestion.label}</strong>
                {describeTipChanges(tip) ? ` ${describeTipChanges(tip)}` : ""}
              </p>
              <button type="button" className="text-button" onClick={() => onApply(tip)}>
                Aplicar sugestão
              </button>
            </div>
          ) : null}
          {tip.cta?.href && tip.cta.label ? (
            <a className="gigio-loaf-tip-cta" href={tip.cta.href}>
              {tip.cta.label}
            </a>
          ) : null}
          {tip.notice ? <p className="gigio-loaf-tip-note">{tip.notice}</p> : null}
        </>
      ) : null}
      <div className="gigio-loaf-tip-actions">
        <button
          type="button"
          className="text-button"
          onClick={() =>
            openGigioWithBuilder({
              flour: state.flourName,
              preparation: state.massName,
              inclusions: state.extraNames,
              shape: state.shapeName,
              note: state.freeText,
            })
          }
        >
          Conversar com o Gigio
        </button>
        {tip ? (
          <button type="button" className="text-button" onClick={refresh} disabled={busy}>
            Pedir nova dica
          </button>
        ) : null}
      </div>
    </aside>
  );
}
