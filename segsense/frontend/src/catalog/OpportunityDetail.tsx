import { useState, type SyntheticEvent } from 'react';
import {
  createOpportunityRevision,
  datetimeLocalToUtcIso,
  declaredPlaceholders,
  utcIsoToDatetimeLocal,
  CONTEXT_MODES,
  FIELD_SOURCES,
  FIELD_TYPES,
  OPPORTUNITY_STATUS_LABEL,
  type ContextFieldSource,
  type ContextFieldType,
  type ContextMode,
  type ContextualOpportunity,
  type OpportunityDraft,
  type OpportunityRevisionSnapshot,
} from '../api/opportunity';
import { apiBaseUrl } from '../api/systemInfo';
import OpportunityGovernancePanel from './OpportunityGovernance';
import ContextLinksPanel from './ContextLinks';
import ConsentNoticePanel from './ConsentNoticePanel';
import OpportunityTabs, { type OpportunityTabId } from '../components/OpportunityTabs';
import TechnicalAuditDetails from '../components/TechnicalAuditDetails';
import { adminErrorMessage } from '../i18n/human';

const CONTEXT_MODE_LABEL: Record<ContextMode, string> = {
  STATIC: 'Contexto estático',
  DYNAMIC: 'Contexto dinâmico',
  HYBRID: 'Contexto híbrido',
};

const FIELD_SOURCE_LABEL: Record<ContextFieldSource, string> = {
  PUBLISHER: 'Publicador',
  USER: 'Visitante',
  EITHER: 'Publicador ou visitante',
};

const FIELD_TYPE_LABEL: Record<ContextFieldType, string> = {
  TEXT: 'Texto',
  NUMBER: 'Número',
  BOOLEAN: 'Sim ou não',
  DATE: 'Data',
  ENUM: 'Lista fechada',
};

type FieldDraft = {
  key: string;
  label: string;
  type: ContextFieldType;
  required: boolean;
  source: ContextFieldSource;
  allowedValues: string;
};

export default function OpportunityDetail(props: {
  publisherId: string;
  channelId: string;
  environmentId: string;
  opportunity: ContextualOpportunity;
  history: OpportunityRevisionSnapshot[] | null;
  onReload: () => Promise<ContextualOpportunity>;
  formError?: string | null;
  onFormError?: (message: string | null) => void;
}) {
  const [tab, setTab] = useState<OpportunityTabId>('content');
  const [localError, setLocalError] = useState<string | null>(null);
  const selected = props.opportunity;
  const showLinks =
    selected.status === 'PUBLISHED' ||
    selected.status === 'PAUSED' ||
    selected.status === 'EXPIRED' ||
    selected.status === 'REVOKED';

  return (
    <article>
      <h1>{selected.current.title}</h1>
      <p>
        {OPPORTUNITY_STATUS_LABEL[selected.status]}
        {selected.approvedRevision != null
          ? ` · revisão aprovada ${String(selected.approvedRevision)}`
          : ''}
      </p>
      <OpportunityTabs
        selected={tab}
        onSelect={setTab}
        panels={{
          content: (
            <div>
              <p>{CONTEXT_MODE_LABEL[selected.current.contextMode]}</p>
              <p>{selected.current.contextSummaryTemplate}</p>
              {selected.status === 'DRAFT' ? (
                <OpportunityForm
                  title="Nova revisão"
                  includeKey={false}
                  submitLabel="Criar revisão"
                  initial={selected}
                  error={props.formError ?? localError}
                  onSubmit={(draft) => {
                    createOpportunityRevision(
                      apiBaseUrl(),
                      props.publisherId,
                      props.channelId,
                      props.environmentId,
                      selected.id,
                      selected.version,
                      selected.currentRevision,
                      draft,
                    )
                      .then(() => {
                        setLocalError(null);
                        props.onFormError?.(null);
                        return props.onReload();
                      })
                      .catch((error: unknown) => {
                        const message = adminErrorMessage(
                          error,
                          'Não foi possível criar a revisão.',
                        );
                        setLocalError(message);
                        props.onFormError?.(message);
                      });
                  }}
                />
              ) : (
                <p>Nova revisão só pode ser criada enquanto o status for rascunho.</p>
              )}
              <h2>Histórico somente leitura</h2>
              {props.history && props.history.length > 0 ? (
                <ol aria-label="Histórico de revisões">
                  {props.history.map((revision) => (
                    <li key={revision.id}>
                      Revisão {revision.revisionNumber}: {revision.title} (
                      {CONTEXT_MODE_LABEL[revision.contextMode]})
                    </li>
                  ))}
                </ol>
              ) : (
                <p>O histórico aparece após abrir uma oportunidade.</p>
              )}
              <TechnicalAuditDetails summary="Detalhes técnicos da revisão">
                <p>Modelo de objetivo (não público): {selected.current.objectiveTemplate}</p>
              </TechnicalAuditDetails>
            </div>
          ),
          governance: (
            <OpportunityGovernancePanel
              publisherId={props.publisherId}
              channelId={props.channelId}
              environmentId={props.environmentId}
              opportunityId={selected.id}
              version={selected.version}
              key={`${selected.id}:${String(selected.version)}`}
              onAccepted={() => {
                props.onReload().catch(() => {
                  const message = 'Não foi possível atualizar a oportunidade após a decisão.';
                  setLocalError(message);
                  props.onFormError?.(message);
                });
              }}
            />
          ),
          purpose: (
            <ConsentNoticePanel
              publisherId={props.publisherId}
              channelId={props.channelId}
              environmentId={props.environmentId}
              opportunityId={selected.id}
              approvedRevision={selected.approvedRevision ?? null}
            />
          ),
          links: showLinks ? (
            <ContextLinksPanel
              publisherId={props.publisherId}
              channelId={props.channelId}
              environmentId={props.environmentId}
              opportunity={selected}
            />
          ) : (
            <p>Links contextuais ficam disponíveis depois da autorização de publicação.</p>
          ),
        }}
      />
    </article>
  );
}

export function OpportunityForm(props: {
  title: string;
  includeKey: boolean;
  submitLabel: string;
  initial?: ContextualOpportunity;
  error: string | null;
  onSubmit: (draft: OpportunityDraft) => void;
}) {
  const [key, setKey] = useState('');
  const [title, setTitle] = useState(props.initial?.current.title ?? '');
  const [contextMode, setContextMode] = useState<ContextMode>(
    props.initial?.current.contextMode ?? 'STATIC',
  );
  const [summary, setSummary] = useState(props.initial?.current.contextSummaryTemplate ?? '');
  const [objective, setObjective] = useState(props.initial?.current.objectiveTemplate ?? '');
  const [cta, setCta] = useState(props.initial?.current.callToActionLabel ?? '');
  const [validFrom, setValidFrom] = useState(
    utcIsoToDatetimeLocal(props.initial?.current.validFrom ?? null),
  );
  const [validUntil, setValidUntil] = useState(
    utcIsoToDatetimeLocal(props.initial?.current.validUntil ?? null),
  );
  const [fields, setFields] = useState<FieldDraft[]>(
    props.initial?.current.contextFields.map((field) => ({
      key: field.key,
      label: field.label,
      type: field.type,
      required: field.required,
      source: field.source,
      allowedValues: field.allowedValues.join(', '),
    })) ?? [],
  );
  const [localError, setLocalError] = useState<string | null>(null);

  const draftPreview = {
    title,
    contextSummaryTemplate: summary,
    objectiveTemplate: objective,
    callToActionLabel: cta,
  };
  const placeholders = declaredPlaceholders(draftPreview);

  function onSubmit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (props.includeKey && !/^[a-z][a-z0-9-]{2,49}$/.test(key.trim().toLowerCase())) {
      setLocalError('Informe uma chave válida (minúsculas, 3 a 50 caracteres).');
      return;
    }
    if (title.trim().length < 5 || title.trim().length > 140) {
      setLocalError('O título deve ter entre 5 e 140 caracteres.');
      return;
    }
    let validFromIso: string | null;
    let validUntilIso: string | null;
    try {
      validFromIso = datetimeLocalToUtcIso(validFrom);
      validUntilIso = datetimeLocalToUtcIso(validUntil);
    } catch {
      setLocalError('Informe validFrom e validUntil em UTC no formato data e hora.');
      return;
    }
    if (validFromIso && validUntilIso && validUntilIso <= validFromIso) {
      setLocalError('A validade final (UTC) deve ser posterior ao início.');
      return;
    }
    const contextFields =
      contextMode === 'STATIC'
        ? []
        : fields.map((field) => ({
            key: field.key.trim(),
            label: field.label.trim(),
            type: field.type,
            required: field.required,
            source: field.source,
            classification: 'NON_PERSONAL' as const,
            allowedValues:
              field.type === 'ENUM'
                ? field.allowedValues
                    .split(',')
                    .map((value) => value.trim())
                    .filter((value) => value.length > 0)
                : [],
          }));
    setLocalError(null);
    props.onSubmit({
      key: props.includeKey ? key.trim().toLowerCase() : undefined,
      title: title.trim(),
      contextMode,
      contextSummaryTemplate: summary.trim(),
      objectiveTemplate: objective.trim(),
      callToActionLabel: cta.trim(),
      validFrom: validFromIso,
      validUntil: validUntilIso,
      contextFields,
    });
  }

  return (
    <form onSubmit={onSubmit} aria-label={props.title}>
      <h2>{props.title}</h2>
      {props.includeKey ? (
        <div>
          <label htmlFor={`${props.title}-key`}>Chave</label>
          <input
            id={`${props.title}-key`}
            value={key}
            onChange={(event) => {
              setKey(event.target.value);
            }}
            autoComplete="off"
          />
        </div>
      ) : null}
      <div>
        <label htmlFor={`${props.title}-title`}>Título</label>
        <input
          id={`${props.title}-title`}
          value={title}
          onChange={(event) => {
            setTitle(event.target.value);
          }}
          autoComplete="off"
        />
      </div>
      <div>
        <label htmlFor={`${props.title}-mode`}>Modo de contexto</label>
        <select
          id={`${props.title}-mode`}
          value={contextMode}
          onChange={(event) => {
            setContextMode(event.target.value as ContextMode);
          }}
        >
          {CONTEXT_MODES.map((mode) => (
            <option key={mode} value={mode}>
              {CONTEXT_MODE_LABEL[mode]}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor={`${props.title}-summary`}>Resumo de contexto</label>
        <textarea
          id={`${props.title}-summary`}
          value={summary}
          onChange={(event) => {
            setSummary(event.target.value);
          }}
        />
      </div>
      <div>
        <label htmlFor={`${props.title}-objective`}>Modelo de objetivo</label>
        <textarea
          id={`${props.title}-objective`}
          value={objective}
          onChange={(event) => {
            setObjective(event.target.value);
          }}
        />
      </div>
      <div>
        <label htmlFor={`${props.title}-cta`}>Chamada para ação</label>
        <input
          id={`${props.title}-cta`}
          value={cta}
          onChange={(event) => {
            setCta(event.target.value);
          }}
          autoComplete="off"
        />
      </div>
      <div>
        <label htmlFor={`${props.title}-valid-from`}>Válido a partir (UTC)</label>
        <input
          id={`${props.title}-valid-from`}
          type="datetime-local"
          value={validFrom}
          onChange={(event) => {
            setValidFrom(event.target.value);
          }}
        />
      </div>
      <div>
        <label htmlFor={`${props.title}-valid-until`}>Válido até (UTC)</label>
        <input
          id={`${props.title}-valid-until`}
          type="datetime-local"
          value={validUntil}
          onChange={(event) => {
            setValidUntil(event.target.value);
          }}
        />
      </div>
      <p>
        Os horários são convertidos explicitamente para UTC. Não informe dados pessoais nestes
        campos.
      </p>
      {contextMode !== 'STATIC' ? (
        <fieldset>
          <legend>Campos de contexto</legend>
          {fields.map((field, index) => (
            <div key={`field-${String(index)}`}>
              <label htmlFor={`${props.title}-field-key-${String(index)}`}>Chave do campo</label>
              <input
                id={`${props.title}-field-key-${String(index)}`}
                value={field.key}
                onChange={(event) => {
                  const next = [...fields];
                  next[index] = { ...field, key: event.target.value };
                  setFields(next);
                }}
                autoComplete="off"
              />
              <label htmlFor={`${props.title}-field-label-${String(index)}`}>Rótulo</label>
              <input
                id={`${props.title}-field-label-${String(index)}`}
                value={field.label}
                onChange={(event) => {
                  const next = [...fields];
                  next[index] = { ...field, label: event.target.value };
                  setFields(next);
                }}
                autoComplete="off"
              />
              <label htmlFor={`${props.title}-field-type-${String(index)}`}>Tipo</label>
              <select
                id={`${props.title}-field-type-${String(index)}`}
                value={field.type}
                onChange={(event) => {
                  const next = [...fields];
                  next[index] = { ...field, type: event.target.value as ContextFieldType };
                  setFields(next);
                }}
              >
                {FIELD_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {FIELD_TYPE_LABEL[type]}
                  </option>
                ))}
              </select>
              <label htmlFor={`${props.title}-field-source-${String(index)}`}>Origem</label>
              <select
                id={`${props.title}-field-source-${String(index)}`}
                value={field.source}
                onChange={(event) => {
                  const next = [...fields];
                  next[index] = { ...field, source: event.target.value as ContextFieldSource };
                  setFields(next);
                }}
              >
                {FIELD_SOURCES.map((source) => (
                  <option key={source} value={source}>
                    {FIELD_SOURCE_LABEL[source]}
                  </option>
                ))}
              </select>
              <label htmlFor={`${props.title}-field-required-${String(index)}`}>
                <input
                  id={`${props.title}-field-required-${String(index)}`}
                  type="checkbox"
                  checked={field.required}
                  onChange={(event) => {
                    const next = [...fields];
                    next[index] = { ...field, required: event.target.checked };
                    setFields(next);
                  }}
                />
                Campo obrigatório
              </label>
              <button
                type="button"
                onClick={() => {
                  setFields(fields.filter((_, current) => current !== index));
                }}
                aria-label={`Remover campo ${String(index + 1)}`}
              >
                Remover campo
              </button>
              {field.type === 'ENUM' ? (
                <div>
                  <label htmlFor={`${props.title}-field-enum-${String(index)}`}>
                    Valores da lista (separados por vírgula)
                  </label>
                  <input
                    id={`${props.title}-field-enum-${String(index)}`}
                    value={field.allowedValues}
                    onChange={(event) => {
                      const next = [...fields];
                      next[index] = { ...field, allowedValues: event.target.value };
                      setFields(next);
                    }}
                    autoComplete="off"
                  />
                </div>
              ) : null}
            </div>
          ))}
          <button
            type="button"
            onClick={() => {
              if (fields.length >= 20) {
                return;
              }
              setFields([
                ...fields,
                {
                  key: '',
                  label: '',
                  type: 'TEXT',
                  required: false,
                  source: 'PUBLISHER',
                  allowedValues: '',
                },
              ]);
            }}
          >
            Adicionar campo
          </button>
        </fieldset>
      ) : null}
      <p>Placeholders declarados (sem valores de runtime): {placeholders.join(' ') || 'nenhum'}</p>
      {localError ? <p role="alert">{localError}</p> : null}
      {props.error ? <p role="alert">{props.error}</p> : null}
      <button type="submit" className="button-primary">
        {props.submitLabel}
      </button>
    </form>
  );
}
