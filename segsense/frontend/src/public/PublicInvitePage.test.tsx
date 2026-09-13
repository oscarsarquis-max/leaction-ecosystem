import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from '../App';

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

const TOKEN = 'A'.repeat(43);

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

function systemInfo() {
  return {
    name: 'SegSense',
    version: '0.1.0',
    applicationId: 'SEGSENSE',
    operationalState: 'UP',
  };
}

function continuityEnvelope() {
  return {
    ...envelope(),
    continuity: {
      available: true,
      noticeVersion: 1,
      purposeTitle: 'Uso no SegSense',
      purposeDescription: 'Continuar esta jornada apenas no SegSense, sem envio externo.',
      transparencyText: 'As informações desta etapa permanecem no SegSense e não vão a seguradora.',
      noExternalSharingStatement: 'Não há compartilhamento externo nesta etapa.',
    },
  };
}

function instancePayload() {
  return {
    status: 'AWAITING_INPUT',
    expectedVersion: 0,
    expiresAt: '2026-09-12T12:00:00Z',
    noticeVersion: 1,
    valuesUnavailable: false,
    credentialIssued: true,
    instanceCredential: 'B'.repeat(43),
    sessionEndsOnReload: true,
    collectibleFields: [
      { key: 'area', label: 'Área plantada', type: 'NUMBER', required: true, allowedValues: [], value: null },
      { key: 'harvestDate', label: 'Data da colheita', type: 'DATE', required: true, allowedValues: [], value: null },
      { key: 'comment', label: 'Comentário adicional', type: 'TEXT', required: false, allowedValues: [], value: null },
      { key: 'irrigated', label: 'Irrigado', type: 'BOOLEAN', required: true, allowedValues: [], value: null },
      { key: 'cropKind', label: 'Cultura', type: 'ENUM', required: false, allowedValues: ['soja', 'milho'], value: null },
    ],
  };
}

function envelope() {
  return {
    applicationId: 'SEGSENSE',
    resolutionId: '99999999-9999-4999-8999-999999999999',
    title: 'Proteção para situações de quebra de safra',
    callToActionLabel: 'Contratar agora',
    contextMode: 'DYNAMIC',
    contextSummary: {
      template: 'Resumo para {{riskType}}.<img src=x onerror=alert(1)>',
      publisherValues: { riskType: '<b>soja</script>' },
    },
    publisherBindings: [
      { fieldKey: 'riskType', label: 'Tipo de risco', type: 'ENUM', value: 'quebra de safra' },
    ],
    userFields: [{ key: 'comment', label: 'Comentário adicional', type: 'TEXT', required: false, allowedValues: [] }],
    effectiveValidFrom: null,
    effectiveValidUntil: '2026-10-01T00:00:00Z',
    quotationPerformed: false,
    eligibilityEvaluated: false,
    recommendationPerformed: false,
    objectiveTemplate: 'Objetivo interno secreto',
  };
}

function renderPublic(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

describe('public invite page', () => {
  it('does not fetch or reveal a malformed token', async () => {
    const fetchMock = vi.fn(() => jsonResponse(200, envelope()));
    vi.stubGlobal('fetch', fetchMock);
    renderPublic('/c/short');
    expect(await screen.findByText('Este endereço não está disponível.')).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
    expect(document.body.textContent).not.toContain('short');
  });

  it('renders a successful invite without exposing token, ids or templates', async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = requestUrl(input);
      if (url.includes('/context-links/')) {
        return jsonResponse(200, envelope());
      }
      return jsonResponse(200, systemInfo());
    });
    vi.stubGlobal('fetch', fetchMock);
    renderPublic(`/c/${TOKEN}`);
    expect(await screen.findByRole('heading', { name: 'Proteção para situações de quebra de safra' })).toBeInTheDocument();
    expect(screen.getByText('Um convite contextual')).toBeInTheDocument();
    expect(screen.getByText(/Resumo para <b>soja<\/script>/)).toBeInTheDocument();
    expect(screen.getByText('Tipo de risco')).toBeInTheDocument();
    expect(screen.getByText('quebra de safra')).toBeInTheDocument();
    expect(screen.getByText('Comentário adicional')).toBeInTheDocument();
    expect(screen.getByText(/Vigente até 1º de outubro de 2026/)).toBeInTheDocument();
    expect(screen.getByText(/Finalidade deste convite: avaliar opções de proteção/)).toBeInTheDocument();
    expect(screen.queryByRole('img', { name: '' })).not.toBeInTheDocument();
    expect(document.body.textContent).not.toContain(TOKEN);
    expect(document.body.textContent).not.toContain('riskType');
    expect(document.body.textContent).not.toContain('99999999-9999-4999-8999-999999999999');
    expect(document.body.textContent).not.toContain('Objetivo interno secreto');
    expect(document.body.textContent).not.toContain('{{riskType}}');
    expect(document.body.textContent).not.toContain('CONTEXT_LINK');
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
    const source = readFileSync(
      join(dirname(fileURLToPath(import.meta.url)), './PublicInvitePage.tsx'),
      'utf8',
    );
    expect(source).toContain('key={binding.fieldKey');
    expect(source).toContain('key={field.key}');
    const calls = fetchMock.mock.calls.length;
    fireEvent.click(screen.getByRole('button', { name: 'Entender os próximos passos' }));
    expect(await screen.findByRole('heading', { name: 'O que acontece agora?' })).toBeInTheDocument();
    expect(fetchMock.mock.calls.length).toBe(calls);
  });

  it('maps public error states without retry on terminal outcomes', async () => {
    const cases: Array<{ code: string; status: number; title: string; retry: boolean }> = [
      { code: 'CONTEXT_LINK_NOT_FOUND', status: 404, title: 'Este endereço não está disponível.', retry: false },
      { code: 'CONTEXT_LINK_REVOKED', status: 410, title: 'Este convite não vale mais.', retry: false },
      { code: 'CONTEXT_LINK_EXPIRED', status: 410, title: 'Este convite não está mais vigente.', retry: false },
      { code: 'CONTEXT_LINK_UNAVAILABLE', status: 410, title: 'Este convite não está mais disponível.', retry: false },
      {
        code: 'CONTEXT_LINK_TEMPORARILY_UNAVAILABLE',
        status: 503,
        title: 'Temporariamente indisponível.',
        retry: true,
      },
    ];
    for (const item of cases) {
      vi.stubGlobal(
        'fetch',
        vi.fn(() => jsonResponse(item.status, { code: item.code, message: item.code })),
      );
      const view = renderPublic(`/c/${TOKEN}`);
      expect(await screen.findByText(item.title)).toBeInTheDocument();
      expect(screen.queryByText(item.code)).not.toBeInTheDocument();
      expect(document.body.textContent).not.toContain(TOKEN);
      if (item.retry) {
        expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeInTheDocument();
      } else {
        expect(screen.queryByRole('button', { name: 'Tentar novamente' })).not.toBeInTheDocument();
      }
      view.unmount();
    }
  });

  it('offers retry on network failure and ignores stale responses', async () => {
    let resolveFirst: ((value: Response) => void) | undefined;
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = requestUrl(input);
      if (url.endsWith(`/context-links/${TOKEN}`)) {
        return new Promise<Response>((resolve) => {
          resolveFirst = resolve;
        });
      }
      return jsonResponse(404, { code: 'CONTEXT_LINK_NOT_FOUND', message: 'missing' });
    });
    vi.stubGlobal('fetch', fetchMock);
    const first = renderPublic(`/c/${TOKEN}`);
    expect(await screen.findByText('Preparando este convite…')).toBeInTheDocument();
    first.unmount();
    resolveFirst?.(
      new Response(JSON.stringify(envelope()), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const second = renderPublic('/c/short');
    expect(await screen.findByText('Este endereço não está disponível.')).toBeInTheDocument();
    expect(screen.queryByText('Proteção para situações de quebra de safra')).not.toBeInTheDocument();
    second.unmount();

    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new TypeError('Failed to fetch'))));
    renderPublic(`/c/${TOKEN}`);
    expect(await screen.findByText('Não foi possível carregar agora.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeInTheDocument();
  });

  it('keeps the public column usable at 320px', () => {
    const css = readFileSync(join(dirname(fileURLToPath(import.meta.url)), '../index.css'), 'utf8');
    expect(css).toContain('min-width: 320px');
    expect(css).toContain('overflow-x: hidden');
    expect(css).not.toMatch(/\.public-[^{]+\{[^}]*min-width:\s*(3[3-9][0-9]|[4-9][0-9]{2,})px/);
    expect(css).toContain('grid-template-columns: 1fr');
    expect(css).toContain('--segsense-danger-surface');
    expect(css).toContain('--segsense-warning-surface');
  });

  it('starts a local continuity session without storing the credential', async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = requestUrl(input);
      if (url.endsWith(`/context-links/${TOKEN}`) && (init?.method ?? 'GET') === 'GET') {
        return jsonResponse(200, {
          ...envelope(),
          continuity: {
            available: true,
            noticeVersion: 1,
            purposeTitle: 'Uso no SegSense',
            purposeDescription: 'Continuar esta jornada apenas no SegSense, sem envio externo.',
            transparencyText: 'As informações desta etapa permanecem no SegSense e não vão a seguradora.',
            noExternalSharingStatement: 'Não há compartilhamento externo nesta etapa.',
          },
        });
      }
      if (url.includes('/context-instances') && (init?.method ?? 'GET') === 'POST') {
        return jsonResponse(201, {
          status: 'AWAITING_INPUT',
          expectedVersion: 0,
          expiresAt: '2026-09-12T12:00:00Z',
          noticeVersion: 1,
          valuesUnavailable: false,
          credentialIssued: true,
          instanceCredential: 'B'.repeat(43),
          sessionEndsOnReload: true,
          collectibleFields: [
            { key: 'comment', label: 'Comentário adicional', type: 'TEXT', required: false, allowedValues: [], value: null },
          ],
        });
      }
      return jsonResponse(200, systemInfo());
    });
    vi.stubGlobal('fetch', fetchMock);
    renderPublic(`/c/${TOKEN}`);
    expect(await screen.findByRole('button', { name: 'Continuar com segurança' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Continuar com segurança' }));
    expect(await screen.findByRole('heading', { name: 'Uso no SegSense' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Começar esta sessão' }));
    expect(await screen.findByLabelText(/Comentário adicional/)).toBeInTheDocument();
    expect(document.body.textContent).not.toContain('B'.repeat(43));
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
  });

  it('validates BOOLEAN DATE NUMBER and ENUM without coercing empty to false', async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = requestUrl(input);
      if (url.endsWith(`/context-links/${TOKEN}`) && (init?.method ?? 'GET') === 'GET') {
        return jsonResponse(200, continuityEnvelope());
      }
      if (url.includes('/context-instances') && !url.includes('/current') && (init?.method ?? 'GET') === 'POST') {
        return jsonResponse(201, instancePayload());
      }
      if (url.includes('/current/values')) {
        return jsonResponse(200, {
          ...instancePayload(),
          status: 'AWAITING_DECISION',
          expectedVersion: 1,
          credentialIssued: false,
          instanceCredential: null,
        });
      }
      return jsonResponse(200, systemInfo());
    });
    vi.stubGlobal('fetch', fetchMock);
    renderPublic(`/c/${TOKEN}`);
    fireEvent.click(await screen.findByRole('button', { name: 'Continuar com segurança' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Começar esta sessão' }));
    expect(await screen.findByLabelText(/Área plantada/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Continuar' }));
    expect((await screen.findAllByText(/Informe Área plantada/)).length).toBeGreaterThan(0);
    fireEvent.change(screen.getByLabelText(/Área plantada/), { target: { value: 'abc' } });
    fireEvent.change(screen.getByLabelText(/Data da colheita/), { target: { value: '2026-99-99' } });
    fireEvent.click(screen.getByRole('button', { name: 'Continuar' }));
    expect((await screen.findAllByText(/Área plantada precisa ser um número/)).length).toBeGreaterThan(0);
    expect((await screen.findAllByText(/Data da colheita precisa ser uma data válida/)).length).toBeGreaterThan(0);
    fireEvent.change(screen.getByLabelText(/Área plantada/), { target: { value: '12.5' } });
    fireEvent.change(screen.getByLabelText(/Data da colheita/), { target: { value: '2026-09-01' } });
    fireEvent.click(screen.getByRole('button', { name: 'Continuar' }));
    expect(await screen.findByRole('radio', { name: 'Não' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Revisar informações' }));
    expect((await screen.findAllByText(/Selecione Sim ou Não/)).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole('radio', { name: 'Não' }));
    fireEvent.click(screen.getByRole('button', { name: 'Revisar informações' }));
    expect(await screen.findByRole('heading', { name: 'Revisar e autorizar' })).toBeInTheDocument();
    expect(screen.getByText(/Irrigado: Não/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Corrigir informações' }));
    expect(await screen.findByLabelText(/Área plantada/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Voltar' }));
    expect(await screen.findByRole('heading', { name: 'Uso no SegSense' })).toBeInTheDocument();
  });

  it('does not send a previous credential after a route change and rotates after replay', async () => {
    const tokenB = 'C'.repeat(43);
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = requestUrl(input);
      const headers = new Headers(init?.headers);
      if (url.includes('/context-instances') && (init?.method ?? 'GET') === 'POST') {
        if (headers.get('X-SegSense-Instance-Credential')) {
          return jsonResponse(400, { code: 'VALIDATION_ERROR', message: 'credencial indevida' });
        }
        if (headers.get('Idempotency-Key') === 'fixed-key-should-not-leak') {
          return jsonResponse(409, {
            code: 'INSTANCE_CREDENTIAL_NOT_REPLAYABLE',
            message: 'A resposta inicial desta sessão não pode ser recuperada. Comece uma nova tentativa com uma nova chave.',
          });
        }
        if (url.includes(tokenB)) {
          return jsonResponse(201, {
            ...instancePayload(),
            instanceCredential: 'D'.repeat(43),
            collectibleFields: [
              {
                key: 'comment',
                label: 'Comentário adicional',
                type: 'TEXT',
                required: false,
                allowedValues: [],
                value: null,
              },
            ],
          });
        }
        return jsonResponse(201, instancePayload());
      }
      if (url.includes('/context-links/') && (init?.method ?? 'GET') === 'GET') {
        return jsonResponse(200, continuityEnvelope());
      }
      return jsonResponse(200, systemInfo());
    });
    vi.stubGlobal('fetch', fetchMock);
    const first = renderPublic(`/c/${TOKEN}`);
    fireEvent.click(await screen.findByRole('button', { name: 'Continuar com segurança' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Começar esta sessão' }));
    expect(await screen.findByLabelText(/Área plantada/)).toBeInTheDocument();
    expect(document.body.textContent).not.toContain('B'.repeat(43));
    first.unmount();
    renderPublic(`/c/${tokenB}`);
    fireEvent.click(await screen.findByRole('button', { name: 'Continuar com segurança' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Começar esta sessão' }));
    expect(await screen.findByLabelText(/Comentário adicional/)).toBeInTheDocument();
    expect(document.body.textContent).not.toContain('B'.repeat(43));
    expect(document.body.textContent).not.toContain('D'.repeat(43));
    const postB = fetchMock.mock.calls.find((call) => {
      const url = requestUrl(call[0]);
      return url.includes(tokenB) && url.includes('/context-instances');
    });
    expect(postB).toBeTruthy();
    expect(new Headers(postB?.[1]?.headers).get('X-SegSense-Instance-Credential')).toBeNull();
  });

  it('does not continue when the initial create response is not replayable', async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = requestUrl(input);
      if (url.includes('/context-instances') && (init?.method ?? 'GET') === 'POST') {
        return jsonResponse(409, {
          code: 'INSTANCE_CREDENTIAL_NOT_REPLAYABLE',
          message:
            'A resposta inicial desta sessão não pode ser recuperada. Comece uma nova tentativa com uma nova chave.',
        });
      }
      if (url.includes('/context-links/')) {
        return jsonResponse(200, continuityEnvelope());
      }
      return jsonResponse(200, systemInfo());
    });
    vi.stubGlobal('fetch', fetchMock);
    renderPublic(`/c/${TOKEN}`);
    fireEvent.click(await screen.findByRole('button', { name: 'Continuar com segurança' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Começar esta sessão' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/nova chave/);
    expect(screen.queryByLabelText(/Área plantada/)).not.toBeInTheDocument();
    expect(document.body.textContent).not.toContain('instanceCredential');
  });
});

describe('admin routing', () => {
  it('exposes admin routes and does not invent a login screen', async () => {
    vi.stubGlobal('fetch', vi.fn(() => jsonResponse(200, systemInfo())));
    render(
      <MemoryRouter initialEntries={['/admin/catalogo']}>
        <App />
      </MemoryRouter>,
    );
    expect(await screen.findByRole('heading', { name: 'Catálogo' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Início' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Catálogo' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Oportunidades' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /entrar/i })).not.toBeInTheDocument();
  });
});
