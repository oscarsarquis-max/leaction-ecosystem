import { CORRELATION_HEADER, newCorrelationId } from './systemInfo';
import { readApiError } from './errors';

export type DemoJourneyItem = {
  code: string;
  title: string;
  kind: string;
  notOfferable: boolean;
  needAddressed?: string | null;
  pertinence?: string | null;
  limits?: string | null;
};

export type DemoJourneyProjection = {
  id: string;
  watermark: string;
  notCommercial: boolean;
  notIcatuProposal: boolean;
  demoSliceOnly: boolean;
  generatedAt?: string;
  scenarioKey: string;
  declaredObjective: string;
  status: string;
  correlationId: string;
  spiderDecisionId: string | null;
  decisionProvenance: string | null;
  explanation: string;
  mockCalled: boolean;
  mockOrigin: string | null;
  providerId: string | null;
  mockResultId: string | null;
  satelliteId?: string | null;
  satelliteRole?: string | null;
  satelliteContractVersion?: string | null;
  capabilityId?: string | null;
  providerRequestId?: string | null;
  requiredAction?: string | null;
  originProvenance?: {
    channel?: string;
    purpose?: string;
    editorialPieceKey?: string;
    sourceType?: string;
    sourceId?: string;
    sourceTimestamp?: string;
    captureMethod?: string;
    trustLevel?: string;
    nonPersonal?: boolean;
    selectedContribution?: string;
    contributions?: Array<Record<string, unknown>>;
    attributes?: { channel?: string };
  };
  spiderPath?: string | null;
  items?: DemoJourneyItem[];
  pendingForBroker?: string[];
  contextSourceTitle?: string | null;
  contextSourceLabel?: string | null;
  contextSourceVersion?: string | null;
  contextSourceUrl?: string | null;
  declaredContextTheme?: string | null;
  sourceTheme?: string | null;
  contextConflict?: boolean;
  contextElements?: Record<string, string | boolean | undefined>;
  contextContributions?: Array<Record<string, unknown>>;
  selectedContribution?: string | null;
  primarySourceType?: string | null;
  messageCreatedAt?: string;
  objectiveDeclaredAt?: string;
  editorialSourceTimestamp?: string;
  intentionInterpretation?: string | null;
  simulatedQuote?: {
    premiumAnnualCents?: number;
    insuredAmountCents?: number;
    coverPeriodMonths?: number;
    dwellingType?: string;
    dwellingBps?: number;
    ratingRuleVersion?: string;
    humanCalculation?: string;
    premises?: string[];
    nearbyFiresDidNotAdjustPremium?: boolean;
    quoteReference?: string;
    providerReference?: string;
    origin?: string;
    status?: string;
  } | null;
  quoteReference?: string | null;
  missingContext?: string[];
  missingQuestions?: Array<{ code: string; prompt: string }>;
};

export function isConfirmedPreProposal(projection: DemoJourneyProjection): boolean {
  return (
    projection.status === 'PRE_PROPOSAL_AVAILABLE' &&
    Boolean(projection.spiderDecisionId) &&
    Boolean(projection.mockResultId)
  );
}

export function isConfirmedSimulatedQuote(projection: DemoJourneyProjection): boolean {
  return (
    projection.status === 'SIMULATED_QUOTE_AVAILABLE' &&
    Boolean(projection.spiderDecisionId) &&
    Boolean(projection.quoteReference || projection.mockResultId) &&
    projection.simulatedQuote?.premiumAnnualCents != null
  );
}

export async function submitDemoProtectionJourney(
  baseUrl: string,
  declaredObjective: string,
  idempotencyKey: string,
    extras?: {
    sourceUrl?: string;
    declaredContext?: string;
    contextChoice?: string;
    intentionConfirmed?: boolean;
    declaredIntention?: string;
    dwellingType?: string;
    insuredAmountCents?: string;
    coverPeriodMonths?: string;
    captureId?: string;
  },
  signal?: AbortSignal,
): Promise<DemoJourneyProjection> {
  const response = await fetch(`${baseUrl}/api/v1/public/demo/protection-journeys`, {
    method: 'POST',
    credentials: 'omit',
    signal,
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      [CORRELATION_HEADER]: newCorrelationId(),
      'Idempotency-Key': idempotencyKey,
    },
    body: JSON.stringify({
      declaredObjective,
      declaredIntention: extras?.declaredIntention || undefined,
      sourceUrl: extras?.sourceUrl || undefined,
      declaredContext: extras?.declaredContext || undefined,
      contextChoice: extras?.contextChoice || undefined,
      intentionConfirmed: extras?.intentionConfirmed ? 'true' : undefined,
      dwellingType: extras?.dwellingType || undefined,
      insuredAmountCents: extras?.insuredAmountCents || undefined,
      coverPeriodMonths: extras?.coverPeriodMonths || undefined,
      captureId: extras?.captureId || undefined,
    }),
  });
  if (!response.ok) {
    throw await readApiError(response);
  }
  return (await response.json()) as DemoJourneyProjection;
}
