import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from '../App';

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('SegSense public home', () => {
  it('answers the five positioning questions without becoming an Icatu home', () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.reject(new TypeError('Failed to fetch'))),
    );

    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>,
    );

    expect(screen.getByRole('heading', { name: /Do contexto percebido à jornada de proteção/i })).toBeInTheDocument();
    expect(
      screen.getByText(/distribui oportunidades contextualizadas e compõe jornadas explicáveis/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/Hoje o ganho é ligar um conteúdo ou canal/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Seguradoras e intermediários autorizados/i).length).toBeGreaterThan(0);
    expect(screen.getByRole('heading', { name: 'Limites técnicos desta etapa' })).toBeInTheDocument();
    expect(screen.getByText(/Satellite Contract/i)).toBeInTheDocument();
    expect(screen.getByText(/co-desenvolvimento com a seguradora/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Ver o que já opera/i })).toHaveAttribute('href', '#capacidades');
    expect(screen.getByRole('link', { name: /Ver MVP integrado sintético/i })).toHaveAttribute(
      'href',
      '/demonstracao/mvp-integrado',
    );
    expect(screen.getByRole('link', { name: /Ver cenário demonstrativo Icatu/i })).toHaveAttribute(
      'href',
      '/demonstracao/icatu',
    );
    expect(screen.queryByRole('heading', { name: 'Ambiente editorial' })).not.toBeInTheDocument();
    expect(screen.queryByText(/Em validação/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Spider não é dona/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/lavoura|agrícola|quebra de safra/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/contratar agora|simular seu seguro/i)).not.toBeInTheDocument();
  });

  it('keeps unknown public paths on the SegSense home', () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.reject(new TypeError('Failed to fetch'))),
    );

    render(
      <MemoryRouter initialEntries={['/rota-inexistente']}>
        <App />
      </MemoryRouter>,
    );

    expect(screen.getByRole('heading', { name: /Do contexto percebido/i })).toBeInTheDocument();
  });
});
