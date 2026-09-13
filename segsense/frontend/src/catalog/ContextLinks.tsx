import { useEffect, useState } from 'react';
import { ApiClientError } from '../api/errors';
import {
  EFFECTIVE_LINK_STATUS_LABEL,
  fetchContextLinks,
  issueContextLink,
  revokeContextLink,
  type ContextLink,
  type IssuedContextLink,
} from '../api/links';
import { apiBaseUrl } from '../api/systemInfo';
import {
  type ContextField,
  type ContextualOpportunity,
} from '../api/opportunity';
import CopyOnceLink from '../components/CopyOnceLink';
import DestructiveConfirmation from '../components/DestructiveConfirmation';
import TechnicalAuditDetails from '../components/TechnicalAuditDetails';
import { adminErrorMessage, AUTH_NOT_CONFIGURED, formatValidityPtBr } from '../i18n/human';

type PanelState =
  | { status: 'loading' }
  | { status: 'unauthenticated' }
  | { status: 'forbidden' }
  | { status: 'missing' }
  | { status: 'error'; message: string }
  | { status: 'ready'; items: ContextLink[] };

type IssueDraft = {
  placementKey: string;
  label: string;
  expiresAt: string;
  publisherContext: Array<{ fieldKey: string; value: string | number | boolean; label: string }>;
};

const bindable = (field: ContextField) =>
  field.source === 'PUBLISHER' || field.source === 'EITHER';

export default function ContextLinksPanel(props: {
  publisherId: string;
  channelId: string;
  environmentId: string;
  opportunity: ContextualOpportunity;
}) {
  const [panel, setPanel] = useState<PanelState>({ status: 'loading' });
  const [placementKey, setPlacementKey] = useState('');
  const [label, setLabel] = useState('');
  const [expiresAt, setExpiresAt] = useState('2026-10-01T00:00');
  const [bindingValues, setBindingValues] = useState<Record<string, string>>({});
  const [review, setReview] = useState<IssueDraft | null>(null);
  const [issued, setIssued] = useState<IssuedContextLink | null>(null);
  const [commandError, setCommandError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [revokeTarget, setRevokeTarget] = useState<ContextLink | null>(null);
  const [justification, setJustification] = useState('');
  const [returnFocusTo, setReturnFocusTo] = useState<HTMLElement | null>(null);

  const canIssue =
    props.opportunity.status === 'PUBLISHED' && Boolean(props.opportunity.effectivelyPublished);
  const bindableFields = props.opportunity.current.contextFields.filter(bindable);

  useEffect(() => {
    let cancelled = false;
    fetchContextLinks(
      apiBaseUrl(),
      props.publisherId,
      props.channelId,
      props.environmentId,
      props.opportunity.id,
    )
      .then((page) => {
        if (!cancelled) {
          setPanel({ status: 'ready', items: page.items });
        }
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        if (error instanceof ApiClientError && error.authenticationRequired) {
          setPanel({ status: 'unauthenticated' });
          return;
        }
        if (error instanceof ApiClientError && error.accessDenied) {
          setPanel({ status: 'forbidden' });
          return;
        }
        if (error instanceof ApiClientError && error.status === 404) {
          setPanel({ status: 'missing' });
          return;
        }
        setPanel({
          status: 'error',
          message: adminErrorMessage(error, 'Não foi possível carregar os links contextuais.'),
        });
      });
    return () => {
      cancelled = true;
    };
  }, [
    props.publisherId,
    props.channelId,
    props.environmentId,
    props.opportunity.id,
    props.opportunity.version,
  ]);

  function reload() {
    return fetchContextLinks(
      apiBaseUrl(),
      props.publisherId,
      props.channelId,
      props.environmentId,
      props.opportunity.id,
    ).then((page) => {
      setPanel({ status: 'ready', items: page.items });
      return page;
    });
  }

  function bindingPayload(): IssueDraft['publisherContext'] {
    const payload: IssueDraft['publisherContext'] = [];
    for (const field of bindableFields) {
      if (field.type === 'BOOLEAN') {
        payload.push({
          fieldKey: field.key,
          value: bindingValues[field.key] === 'true',
          label: field.label,
        });
        continue;
      }
      const raw = bindingValues[field.key] ?? '';
      if (raw.length === 0) {
        continue;
      }
      if (field.type === 'NUMBER') {
        payload.push({ fieldKey: field.key, value: Number(raw), label: field.label });
        continue;
      }
      payload.push({ fieldKey: field.key, value: raw, label: field.label });
    }
    return payload;
  }

  function issue(draft: IssueDraft) {
    setBusy(true);
    setCommandError(null);
    issueContextLink(
      apiBaseUrl(),
      props.publisherId,
      props.channelId,
      props.environmentId,
      props.opportunity.id,
      {
        placementKey: draft.placementKey,
        label: draft.label,
        expiresAt: `${draft.expiresAt}:00.000Z`,
        publisherContext: draft.publisherContext.map((item) => ({
          fieldKey: item.fieldKey,
          value: item.value,
        })),
      },
    )
      .then((created) => {
        setIssued(created);
        setReview(null);
        setPlacementKey('');
        setLabel('');
        return reload();
      })
      .catch((error: unknown) => {
        setCommandError(adminErrorMessage(error, 'Não foi possível concluir a operação do link.'));
      })
      .finally(() => {
        setBusy(false);
      });
  }

  return (
    <section className="context-links" aria-labelledby="context-links-heading">
      <h2 id="context-links-heading">Links contextuais</h2>
      <p>
        O endereço público contém somente um identificador opaco. Os valores editoriais ficam no
        servidor e não entram no endereço. Campos de origem exclusiva do visitante não são coletados
        aqui.
      </p>
      {panel.status === 'loading' ? <p role="status">Carregando links contextuais…</p> : null}
      {panel.status === 'unauthenticated' ? <p role="status">{AUTH_NOT_CONFIGURED}</p> : null}
      {panel.status === 'forbidden' ? (
        <p role="alert">Sem permissão para consultar links contextuais.</p>
      ) : null}
      {panel.status === 'missing' ? <p role="alert">Oportunidade não encontrada.</p> : null}
      {panel.status === 'error' ? <p role="alert">{panel.message}</p> : null}
      {panel.status === 'ready' && canIssue && review == null && issued == null ? (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            setCommandError(null);
            setReview({
              placementKey,
              label,
              expiresAt,
              publisherContext: bindingPayload(),
            });
          }}
        >
          <label>
            Onde este link será usado?
            <input
              aria-label="Posicionamento"
              value={placementKey}
              onChange={(change) => {
                setPlacementKey(change.target.value);
              }}
              pattern="^[a-z][a-z0-9-]{2,79}$"
              required
            />
          </label>
          <label>
            Nome administrativo
            <input
              value={label}
              onChange={(change) => {
                setLabel(change.target.value);
              }}
              minLength={5}
              maxLength={120}
              required
            />
          </label>
          <label>
            Válido até (UTC)
            <input
              aria-label="Expira em (UTC)"
              type="datetime-local"
              value={expiresAt}
              onChange={(change) => {
                setExpiresAt(change.target.value);
              }}
              required
            />
          </label>
          {bindableFields.length === 0 ? (
            <p>Esta revisão não admite valores do publicador.</p>
          ) : (
            bindableFields.map((field) => (
              <label key={field.key}>
                {field.label} (
                {field.source === 'PUBLISHER' ? 'publicador' : 'publicador ou visitante'})
                {field.type === 'BOOLEAN' ? (
                  <input
                    type="checkbox"
                    checked={bindingValues[field.key] === 'true'}
                    onChange={(change) => {
                      setBindingValues((current) => ({
                        ...current,
                        [field.key]: change.target.checked ? 'true' : 'false',
                      }));
                    }}
                  />
                ) : null}
                {field.type === 'ENUM' ? (
                  <select
                    value={bindingValues[field.key] ?? ''}
                    onChange={(change) => {
                      setBindingValues((current) => ({
                        ...current,
                        [field.key]: change.target.value,
                      }));
                    }}
                    required={field.required && field.source === 'PUBLISHER'}
                  >
                    <option value="">Selecione</option>
                    {field.allowedValues.map((value) => (
                      <option key={value} value={value}>
                        {value}
                      </option>
                    ))}
                  </select>
                ) : null}
                {field.type === 'DATE' ? (
                  <input
                    type="date"
                    value={bindingValues[field.key] ?? ''}
                    onChange={(change) => {
                      setBindingValues((current) => ({
                        ...current,
                        [field.key]: change.target.value,
                      }));
                    }}
                    required={field.required && field.source === 'PUBLISHER'}
                  />
                ) : null}
                {field.type === 'NUMBER' ? (
                  <input
                    type="number"
                    value={bindingValues[field.key] ?? ''}
                    onChange={(change) => {
                      setBindingValues((current) => ({
                        ...current,
                        [field.key]: change.target.value,
                      }));
                    }}
                    required={field.required && field.source === 'PUBLISHER'}
                  />
                ) : null}
                {field.type === 'TEXT' ? (
                  <input
                    value={bindingValues[field.key] ?? ''}
                    onChange={(change) => {
                      setBindingValues((current) => ({
                        ...current,
                        [field.key]: change.target.value,
                      }));
                    }}
                    required={field.required && field.source === 'PUBLISHER'}
                  />
                ) : null}
              </label>
            ))
          )}
          <p>
            Os valores ficam protegidos no SegSense e não aparecem no endereço. O endereço será
            mostrado apenas uma vez.
          </p>
          <button type="submit" className="button-primary" disabled={busy}>
            Revisar emissão
          </button>
        </form>
      ) : null}
      {review ? (
        <section>
          <h3>Revise antes de emitir</h3>
          <p>Uso: {review.label}</p>
          <p>{formatValidityPtBr(`${review.expiresAt}:00.000Z`)}</p>
          <p>
            Contexto:{' '}
            {review.publisherContext
              .map((item) => `${item.label} — ${String(item.value)}`)
              .join('; ') || 'nenhum valor adicional'}
          </p>
          <p>O endereço será mostrado apenas uma vez.</p>
          <button
            type="button"
            className="button-secondary"
            onClick={() => {
              setReview(null);
            }}
          >
            Voltar
          </button>
          <button
            type="button"
            className="button-primary"
            disabled={busy}
            onClick={() => {
              issue(review);
            }}
          >
            Emitir link
          </button>
        </section>
      ) : null}
      {issued ? (
        <CopyOnceLink
          url={issued.publicUrl}
          onDismiss={() => {
            setIssued(null);
          }}
        />
      ) : null}
      {commandError ? <p role="alert">{commandError}</p> : null}
      {panel.status === 'ready' && panel.items.length === 0 ? (
        <p>Nenhum link contextual emitido.</p>
      ) : null}
      {panel.status === 'ready' && panel.items.length > 0 ? (
        <ol aria-label="Links contextuais emitidos">
          {panel.items.map((item) => (
            <li key={item.id}>
              <p>
                {item.label} — {EFFECTIVE_LINK_STATUS_LABEL[item.effectiveStatus]}
              </p>
              {item.effectiveStatus === 'ACTIVE' ? (
                <button
                  type="button"
                  className="button-danger"
                  onClick={(event) => {
                    setReturnFocusTo(event.currentTarget);
                    setRevokeTarget(item);
                    setJustification('');
                  }}
                >
                  Revogar {item.label}
                </button>
              ) : null}
              <TechnicalAuditDetails summary="Detalhes técnicos deste link">
                <p>Posicionamento: {item.placementKey}</p>
                <p>Dica administrativa: {item.tokenHint}</p>
              </TechnicalAuditDetails>
            </li>
          ))}
        </ol>
      ) : null}
      <DestructiveConfirmation
        open={revokeTarget != null}
        title="Revogar este link?"
        cancelLabel="Manter link"
        confirmLabel="Revogar definitivamente"
        confirmDisabled={justification.trim().length < 10}
        busy={busy}
        returnFocusTo={returnFocusTo}
        onCancel={() => {
          setRevokeTarget(null);
        }}
        onConfirm={() => {
          if (revokeTarget == null) {
            return;
          }
          setBusy(true);
          setCommandError(null);
          revokeContextLink(
            apiBaseUrl(),
            props.publisherId,
            props.channelId,
            props.environmentId,
            props.opportunity.id,
            revokeTarget.id,
            revokeTarget.version,
            justification,
          )
            .then(() => {
              setRevokeTarget(null);
              setIssued(null);
              return reload();
            })
            .catch((error: unknown) => {
              setCommandError(
                adminErrorMessage(error, 'Não foi possível concluir a operação do link.'),
              );
            })
            .finally(() => {
              setBusy(false);
            });
        }}
      >
        <p>O endereço deixará de funcionar imediatamente e não poderá ser reativado.</p>
        <label htmlFor="revoke-justification">Motivo da revogação</label>
        <textarea
          id="revoke-justification"
          value={justification}
          onChange={(change) => {
            setJustification(change.target.value);
          }}
          minLength={10}
          maxLength={500}
          required
        />
        <p>Não inclua dados pessoais.</p>
      </DestructiveConfirmation>
    </section>
  );
}
