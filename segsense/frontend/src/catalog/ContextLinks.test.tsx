import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import ContextLinksPanel from './ContextLinks';
import { AUTHENTICATION_REQUIRED } from '../api/errors';
import type { ContextualOpportunity } from '../api/opportunity';

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

const opportunity: ContextualOpportunity = {
  id: '44444444-4444-4444-8444-444444444444',
  publisherId: '11111111-1111-4111-8111-111111111111',
  channelId: '22222222-2222-4222-8222-222222222222',
  environmentId: '33333333-3333-4333-8333-333333333333',
  key: 'crop-risk',
  status: 'PUBLISHED',
  currentRevision: 1,
  version: 4,
  createdAt: '2026-09-04T12:00:00Z',
  updatedAt: '2026-09-04T12:00:00Z',
  createdBy: 'tester',
  updatedBy: 'activator',
  effectivelyAvailable: true,
  effectivelyPublished: true,
  current: {
    id: '55555555-5555-4555-8555-555555555555',
    revisionNumber: 1,
    createdAt: '2026-09-04T12:00:00Z',
    createdBy: 'tester',
    title: 'Avaliar protecao agricola',
    contextMode: 'DYNAMIC',
    contextSummaryTemplate: 'Resumo para {{riskType}} no ambiente.',
    objectiveTemplate: 'Objetivo interno nao publico.',
    callToActionLabel: 'Avaliar',
    validFrom: null,
    validUntil: null,
    contextFields: [
      {
        key: 'riskType',
        label: 'Tipo de risco',
        type: 'ENUM',
        required: true,
        source: 'PUBLISHER',
        classification: 'NON_PERSONAL',
        position: 0,
        allowedValues: ['quebra-safra', 'seca'],
      },
      {
        key: 'comment',
        label: 'Comentario',
        type: 'TEXT',
        required: false,
        source: 'USER',
        classification: 'NON_PERSONAL',
        position: 1,
        allowedValues: [],
      },
    ],
  },
};

describe('ContextLinksPanel', () => {
  it('shows honest 401 without fake links', async () => {
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
      <ContextLinksPanel
        publisherId={opportunity.publisherId}
        channelId={opportunity.channelId}
        environmentId={opportunity.environmentId}
        opportunity={opportunity}
      />,
    );
    expect(await screen.findByText(/autenticação administrativa ainda não está configurada/i)).toBeInTheDocument();
    expect(screen.queryByText('http://evil.example')).not.toBeInTheDocument();
  });

  it('issues a link once and does not recover the url from the list', async () => {
    const issuedUrl = 'http://127.0.0.1:5178/c/' + 'A'.repeat(43);
    let issued = false;
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = requestUrl(input);
        if (init?.method === 'POST' && url.endsWith('/links')) {
          issued = true;
          return jsonResponse(201, {
            id: '66666666-6666-4666-8666-666666666666',
            placementKey: 'artigo-quebra-safra-2026',
            label: 'Artigo quebra de safra',
            status: 'ACTIVE',
            effectiveStatus: 'ACTIVE',
            revisionNumber: 1,
            issuedAt: '2026-09-04T12:00:00Z',
            issuedBy: 'link-manager',
            expiresAt: '2026-10-01T00:00:00Z',
            version: 0,
            token: 'A'.repeat(43),
            publicUrl: issuedUrl,
            tokenHint: 'AAAAAAAA',
            publisherContext: [{ fieldKey: 'riskType', type: 'ENUM', value: 'quebra-safra' }],
          });
        }
        return jsonResponse(200, {
          items: issued
            ? [
                {
                  id: '66666666-6666-4666-8666-666666666666',
                  placementKey: 'artigo-quebra-safra-2026',
                  label: 'Artigo quebra de safra',
                  status: 'ACTIVE',
                  effectiveStatus: 'ACTIVE',
                  revisionNumber: 1,
                  issuedAt: '2026-09-04T12:00:00Z',
                  issuedBy: 'link-manager',
                  expiresAt: '2026-10-01T00:00:00Z',
                  revokedAt: null,
                  revokedBy: null,
                  revocationReason: null,
                  version: 0,
                  tokenHint: 'AAAAAAAA',
                  publisherContext: [{ fieldKey: 'riskType', type: 'ENUM', value: 'quebra-safra' }],
                },
              ]
            : [],
          page: { size: 20, next: null },
        });
      }),
    );
    const writeText = vi.fn(() => Promise.resolve());
    Object.assign(navigator, { clipboard: { writeText } });
    render(
      <ContextLinksPanel
        publisherId={opportunity.publisherId}
        channelId={opportunity.channelId}
        environmentId={opportunity.environmentId}
        opportunity={opportunity}
      />,
    );
    expect(await screen.findByText('Nenhum link contextual emitido.')).toBeInTheDocument();
    expect(screen.queryByLabelText('Comentario')).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Posicionamento'), {
      target: { value: 'artigo-quebra-safra-2026' },
    });
    fireEvent.change(screen.getByLabelText('Nome administrativo'), {
      target: { value: 'Artigo quebra de safra' },
    });
    fireEvent.change(screen.getByLabelText(/Tipo de risco/), { target: { value: 'quebra-safra' } });
    fireEvent.click(screen.getByRole('button', { name: 'Revisar emissão' }));
    fireEvent.click(screen.getByRole('button', { name: 'Emitir link' }));
    expect(await screen.findByDisplayValue(issuedUrl)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Copiar endereço' }));
    expect(writeText).toHaveBeenCalledWith(issuedUrl);
    expect(await screen.findByText('Endereço copiado')).toBeInTheDocument();
    expect(await screen.findByText(/Artigo quebra de safra — Ativo/)).toBeInTheDocument();
    const list = screen.getByRole('list', { name: 'Links contextuais emitidos' });
    expect(list).not.toHaveTextContent(issuedUrl);
    fireEvent.click(screen.getByRole('button', { name: 'Concluir' }));
    expect(screen.queryByDisplayValue(issuedUrl)).not.toBeInTheDocument();
    expect(screen.queryByText(issuedUrl)).not.toBeInTheDocument();
  });
});
