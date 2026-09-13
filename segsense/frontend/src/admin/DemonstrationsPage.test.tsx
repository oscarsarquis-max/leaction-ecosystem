import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from '../App';
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

describe('demonstration admin', () => {
  it('does not invent a login when the BFF returns 401', async () => {
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
      <MemoryRouter initialEntries={['/admin/demonstracoes']}>
        <App />
      </MemoryRouter>,
    );

    expect(
      await screen.findByText(/autenticação administrativa ainda não está configurada/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/Editar, aprovar e publicar histórias continua indisponível/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ver apresentação pública do SegSense' })).toHaveAttribute(
      'href',
      '/',
    );
    expect(
      screen.getByRole('link', { name: 'Ver cenário demonstrativo Icatu — não oficial' }),
    ).toHaveAttribute('href', '/demonstracao/icatu');
    expect(screen.getByRole('link', { name: 'Ver MVP integrado sintético — não é Icatu' })).toHaveAttribute(
      'href',
      '/demonstracao/mvp-integrado',
    );
    expect(screen.queryByRole('button', { name: /entrar/i })).not.toBeInTheDocument();
  });
});
