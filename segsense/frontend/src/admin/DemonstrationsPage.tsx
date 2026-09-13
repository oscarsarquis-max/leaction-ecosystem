import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiClientError } from '../api/errors';
import { fetchDemonstrations, type AdminDemonstration } from '../api/adminDemonstration';
import { apiBaseUrl } from '../api/systemInfo';
import HumanStatus from '../components/HumanStatus';
import { AUTH_NOT_CONFIGURED, adminErrorMessage } from '../i18n/human';

export default function DemonstrationsPage() {
  const [items, setItems] = useState<AdminDemonstration[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [unauthenticated, setUnauthenticated] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    fetchDemonstrations(apiBaseUrl(), controller.signal)
      .then(setItems)
      .catch((error: unknown) => {
        if (error instanceof ApiClientError && error.authenticationRequired) {
          setUnauthenticated(true);
          return;
        }
        setError(adminErrorMessage(error, 'Não foi possível carregar as demonstrações.'));
      });
    return () => {
      controller.abort();
    };
  }, []);

  if (unauthenticated) {
    return (
      <article className="page-block">
        <p className="breadcrumb">Demonstrações</p>
        <h1>Apresentações demonstrativas</h1>
        <HumanStatus kind="info" title="Acesso administrativo" headingLevel="h2">
          <p>{AUTH_NOT_CONFIGURED} Não há tela de entrada nesta etapa.</p>
          <p>Editar, aprovar e publicar histórias continua indisponível sem identidade.</p>
        </HumanStatus>
        <p className="admin-public-links">
          <Link className="button-primary" to="/">
            Ver apresentação pública do SegSense
          </Link>
          <Link className="button-secondary" to="/demonstracao/icatu">
            Ver cenário demonstrativo Icatu — não oficial
          </Link>
          <Link className="button-secondary" to="/demonstracao/mvp-integrado">
            Ver MVP integrado sintético — não é Icatu
          </Link>
        </p>
      </article>
    );
  }

  return (
    <article className="page-block">
      <p className="breadcrumb">Demonstrações</p>
      <h1>Apresentações demonstrativas</h1>
      <p>Prévia administrativa. Publicar aqui só altera a narrativa SegSense, nunca uma API ou seguradora.</p>
      {error ? <p>{error}</p> : null}
      {items ? (
        <ul>
          {items.map((item) => (
            <li key={item.key}>
              <Link to={`/admin/demonstracoes/${item.key}`}>{item.title}</Link>
              <span>
                {' '}
                — {item.workflowStatus} / {item.publicationStatus}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p>Carregando…</p>
      )}
    </article>
  );
}
