import { useEffect, useState } from 'react';
import { ApiClientError } from '../api/errors';
import {
  createOpportunity,
  fetchOpportunities,
  fetchOpportunity,
  fetchOpportunityRevisions,
  OPPORTUNITY_STATUS_LABEL,
  type ContextualOpportunity,
  type OpportunityRevisionSnapshot,
} from '../api/opportunity';
import { apiBaseUrl } from '../api/systemInfo';
import OpportunityDetail, { OpportunityForm } from './OpportunityDetail';
import { adminErrorMessage, AUTH_NOT_CONFIGURED } from '../i18n/human';

type ListState =
  | { status: 'loading' }
  | { status: 'unauthenticated' }
  | { status: 'forbidden' }
  | { status: 'error' }
  | { status: 'ready'; items: ContextualOpportunity[] };

export default function OpportunityAdmin(props: {
  publisherId: string;
  channelId: string;
  environmentId: string;
  environmentName: string;
  publisherName?: string;
  channelName?: string;
  onOpenOpportunity?: (opportunityId: string) => void;
}) {
  const [list, setList] = useState<ListState>({ status: 'loading' });
  const [selected, setSelected] = useState<ContextualOpportunity | null>(null);
  const [history, setHistory] = useState<OpportunityRevisionSnapshot[] | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    fetchOpportunities(
      apiBaseUrl(),
      props.publisherId,
      props.channelId,
      props.environmentId,
      controller.signal,
    )
      .then((page) => {
        if (!cancelled) {
          setList({ status: 'ready', items: page.items });
        }
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        if (error instanceof ApiClientError && error.authenticationRequired) {
          setList({ status: 'unauthenticated' });
          return;
        }
        if (error instanceof ApiClientError && error.accessDenied) {
          setList({ status: 'forbidden' });
          return;
        }
        setList({ status: 'error' });
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [props.publisherId, props.channelId, props.environmentId]);

  function reloadDetail(opportunityId: string) {
    return fetchOpportunity(
      apiBaseUrl(),
      props.publisherId,
      props.channelId,
      props.environmentId,
      opportunityId,
    ).then((detail) => {
      setSelected(detail);
      return fetchOpportunityRevisions(
        apiBaseUrl(),
        props.publisherId,
        props.channelId,
        props.environmentId,
        opportunityId,
      ).then((page) => {
        setHistory(page.items);
        return detail;
      });
    });
  }

  function openOpportunity(item: ContextualOpportunity) {
    if (props.onOpenOpportunity) {
      props.onOpenOpportunity(item.id);
      return;
    }
    reloadDetail(item.id).catch((error: unknown) => {
      setFormError(adminErrorMessage(error, 'Não foi possível carregar a oportunidade.'));
    });
  }

  const breadcrumb = [props.publisherName, props.channelName, props.environmentName]
    .filter((part): part is string => Boolean(part))
    .join(' / ');

  return (
    <section aria-labelledby="opportunity-heading">
      {breadcrumb ? <p className="breadcrumb">{breadcrumb}</p> : null}
      <h1 id="opportunity-heading">Oportunidades de {props.environmentName}</h1>
      <p>
        Rascunhos editoriais locais. A governança desta etapa autoriza publicação interna; ainda não
        interpreta contexto e não envia objetivo à Spider.
      </p>
      <div aria-live="polite" aria-busy={list.status === 'loading'}>
        {list.status === 'loading' ? <p role="status">Carregando oportunidades…</p> : null}
        {list.status === 'unauthenticated' ? (
          <p role="status">{AUTH_NOT_CONFIGURED}</p>
        ) : null}
        {list.status === 'forbidden' ? (
          <p role="alert">Acesso negado para consultar oportunidades deste ambiente.</p>
        ) : null}
        {list.status === 'error' ? (
          <p role="alert">Não foi possível carregar as oportunidades.</p>
        ) : null}
        {list.status === 'ready' && list.items.length === 0 ? (
          <p>Nenhuma oportunidade cadastrada.</p>
        ) : null}
        {list.status === 'ready' && list.items.length > 0 ? (
          <ul aria-label="Oportunidades" className="catalog-list">
            {list.items.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => {
                    openOpportunity(item);
                  }}
                  aria-label={`Abrir oportunidade ${item.current.title}`}
                >
                  {item.current.title}
                </button>
                <span>
                  {OPPORTUNITY_STATUS_LABEL[item.status]}
                  {item.effectivelyAvailable ? '' : ' · indisponível'}
                </span>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
      <OpportunityForm
        title="Nova oportunidade"
        includeKey
        submitLabel="Criar oportunidade"
        error={formError}
        onSubmit={(draft) => {
          createOpportunity(
            apiBaseUrl(),
            props.publisherId,
            props.channelId,
            props.environmentId,
            draft,
          )
            .then((created) => {
              setFormError(null);
              setSelected(created);
              setList((current) =>
                current.status === 'ready'
                  ? { status: 'ready', items: [...current.items, created] }
                  : { status: 'ready', items: [created] },
              );
            })
            .catch((error: unknown) => {
              setFormError(adminErrorMessage(error, 'Não foi possível criar a oportunidade.'));
            });
        }}
      />
      {selected && props.onOpenOpportunity == null ? (
        <OpportunityDetail
          publisherId={props.publisherId}
          channelId={props.channelId}
          environmentId={props.environmentId}
          opportunity={selected}
          history={history}
          formError={formError}
          onFormError={setFormError}
          onReload={() => reloadDetail(selected.id)}
        />
      ) : null}
    </section>
  );
}
