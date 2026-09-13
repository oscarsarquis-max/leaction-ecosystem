import { useEffect, useState, type SyntheticEvent } from 'react';
import { ApiClientError } from '../api/errors';
import {
  CHANNEL_TYPES,
  CHANNEL_TYPE_LABEL,
  ENVIRONMENT_TYPES,
  ENVIRONMENT_TYPE_LABEL,
  STATUS_LABEL,
  fetchChannels,
  fetchEnvironments,
  fetchPublishers,
  type Channel,
  type ChannelType,
  type ContextualEnvironment,
  type EnvironmentType,
  type Publisher,
} from '../api/catalog';
import { apiBaseUrl } from '../api/systemInfo';
import OpportunityAdmin from './OpportunityAdmin';
import type { CatalogSelection } from '../admin/CatalogSelectionContext';
import { AUTH_NOT_CONFIGURED } from '../i18n/human';

type CatalogState =
  | { status: 'loading' }
  | { status: 'unauthenticated' }
  | { status: 'error'; detail: string }
  | { status: 'ready'; publishers: Publisher[] };

const KEY_PATTERN = '^[a-z][a-z0-9-]{2,49}$';

export default function CatalogAdmin(props: {
  onReadyForOpportunities?: (selection: CatalogSelection) => void;
}) {
  const [state, setState] = useState<CatalogState>({ status: 'loading' });
  const [selectedPublisher, setSelectedPublisher] = useState<Publisher | null>(null);
  const [channels, setChannels] = useState<Channel[] | null>(null);
  const [channelsStatus, setChannelsStatus] = useState<'idle' | 'loading' | 'error'>('idle');
  const [selectedChannel, setSelectedChannel] = useState<Channel | null>(null);
  const [environments, setEnvironments] = useState<ContextualEnvironment[] | null>(null);
  const [environmentsStatus, setEnvironmentsStatus] = useState<'idle' | 'loading' | 'error'>('idle');
  const [selectedEnvironment, setSelectedEnvironment] = useState<ContextualEnvironment | null>(
    null,
  );
  const [publisherFormError, setPublisherFormError] = useState<string | null>(null);
  const [publisherKey, setPublisherKey] = useState('');
  const [publisherName, setPublisherName] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    fetchPublishers(apiBaseUrl(), controller.signal)
      .then((page) => {
        if (!cancelled) {
          setState({ status: 'ready', publishers: page.items });
        }
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        if (error instanceof ApiClientError && error.authenticationRequired) {
          setState({ status: 'unauthenticated' });
          return;
        }
        setState({
          status: 'error',
          detail: 'Não foi possível carregar o catálogo administrativo.',
        });
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, []);

  function openChannels(publisher: Publisher) {
    setSelectedPublisher(publisher);
    setSelectedChannel(null);
    setSelectedEnvironment(null);
    setEnvironments(null);
    setChannelsStatus('loading');
    fetchChannels(apiBaseUrl(), publisher.id)
      .then((page) => {
        setChannels(page.items);
        setChannelsStatus('idle');
      })
      .catch(() => {
        setChannelsStatus('error');
      });
  }

  function openEnvironments(channel: Channel) {
    if (!selectedPublisher) {
      return;
    }
    setSelectedChannel(channel);
    setSelectedEnvironment(null);
    setEnvironmentsStatus('loading');
    fetchEnvironments(apiBaseUrl(), selectedPublisher.id, channel.id)
      .then((page) => {
        setEnvironments(page.items);
        setEnvironmentsStatus('idle');
      })
      .catch(() => {
        setEnvironmentsStatus('error');
      });
  }

  function onCreatePublisher(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    const key = publisherKey.trim().toLowerCase();
    const name = publisherName.trim();
    if (!new RegExp(KEY_PATTERN).test(key)) {
      setPublisherFormError('Informe uma chave válida (minúsculas, 3 a 50 caracteres).');
      return;
    }
    if (name.length < 3 || name.length > 120) {
      setPublisherFormError('Informe um nome entre 3 e 120 caracteres.');
      return;
    }
    setPublisherFormError(
      'A criação pela interface permanece bloqueada: autenticação ainda não configurada.',
    );
  }

  return (
    <section className="catalog" aria-labelledby="catalog-heading">
      <p className="breadcrumb">Catálogo</p>
      <h1 id="catalog-heading">Catálogo</h1>
      <p>Organize onde cada oportunidade poderá aparecer.</p>
      <p>
        Publicadores, canais e ambientes contextuais são locais ao SegSense. Sem IdP, a API
        administrativa responde 401 e esta tela não simula cadastros.
      </p>
      <div aria-live="polite" aria-busy={state.status === 'loading'}>
        {state.status === 'loading' ? (
          <p role="status">Carregando catálogo administrativo…</p>
        ) : null}
        {state.status === 'unauthenticated' ? (
          <p role="status">{AUTH_NOT_CONFIGURED}</p>
        ) : null}
        {state.status === 'error' ? <p role="alert">{state.detail}</p> : null}
        {state.status === 'ready' ? (
          <div>
            <div className="catalog-columns">
              <section>
                <h2>Publicadores</h2>
                {state.publishers.length === 0 ? (
                  <p>Nenhum publicador cadastrado.</p>
                ) : (
                  <ul aria-label="Publicadores" className="catalog-list">
                    {state.publishers.map((publisher) => (
                      <li key={publisher.id}>
                        <button
                          type="button"
                          onClick={() => {
                            openChannels(publisher);
                          }}
                          aria-label={`Abrir canais de ${publisher.name}`}
                          aria-current={selectedPublisher?.id === publisher.id}
                        >
                          {publisher.name}
                        </button>
                        <span>
                          {STATUS_LABEL[publisher.status]}
                          {publisher.effectivelyAvailable ? '' : ' · indisponível'}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
                <form onSubmit={onCreatePublisher} aria-label="Novo publicador">
                  <div>
                    <label htmlFor="publisher-key">Chave</label>
                    <input
                      id="publisher-key"
                      name="key"
                      value={publisherKey}
                      onChange={(event) => {
                        setPublisherKey(event.target.value);
                      }}
                      autoComplete="off"
                    />
                  </div>
                  <div>
                    <label htmlFor="publisher-name">Nome</label>
                    <input
                      id="publisher-name"
                      name="name"
                      value={publisherName}
                      onChange={(event) => {
                        setPublisherName(event.target.value);
                      }}
                      autoComplete="off"
                    />
                  </div>
                  {publisherFormError ? <p role="alert">{publisherFormError}</p> : null}
                  <button type="submit">Criar publicador</button>
                </form>
              </section>
              {selectedPublisher ? (
                <section>
                  <h2>Canais de {selectedPublisher.name}</h2>
                  {channelsStatus === 'loading' ? (
                    <p role="status">Carregando canais…</p>
                  ) : null}
                  {channelsStatus === 'error' ? (
                    <p role="alert">Não foi possível carregar os canais.</p>
                  ) : null}
                  {channels && channels.length === 0 ? <p>Nenhum canal cadastrado.</p> : null}
                  {channels && channels.length > 0 ? (
                    <ul aria-label="Canais" className="catalog-list">
                      {channels.map((channel) => (
                        <li key={channel.id}>
                          <button
                            type="button"
                            onClick={() => {
                              openEnvironments(channel);
                            }}
                            aria-label={`Abrir ambientes de ${channel.name}`}
                            aria-current={selectedChannel?.id === channel.id}
                          >
                            {channel.name}
                          </button>
                          <span>
                            {CHANNEL_TYPE_LABEL[channel.type]} · {STATUS_LABEL[channel.status]}
                          </span>
                        </li>
                      ))}
                    </ul>
                  ) : null}
                  <ChannelPreviewFields />
                </section>
              ) : null}
              {selectedChannel ? (
                <section>
                  <h2>Ambientes de {selectedChannel.name}</h2>
                  {environmentsStatus === 'loading' ? (
                    <p role="status">Carregando ambientes…</p>
                  ) : null}
                  {environmentsStatus === 'error' ? (
                    <p role="alert">Não foi possível carregar os ambientes.</p>
                  ) : null}
                  {environments && environments.length === 0 ? (
                    <p>Nenhum ambiente cadastrado.</p>
                  ) : null}
                  {environments && environments.length > 0 ? (
                    <ul aria-label="Ambientes" className="catalog-list">
                      {environments.map((environment) => (
                        <li key={environment.id}>
                          <button
                            type="button"
                            onClick={() => {
                              setSelectedEnvironment(environment);
                            }}
                            aria-label={`Abrir oportunidades de ${environment.name}`}
                            aria-current={selectedEnvironment?.id === environment.id}
                          >
                            {environment.name}
                          </button>
                          <span>
                            {ENVIRONMENT_TYPE_LABEL[environment.type]} ·{' '}
                            {STATUS_LABEL[environment.status]}
                          </span>
                        </li>
                      ))}
                    </ul>
                  ) : null}
                  <EnvironmentPreviewFields />
                </section>
              ) : null}
            </div>
            {selectedPublisher && selectedChannel && selectedEnvironment ? (
              <div className="catalog-context">
                <p>
                  Contexto selecionado: {selectedPublisher.name} › {selectedChannel.name} ›{' '}
                  {selectedEnvironment.name}
                </p>
                {props.onReadyForOpportunities ? (
                  <button
                    type="button"
                    className="button-primary"
                    onClick={() => {
                      props.onReadyForOpportunities?.({
                        publisher: selectedPublisher,
                        channel: selectedChannel,
                        environment: selectedEnvironment,
                      });
                    }}
                  >
                    Ver oportunidades
                  </button>
                ) : (
                  <OpportunityAdmin
                    publisherId={selectedPublisher.id}
                    channelId={selectedChannel.id}
                    environmentId={selectedEnvironment.id}
                    environmentName={selectedEnvironment.name}
                  />
                )}
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </section>
  );
}

function ChannelPreviewFields() {
  const [type, setType] = useState<ChannelType>('WEBSITE');
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
      }}
      aria-label="Novo canal"
    >
      <div>
        <label htmlFor="channel-key">Chave do canal</label>
        <input id="channel-key" name="channelKey" autoComplete="off" />
      </div>
      <div>
        <label htmlFor="channel-name">Nome do canal</label>
        <input id="channel-name" name="channelName" autoComplete="off" />
      </div>
      <div>
        <label htmlFor="channel-type">Tipo</label>
        <select
          id="channel-type"
          name="channelType"
          value={type}
          onChange={(event) => {
            setType(event.target.value as ChannelType);
          }}
        >
          {CHANNEL_TYPES.map((option) => (
            <option key={option} value={option}>
              {CHANNEL_TYPE_LABEL[option]}
            </option>
          ))}
        </select>
      </div>
      <p>Envio real bloqueado até existir autenticação.</p>
    </form>
  );
}

function EnvironmentPreviewFields() {
  const [type, setType] = useState<EnvironmentType>('PAGE');
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
      }}
      aria-label="Novo ambiente"
    >
      <div>
        <label htmlFor="environment-key">Chave do ambiente</label>
        <input id="environment-key" name="environmentKey" autoComplete="off" />
      </div>
      <div>
        <label htmlFor="environment-name">Nome do ambiente</label>
        <input id="environment-name" name="environmentName" autoComplete="off" />
      </div>
      <div>
        <label htmlFor="environment-type">Tipo</label>
        <select
          id="environment-type"
          name="environmentType"
          value={type}
          onChange={(event) => {
            setType(event.target.value as EnvironmentType);
          }}
        >
          {ENVIRONMENT_TYPES.map((option) => (
            <option key={option} value={option}>
              {ENVIRONMENT_TYPE_LABEL[option]}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="environment-url">URL canônica (opcional)</label>
        <input id="environment-url" name="canonicalUrl" type="url" autoComplete="off" />
      </div>
      <p>Envio real bloqueado até existir autenticação.</p>
    </form>
  );
}
