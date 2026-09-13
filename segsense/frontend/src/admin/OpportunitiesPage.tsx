import { Link, useNavigate } from 'react-router-dom';
import OpportunityAdmin from '../catalog/OpportunityAdmin';
import { useCatalogSelection } from './CatalogSelectionContext';

export default function OpportunitiesPage() {
  const { selection } = useCatalogSelection();
  const navigate = useNavigate();

  if (selection == null) {
    return (
      <article className="page-block">
        <p className="breadcrumb">Oportunidades</p>
        <h1>Oportunidades</h1>
        <p>
          Selecione um publicador, um canal e um ambiente no catálogo para ver as oportunidades
          deste contexto.
        </p>
        <Link className="button-primary" to="/admin/catalogo">
          Ir ao catálogo
        </Link>
      </article>
    );
  }

  return (
    <OpportunityAdmin
      publisherId={selection.publisher.id}
      channelId={selection.channel.id}
      environmentId={selection.environment.id}
      environmentName={selection.environment.name}
      publisherName={selection.publisher.name}
      channelName={selection.channel.name}
      onOpenOpportunity={(opportunityId) => {
        void navigate(`/admin/oportunidades/${opportunityId}`);
      }}
    />
  );
}
