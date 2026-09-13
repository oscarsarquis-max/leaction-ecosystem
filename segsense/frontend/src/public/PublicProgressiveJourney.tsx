import { useEffect, useId, useRef, useState } from 'react';
import {
  authorizeContextInstance,
  createContextInstance,
  putContextInstanceValues,
  withdrawContextInstance,
  type CollectibleFieldView,
  type ContextInstanceView,
  type PublicContextEnvelope,
} from '../api/publicContext';
import { ApiClientError } from '../api/errors';
import { adminErrorMessage } from '../i18n/human';

type Step = 'invite' | 'transparency' | 'fields' | 'review' | 'authorized' | 'withdrawn';
type DraftMap = Record<string, string | boolean | undefined>;

const FIELDS_PER_BLOCK = 3;

export default function PublicProgressiveJourney(props: {
  token: string;
  envelope: PublicContextEnvelope;
}) {
  const notice = props.envelope.continuity;
  const headingId = useId();
  const errorSummaryId = useId();
  const credentialRef = useRef<string | null>(null);
  const idempotencyKeyRef = useRef(newIdempotencyKey());
  const [step, setStep] = useState<Step>('invite');
  const [instance, setInstance] = useState<ContextInstanceView | null>(null);
  const [draft, setDraft] = useState<DraftMap>({});
  const [fieldBlock, setFieldBlock] = useState(0);
  const [acknowledged, setAcknowledged] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [withdrawUnavailable, setWithdrawUnavailable] = useState(false);

  useEffect(() => {
    return () => {
      credentialRef.current = null;
    };
  }, [props.token]);

  function start() {
    setBusy(true);
    setError(null);
    createContextInstance(props.token, idempotencyKeyRef.current)
      .then((created) => {
        if (created.instanceCredential == null) {
          idempotencyKeyRef.current = newIdempotencyKey();
          setError(
            'A resposta inicial desta sessão não pode ser recuperada. Comece uma nova tentativa.',
          );
          return;
        }
        credentialRef.current = created.instanceCredential;
        setInstance(created);
        const next: DraftMap = {};
        for (const field of created.collectibleFields) {
          next[field.key] = field.value == null ? undefined : coerceDraft(field, field.value);
        }
        setDraft(next);
        setFieldBlock(0);
        setStep(created.collectibleFields.length === 0 ? 'review' : 'fields');
      })
      .catch((failure: unknown) => {
        if (failure instanceof ApiClientError && failure.status === 409) {
          idempotencyKeyRef.current = newIdempotencyKey();
        }
        setError(adminErrorMessage(failure, 'Não foi possível continuar com segurança.'));
      })
      .finally(() => {
        setBusy(false);
      });
  }

  function saveCurrentBlock(fields: CollectibleFieldView[], lastBlock: boolean) {
    const errors = validateFields(fields, draft);
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) {
      setError(null);
      focusFirstError(fields, errors);
      return;
    }
    setError(null);
    if (!lastBlock) {
      setFieldBlock((value) => value + 1);
      return;
    }
    const credential = credentialRef.current;
    if (instance == null || credential == null) {
      setError('Recarregar ou fechar a página impede retomar esta sessão nesta etapa.');
      return;
    }
    setBusy(true);
    const values = instance.collectibleFields
      .map((field) => typedValue(field, draft[field.key]))
      .filter((item): item is { key: string; type: string; value: string | number | boolean } => item != null);
    putContextInstanceValues(props.token, credential, instance.expectedVersion, values)
      .then((updated) => {
        setInstance(updated);
        setStep('review');
      })
      .catch((failure: unknown) => {
        setError(adminErrorMessage(failure, 'Não foi possível guardar estas informações.'));
      })
      .finally(() => {
        setBusy(false);
      });
  }

  function authorize() {
    const credential = credentialRef.current;
    if (instance == null || credential == null || notice.noticeVersion == null) {
      setError('Recarregar ou fechar a página impede retomar esta sessão nesta etapa.');
      return;
    }
    setBusy(true);
    setError(null);
    authorizeContextInstance(props.token, credential, instance.expectedVersion, notice.noticeVersion)
      .then((updated) => {
        setInstance(updated);
        setStep('authorized');
      })
      .catch((failure: unknown) => {
        setError(adminErrorMessage(failure, 'Não foi possível registrar sua escolha.'));
      })
      .finally(() => {
        setBusy(false);
      });
  }

  function withdraw() {
    const credential = credentialRef.current;
    if (instance == null || credential == null) {
      setWithdrawUnavailable(true);
      setError('A retirada não é mais possível nesta sessão. Os valores não foram apagados.');
      return;
    }
    setBusy(true);
    setError(null);
    withdrawContextInstance(props.token, credential, instance.expectedVersion)
      .then((updated) => {
        setInstance(updated);
        setStep('withdrawn');
        credentialRef.current = null;
      })
      .catch((failure: unknown) => {
        if (
          failure instanceof ApiClientError &&
          (failure.status === 410 || failure.code === 'CONTEXT_INSTANCE_EXPIRED')
        ) {
          setWithdrawUnavailable(true);
          setError(
            'A retirada não é mais possível porque esta sessão não está mais vigente. Os valores não foram apagados.',
          );
          return;
        }
        setError(adminErrorMessage(failure, 'Não foi possível retirar a autorização.'));
      })
      .finally(() => {
        setBusy(false);
      });
  }

  const collectible = instance?.collectibleFields ?? [];
  const totalBlocks = Math.max(1, Math.ceil(collectible.length / FIELDS_PER_BLOCK));
  const blockFields = collectible.slice(
    fieldBlock * FIELDS_PER_BLOCK,
    fieldBlock * FIELDS_PER_BLOCK + FIELDS_PER_BLOCK,
  );
  const lastBlock = fieldBlock >= totalBlocks - 1;

  return (
    <div>
      {step === 'invite' ? (
        <button
          type="button"
          className="button-primary public-cta"
          disabled={busy}
          onClick={() => {
            setStep('transparency');
          }}
        >
          Continuar com segurança
        </button>
      ) : null}
      {step === 'transparency' ? (
        <section className="public-transparency" aria-labelledby={headingId}>
          <h2 id={headingId}>{notice.purposeTitle}</h2>
          <p>{notice.purposeDescription}</p>
          <p>{notice.transparencyText}</p>
          <p>{notice.noExternalSharingStatement}</p>
          <p>
            As informações pedidas são apenas as listadas. Nesta etapa elas permanecem no SegSense.
            Nenhuma seguradora, Spider ou simulador receberá estes dados. Recarregar ou fechar a
            página impede retomar esta sessão nesta etapa; o convite original poderá iniciar uma nova
            sessão enquanto estiver válido.
          </p>
          <button type="button" className="button-primary" disabled={busy} onClick={start}>
            Começar esta sessão
          </button>
        </section>
      ) : null}
      {step === 'fields' && instance ? (
        <form
          className="public-collection"
          onSubmit={(event) => {
            event.preventDefault();
            saveCurrentBlock(blockFields, lastBlock);
          }}
        >
          <h2>Informações desta etapa</h2>
          {Object.keys(fieldErrors).length > 0 ? (
            <div id={errorSummaryId} role="alert" className="public-error-summary">
              <p>Há informações a corrigir:</p>
              <ul>
                {blockFields
                  .filter((field) => fieldErrors[field.key])
                  .map((field) => (
                    <li key={field.key}>
                      <a href={`#collect-${field.key}`}>{fieldErrors[field.key]}</a>
                    </li>
                  ))}
              </ul>
            </div>
          ) : null}
          {blockFields.map((field) => (
            <FieldControl
              key={field.key}
              field={field}
              value={draft[field.key]}
              error={fieldErrors[field.key]}
              onChange={(value) => {
                setDraft({ ...draft, [field.key]: value });
              }}
            />
          ))}
          <div className="public-actions">
            {fieldBlock > 0 ? (
              <button
                type="button"
                className="button-secondary"
                onClick={() => {
                  setFieldErrors({});
                  setFieldBlock((value) => value - 1);
                }}
              >
                Voltar
              </button>
            ) : (
              <button
                type="button"
                className="button-secondary"
                onClick={() => {
                  setStep('transparency');
                }}
              >
                Voltar
              </button>
            )}
            <button type="submit" className="button-primary" disabled={busy}>
              {lastBlock ? 'Revisar informações' : 'Continuar'}
            </button>
          </div>
        </form>
      ) : null}
      {step === 'review' && instance ? (
        <section className="public-transparency">
          <h2>Revisar e autorizar</h2>
          <p>{notice.purposeTitle}</p>
          <p>{notice.transparencyText}</p>
          <ul>
            {instance.collectibleFields.map((field) => (
              <li key={field.key}>
                {field.label}: {reviewLabel(field, draft[field.key])}
              </li>
            ))}
          </ul>
          {instance.collectibleFields.length > 0 ? (
            <button
              type="button"
              className="button-secondary"
              onClick={() => {
                setFieldBlock(0);
                setStep('fields');
              }}
            >
              Corrigir informações
            </button>
          ) : null}
          <label htmlFor="authorize-ack">
            <input
              id="authorize-ack"
              type="checkbox"
              checked={acknowledged}
              onChange={(event) => {
                setAcknowledged(event.target.checked);
              }}
            />
            Li o aviso desta versão e quero registrar minha escolha.
          </label>
          <button
            type="button"
            className="button-primary"
            disabled={busy || !acknowledged}
            onClick={authorize}
          >
            Autorizar uso destas informações no SegSense
          </button>
        </section>
      ) : null}
      {step === 'authorized' ? (
        <section className="public-transparency">
          <h2>Sua escolha foi registrada</h2>
          <p>A autorização vale para esta sessão no SegSense. Nada foi enviado a uma seguradora.</p>
          {withdrawUnavailable ? (
            <p>A retirada não é mais possível nesta sessão. Os valores não foram apagados.</p>
          ) : (
            <button type="button" className="button-secondary" disabled={busy} onClick={withdraw}>
              Retirar autorização
            </button>
          )}
        </section>
      ) : null}
      {step === 'withdrawn' ? (
        <section className="public-transparency">
          <h2>Autorização retirada</h2>
          <p>
            Sua escolha foi registrada. Esta sessão não continua. Os valores não foram apagados
            nesta etapa.
          </p>
        </section>
      ) : null}
      {error ? <p role="alert">{error}</p> : null}
    </div>
  );
}

function FieldControl(props: {
  field: CollectibleFieldView;
  value: string | boolean | undefined;
  error?: string;
  onChange: (value: string | boolean | undefined) => void;
}) {
  const describedBy = props.error ? `${props.field.key}-error` : undefined;
  if (props.field.type === 'BOOLEAN') {
    const selected = props.value;
    return (
      <fieldset className="public-choice" aria-describedby={describedBy}>
        <legend>
          {props.field.label}
          {props.field.required ? ' (obrigatório)' : ''}
        </legend>
        <label htmlFor={`collect-${props.field.key}`}>
          <input
            id={`collect-${props.field.key}`}
            type="radio"
            name={`collect-${props.field.key}`}
            checked={selected === true}
            onChange={() => {
              props.onChange(true);
            }}
          />
          Sim
        </label>
        <label htmlFor={`collect-${props.field.key}-no`}>
          <input
            id={`collect-${props.field.key}-no`}
            type="radio"
            name={`collect-${props.field.key}`}
            checked={selected === false}
            onChange={() => {
              props.onChange(false);
            }}
          />
          Não
        </label>
        {props.error ? (
          <p id={`${props.field.key}-error`} className="field-error">
            {props.error}
          </p>
        ) : null}
      </fieldset>
    );
  }
  if (props.field.type === 'ENUM') {
    return (
      <label htmlFor={`collect-${props.field.key}`}>
        {props.field.label}
        {props.field.required ? ' (obrigatório)' : ''}
        <select
          id={`collect-${props.field.key}`}
          value={typeof props.value === 'string' ? props.value : ''}
          aria-invalid={props.error ? true : undefined}
          aria-describedby={describedBy}
          onChange={(event) => {
            props.onChange(event.target.value === '' ? undefined : event.target.value);
          }}
        >
          <option value="">Selecione</option>
          {props.field.allowedValues.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
        {props.error ? (
          <span id={`${props.field.key}-error`} className="field-error">
            {props.error}
          </span>
        ) : null}
      </label>
    );
  }
  return (
    <label htmlFor={`collect-${props.field.key}`}>
      {props.field.label}
      {props.field.required ? ' (obrigatório)' : ''}
      <input
        id={`collect-${props.field.key}`}
        type="text"
        inputMode={props.field.type === 'NUMBER' ? 'decimal' : props.field.type === 'DATE' ? 'numeric' : undefined}
        autoComplete="off"
        placeholder={props.field.type === 'DATE' ? 'AAAA-MM-DD' : undefined}
        value={typeof props.value === 'string' ? props.value : ''}
        aria-invalid={props.error ? true : undefined}
        aria-describedby={describedBy}
        onChange={(event) => {
          props.onChange(event.target.value);
        }}
      />
      {props.error ? (
        <span id={`${props.field.key}-error`} className="field-error">
          {props.error}
        </span>
      ) : null}
    </label>
  );
}

function validateFields(fields: CollectibleFieldView[], draft: DraftMap): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const field of fields) {
    const raw = draft[field.key];
    if (field.type === 'BOOLEAN') {
      if (raw === undefined) {
        if (field.required) {
          errors[field.key] = `Selecione Sim ou Não para ${field.label}.`;
        }
        continue;
      }
      if (raw !== true && raw !== false) {
        errors[field.key] = `Selecione Sim ou Não para ${field.label}.`;
      }
      continue;
    }
    const text = typeof raw === 'string' ? raw.trim() : '';
    if (text.length === 0) {
      if (field.required) {
        errors[field.key] = `Informe ${field.label}.`;
      }
      continue;
    }
    if (field.type === 'NUMBER') {
      if (!/^-?\d+(\.\d+)?$/.test(text) || !Number.isFinite(Number(text))) {
        errors[field.key] = `${field.label} precisa ser um número.`;
      }
      continue;
    }
    if (field.type === 'DATE') {
      if (!isIsoLocalDate(text)) {
        errors[field.key] = `${field.label} precisa ser uma data válida.`;
      }
      continue;
    }
    if (field.type === 'ENUM' && !field.allowedValues.includes(text)) {
      errors[field.key] = `Selecione uma opção válida para ${field.label}.`;
    }
  }
  return errors;
}

function typedValue(
  field: CollectibleFieldView,
  raw: string | boolean | undefined,
): { key: string; type: string; value: string | number | boolean } | null {
  if (field.type === 'BOOLEAN') {
    if (raw === true || raw === false) {
      return { key: field.key, type: field.type, value: raw };
    }
    return null;
  }
  if (typeof raw !== 'string' || raw.trim().length === 0) {
    return null;
  }
  if (field.type === 'NUMBER') {
    return { key: field.key, type: field.type, value: Number(raw) };
  }
  return { key: field.key, type: field.type, value: raw };
}

function coerceDraft(field: CollectibleFieldView, value: string | number | boolean): string | boolean {
  if (field.type === 'BOOLEAN') {
    return value === true;
  }
  return String(value);
}

function reviewLabel(field: CollectibleFieldView, value: string | boolean | undefined): string {
  if (field.type === 'BOOLEAN') {
    if (value === true) {
      return 'Sim';
    }
    if (value === false) {
      return 'Não';
    }
    return 'não informado';
  }
  if (typeof value === 'string' && value.trim().length > 0) {
    return value;
  }
  return 'não informado';
}

function focusFirstError(fields: CollectibleFieldView[], errors: Record<string, string>): void {
  const first = fields.find((field) => errors[field.key]);
  if (first == null) {
    return;
  }
  const node = document.getElementById(`collect-${first.key}`);
  if (node instanceof HTMLElement) {
    node.focus();
  }
}

function newIdempotencyKey(): string {
  return crypto.randomUUID();
}

function isIsoLocalDate(text: string): boolean {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(text);
  if (match == null || match[1] == null || match[2] == null || match[3] == null) {
    return false;
  }
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const date = new Date(Date.UTC(year, month - 1, day));
  return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day;
}
