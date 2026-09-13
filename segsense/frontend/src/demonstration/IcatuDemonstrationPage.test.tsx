import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from '../App';

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function requestUrl(input: RequestInfo | URL): string {
  if (typeof input === 'string') {
    return input;
  }
  if (input instanceof URL) {
    return input.href;
  }
  return input.url;
}

function jsonResponse(status: number, body: unknown): Promise<Response> {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  );
}

describe('Icatu demonstration page', () => {
  it('renders the institutional narrative without published editorial content', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL) => {
        const url = requestUrl(input);
        if (url.includes('/api/v1/public/demonstrations/')) {
          return jsonResponse(404, {
            code: 'DEMONSTRATION_NOT_PUBLISHED',
            message: 'Não há conteúdo editorial publicado para esta demonstração.',
          });
        }
        return jsonResponse(401, { code: 'AUTHENTICATION_REQUIRED', message: 'Autenticação necessária.' });
      }),
    );

    render(
      <MemoryRouter initialEntries={['/demonstracao/icatu']}>
        <App />
      </MemoryRouter>,
    );

    expect(
      screen.getAllByText(/Demonstração conceitual. Não é uma oferta de seguro/i).length,
    ).toBeGreaterThan(0);
    expect(
      screen.getByRole('heading', {
        name: 'Como um conteúdo vira um convite compreensível',
      }),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Explorar como funcionaria' })).toHaveAttribute(
      'href',
      '#mecanismo',
    );
    expect(screen.getAllByText('Já operante').length).toBeGreaterThan(0);
    expect(screen.getByText('Esta página não chama a Spider')).toBeInTheDocument();
    expect(screen.getByText('Hipótese futura')).toBeInTheDocument();
    expect(screen.getByText(/Continuidade financeira da família/i)).toBeInTheDocument();
    expect(screen.queryByText(/lavoura|agrícola|quebra de safra/i)).not.toBeInTheDocument();
    expect(
      await screen.findByText(/Não há história administrada publicada/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/contratar agora/i)).not.toBeInTheDocument();
  });

  it('keeps disclaimers when editorial content is unavailable', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.reject(new TypeError('Failed to fetch'))),
    );

    render(
      <MemoryRouter initialEntries={['/demonstracao/icatu']}>
        <App />
      </MemoryRouter>,
    );

    expect(
      await screen.findByText(/Conteúdo editorial adicional indisponível/i),
    ).toBeInTheDocument();
    expect(
      screen.getAllByText(/Demonstração conceitual. Não é uma oferta de seguro/i).length,
    ).toBeGreaterThan(0);
    expect(screen.getByRole('heading', { name: 'Como um conteúdo vira um convite compreensível' })).toBeInTheDocument();
  });

  it('treats a 503 editorial response as unavailable without changing the scenario', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL) => {
        const url = requestUrl(input);
        if (url.includes('/api/v1/public/demonstrations/')) {
          return jsonResponse(503, { code: 'SERVICE_UNAVAILABLE', message: 'Indisponível.' });
        }
        return jsonResponse(401, { code: 'AUTHENTICATION_REQUIRED', message: 'x' });
      }),
    );

    render(
      <MemoryRouter initialEntries={['/demonstracao/icatu']}>
        <App />
      </MemoryRouter>,
    );

    expect(
      await screen.findByText(/Conteúdo editorial adicional indisponível/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/integração indisponível/i)).not.toBeInTheDocument();
    expect(
      screen.getAllByText(/Demonstração conceitual. Não é uma oferta de seguro/i).length,
    ).toBeGreaterThan(0);
  });

  it('renders published editorial text as inert copy', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL) => {
        const url = requestUrl(input);
        if (url.includes('/api/v1/public/demonstrations/')) {
          return jsonResponse(200, {
            key: 'icatu-demonstracao',
            title: 'Cenario',
            summary: 'Resumo',
            intendedAudience: 'Gestor',
            scopeNote: 'Cenario demonstrativo nao oficial.',
            revisionNumber: 1,
            publishedAt: '2026-09-12T12:00:00Z',
            blocks: [
              {
                position: 1,
                title: 'Bloco',
                body: '<img src=x onerror=alert(1)> texto hostil',
              },
            ],
            references: [
              {
                url: 'https://portal-api.icatuseguros.com.br/',
                consultedOn: '2026-09-12',
                verificationStatus: 'VERIFIED',
              },
            ],
          });
        }
        return jsonResponse(401, { code: 'AUTHENTICATION_REQUIRED', message: 'x' });
      }),
    );

    const { container } = render(
      <MemoryRouter initialEntries={['/demonstracao/icatu']}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByText(/texto hostil/)).toBeInTheDocument();
    expect(container.querySelector('img[src="x"]')).toBeNull();
    expect(screen.getByRole('link', { name: /Fonte pública consultada/i })).toHaveAttribute(
      'rel',
      'noopener noreferrer',
    );
  });
});
