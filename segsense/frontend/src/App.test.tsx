import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { AUTHENTICATION_REQUIRED } from './api/errors';

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

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

describe('App', () => {
  it('shows backend availability from a real-shaped system info payload', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL) => {
        const url = requestUrl(input);
        if (url.includes('/api/v1/system/info')) {
          return jsonResponse(200, {
            name: 'SegSense',
            version: '0.1.0',
            applicationId: 'SEGSENSE',
            operationalState: 'UP',
          });
        }
        return jsonResponse(401, {
          code: AUTHENTICATION_REQUIRED,
          message: 'Autenticação necessária.',
          timestamp: '2026-09-04T12:00:00Z',
          correlationId: '11111111-1111-4111-8111-111111111111',
        });
      }),
    );

    renderAt('/admin');

    expect(await screen.findByRole('heading', { name: 'Ambiente editorial' })).toBeInTheDocument();
    expect(await screen.findByText('Ambiente disponível')).toBeInTheDocument();
    expect(screen.getByText(/0\.1\.0/)).toBeInTheDocument();
    expect(screen.getByText(/SEGSENSE/)).toBeInTheDocument();
    expect(
      await screen.findByText(/autenticação administrativa ainda não está configurada/i),
    ).toBeInTheDocument();
  });

  it('shows unavailability when the API cannot be reached', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.reject(new TypeError('Failed to fetch'))),
    );

    renderAt('/admin');

    expect(await screen.findByText('Ambiente indisponível')).toBeInTheDocument();
  });

  it('rejects an invalid payload without presenting it as available', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL) => {
        const url = requestUrl(input);
        if (url.includes('/api/v1/system/info')) {
          return jsonResponse(200, {
            name: 'SegSense',
            version: '0.1.0',
            operationalState: 'UP',
          });
        }
        return jsonResponse(401, {
          code: AUTHENTICATION_REQUIRED,
          message: 'Autenticação necessária.',
        });
      }),
    );

    renderAt('/admin');

    expect(await screen.findByText('Ambiente indisponível')).toBeInTheDocument();
  });
});
