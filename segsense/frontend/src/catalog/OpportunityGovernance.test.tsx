import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import OpportunityGovernancePanel from './OpportunityGovernance';
import { AUTHENTICATION_REQUIRED } from '../api/errors';

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

const ids = {
  publisherId: '11111111-1111-4111-8111-111111111111',
  channelId: '22222222-2222-4222-8222-222222222222',
  environmentId: '33333333-3333-4333-8333-333333333333',
  opportunityId: '44444444-4444-4444-8444-444444444444',
};

const governance = {
  opportunityId: ids.opportunityId,
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

describe('OpportunityGovernancePanel', () => {
  it('shows an honest 401 without fake actions', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        jsonResponse(401, {
          code: AUTHENTICATION_REQUIRED,
          message: 'Autenticação necessária.',
        }),
      ),
    );
    render(
      <OpportunityGovernancePanel
        publisherId={ids.publisherId}
        channelId={ids.channelId}
        environmentId={ids.environmentId}
        opportunityId={ids.opportunityId}
        version={0}
        onAccepted={() => undefined}
      />,
    );
    expect(
      await screen.findByText(/autenticação administrativa ainda não está configurada/i),
    ).toBeInTheDocument();
    expect(screen.queryByRole('list', { name: 'Ações de governança' })).not.toBeInTheDocument();
  });

  it('submits from backend availableActions and reloads', async () => {
    const onAccepted = vi.fn();
    const submitted = {
      ...governance,
      status: 'UNDER_REVIEW',
      submittedRevision: 1,
      version: 1,
      availableActions: ['RETURN_FOR_CHANGES', 'APPROVE', 'REJECT'],
    };
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = requestUrl(input);
        const method = init?.method ?? 'GET';
        if (method === 'POST' && url.includes('/governance/submit')) {
          return jsonResponse(200, submitted);
        }
        if (url.includes('/governance/events')) {
          return jsonResponse(200, {
            items: [
              {
                id: '77777777-7777-4777-8777-777777777777',
                opportunityId: ids.opportunityId,
                revisionNumber: 1,
                eventType: 'SUBMITTED',
                previousStatus: 'DRAFT',
                newStatus: 'UNDER_REVIEW',
                actorSubjectId: 'author',
                occurredAt: '2026-09-04T12:00:00Z',
                justification: null,
                correlationId: '88888888-8888-4888-8888-888888888888',
              },
            ],
            page: { size: 20, next: null },
          });
        }
        if (url.includes('/governance')) {
          return jsonResponse(200, governance);
        }
        return jsonResponse(500, { code: 'INTERNAL_ERROR', message: 'falha' });
      }),
    );
    render(
      <OpportunityGovernancePanel
        publisherId={ids.publisherId}
        channelId={ids.channelId}
        environmentId={ids.environmentId}
        opportunityId={ids.opportunityId}
        version={0}
        onAccepted={onAccepted}
      />,
    );
    expect(await screen.findByText(/autorização interna/)).toBeInTheDocument();
    fireEvent.click(await screen.findByRole('button', { name: 'Submeter revisão' }));
    await waitFor(() => {
      expect(onAccepted).toHaveBeenCalled();
    });
  });

  it('asks justification and shows 422 from the backend', async () => {
    const underReview = {
      ...governance,
      status: 'UNDER_REVIEW',
      submittedRevision: 1,
      availableActions: ['RETURN_FOR_CHANGES'],
    };
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = requestUrl(input);
        const method = init?.method ?? 'GET';
        if (method === 'POST') {
          return jsonResponse(422, {
            code: 'INVALID_GOVERNANCE_TRANSITION',
            message: 'A transição de governança solicitada não é permitida neste estado.',
          });
        }
        if (url.includes('/governance/events')) {
          return jsonResponse(200, { items: [], page: { size: 20, next: null } });
        }
        return jsonResponse(200, underReview);
      }),
    );
    render(
      <OpportunityGovernancePanel
        publisherId={ids.publisherId}
        channelId={ids.channelId}
        environmentId={ids.environmentId}
        opportunityId={ids.opportunityId}
        version={0}
        onAccepted={() => undefined}
      />,
    );
    fireEvent.click(await screen.findByRole('button', { name: 'Devolver para alterações' }));
    expect(screen.getByText(/Não inclua dados pessoais/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Justificativa administrativa'), {
      target: { value: 'Ajustar o resumo editorial.' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar Devolver para alterações' }));
    expect(
      await screen.findByText(/transição de governança solicitada não é permitida/),
    ).toBeInTheDocument();
  });
});
