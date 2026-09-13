import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { ApiClientError } from '../api/errors';
import { fetchPublicContextLink, type PublicContextEnvelope } from '../api/publicContext';
import ContextSummary from '../components/ContextSummary';
import HumanStatus from '../components/HumanStatus';
import PublicShell from '../components/PublicShell';
import PublicTransparency from '../components/PublicTransparency';
import PublicProgressiveJourney from './PublicProgressiveJourney';
import {
  CONTEXT_FALLBACK_SUMMARY,
  formatValidityPtBr,
  PUBLIC_EXPIRED,
  PUBLIC_LOADING,
  PUBLIC_NETWORK,
  PUBLIC_NOT_FOUND,
  PUBLIC_REVOKED,
  PUBLIC_TEMPORARY,
  PUBLIC_TERMINAL,
  purposeFromCallToAction,
} from '../i18n/human';
import { materializeContextSummary } from './materializeSummary';
import { isOpaqueTokenShape } from './tokenShape';

type PublicView =
  | { status: 'loading' }
  | { status: 'ready'; envelope: PublicContextEnvelope }
  | { status: 'not-found' }
  | { status: 'revoked' }
  | { status: 'expired' }
  | { status: 'terminal' }
  | { status: 'temporary' }
  | { status: 'network' };

function mapError(error: unknown): PublicView {
  if (!(error instanceof ApiClientError)) {
    return { status: 'network' };
  }
  if (error.status === 404) {
    return { status: 'not-found' };
  }
  if (error.status === 503) {
    return { status: 'temporary' };
  }
  if (error.status === 410 && error.code === 'CONTEXT_LINK_REVOKED') {
    return { status: 'revoked' };
  }
  if (error.status === 410 && error.code === 'CONTEXT_LINK_EXPIRED') {
    return { status: 'expired' };
  }
  if (error.status === 410) {
    return { status: 'terminal' };
  }
  return { status: 'network' };
}

export default function PublicInvitePage() {
  const token = useParams()['token'] ?? '';
  return <PublicInviteLoader key={token} token={token} />;
}

function PublicInviteLoader(props: { token: string }) {
  const valid = isOpaqueTokenShape(props.token);
  const [view, setView] = useState<PublicView>(
    valid ? { status: 'loading' } : { status: 'not-found' },
  );
  const [retryNonce, setRetryNonce] = useState(0);

  useEffect(() => {
    if (!valid) {
      return;
    }
    const controller = new AbortController();
    fetchPublicContextLink(props.token, controller.signal)
      .then((envelope) => {
        if (!controller.signal.aborted) {
          setView({ status: 'ready', envelope });
        }
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        setView(mapError(error));
      });
    return () => {
      controller.abort();
    };
  }, [props.token, valid, retryNonce]);

  function retry() {
    setView({ status: 'loading' });
    setRetryNonce((value) => value + 1);
  }

  return (
    <PublicShell>
      {view.status === 'loading' ? (
        <HumanStatus kind="loading" title={PUBLIC_LOADING} live="polite" />
      ) : null}
      {view.status === 'not-found' ? (
        <HumanStatus kind="danger" title={PUBLIC_NOT_FOUND}>
          <p>Verifique se ele foi copiado por completo ou retorne ao conteúdo de origem.</p>
        </HumanStatus>
      ) : null}
      {view.status === 'revoked' ? (
        <HumanStatus kind="danger" title={PUBLIC_REVOKED}>
          <p>Ele foi encerrado por quem o publicou.</p>
        </HumanStatus>
      ) : null}
      {view.status === 'expired' ? (
        <HumanStatus kind="warning" title={PUBLIC_EXPIRED}>
          <p>O período de acesso terminou.</p>
        </HumanStatus>
      ) : null}
      {view.status === 'terminal' ? (
        <HumanStatus kind="danger" title={PUBLIC_TERMINAL}>
          <p>Não há nenhuma ação necessária.</p>
        </HumanStatus>
      ) : null}
      {view.status === 'temporary' ? (
        <HumanStatus kind="warning" title="Temporariamente indisponível.">
          <p>{PUBLIC_TEMPORARY}</p>
          <button type="button" className="button-primary" onClick={retry}>
            Tentar novamente
          </button>
        </HumanStatus>
      ) : null}
      {view.status === 'network' ? (
        <HumanStatus kind="warning" title="Não foi possível carregar agora.">
          <p>{PUBLIC_NETWORK}</p>
          <button type="button" className="button-primary" onClick={retry}>
            Tentar novamente
          </button>
        </HumanStatus>
      ) : null}
      {view.status === 'ready' ? (
        <ReadyInvite token={props.token} envelope={view.envelope} />
      ) : null}
    </PublicShell>
  );
}

function ReadyInvite(props: { token: string; envelope: PublicContextEnvelope }) {
  const [transparencyOpen, setTransparencyOpen] = useState(false);
  const materialized = materializeContextSummary(
    props.envelope.contextSummary.template,
    props.envelope.contextSummary.publisherValues,
  );
  const purpose = purposeFromCallToAction(props.envelope.callToActionLabel);
  const continuityAvailable = props.envelope.continuity.available;

  return (
    <article className="public-invite">
      <p className="public-kicker">Um convite contextual</p>
      <h1>{props.envelope.title}</h1>
      <p className="public-lede">
        {materialized.mode === 'materialized' ? materialized.text : CONTEXT_FALLBACK_SUMMARY}
      </p>
      {props.envelope.publisherBindings.length > 0 ? (
        <ContextSummary>
          <dl>
            {props.envelope.publisherBindings.map((binding) => (
              <div key={binding.fieldKey || binding.label}>
                <dt>{binding.label}</dt>
                <dd>{String(binding.value)}</dd>
              </div>
            ))}
          </dl>
        </ContextSummary>
      ) : null}
      {props.envelope.userFields.length > 0 ? (
        <section>
          <h2>Para uma próxima etapa</h2>
          <p>
            Poderão ser necessárias informações adicionais. Nenhuma informação pessoal está sendo
            solicitada agora.
          </p>
          <ul>
            {props.envelope.userFields.map((field) => (
              <li key={field.key}>{field.label}</li>
            ))}
          </ul>
        </section>
      ) : null}
      <p>{formatValidityPtBr(props.envelope.effectiveValidUntil)}</p>
      {purpose ? <p>{purpose}</p> : null}
      {continuityAvailable ? (
        <PublicProgressiveJourney key={props.token} token={props.token} envelope={props.envelope} />
      ) : (
        <>
          <button
            type="button"
            className="button-primary public-cta"
            onClick={() => {
              setTransparencyOpen(true);
              window.requestAnimationFrame(() => {
                const heading = document.getElementById('public-next-steps');
                if (heading instanceof HTMLElement) {
                  heading.setAttribute('tabIndex', '-1');
                  heading.focus();
                }
              });
            }}
          >
            Entender os próximos passos
          </button>
          <PublicTransparency open={transparencyOpen} headingId="public-next-steps" />
        </>
      )}
      <p className="public-footnote">
        Nenhuma cotação, análise de elegibilidade ou recomendação foi realizada.
      </p>
    </article>
  );
}
