import { useEffect, useState, type SyntheticEvent } from 'react';
import { ApiClientError } from '../api/errors';
import {
  fetchConsentNotice,
  postConsentNotice,
  type ConsentNotice,
} from '../api/consentNotice';
import { apiBaseUrl } from '../api/systemInfo';
import { adminErrorMessage } from '../i18n/human';

type PanelState =
  | { status: 'loading' }
  | { status: 'missing' }
  | { status: 'unauthenticated' }
  | { status: 'forbidden' }
  | { status: 'error'; message: string }
  | { status: 'ready'; notice: ConsentNotice };

export default function ConsentNoticePanel(props: {
  publisherId: string;
  channelId: string;
  environmentId: string;
  opportunityId: string;
  approvedRevision: number | null;
}) {
  const [panel, setPanel] = useState<PanelState>({ status: 'loading' });
  const [title, setTitle] = useState('Uso destas informações no SegSense');
  const [description, setDescription] = useState(
    'Usar as informações desta etapa somente para continuar a jornada no SegSense.',
  );
  const [transparency, setTransparency] = useState(
    'As informações permanecem no SegSense e não são enviadas a seguradora, Spider ou simulador nesta etapa.',
  );
  const [sharing, setSharing] = useState('Não há compartilhamento externo nesta etapa.');
  const [justification, setJustification] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchConsentNotice(
      apiBaseUrl(),
      props.publisherId,
      props.channelId,
      props.environmentId,
      props.opportunityId,
    )
      .then((notice) => {
        if (cancelled) {
          return;
        }
        setPanel({ status: 'ready', notice });
        setTitle(notice.current.purposeTitle);
        setDescription(notice.current.purposeDescription);
        setTransparency(notice.current.transparencyText);
        setSharing(notice.current.noExternalSharingText);
      })
      .catch((failure: unknown) => {
        if (cancelled) {
          return;
        }
        if (failure instanceof ApiClientError && failure.status === 404) {
          setPanel({ status: 'missing' });
          return;
        }
        if (failure instanceof ApiClientError && failure.authenticationRequired) {
          setPanel({ status: 'unauthenticated' });
          return;
        }
        if (failure instanceof ApiClientError && failure.accessDenied) {
          setPanel({ status: 'forbidden' });
          return;
        }
        setPanel({
          status: 'error',
          message: adminErrorMessage(failure, 'Não foi possível carregar o aviso de finalidade.'),
        });
      });
    return () => {
      cancelled = true;
    };
  }, [props.opportunityId, props.approvedRevision, props.publisherId, props.channelId, props.environmentId]);

  function submit(path: '' | '/draft' | '/approve' | '/retire', extra: Record<string, unknown> = {}) {
    const notice = panel.status === 'ready' ? panel.notice : null;
    setError(null);
    postConsentNotice(
      apiBaseUrl(),
      props.publisherId,
      props.channelId,
      props.environmentId,
      props.opportunityId,
      path,
      {
        purposeTitle: title,
        purposeDescription: description,
        transparencyText: transparency,
        noExternalSharingText: sharing,
        expectedVersion: notice?.version,
        ...extra,
      },
    )
      .then((updated) => {
        setPanel({ status: 'ready', notice: updated });
      })
      .catch((failure: unknown) => {
        setError(adminErrorMessage(failure, 'Não foi possível salvar o aviso de finalidade.'));
      });
  }

  function onCreate(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    submit('');
  }

  if (panel.status === 'loading') {
    return <p>Carregando finalidade e transparência…</p>;
  }
  if (panel.status === 'unauthenticated') {
    return <p>A autenticação administrativa ainda não está configurada.</p>;
  }
  if (panel.status === 'forbidden') {
    return <p>Seu acesso não permite gerenciar o aviso de finalidade.</p>;
  }
  if (panel.status === 'error') {
    return <p role="alert">{panel.message}</p>;
  }
  if (props.approvedRevision == null) {
    return <p>A finalidade só pode ser definida depois da aprovação da revisão.</p>;
  }

  const notice = panel.status === 'ready' ? panel.notice : null;
  const editable = notice == null || notice.status === 'DRAFT';

  return (
    <section>
      <h2>Finalidade e transparência</h2>
      <p>
        Este texto é a versão que a pessoa verá antes de autorizar o uso das informações no SegSense.
        Não descreve consentimento jurídico válido.
      </p>
      {notice ? <p>Estado: {notice.status === 'DRAFT' ? 'Rascunho' : notice.status === 'APPROVED' ? 'Aprovado' : 'Encerrado'}</p> : null}
      <form
        onSubmit={
          notice == null
            ? onCreate
            : (event) => {
                event.preventDefault();
                submit('/draft');
              }
        }
      >
        <label htmlFor="purpose-title">Título da finalidade</label>
        <input
          id="purpose-title"
          value={title}
          disabled={!editable}
          onChange={(event) => {
            setTitle(event.target.value);
          }}
        />
        <label htmlFor="purpose-description">Descrição da finalidade</label>
        <textarea
          id="purpose-description"
          value={description}
          disabled={!editable}
          onChange={(event) => {
            setDescription(event.target.value);
          }}
        />
        <label htmlFor="purpose-transparency">Texto de transparência</label>
        <textarea
          id="purpose-transparency"
          value={transparency}
          disabled={!editable}
          onChange={(event) => {
            setTransparency(event.target.value);
          }}
        />
        <label htmlFor="purpose-sharing">Não compartilhamento externo</label>
        <textarea
          id="purpose-sharing"
          value={sharing}
          disabled={!editable}
          onChange={(event) => {
            setSharing(event.target.value);
          }}
        />
        {editable ? (
          <button type="submit" className="button-primary">
            {notice == null ? 'Criar aviso' : 'Guardar nova versão'}
          </button>
        ) : null}
      </form>
      {notice?.status === 'DRAFT' ? (
        <div>
          <label htmlFor="purpose-approve">Justificativa para aprovar</label>
          <textarea
            id="purpose-approve"
            value={justification}
            onChange={(event) => {
              setJustification(event.target.value);
            }}
          />
          <button
            type="button"
            className="button-secondary"
            onClick={() => {
              submit('/approve', { justification });
            }}
          >
            Aprovar aviso
          </button>
        </div>
      ) : null}
      {notice?.status === 'APPROVED' ? (
        <div>
          <label htmlFor="purpose-retire">Justificativa para encerrar</label>
          <textarea
            id="purpose-retire"
            value={justification}
            onChange={(event) => {
              setJustification(event.target.value);
            }}
          />
          <button
            type="button"
            className="button-danger"
            onClick={() => {
              submit('/retire', { justification });
            }}
          >
            Encerrar aviso
          </button>
        </div>
      ) : null}
      {error ? <p role="alert">{error}</p> : null}
    </section>
  );
}
