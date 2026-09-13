import { useEffect, useState } from 'react';
import { ApiClientError } from '../api/errors';
import {
  GOVERNANCE_ACTION_LABEL,
  OPPORTUNITY_STATUS_LABEL,
  fetchOpportunityGovernance,
  fetchOpportunityGovernanceEvents,
  postOpportunityGovernance,
  type GovernanceAction,
  type LifecycleEvent,
  type OpportunityGovernance,
} from '../api/opportunity';
import { apiBaseUrl } from '../api/systemInfo';

type PanelState =
  | { status: 'loading' }
  | { status: 'unauthenticated' }
  | { status: 'forbidden' }
  | { status: 'missing' }
  | { status: 'error'; message: string }
  | { status: 'ready'; governance: OpportunityGovernance; events: LifecycleEvent[] };

const JUSTIFICATION_ACTIONS: GovernanceAction[] = ['RETURN_FOR_CHANGES', 'REJECT', 'REVOKE'];

const EVENT_LABEL: Record<string, string> = {
  SUBMITTED: 'Submetida',
  RETURNED: 'Devolvida para alterações',
  APPROVED: 'Aprovada',
  REJECTED: 'Rejeitada',
  ACTIVATED: 'Autorização de publicação ativada',
  PAUSED: 'Pausada',
  RESUMED: 'Retomada',
  EXPIRED: 'Expirada',
  REVOKED: 'Revogada',
};

export default function OpportunityGovernancePanel(props: {
  publisherId: string;
  channelId: string;
  environmentId: string;
  opportunityId: string;
  version: number;
  onAccepted: () => void;
}) {
  const [panel, setPanel] = useState<PanelState>({ status: 'loading' });
  const [pendingAction, setPendingAction] = useState<GovernanceAction | null>(null);
  const [justification, setJustification] = useState('');
  const [commandError, setCommandError] = useState<string | null>(null);
  const [commandBusy, setCommandBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetchOpportunityGovernance(
        apiBaseUrl(),
        props.publisherId,
        props.channelId,
        props.environmentId,
        props.opportunityId,
      ),
      fetchOpportunityGovernanceEvents(
        apiBaseUrl(),
        props.publisherId,
        props.channelId,
        props.environmentId,
        props.opportunityId,
      ),
    ])
      .then(([governance, events]) => {
        if (!cancelled) {
          setPanel({ status: 'ready', governance, events: events.items });
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
          message:
            error instanceof ApiClientError
              ? error.message
              : 'Não foi possível carregar a governança.',
        });
      });
    return () => {
      cancelled = true;
    };
  }, [props.publisherId, props.channelId, props.environmentId, props.opportunityId, props.version]);

  function runAction(action: GovernanceAction, text?: string) {
    if (panel.status !== 'ready') {
      return;
    }
    setCommandBusy(true);
    setCommandError(null);
    postOpportunityGovernance(
      apiBaseUrl(),
      props.publisherId,
      props.channelId,
      props.environmentId,
      props.opportunityId,
      action,
      panel.governance.version,
      panel.governance.submittedRevision,
      text,
    )
      .then(() => {
        setPendingAction(null);
        setJustification('');
        setCommandBusy(false);
        props.onAccepted();
      })
      .catch((error: unknown) => {
        setCommandBusy(false);
        setCommandError(commandMessage(error));
      });
  }

  return (
    <section aria-labelledby="governance-heading">
      <h4 id="governance-heading">Governança editorial</h4>
      <p>
        PUBLISHED nesta etapa é somente autorização interna de publicação. Ainda não existe link,
        página pública ou envio à Spider.
      </p>
      <p>
        A pessoa que criou ou submeteu a revisão não pode aprová-la. Quem aprovou não pode ativar a
        publicação da mesma revisão.
      </p>
      <div aria-live="polite" aria-busy={panel.status === 'loading' || commandBusy}>
        {panel.status === 'loading' ? <p role="status">Carregando governança…</p> : null}
        {panel.status === 'unauthenticated' ? (
          <p role="status">
            A autenticação administrativa ainda não está configurada. A governança real permanece
            inacessível até existir um provedor de identidade.
          </p>
        ) : null}
        {panel.status === 'forbidden' ? (
          <p role="alert">Acesso negado para consultar a governança desta oportunidade.</p>
        ) : null}
        {panel.status === 'missing' ? (
          <p role="alert">A oportunidade não foi encontrada neste ambiente.</p>
        ) : null}
        {panel.status === 'error' ? <p role="alert">{panel.message}</p> : null}
        {panel.status === 'ready' ? (
          <GovernanceReady
            governance={panel.governance}
            events={panel.events}
            pendingAction={pendingAction}
            justification={justification}
            commandError={commandError}
            commandBusy={commandBusy}
            onPendingAction={setPendingAction}
            onJustification={setJustification}
            onRun={runAction}
          />
        ) : null}
      </div>
    </section>
  );
}

function GovernanceReady(props: {
  governance: OpportunityGovernance;
  events: LifecycleEvent[];
  pendingAction: GovernanceAction | null;
  justification: string;
  commandError: string | null;
  commandBusy: boolean;
  onPendingAction: (action: GovernanceAction | null) => void;
  onJustification: (value: string) => void;
  onRun: (action: GovernanceAction, text?: string) => void;
}) {
  const governance = props.governance;
  return (
    <div>
      <p>
        {OPPORTUNITY_STATUS_LABEL[governance.status]}
      </p>
      <p>
        Revisão corrente {governance.currentRevision}
        {governance.submittedRevision != null
          ? ` · submetida ${String(governance.submittedRevision)}`
          : ''}
        {governance.approvedRevision != null
          ? ` · aprovada ${String(governance.approvedRevision)}`
          : ''}
      </p>
      <p>
        Autorização efetiva: {governance.effectivelyPublished ? 'sim' : 'não'} · janela UTC:{' '}
        {governance.windowOpen ? 'aberta' : 'fechada'} · hierarquia:{' '}
        {governance.effectivelyAvailable ? 'disponível' : 'indisponível'}
      </p>
      {!governance.windowOpen ? (
        <p>A janela temporal da revisão corrente não está aberta em UTC.</p>
      ) : null}
      {!governance.effectivelyAvailable ? (
        <p>
          A hierarquia está suspensa ou inativa. Isso não altera o status persistido, mas impede
          ativar ou retomar.
        </p>
      ) : null}
      <h5>Linha do tempo</h5>
      {props.events.length === 0 ? (
        <p>Nenhum evento de governança registrado.</p>
      ) : (
        <ol aria-label="Linha do tempo de governança">
          {props.events.map((event) => (
            <li key={event.id}>
              {EVENT_LABEL[event.eventType] ?? event.eventType} · revisão {event.revisionNumber} ·{' '}
              {event.previousStatus} → {event.newStatus}
            </li>
          ))}
        </ol>
      )}
      <h5>Ações</h5>
      {governance.availableActions.length === 0 ? (
        <p>Nenhuma ação de governança está disponível neste estado.</p>
      ) : (
        <ul aria-label="Ações de governança">
          {governance.availableActions.map((action) => (
            <li key={action}>
              <button
                type="button"
                disabled={props.commandBusy}
                onClick={() => {
                  if (JUSTIFICATION_ACTIONS.includes(action)) {
                    props.onPendingAction(action);
                    return;
                  }
                  props.onRun(action);
                }}
              >
                {GOVERNANCE_ACTION_LABEL[action]}
              </button>
            </li>
          ))}
        </ul>
      )}
      {props.pendingAction ? (
        <form
          aria-label="Confirmar justificativa"
          onSubmit={(event) => {
            event.preventDefault();
            if (props.pendingAction) {
              props.onRun(props.pendingAction, props.justification);
            }
          }}
        >
          <label htmlFor="governance-justification">Justificativa administrativa</label>
          <textarea
            id="governance-justification"
            value={props.justification}
            onChange={(event) => {
              props.onJustification(event.target.value);
            }}
          />
          <p>
            Não inclua dados pessoais. A justificativa é texto administrativo de 10 a 500
            caracteres, sem HTML.
          </p>
          <button type="submit" disabled={props.commandBusy}>
            Confirmar {GOVERNANCE_ACTION_LABEL[props.pendingAction]}
          </button>
          <button
            type="button"
            onClick={() => {
              props.onPendingAction(null);
            }}
          >
            Cancelar
          </button>
        </form>
      ) : null}
      {props.commandBusy ? <p role="status">Aplicando decisão…</p> : null}
      {props.commandError ? <p role="alert">{props.commandError}</p> : null}
    </div>
  );
}

function commandMessage(error: unknown): string {
  if (!(error instanceof ApiClientError)) {
    return 'Não foi possível concluir a decisão.';
  }
  if (error.authenticationRequired) {
    return 'A decisão permanece bloqueada: autenticação ainda não configurada.';
  }
  if (error.code === 'SEGREGATION_OF_DUTIES_VIOLATION' || error.accessDenied) {
    return error.message;
  }
  if (error.status === 404) {
    return 'A oportunidade não foi encontrada neste ambiente.';
  }
  if (error.status === 409 || error.status === 422) {
    return error.message;
  }
  return error.message || 'Não foi possível concluir a decisão.';
}
