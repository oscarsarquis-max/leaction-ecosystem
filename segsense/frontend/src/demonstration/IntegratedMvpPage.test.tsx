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

function confirmedPayload(overrides: Record<string, unknown> = {}) {
  return {
    id: 'j1',
    watermark: 'DEMONSTRAÇÃO — SEM VALOR COMERCIAL — NÃO É COTAÇÃO/PROPOSTA DE CONTRATAÇÃO',
    notCommercial: true,
    notIcatuProposal: true,
    demoSliceOnly: true,
    generatedAt: '2026-09-13T12:00:00Z',
    scenarioKey: 'SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1',
    declaredObjective: 'UNDERSTAND_FAMILY_PROTECTION_OPTIONS',
    status: 'PRE_PROPOSAL_AVAILABLE',
    correlationId: '33333333-3333-3333-3333-333333333333',
    spiderDecisionId: 'spd-test',
    decisionProvenance: 'SPIDER_SATELLITE_CONTRACT_V1',
    explanation: 'A Spider despachou a capability ao executor registrado.',
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
      purpose: 'Apresentar jornada ilustrativa de proteção familiar, sem cotação.',
      nonPersonal: true,
    },
    spiderPath: 'SATELLITE_CONTRACT_V1_THEN_CAPABILITY_RESOLUTION',
    items: [
      {
        code: 'STEP',
        title: 'Revisar o contexto familiar declarado no cenário sintético',
        kind: 'JOURNEY_STEP',
        notOfferable: true,
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
  });

  it('is distinct from Icatu and does not promise a quote', () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.reject(new TypeError('Failed to fetch'))),
    );

    renderMvp();

    expect(screen.getByText(/SEM VALOR COMERCIAL/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Continuidade financeira da família/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Cenário Icatu/i })).toHaveAttribute(
      'href',
      '/demonstracao/icatu',
    );
    expect(screen.getByRole('button', { name: /Enviar à Spider/i })).toBeInTheDocument();
    expect(screen.getByText(/ainda não houve envio nesta página/i)).toBeInTheDocument();
    expect(screen.queryByText(/logo Icatu|contratar agora|cotação vinculante/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Não é cotação, proposta Icatu nem produção/i)).toBeInTheDocument();
    expect(screen.queryByText(/R\$/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Em análise na Spider/i)).not.toBeInTheDocument();
  });

  it('does not invent a pre-proposal when the backend is down', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.reject(new TypeError('Failed to fetch'))),
    );
    renderMvp();
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: /Enviar à Spider/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/indisponível/i);
    expect(screen.queryByRole('heading', { name: /Pré-proposta demonstrativa/i })).not.toBeInTheDocument();
  });

  it('keeps waiting as a client fact and never claims Spider analysis while pending', async () => {
    vi.useFakeTimers();
    vi.stubGlobal(
      'fetch',
      vi.fn(() => new Promise<Response>(() => {})),
    );
    renderMvp();
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: /Enviar à Spider/i }));
    expect(screen.getByText(/Aguardando resposta da Spider/i)).toBeInTheDocument();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    expect(screen.getByText(/Aguardando resposta da Spider/i)).toBeInTheDocument();
    expect(screen.queryByText(/Em análise/i)).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: /Pré-proposta demonstrativa/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/BUILD_ILLUSTRATIVE/)).not.toBeInTheDocument();
  });

  it('renders a pre-proposal only from a confirmed canonical payload', async () => {
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
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: /Enviar à Spider/i }));
    expect(await screen.findByRole('heading', { name: /Pré-proposta demonstrativa/i })).toBeInTheDocument();
    expect(screen.getByText(/spd-test/)).toBeInTheDocument();
    expect(screen.getByText(/ILLUSTRATIVE_NOT_ICATU_CONTRACT/)).toBeInTheDocument();
    expect(screen.getByText(/SEGSENSE_PUBLIC_DEMO/)).toBeInTheDocument();
    expect(screen.getByText(/segsense · EXPERIENCE · contrato 1\.0/i)).toBeInTheDocument();
    expect(screen.getByText(/BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO/)).toBeInTheDocument();
    expect(screen.queryByText(/ainda não houve envio nesta página/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/R\$/)).not.toBeInTheDocument();
  });

  it('does not declare a decision when decisionId is missing', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          new Response(
            JSON.stringify(
              confirmedPayload({
                spiderDecisionId: null,
                items: [{ code: 'STEP', title: 'Item fictício', kind: 'JOURNEY_STEP', notOfferable: true }],
              }),
            ),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          ),
        ),
      ),
    );
    renderMvp();
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: /Enviar à Spider/i }));
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
    expect(screen.queryByRole('heading', { name: /Pré-proposta demonstrativa/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/Item fictício/)).not.toBeInTheDocument();
  });

  it('does not declare a provider return without providerReference', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          new Response(
            JSON.stringify(
              confirmedPayload({
                mockResultId: null,
                capabilityId: 'BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO',
                items: [{ code: 'STEP', title: 'Item sem referência', kind: 'JOURNEY_STEP', notOfferable: true }],
              }),
            ),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          ),
        ),
      ),
    );
    renderMvp();
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: /Enviar à Spider/i }));
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
    expect(screen.queryByRole('heading', { name: /Pré-proposta demonstrativa/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/Item sem referência/)).not.toBeInTheDocument();
    expect(screen.queryByText(/BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO/)).not.toBeInTheDocument();
  });

  it('shows a true error when Spider is unavailable instead of a ready pre-proposal', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          new Response(
            JSON.stringify({
              id: 'j2',
              watermark: 'DEMONSTRAÇÃO — SEM VALOR COMERCIAL — NÃO É COTAÇÃO/PROPOSTA DE CONTRATAÇÃO',
              status: 'SPIDER_UNAVAILABLE',
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
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: /Enviar à Spider/i }));
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/Spider indisponível/i);
    });
    expect(screen.queryByRole('heading', { name: /Pré-proposta demonstrativa/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/Não deve aparecer/)).not.toBeInTheDocument();
  });
});
