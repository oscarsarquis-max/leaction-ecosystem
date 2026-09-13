import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import OpportunityAdmin from './OpportunityAdmin';
import { ACCESS_DENIED, AUTHENTICATION_REQUIRED } from '../api/errors';

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function jsonResponse(status: number, body: unknown): Promise<Response> {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  );
}

function requestUrl(input: RequestInfo | URL): string {
  if (typeof input === 'string') {
    return input;
  }
  if (input instanceof URL) {
    return input.href;
  }
  return input.url;
}

const opportunity = {
  id: '44444444-4444-4444-8444-444444444444',
  publisherId: '11111111-1111-4111-8111-111111111111',
  channelId: '22222222-2222-4222-8222-222222222222',
  environmentId: '33333333-3333-4333-8333-333333333333',
  key: 'crop-risk',
  status: 'DRAFT',
  currentRevision: 1,
  version: 0,
  createdAt: '2026-09-04T12:00:00Z',
  updatedAt: '2026-09-04T12:00:00Z',
  createdBy: 'tester',
  updatedBy: 'tester',
  effectivelyAvailable: true,
  current: {
    id: '55555555-5555-4555-8555-555555555555',
    revisionNumber: 1,
    createdAt: '2026-09-04T12:00:00Z',
    createdBy: 'tester',
    title: 'Avaliar proteção agrícola',
    contextMode: 'STATIC',
    contextSummaryTemplate: 'Resumo estático de contexto.',
    objectiveTemplate: 'Objetivo estático de avaliação.',
    callToActionLabel: 'Avaliar',
    validFrom: null,
    validUntil: null,
    contextFields: [],
  },
};

const governanceDraft = {
  opportunityId: opportunity.id,
  status: 'DRAFT',
  currentRevision: 1,
  submittedRevision: null,
  approvedRevision: null,
  openSubmissionId: null,
  submittedBy: null,
  approvedBy: null,
  version: 0,
  effectivelyAvailable: true,
  effectivelyPublishable: true,
  effectivelyPublished: false,
  windowOpen: true,
  windowExpired: false,
  publishedMeans: 'INTERNAL_AUTHORIZATION_ONLY',
  latestDecision: null,
  availableActions: ['SUBMIT'],
};

describe('OpportunityAdmin', () => {
  it('shows an honest 401 without fake opportunities', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        jsonResponse(401, {
          code: AUTHENTICATION_REQUIRED,
          message: 'Autenticação necessária.',
          timestamp: '2026-09-04T12:00:00Z',
          correlationId: '11111111-1111-4111-8111-111111111111',
        }),
      ),
    );
    render(
      <OpportunityAdmin
        publisherId={opportunity.publisherId}
        channelId={opportunity.channelId}
        environmentId={opportunity.environmentId}
        environmentName="Home"
      />,
    );
    expect(await screen.findByText(/autenticação administrativa ainda não está configurada/i)).toBeInTheDocument();
    expect(screen.queryByRole('list', { name: 'Oportunidades' })).not.toBeInTheDocument();
    expect(screen.queryByText('Oportunidade fictícia')).not.toBeInTheDocument();
  });

  it('shows 403 and error states', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        jsonResponse(403, { code: ACCESS_DENIED, message: 'Acesso negado.' }),
      ),
    );
    const first = render(
      <OpportunityAdmin
        publisherId={opportunity.publisherId}
        channelId={opportunity.channelId}
        environmentId={opportunity.environmentId}
        environmentName="Home"
      />,
    );
    expect(await screen.findByRole('alert')).toHaveTextContent('Acesso negado');
    first.unmount();

    vi.stubGlobal('fetch', vi.fn(() => jsonResponse(500, { code: 'INTERNAL_ERROR', message: 'falha' })));
    render(
      <OpportunityAdmin
        publisherId={opportunity.publisherId}
        channelId={opportunity.channelId}
        environmentId={opportunity.environmentId}
        environmentName="Home"
      />,
    );
    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível carregar as oportunidades');
  });

  it('renders empty and populated lists from injected HTTP', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => jsonResponse(200, { items: [], page: { size: 20, next: null } })),
    );
    const empty = render(
      <OpportunityAdmin
        publisherId={opportunity.publisherId}
        channelId={opportunity.channelId}
        environmentId={opportunity.environmentId}
        environmentName="Home"
      />,
    );
    expect(screen.getByText('Carregando oportunidades…')).toBeInTheDocument();
    expect(await screen.findByText('Nenhuma oportunidade cadastrada.')).toBeInTheDocument();
    empty.unmount();

    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL) => {
        const url = requestUrl(input);
        if (url.includes('consent-notice')) {
          return jsonResponse(404, { code: 'NOT_FOUND', message: 'missing' });
        }
        if (url.includes('/governance/events')) {
          return jsonResponse(200, { items: [], page: { size: 20, next: null } });
        }
        if (url.includes('/governance')) {
          return jsonResponse(200, governanceDraft);
        }
        if (url.includes('/revisions')) {
          return jsonResponse(200, { items: [opportunity.current], page: { size: 20, next: null } });
        }
        if (url.includes(opportunity.id)) {
          return jsonResponse(200, opportunity);
        }
        return jsonResponse(200, { items: [opportunity], page: { size: 20, next: null } });
      }),
    );
    render(
      <OpportunityAdmin
        publisherId={opportunity.publisherId}
        channelId={opportunity.channelId}
        environmentId={opportunity.environmentId}
        environmentName="Home"
      />,
    );
    expect(await screen.findByRole('list', { name: 'Oportunidades' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Abrir oportunidade Avaliar proteção agrícola' }));
    expect(await screen.findByRole('tab', { name: 'Conteúdo' })).toBeInTheDocument();
    expect(await screen.findByRole('list', { name: 'Histórico de revisões' })).toBeInTheDocument();
  });

  it('validates the create form and previews placeholders without runtime values', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => jsonResponse(200, { items: [], page: { size: 20, next: null } })),
    );
    render(
      <OpportunityAdmin
        publisherId={opportunity.publisherId}
        channelId={opportunity.channelId}
        environmentId={opportunity.environmentId}
        environmentName="Home"
      />,
    );
    expect(await screen.findByText('Nenhuma oportunidade cadastrada.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Criar oportunidade' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Informe uma chave válida');

    fireEvent.change(screen.getByLabelText('Modelo de objetivo'), {
      target: { value: 'Quero avaliar proteção para {{cropType}}.' },
    });
    expect(screen.getByText(/Placeholders declarados/)).toHaveTextContent('{{cropType}}');
    expect(screen.queryByText('soja')).not.toBeInTheDocument();
  });

  it('toggles required on a context field', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => jsonResponse(200, { items: [], page: { size: 20, next: null } })),
    );
    render(
      <OpportunityAdmin
        publisherId={opportunity.publisherId}
        channelId={opportunity.channelId}
        environmentId={opportunity.environmentId}
        environmentName="Home"
      />,
    );
    expect(await screen.findByText('Nenhuma oportunidade cadastrada.')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Modo de contexto'), { target: { value: 'DYNAMIC' } });
    fireEvent.click(screen.getByRole('button', { name: 'Adicionar campo' }));
    const required = screen.getByLabelText('Campo obrigatório');
    expect(required).not.toBeChecked();
    fireEvent.click(required);
    expect(required).toBeChecked();
    fireEvent.click(required);
    expect(required).not.toBeChecked();
  });

  it('removes an added context field and keeps remaining order', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => jsonResponse(200, { items: [], page: { size: 20, next: null } })),
    );
    render(
      <OpportunityAdmin
        publisherId={opportunity.publisherId}
        channelId={opportunity.channelId}
        environmentId={opportunity.environmentId}
        environmentName="Home"
      />,
    );
    expect(await screen.findByText('Nenhuma oportunidade cadastrada.')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Modo de contexto'), { target: { value: 'DYNAMIC' } });
    fireEvent.click(screen.getByRole('button', { name: 'Adicionar campo' }));
    fireEvent.click(screen.getByRole('button', { name: 'Adicionar campo' }));
    const keys = screen.getAllByLabelText('Chave do campo');
    expect(keys[0]).toBeDefined();
    expect(keys[1]).toBeDefined();
    fireEvent.change(keys[0] as HTMLInputElement, { target: { value: 'cropType' } });
    fireEvent.change(keys[1] as HTMLInputElement, { target: { value: 'riskType' } });
    fireEvent.click(screen.getByRole('button', { name: 'Remover campo 1' }));
    expect(screen.getByLabelText('Chave do campo')).toHaveValue('riskType');
    expect(screen.queryByRole('button', { name: 'Remover campo 2' })).not.toBeInTheDocument();
  });

  it('validates UTC validity window before submit', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => jsonResponse(200, { items: [], page: { size: 20, next: null } })),
    );
    render(
      <OpportunityAdmin
        publisherId={opportunity.publisherId}
        channelId={opportunity.channelId}
        environmentId={opportunity.environmentId}
        environmentName="Home"
      />,
    );
    expect(await screen.findByText('Nenhuma oportunidade cadastrada.')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Chave'), { target: { value: 'crop-risk' } });
    fireEvent.change(screen.getByLabelText('Título'), { target: { value: 'Avaliar proteção agrícola' } });
    fireEvent.change(screen.getByLabelText('Válido a partir (UTC)'), {
      target: { value: '2026-09-10T12:00' },
    });
    fireEvent.change(screen.getByLabelText('Válido até (UTC)'), {
      target: { value: '2026-09-01T12:00' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Criar oportunidade' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'A validade final (UTC) deve ser posterior ao início.',
    );
  });

  it('reloads detail and history after creating a revision', async () => {
    const revisionTwo = {
      ...opportunity.current,
      id: '66666666-6666-4666-8666-666666666666',
      revisionNumber: 2,
      title: 'Avaliar outra proteção xx',
    };
    const updated = {
      ...opportunity,
      currentRevision: 2,
      version: 1,
      current: revisionTwo,
    };
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = requestUrl(input);
        const method = init?.method ?? 'GET';
        if (url.includes('consent-notice')) {
          return jsonResponse(404, { code: 'NOT_FOUND', message: 'missing' });
        }
        if (method === 'POST' && url.includes('/revisions')) {
          return jsonResponse(200, updated);
        }
        if (url.includes('/governance/events')) {
          return jsonResponse(200, { items: [], page: { size: 20, next: null } });
        }
        if (url.includes('/governance')) {
          return jsonResponse(200, { ...governanceDraft, version: updated.version, currentRevision: 2 });
        }
        if (url.includes('/revisions')) {
          return jsonResponse(200, {
            items: [opportunity.current, revisionTwo],
            page: { size: 20, next: null },
          });
        }
        if (url.includes(opportunity.id)) {
          return jsonResponse(200, updated);
        }
        return jsonResponse(200, { items: [opportunity], page: { size: 20, next: null } });
      }),
    );
    render(
      <OpportunityAdmin
        publisherId={opportunity.publisherId}
        channelId={opportunity.channelId}
        environmentId={opportunity.environmentId}
        environmentName="Home"
      />,
    );
    fireEvent.click(await screen.findByRole('button', { name: 'Abrir oportunidade Avaliar proteção agrícola' }));
    expect(await screen.findByRole('list', { name: 'Histórico de revisões' })).toBeInTheDocument();
    const revisionTitle = screen.getAllByLabelText('Título')[1];
    expect(revisionTitle).toBeDefined();
    fireEvent.change(revisionTitle as HTMLInputElement, { target: { value: 'Avaliar outra proteção xx' } });
    fireEvent.click(screen.getByRole('button', { name: 'Criar revisão' }));
    expect(await screen.findByText(/Revisão 2:/)).toBeInTheDocument();
    expect(screen.getByRole('list', { name: 'Histórico de revisões' })).toHaveTextContent(
      'Avaliar outra proteção xx',
    );
  });
});
