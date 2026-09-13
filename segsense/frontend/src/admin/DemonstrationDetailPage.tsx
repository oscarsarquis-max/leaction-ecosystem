import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  fetchDemonstration,
  fetchDemonstrationSources,
  postDemonstration,
  type AdminDemonstration,
  type AdminSource,
} from '../api/adminDemonstration';
import { apiBaseUrl } from '../api/systemInfo';
import { ApiClientError } from '../api/errors';
import HumanStatus from '../components/HumanStatus';
import { AUTH_NOT_CONFIGURED, adminErrorMessage } from '../i18n/human';

export default function DemonstrationDetailPage() {
  const { storyKey } = useParams();
  const [story, setStory] = useState<AdminDemonstration | null>(null);
  const [sources, setSources] = useState<AdminSource[]>([]);
  const [unauthenticated, setUnauthenticated] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState('');
  const [summary, setSummary] = useState('');
  const [audience, setAudience] = useState('');
  const [scope, setScope] = useState('');
  const [blockTitle, setBlockTitle] = useState('');
  const [blockBody, setBlockBody] = useState('');
  const [claimText, setClaimText] = useState('');
  const [sourceKey, setSourceKey] = useState('icatu-hub-home');
  const [justification, setJustification] = useState('');

  useEffect(() => {
    if (!storyKey) {
      return;
    }
    const controller = new AbortController();
    Promise.all([
      fetchDemonstration(apiBaseUrl(), storyKey, controller.signal),
      fetchDemonstrationSources(apiBaseUrl(), controller.signal),
    ])
      .then(([loaded, catalog]) => {
        setStory(loaded);
        setSources(catalog);
        setTitle(loaded.title);
        setSummary(loaded.summary);
        setAudience(loaded.intendedAudience);
        setScope(loaded.scopeNote);
        setBlockTitle(loaded.blocks[0]?.title ?? '');
        setBlockBody(loaded.blocks[0]?.body ?? '');
      })
      .catch((error: unknown) => {
        if (error instanceof ApiClientError && error.authenticationRequired) {
          setUnauthenticated(true);
          return;
        }
        setError(adminErrorMessage(error, 'Não foi possível abrir esta demonstração.'));
      });
    return () => {
      controller.abort();
    };
  }, [storyKey]);

  if (unauthenticated) {
    return (
      <article className="page-block">
        <h1>Prévia administrativa</h1>
        <HumanStatus kind="info" title="Acesso administrativo" headingLevel="h2">
          <p>{AUTH_NOT_CONFIGURED}</p>
        </HumanStatus>
      </article>
    );
  }

  async function run(action: string, extra: Record<string, unknown> = {}) {
    if (!story || storyKey === undefined) {
      return;
    }
    try {
      const next = await postDemonstration(apiBaseUrl(), `/api/v1/admin/demonstrations/${storyKey}/${action}`, {
        version: story.version,
        title,
        summary,
        intendedAudience: audience,
        scopeNote: scope,
        justification,
        blocks: [{ title: blockTitle, body: blockBody }],
        claims: claimText
          ? [{ text: claimText, sourceKey }]
          : story.claims.map((claim) => ({
              text: claim.text,
              sourceKey:
                sources.find((source) => source.id === claim.sourceId)?.key ?? sourceKey,
            })),
        ...extra,
      });
      setStory(next);
      setError(null);
    } catch (error: unknown) {
      setError(adminErrorMessage(error, 'Não foi possível concluir a ação editorial.'));
    }
  }

  function onSave(event: { preventDefault(): void }) {
    event.preventDefault();
    void run('draft');
  }

  return (
    <article className="page-block">
      <p className="breadcrumb">Demonstrações / prévia administrativa</p>
      <HumanStatus kind="warning" title="Prévia administrativa" headingLevel="h2">
        <p>Esta tela não é a página pública e não ativa Spider, Icatu ou mock.</p>
      </HumanStatus>
      {error ? <p>{error}</p> : null}
      {story ? (
        <form onSubmit={onSave}>
          <p>
            Situação: {story.workflowStatus} / publicação {story.publicationStatus}
          </p>
          <label>
            Título
            <input
              value={title}
              onChange={(event) => {
                setTitle(event.target.value);
              }}
            />
          </label>
          <label>
            Resumo
            <textarea
              value={summary}
              onChange={(event) => {
                setSummary(event.target.value);
              }}
            />
          </label>
          <label>
            Público pretendido
            <input
              value={audience}
              onChange={(event) => {
                setAudience(event.target.value);
              }}
            />
          </label>
          <label>
            Nota de escopo
            <textarea
              value={scope}
              onChange={(event) => {
                setScope(event.target.value);
              }}
            />
          </label>
          <label>
            Bloco
            <input
              value={blockTitle}
              onChange={(event) => {
                setBlockTitle(event.target.value);
              }}
            />
          </label>
          <label>
            Texto do bloco
            <textarea
              value={blockBody}
              onChange={(event) => {
                setBlockBody(event.target.value);
              }}
            />
          </label>
          <label>
            Alegação
            <textarea
              value={claimText}
              onChange={(event) => {
                setClaimText(event.target.value);
              }}
            />
          </label>
          <label>
            Fonte
            <select
              value={sourceKey}
              onChange={(event) => {
                setSourceKey(event.target.value);
              }}
            >
              {sources.map((source) => (
                <option key={source.key} value={source.key}>
                  {source.key} ({source.verificationStatus})
                </option>
              ))}
            </select>
          </label>
          <label>
            Justificativa
            <textarea
              value={justification}
              onChange={(event) => {
                setJustification(event.target.value);
              }}
            />
          </label>
          <button type="submit" className="button-secondary">
            Salvar rascunho
          </button>
          <button
            type="button"
            className="button-secondary"
            onClick={() => {
              void run('submit');
            }}
          >
            Enviar para revisão
          </button>
          <button
            type="button"
            className="button-primary"
            onClick={() => {
              void run('approve');
            }}
          >
            Aprovar
          </button>
          <button
            type="button"
            className="button-primary"
            onClick={() => {
              void run('publish');
            }}
          >
            Publicar narrativa
          </button>
          <button
            type="button"
            className="button-secondary"
            onClick={() => {
              void run('pause');
            }}
          >
            Pausar
          </button>
          <button
            type="button"
            className="button-danger"
            onClick={() => {
              void run('retire');
            }}
          >
            Retirar
          </button>
        </form>
      ) : (
        <p>Carregando…</p>
      )}
    </article>
  );
}
