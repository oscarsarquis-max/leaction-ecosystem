export type CreditContext = {
  environment: string;
  synthetic: boolean;
  title: string;
  summary: string;
  originLabel: string;
  originDetail: string;
  sourceId: string;
  captureMethod: string;
  trustLevel: string;
  classification: string;
  nonPersonal: boolean;
  objectiveLabel: string;
  objectiveCode: string;
  objectiveHelp: string;
  limits: string;
};

export type CreditImpediment = {
  sequence: number;
  capabilityId: string;
  availability: string;
  reason: string;
  title: string;
};

export type CreditSimulation = {
  watermark?: string;
  premises?: string[];
  principalCents?: number;
  termMonths?: number;
  interestCents?: number;
  totalCents?: number;
  installmentsCents?: number[];
  currency?: string;
  calculationRule?: string;
  offerable?: boolean;
  testDouble?: boolean;
};

export type CreditEligibleProduct = {
  productCode?: string;
  title?: string;
  offerable?: boolean;
  commercialValidity?: boolean;
  testDouble?: boolean;
};

export type CreditOptions = {
  principalCents?: number;
  termMonths?: number;
  origin?: string;
  eligibleProducts?: {
    products?: CreditEligibleProduct[];
  };
  simulation?: CreditSimulation;
  composedOnlyFromReceivedResults?: boolean;
};

export type CreditJourney = {
  status: string;
  headline: string;
  explanation: string;
  watermark: string;
  correlationId: string;
  decisionId: string;
  contextRef: string;
  requiredAction: string;
  analysisComplete: boolean;
  simulationComplete: boolean;
  creditDecision: string;
  retryable: boolean;
  impediments: CreditImpediment[];
  missingContext: string[];
  options?: CreditOptions;
  technical?: {
    spiderStatus?: string;
    contractVersion?: string;
    spiderPath?: string;
    intent?: string;
    planId?: string;
    providerDispatched?: boolean;
  };
};

export type DemoSession = {
  environment: string;
  synthetic: boolean;
  label: string;
  persona: string;
  subjectRef: string;
  assertion: string;
  expiresAt: string;
  warning: string;
};

export type CreditError = {
  errorCode: string;
  message: string;
  retryable: boolean;
  creditDecision: string;
};

async function readJson<T>(response: Response): Promise<T> {
  return (await response.json()) as T;
}

export async function fetchCreditContext(): Promise<CreditContext> {
  const response = await fetch('/api/credit/context', { headers: { Accept: 'application/json' } });
  if (!response.ok) {
    throw new Error('Não foi possível carregar o contexto demonstrativo.');
  }
  return readJson<CreditContext>(response);
}

export async function startDemoSession(persona = 'ok'): Promise<DemoSession> {
  const response = await fetch('/api/credit/demo-session', {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify({ persona }),
  });
  const body = await readJson<DemoSession & CreditError>(response);
  if (!response.ok) {
    const error = new Error(body.message || 'Não foi possível abrir a sessão demonstrativa.') as Error & CreditError;
    error.errorCode = body.errorCode;
    error.retryable = Boolean(body.retryable);
    error.creditDecision = body.creditDecision ?? 'NONE';
    throw error;
  }
  return body;
}

export async function submitCreditJourney(input: {
  objectiveConfirmed: boolean;
  correlationId: string;
  idempotencyKey: string;
  sessionAssertion?: string;
  principalCents?: number;
  termMonths?: number;
}): Promise<CreditJourney> {
  const response = await fetch('/api/credit/journeys', {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      'X-Correlation-ID': input.correlationId,
      'Idempotency-Key': input.idempotencyKey,
    },
    body: JSON.stringify({
      objectiveConfirmed: input.objectiveConfirmed,
      correlationId: input.correlationId,
      idempotencyKey: input.idempotencyKey,
      sessionAssertion: input.sessionAssertion,
      principalCents: input.principalCents,
      termMonths: input.termMonths,
    }),
  });
  const body = (await response.json()) as CreditJourney & CreditError;
  if (!response.ok) {
    const error = new Error(body.message || 'Falha ao enviar a interação.') as Error & CreditError;
    error.errorCode = body.errorCode;
    error.retryable = Boolean(body.retryable);
    error.creditDecision = body.creditDecision ?? 'NONE';
    throw error;
  }
  if (!body.status || !body.correlationId) {
    throw new Error('A resposta do BFF não pode ser apresentada como resultado válido.');
  }
  return body;
}

export function newCorrelationId(): string {
  return crypto.randomUUID();
}

export function newIdempotencyKey(): string {
  return `idem-${crypto.randomUUID()}`;
}

export function reaisToCents(reais: string): number | undefined {
  const normalized = reais.replace(/\s/g, '').replace(/\./g, '').replace(',', '.');
  if (!normalized) {
    return undefined;
  }
  const value = Number(normalized);
  if (!Number.isFinite(value)) {
    return undefined;
  }
  return Math.round(value * 100);
}

export function formatCents(cents: number | undefined): string {
  if (cents == null || !Number.isFinite(cents)) {
    return '—';
  }
  return (cents / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}
