import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { CreditJourneyPage } from './CreditJourneyPage';

const context = {
  environment: 'MOCK_ONLY',
  synthetic: true,
  title: 'Situação demonstrativa de capital de giro',
  summary: 'Empresa ilustrativa com necessidade temporária de caixa.',
  originLabel: 'Fonte governada do SpiderBank',
  originDetail: 'Registro no servidor da Spider.',
  sourceId: 'SPIDERBANK_WORKING_CAPITAL_SYNTHETIC_V1',
  captureMethod: 'SERVER_REGISTRY',
  trustLevel: 'GOVERNED',
  classification: 'INTERNAL',
  nonPersonal: true,
  objectiveLabel: 'Buscar capital de giro',
  objectiveCode: 'SEEK_WORKING_CAPITAL',
  objectiveHelp: 'A confirmação envia a declaração reconhecida.',
  limits: 'Esta fonte não substitui cadastro nem perfil de crédito.',
};

const session = {
  environment: 'TEST_DOUBLE',
  synthetic: true,
  label: 'Cliente sintético de teste',
  persona: 'ok',
  subjectRef: 'cust-demo-ok',
  assertion: 'v1.spiderbank.cust-demo-ok.1.2.abc',
  expiresAt: '2026-09-18T16:00:00Z',
  warning: 'Sessão demonstrativa. Não é autenticação de cliente real.',
};

const impeded = {
  status: 'ANALYSIS_BLOCKED',
  headline: 'A análise não pode prosseguir nesta demonstração',
  explanation: 'A Spider devolveu impedimentos reais. Isso não é recusa de crédito.',
  watermark: 'DEMONSTRAÇÃO — DADOS SINTÉTICOS — NÃO É ANÁLISE DE CRÉDITO NEM OFERTA',
  correlationId: 'corr-fe-1',
  decisionId: 'spd-fe-1',
  contextRef: 'ctx-fe-1',
  requiredAction: 'PRESENT_PLAN_IMPEDIMENTS',
  analysisComplete: false,
  simulationComplete: false,
  creditDecision: 'NONE',
  retryable: false,
  impediments: [
    {
      sequence: 1,
      capabilityId: 'IDENTIFY_CUSTOMER',
      availability: 'AVAILABLE',
      reason: 'A identidade técnica do satélite não identifica o cliente.',
      title: 'Identificar o cliente autenticado',
    },
    {
      sequence: 6,
      capabilityId: 'SIMULATE_WORKING_CAPITAL',
      availability: 'NOT_AVAILABLE',
      reason: 'Capability SIMULATE_WORKING_CAPITAL permanece indisponível.',
      title: 'Simular capital de giro',
    },
  ],
  missingContext: [],
  options: {},
  technical: { intent: 'SEEK_WORKING_CAPITAL', planId: 'WORKING_CAPITAL_DIAGNOSTIC_V1' },
};

const shown = {
  ...impeded,
  status: 'SIMULATION_SHOWN',
  headline: 'Simulação demonstrativa concluída',
  explanation: 'A Spider executou o plano com sistemas simulados.',
  simulationComplete: true,
  impediments: [],
  options: {
    principalCents: 1000000,
    termMonths: 12,
    origin: 'USER_DECLARED',
    eligibleProducts: {
      products: [{ title: 'Capital de giro sintético de teste', offerable: false, commercialValidity: false }],
    },
    simulation: {
      watermark: 'SIMULAÇÃO ILUSTRATIVA — SEM VALOR COMERCIAL — NÃO É OFERTA, APROVAÇÃO OU CONTRATAÇÃO',
      premises: ['Taxa fictícia de teste; sem calibração de mercado.'],
      principalCents: 1000000,
      termMonths: 12,
      interestCents: 120000,
      totalCents: 1120000,
      installmentsCents: Array.from({ length: 12 }, () => 93334).map((value, index) => (index < 4 ? 93334 : 93333)),
    },
  },
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status });
}

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo) => {
      const url = String(input);
      if (url.includes('/api/credit/context')) {
        return json(context);
      }
      if (url.includes('/api/credit/demo-session')) {
        return json(session);
      }
      return json(impeded);
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

test('requires explicit confirmation before calling the BFF', async () => {
  const user = userEvent.setup();
  render(<CreditJourneyPage />);
  expect(await screen.findByTestId('demo-banner')).toHaveTextContent('dados sintéticos');
  expect(await screen.findByTestId('demo-session')).toHaveTextContent('TEST_DOUBLE');
  expect(screen.getByTestId('credit-context')).toHaveTextContent('Fonte governada do SpiderBank');
  const submit = screen.getByTestId('submit-journey');
  expect(submit).toBeDisabled();
  await user.click(submit);
  expect(vi.mocked(fetch).mock.calls.some((call) => String(call[0]).includes('/api/credit/journeys'))).toBe(false);
  await user.click(screen.getByTestId('confirm-objective'));
  await user.click(submit);
  await waitFor(() => expect(screen.getByTestId('credit-result')).toBeInTheDocument());
  expect(screen.getByTestId('impediments')).toHaveTextContent('não identifica o cliente');
  expect(screen.queryByText(/aprovad/i)).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /contratar|desembolsar|aceitar oferta/i })).not.toBeInTheDocument();
  const journeyCall = vi.mocked(fetch).mock.calls.find((call) => String(call[0]).includes('/api/credit/journeys'));
  const body = JSON.parse(String((journeyCall?.[1] as RequestInit).body));
  expect(body).toMatchObject({
    sessionAssertion: session.assertion,
    principalCents: 1000000,
    termMonths: 12,
  });
  expect(body.scenarioKey).toBeUndefined();
  expect(body.intent).toBeUndefined();
});

test('shows received simulation next to the warning and does not invent a hire action', async () => {
  const user = userEvent.setup();
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo) => {
      const url = String(input);
      if (url.includes('/api/credit/context')) return json(context);
      if (url.includes('/api/credit/demo-session')) return json(session);
      return json(shown);
    }),
  );
  render(<CreditJourneyPage />);
  await screen.findByTestId('demo-session');
  await user.click(screen.getByTestId('confirm-objective'));
  await user.click(screen.getByTestId('submit-journey'));
  const result = await screen.findByTestId('credit-result');
  expect(screen.getByTestId('credit-simulation')).toHaveTextContent('R$');
  expect(screen.getByTestId('simulation-warning')).toHaveTextContent('SEM VALOR COMERCIAL');
  expect(result).toHaveTextContent('Análise de crédito: não');
  expect(screen.queryByRole('button', { name: /contratar|desembolsar/i })).not.toBeInTheDocument();
});

test('retry keeps the same keys on transient failure', async () => {
  const user = userEvent.setup();
  let attempts = 0;
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo) => {
      const url = String(input);
      if (url.includes('/api/credit/context')) return json(context);
      if (url.includes('/api/credit/demo-session')) return json(session);
      attempts += 1;
      if (attempts === 1) {
        return json(
          {
            errorCode: 'SPIDER_UNAVAILABLE',
            message: 'A Spider está indisponível neste momento. Isso não é recusa de crédito.',
            retryable: true,
            creditDecision: 'NONE',
          },
          503,
        );
      }
      return json(impeded);
    }),
  );
  render(<CreditJourneyPage />);
  await screen.findByTestId('credit-context');
  await user.click(screen.getByTestId('confirm-objective'));
  await user.click(screen.getByTestId('submit-journey'));
  expect(await screen.findByTestId('credit-error')).toHaveTextContent('não é recusa de crédito');
  await user.click(screen.getByTestId('retry-journey'));
  await waitFor(() => expect(screen.getByTestId('credit-result')).toBeInTheDocument());
  const journeyCalls = vi
    .mocked(fetch)
    .mock.calls.filter((call) => String(call[0]).includes('/api/credit/journeys'));
  const first = journeyCalls[0]?.[1] as RequestInit;
  const second = journeyCalls[1]?.[1] as RequestInit;
  expect(first.headers).toEqual(second.headers);
});
