import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import CatalogAdmin from './CatalogAdmin';
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

describe('CatalogAdmin', () => {
  it('shows an honest 401 without fake catalog rows', async () => {
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

    render(<CatalogAdmin />);

    expect(await screen.findByText(/autenticação administrativa ainda não está configurada/i)).toBeInTheDocument();
    expect(screen.queryByRole('list', { name: 'Publicadores' })).not.toBeInTheDocument();
    expect(screen.queryByText('Publicador fictício')).not.toBeInTheDocument();
  });

  it('renders an empty publisher list from injected HTTP', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => jsonResponse(200, { items: [], page: { size: 20, next: null } })),
    );

    render(<CatalogAdmin />);
    expect(screen.getByText('Carregando catálogo administrativo…')).toBeInTheDocument();
    expect(await screen.findByText('Nenhum publicador cadastrado.')).toBeInTheDocument();
  });

  it('renders publishers from injected HTTP', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        jsonResponse(200, {
          items: [
            {
              id: '11111111-1111-4111-8111-111111111111',
              key: 'acme',
              name: 'Acme Mídia',
              status: 'DRAFT',
              version: 0,
              createdAt: '2026-09-04T12:00:00Z',
              updatedAt: '2026-09-04T12:00:00Z',
              createdBy: 'tester',
              updatedBy: 'tester',
              effectivelyAvailable: false,
            },
          ],
          page: { size: 20, next: null },
        }),
      ),
    );
    render(<CatalogAdmin />);
    expect(await screen.findByRole('list', { name: 'Publicadores' })).toBeInTheDocument();
    expect(screen.getByText('Acme Mídia')).toBeInTheDocument();
  });

  it('validates the publisher form before submit', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => jsonResponse(200, { items: [], page: { size: 20, next: null } })),
    );
    render(<CatalogAdmin />);
    expect(await screen.findByText('Nenhum publicador cadastrado.')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Criar publicador' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Informe uma chave válida');
  });

  it('navigates publisher → channel → environment from injected HTTP', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL) => {
        const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
        if (url.includes('/opportunities')) {
          return jsonResponse(200, { items: [], page: { size: 20, next: null } });
        }
        if (url.includes('/environments')) {
          return jsonResponse(200, {
            items: [
              {
                id: '33333333-3333-4333-8333-333333333333',
                publisherId: '11111111-1111-4111-8111-111111111111',
                channelId: '22222222-2222-4222-8222-222222222222',
                key: 'home',
                name: 'Home',
                type: 'PAGE',
                canonicalUrl: 'https://example.com/home',
                status: 'DRAFT',
                version: 0,
                createdAt: '2026-09-04T12:00:00Z',
                updatedAt: '2026-09-04T12:00:00Z',
                createdBy: 'tester',
                updatedBy: 'tester',
                effectivelyAvailable: false,
              },
            ],
            page: { size: 20, next: null },
          });
        }
        if (url.includes('/channels')) {
          return jsonResponse(200, {
            items: [
              {
                id: '22222222-2222-4222-8222-222222222222',
                publisherId: '11111111-1111-4111-8111-111111111111',
                key: 'portal',
                name: 'Portal',
                type: 'WEBSITE',
                status: 'DRAFT',
                version: 0,
                createdAt: '2026-09-04T12:00:00Z',
                updatedAt: '2026-09-04T12:00:00Z',
                createdBy: 'tester',
                updatedBy: 'tester',
                effectivelyAvailable: false,
              },
            ],
            page: { size: 20, next: null },
          });
        }
        return jsonResponse(200, {
          items: [
            {
              id: '11111111-1111-4111-8111-111111111111',
              key: 'acme',
              name: 'Acme Mídia',
              status: 'ACTIVE',
              version: 1,
              createdAt: '2026-09-04T12:00:00Z',
              updatedAt: '2026-09-04T12:00:00Z',
              createdBy: 'tester',
              updatedBy: 'tester',
              effectivelyAvailable: true,
            },
          ],
          page: { size: 20, next: null },
        });
      }),
    );

    render(<CatalogAdmin />);
    fireEvent.click(await screen.findByRole('button', { name: 'Abrir canais de Acme Mídia' }));
    expect(await screen.findByRole('list', { name: 'Canais' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Abrir ambientes de Portal' }));
    expect(await screen.findByRole('list', { name: 'Ambientes' })).toBeInTheDocument();
    expect(screen.getByText('Home')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Abrir oportunidades de Home' }));
    expect(await screen.findByText('Nenhuma oportunidade cadastrada.')).toBeInTheDocument();
  });

  it('shows error state when the catalog request fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => jsonResponse(500, { code: 'INTERNAL_ERROR', message: 'falha' })),
    );
    render(<CatalogAdmin />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível carregar');
  });
});
