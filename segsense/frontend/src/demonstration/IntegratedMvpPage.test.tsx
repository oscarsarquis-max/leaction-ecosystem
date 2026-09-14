import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from '../App';

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  vi.useRealTimers();
});

function renderMvp() {
  return render(
    <MemoryRouter initialEntries={['/demonstracao/mvp-integrado']}>
      <App />
    </MemoryRouter>,
  );
}

function fillReadyForm() {
  fireEvent.change(screen.getByLabelText(/Descreva o contexto/i), {
    target: { value: 'continuidade familiar com dependentes' },
  });
  fireEvent.change(screen.getByRole('textbox', { name: /O que você quer fazer/i }), {
    target: { value: 'entender opções ilustrativas de proteção' },
  });
}

function confirmedPayload(overrides: Record<string, unknown> = {}) {
  return {
    id: 'j1',
    watermark: 'DEMONSTRAÇÃO — SEM VALOR COMERCIAL — NÃO É COTAÇÃO/PROPOSTA DE CONTRATAÇÃO',
    notCommercial: true,
    notIcatuProposal: true,
    demoSliceOnly: true,
    generatedAt: '2026-09-13T12:00:00Z',
    scenarioKey: 'SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1',
    declaredObjective: 'UNDERSTAND_PROTECTION_OPTIONS',
    status: 'PRE_PROPOSAL_AVAILABLE',
    correlationId: '33333333-3333-3333-3333-333333333333',
    spiderDecisionId: 'spd-test',
    decisionProvenance: 'SPIDER_SATELLITE_CONTRACT_V1',
    explanation:
      'A Spider aplicou regras explícitas ao contexto de continuidade familiar e à intenção de entender opções ilustrativas de proteção. O resultado permite encaminhar o pedido ao provedor ilustrativo desta demonstração. Sem composição de seguro real.',
    mockCalled: true,
    mockOrigin: 'ILLUSTRATIVE_NOT_ICATU_CONTRACT',
    providerId: 'insurance-provider-mock',
    mockResultId: 'ill-test',
    satelliteId: 'segsense',
    satelliteRole: 'EXPERIENCE',
    satelliteContractVersion: '1.0',
    capabilityId: 'BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO',
    providerRequestId: 'preq-test',
    originProvenance: {
      channel: 'SEGSENSE_PUBLIC_DEMO',
      sourceType: 'SATELLITE_GOVERNED',
      sourceId: 'SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1',
      nonPersonal: true,
    },
    spiderPath: 'SATELLITE_CONTRACT_V1_THEN_CAPABILITY_RESOLUTION',
    contextSourceTitle: 'Continuidade financeira da família (sintético)',
    items: [
      {
        code: 'ILLUSTRATIVE_FAMILY_CONTINUITY_CONVERSATION',
        title: 'Conversar sobre continuidade da renda familiar (ilustrativo)',
        kind: 'ILLUSTRATIVE_POSSIBILITY',
        notOfferable: true,
        pertinence: 'O tema da fonte é continuidade familiar e a intenção é entender opções ilustrativas.',
        limits: 'Não é produto, cobertura, preço nem oferta Icatu.',
      },
    ],
    pendingForBroker: ['Confirmar com a seguradora autorizada.'],
    ...overrides,
  };
}

describe('integrated synthetic MVP page', () => {
  it('does not use timers to fake Spider or mock progress', () => {
    const source = readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'IntegratedMvpPage.tsx'), 'utf8');
    expect(source).not.toMatch(/setTimeout/);
    expect(source).not.toMatch(/analyzing/);
    expect(source).not.toMatch(/Em análise na Spider/);
    expect(source).not.toMatch(/ILLUSTRATIVE_FAMILY_CONTINUITY_CONVERSATION/);
  });

  it('is distinct from Icatu and leads with context and intention', () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new TypeError('Failed to fetch'))));
    renderMvp();
    expect(screen.getByText(/SEM VALOR COMERCIAL/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Contexto, o que você quer e simulação/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Fonte ou relato/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Elementos extraídos ou declarados/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Sua intenção/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/O que você quer fazer\?/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Descreva o contexto/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Usar contexto de um link/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Continuar/i })).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: /Voltar à apresentação/i }).length).toBe(2);
    expect(screen.queryByRole('button', { name: /Enviar ao SegSense/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: /Evidências desta simulação/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/logo Icatu|contratar agora/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/Pedir cotação vinculante/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/Confirmo esta intenção/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/Confirmo que não informei dados pessoais/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/R\$/)).not.toBeInTheDocument();
  });

  it('does not invent possibilities when the backend is down', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new TypeError('Failed to fetch'))));
    renderMvp();
    fillReadyForm();
    fireEvent.click(screen.getByRole('button', { name: /Ver possibilidades ilustrativas/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/indisponível/i);
    expect(screen.queryByText(/Conversar sobre continuidade/i)).not.toBeInTheDocument();
  });

  it('keeps waiting as a client fact and never claims Spider analysis while pending', async () => {
    vi.useFakeTimers();
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(() => {})));
    renderMvp();
    fillReadyForm();
    fireEvent.click(screen.getByRole('button', { name: /Ver possibilidades ilustrativas/i }));
    expect(screen.getByText(/Solicitação enviada; aguardando o resultado desta tentativa/i)).toBeInTheDocument();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    expect(screen.queryByText(/Em análise/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Aguardando resposta da Spider/i)).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: /Evidências desta simulação/i })).not.toBeInTheDocument();
  });

  it('renders possibilities only from a confirmed canonical payload', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          new Response(JSON.stringify(confirmedPayload()), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          }),
        ),
      ),
    );
    renderMvp();
    fillReadyForm();
    fireEvent.click(screen.getByRole('button', { name: /Ver possibilidades ilustrativas/i }));
    expect(
      await screen.findByRole('heading', { name: /^Possibilidades ilustrativas$/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Conversar sobre continuidade da renda familiar/i)).toBeInTheDocument();
    expect(screen.getByText(/O tema da fonte é continuidade familiar/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /^Por que surgiram$/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /O que ainda depende de corretora/i })).toBeInTheDocument();
    expect(screen.getAllByText(/regras explícitas/i).length).toBeGreaterThan(0);
    expect(screen.getByRole('heading', { name: /^Por que surgiram$/i }).closest('section')).not.toHaveTextContent(
      'UNDERSTAND_PROTECTION_OPTIONS',
    );
    expect(screen.getByRole('heading', { name: /^Por que surgiram$/i }).closest('section')).not.toHaveTextContent(
      'BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO',
    );
    expect(screen.getByRole('heading', { name: /O que ainda depende de corretora/i }).closest('section')).not.toHaveTextContent(
      'ILLUSTRATIVE_NOT_ICATU_CONTRACT',
    );
    expect(screen.queryByText(/compreendeu/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/R\$/)).not.toBeInTheDocument();
  });

  it('does not show provider items without providerReference', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          new Response(
            JSON.stringify(
              confirmedPayload({
                mockResultId: null,
                items: [{ code: 'STEP', title: 'Item sem referência', kind: 'JOURNEY_STEP', notOfferable: true }],
              }),
            ),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          ),
        ),
      ),
    );
    renderMvp();
    fillReadyForm();
    fireEvent.click(screen.getByRole('button', { name: /Ver possibilidades ilustrativas/i }));
    await waitFor(() => {
      expect(screen.getByText(/Nenhuma possibilidade ilustrativa/i)).toBeInTheDocument();
    });
    expect(screen.queryByText(/Item sem referência/)).not.toBeInTheDocument();
  });

  it('shows Spider unavailability without leftover items', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          new Response(
            JSON.stringify({
              id: 'j2',
              watermark: 'DEMONSTRAÇÃO — SEM VALOR COMERCIAL — NÃO É COTAÇÃO/PROPOSTA DE CONTRATAÇÃO',
              status: 'SPIDER_UNAVAILABLE',
              declaredObjective: 'UNDERSTAND_PROTECTION_OPTIONS',
              explanation: 'A Spider não respondeu.',
              items: [{ code: 'STEP', title: 'Não deve aparecer', kind: 'JOURNEY_STEP', notOfferable: true }],
              pendingForBroker: [],
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          ),
        ),
      ),
    );
    renderMvp();
    fillReadyForm();
    fireEvent.click(screen.getByRole('button', { name: /Ver possibilidades ilustrativas/i }));
    expect(await screen.findAllByText(/Spider indisponível/i)).not.toHaveLength(0);
    expect(screen.queryByText(/Não deve aparecer/)).not.toBeInTheDocument();
  });

  it('shows a rejected intention without Test Double items', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          new Response(
            JSON.stringify(
              confirmedPayload({
                status: 'REJECTED',
                declaredObjective: 'REQUEST_BINDING_QUOTE',
                spiderDecisionId: 'spd-reject',
                explanation:
                  'A Spider recusou a intenção confirmada: não está entre as permitidas nesta demonstração. Nenhum encaminhamento ao Test Double foi feito.',
                mockResultId: null,
                capabilityId: null,
                items: [{ code: 'STEP', title: 'Item recusado', kind: 'JOURNEY_STEP', notOfferable: true }],
              }),
            ),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          ),
        ),
      ),
    );
    renderMvp();
    fillReadyForm();
    fireEvent.change(screen.getByLabelText(/O que você quer fazer/i), {
      target: { value: 'quero pagar agora' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Continuar/i }));
    expect(await screen.findAllByText(/Pedido recusado nesta demonstração/i)).not.toHaveLength(0);
    expect(screen.queryByText(/Item recusado/)).not.toBeInTheDocument();
  });

  it('drops a previous confirmed result when a later attempt fails', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify(confirmedPayload()), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockRejectedValueOnce(new TypeError('Failed to fetch'));
    vi.stubGlobal('fetch', fetchMock);
    renderMvp();
    fillReadyForm();
    fireEvent.click(screen.getByRole('button', { name: /Ver possibilidades ilustrativas/i }));
    expect(await screen.findByText(/Conversar sobre continuidade da renda familiar/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Nova tentativa/i }));
    expect(screen.queryByText(/Conversar sobre continuidade da renda familiar/i)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Ver possibilidades ilustrativas/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/indisponível/i);
    expect(screen.queryByText(/Conversar sobre continuidade da renda familiar/i)).not.toBeInTheDocument();
  });

  it('does not claim SegSense controls browser speech audio', () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new TypeError('Failed to fetch'))));
    renderMvp();
    expect(screen.queryByText(/nada de áudio é enviado/i)).not.toBeInTheDocument();
    expect(screen.getByText(/O SegSense não recebe nem grava arquivo de áudio/i)).toBeInTheDocument();
    expect(screen.queryByText(/processa localmente/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/reconhecimento de fala do navegador/i)).not.toBeInTheDocument();
  });

  it('freezes inputs while a request is in flight', async () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(() => {})));
    renderMvp();
    fillReadyForm();
    fireEvent.click(screen.getByRole('button', { name: /Ver possibilidades ilustrativas/i }));
    expect(await screen.findByText(/Solicitação enviada; aguardando o resultado desta tentativa/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Descreva o contexto/i)).toBeDisabled();
    expect(screen.getByLabelText(/Usar contexto de um link/i)).toBeDisabled();
  });

  it('ignores a stale governed URL resolution after a rapid A to B swap', async () => {
    const familyTitle = 'Continuidade financeira da família (sintético)';
    const incomeTitle = 'Interrupção de renda do trabalho (sintético)';
    let resolveCalls = 0;
    const first = deferredResponse();
    const second = deferredResponse();
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo) => {
        const url = requestUrl(input);
        if (url.includes('context-sources/resolve')) {
          resolveCalls += 1;
          return resolveCalls === 1 ? first.promise : second.promise;
        }
        return Promise.reject(new TypeError('no submit'));
      }),
    );
    renderMvp();
    fireEvent.click(screen.getByRole('button', { name: /^continuidade familiar$/i }));
    fireEvent.click(screen.getByRole('button', { name: /interrupção de renda/i }));
    await act(async () => {
      first.resolve(
        jsonResponse({
          id: 'SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1',
          slug: 'continuidade-familiar',
          title: familyTitle,
          sourceLabel: 'Fonte editorial',
          version: 'demo-editorial-v1',
          capturedAt: '2026-09-13T12:00:00Z',
          revoked: false,
          url: 'http://localhost/demonstracao/fontes/continuidade-familiar',
          elements: { theme: 'family_continuity', situation: 'dependentes' },
        }),
      );
      await Promise.resolve();
    });
    expect(screen.queryByText(/Continuidade financeira da família/)).not.toBeInTheDocument();
    await act(async () => {
      second.resolve(
        jsonResponse({
          id: 'SEGSENSE_INCOME_INTERRUPTION_SYNTHETIC_V1',
          slug: 'interrupcao-renda',
          title: incomeTitle,
          sourceLabel: 'Fonte editorial',
          version: 'demo-income-v1',
          capturedAt: '2026-09-13T12:00:00Z',
          revoked: false,
          url: 'http://localhost/demonstracao/fontes/interrupcao-renda',
          elements: { theme: 'income_interruption', situation: 'renda' },
        }),
      );
      await Promise.resolve();
    });
    expect(await screen.findByText(/Interrupção de renda do trabalho/)).toBeInTheDocument();
    expect(screen.queryByText(/Continuidade financeira da família/)).not.toBeInTheDocument();
  });

  it('clears a READY result when context changes and rotates the idempotency key', async () => {
    const fetchMock = vi.fn((...args: [RequestInfo, RequestInit?]) => {
      const url = requestUrl(args[0]);
      if (url.includes('protection-journeys')) {
        return Promise.resolve(jsonResponse(confirmedPayload()));
      }
      return Promise.reject(new TypeError('no resolve'));
    });
    vi.stubGlobal('fetch', fetchMock);
    renderMvp();
    fillReadyForm();
    fireEvent.click(screen.getByRole('button', { name: /Ver possibilidades ilustrativas/i }));
    expect(await screen.findByText(/Conversar sobre continuidade da renda familiar/i)).toBeInTheDocument();
    const firstHeaders = fetchMock.mock.calls[0]?.[1]?.headers as Record<string, string> | undefined;
    const firstKey = firstHeaders?.['Idempotency-Key'] ?? '';
    fireEvent.change(screen.getByLabelText(/Descreva o contexto/i), {
      target: { value: 'interrupção de renda se o trabalho parar' },
    });
    expect(screen.queryByText(/Conversar sobre continuidade da renda familiar/i)).not.toBeInTheDocument();
    expect(screen.getByText(/tentativa anterior foi descartada/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Ver possibilidades ilustrativas/i }));
    await waitFor(() => {
      expect(fetchMock.mock.calls.length).toBeGreaterThan(1);
    });
    const secondHeaders = fetchMock.mock.calls[1]?.[1]?.headers as Record<string, string> | undefined;
    const secondKey = secondHeaders?.['Idempotency-Key'] ?? '';
    expect(firstKey).not.toEqual('');
    expect(secondKey).not.toEqual(firstKey);
  });

  it('clears a READY result when intention changes', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(jsonResponse(confirmedPayload()))),
    );
    renderMvp();
    fillReadyForm();
    fireEvent.click(screen.getByRole('button', { name: /Ver possibilidades ilustrativas/i }));
    expect(await screen.findByText(/Conversar sobre continuidade da renda familiar/i)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/O que você quer fazer/i), {
      target: { value: 'comparar lacunas ilustrativas deste contexto' },
    });
    expect(screen.queryByText(/Conversar sobre continuidade da renda familiar/i)).not.toBeInTheDocument();
    expect(screen.getByText(/tentativa anterior foi descartada/i)).toBeInTheDocument();
  });

  it('ignores a late response from a cancelled previous request', async () => {
    const first = deferredResponse();
    const second = deferredResponse();
    let submits = 0;
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo) => {
        const url = requestUrl(input);
        if (url.includes('protection-journeys')) {
          submits += 1;
          return submits === 1 ? first.promise : second.promise;
        }
        return Promise.reject(new TypeError('no resolve'));
      }),
    );
    renderMvp();
    fillReadyForm();
    fireEvent.click(screen.getByRole('button', { name: /Ver possibilidades ilustrativas/i }));
    expect(await screen.findByText(/Solicitação enviada; aguardando o resultado desta tentativa/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Cancelar esta tentativa/i }));
    fireEvent.click(screen.getByRole('button', { name: /Ver possibilidades ilustrativas/i }));
    await act(async () => {
      first.resolve(jsonResponse(confirmedPayload({ id: 'stale-old' })));
      await Promise.resolve();
    });
    expect(screen.queryByText(/Conversar sobre continuidade da renda familiar/i)).not.toBeInTheDocument();
    await act(async () => {
      second.resolve(
        jsonResponse(
          confirmedPayload({
            id: 'fresh',
            items: [
              {
                code: 'ILLUSTRATIVE_INCOME_GAP_COMPARE',
                title: 'Comparar lacunas ilustrativas de renda',
                kind: 'ILLUSTRATIVE_POSSIBILITY',
                notOfferable: true,
              },
            ],
          }),
        ),
      );
      await Promise.resolve();
    });
    expect(await screen.findByText(/Comparar lacunas ilustrativas de renda/i)).toBeInTheDocument();
    expect(screen.queryByText(/Conversar sobre continuidade da renda familiar/i)).not.toBeInTheDocument();
  });

  it('ignores a late error from a previous request after a later success', async () => {
    const first = deferredResponse();
    const second = deferredResponse();
    let submits = 0;
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo) => {
        const url = requestUrl(input);
        if (url.includes('protection-journeys')) {
          submits += 1;
          return submits === 1 ? first.promise : second.promise;
        }
        return Promise.reject(new TypeError('no resolve'));
      }),
    );
    renderMvp();
    fillReadyForm();
    fireEvent.click(screen.getByRole('button', { name: /Ver possibilidades ilustrativas/i }));
    fireEvent.click(await screen.findByRole('button', { name: /Cancelar esta tentativa/i }));
    fireEvent.click(screen.getByRole('button', { name: /Ver possibilidades ilustrativas/i }));
    await act(async () => {
      second.resolve(jsonResponse(confirmedPayload()));
      await Promise.resolve();
    });
    expect(await screen.findByText(/Conversar sobre continuidade da renda familiar/i)).toBeInTheDocument();
    await act(async () => {
      first.reject(new TypeError('Failed to fetch'));
      await Promise.resolve();
    });
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByText(/Conversar sobre continuidade da renda familiar/i)).toBeInTheDocument();
  });

  it('shows a simulated quote only after a confirmed payload with premium', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          jsonResponse(
            confirmedPayload({
              status: 'SIMULATED_QUOTE_AVAILABLE',
              declaredObjective: 'SIMULATE_HOME_QUOTE',
              mockOrigin: 'NON_BINDING_DEMO',
              mockResultId: 'qte-1',
              quoteReference: 'qte-1',
              simulatedQuote: {
                premiumAnnualCents: 54000,
                insuredAmountCents: 30000000,
                coverPeriodMonths: 12,
                dwellingType: 'APARTMENT',
                humanCalculation: 'Prêmio anual simulado = capital declarado × 18 bps.',
                premises: ['Taxas inventadas para demonstrar o software.'],
                nearbyFiresDidNotAdjustPremium: true,
              },
              items: [],
            }),
          ),
        ),
      ),
    );
    renderMvp();
    fireEvent.change(screen.getByLabelText(/Descreva o contexto/i), {
      target: { value: 'Houve incêndios nas proximidades' },
    });
    fireEvent.change(screen.getByLabelText(/O que você quer fazer/i), {
      target: { value: 'Quero contratar um seguro residencial' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Gerar cotação simulada/i }));
    expect(await screen.findByRole('heading', { name: /Cotação simulada/i })).toBeInTheDocument();
    expect(screen.getByText(/R\$\s*540,00/)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Como este valor foi calculado/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Cotação simulada/i }).closest('section')).not.toHaveTextContent(
      'Test Double',
    );
    expect(screen.queryByRole('heading', { name: /^Possibilidades ilustrativas$/i })).not.toBeInTheDocument();
  });
});

function requestUrl(input: RequestInfo): string {
  if (typeof input === 'string') {
    return input;
  }
  if (input instanceof URL) {
    return input.href;
  }
  return input.url;
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function deferredResponse() {
  let resolve!: (value: Response) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<Response>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}
