import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ApiClientError } from '../api/errors';
import {
  fetchOpportunity,
  fetchOpportunityRevisions,
  type ContextualOpportunity,
  type OpportunityRevisionSnapshot,
} from '../api/opportunity';
import { apiBaseUrl } from '../api/systemInfo';
import OpportunityDetail from '../catalog/OpportunityDetail';
import AsyncState from '../components/AsyncState';
import { adminErrorMessage, AUTH_NOT_CONFIGURED } from '../i18n/human';
import { useCatalogSelection, type CatalogSelection } from './CatalogSelectionContext';

export default function OpportunityDetailPage() {
  const { opportunityId } = useParams();
  const { selection } = useCatalogSelection();

  if (selection == null || opportunityId == null) {
    return (
      <article className="page-block">
        <p className="breadcrumb">Oportunidades</p>
        <h1>Oportunidade</h1>
        <p>Selecione o contexto no catálogo para abrir esta oportunidade.</p>
        <Link className="button-primary" to="/admin/catalogo">
          Ir ao catálogo
        </Link>
      </article>
    );
  }

  return <OpportunityDetailLoader selection={selection} opportunityId={opportunityId} />;
}

function OpportunityDetailLoader(props: {
  selection: CatalogSelection;
  opportunityId: string;
}) {
  const [opportunity, setOpportunity] = useState<ContextualOpportunity | null>(null);
  const [history, setHistory] = useState<OpportunityRevisionSnapshot[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetchOpportunity(
      apiBaseUrl(),
      props.selection.publisher.id,
      props.selection.channel.id,
      props.selection.environment.id,
      props.opportunityId,
    )
      .then((detail) => {
        if (cancelled) {
          return detail;
        }
        setOpportunity(detail);
        return fetchOpportunityRevisions(
          apiBaseUrl(),
          props.selection.publisher.id,
          props.selection.channel.id,
          props.selection.environment.id,
          props.opportunityId,
        ).then((page) => {
          if (!cancelled) {
            setHistory(page.items);
            setError(null);
          }
          return detail;
        });
      })
      .catch((caught: unknown) => {
        if (cancelled) {
          return;
        }
        setOpportunity(null);
        if (caught instanceof ApiClientError && caught.authenticationRequired) {
          setError(AUTH_NOT_CONFIGURED);
          return;
        }
        setError(adminErrorMessage(caught, 'Não foi possível carregar a oportunidade.'));
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [props.selection, props.opportunityId]);

  return (
    <article className="page-block">
      <p className="breadcrumb">
        {props.selection.publisher.name} / {props.selection.channel.name} /{' '}
        {props.selection.environment.name}
      </p>
      <AsyncState
        loading={loading}
        loadingLabel="Carregando oportunidade…"
        error={error}
        empty={opportunity == null}
        emptyLabel="Esta oportunidade não está disponível neste contexto."
      >
        {opportunity ? (
          <OpportunityDetail
            publisherId={props.selection.publisher.id}
            channelId={props.selection.channel.id}
            environmentId={props.selection.environment.id}
            opportunity={opportunity}
            history={history}
            onReload={() => {
              return fetchOpportunity(
                apiBaseUrl(),
                props.selection.publisher.id,
                props.selection.channel.id,
                props.selection.environment.id,
                opportunity.id,
              ).then((detail) => {
                setOpportunity(detail);
                return fetchOpportunityRevisions(
                  apiBaseUrl(),
                  props.selection.publisher.id,
                  props.selection.channel.id,
                  props.selection.environment.id,
                  opportunity.id,
                ).then((page) => {
                  setHistory(page.items);
                  return detail;
                });
              });
            }}
          />
        ) : null}
      </AsyncState>
    </article>
  );
}
