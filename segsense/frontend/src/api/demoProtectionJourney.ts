import { CORRELATION_HEADER, newCorrelationId } from './systemInfo';
import { readApiError } from './errors';

export type DemoJourneyItem = {
  code: string;
  title: string;
  kind: string;
  notOfferable: boolean;
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
    nonPersonal?: boolean;
  };
  spiderPath?: string | null;
  items?: DemoJourneyItem[];
  pendingForBroker?: string[];
};

export function isConfirmedPreProposal(projection: DemoJourneyProjection): boolean {
  return (
    projection.status === 'PRE_PROPOSAL_AVAILABLE' &&
    Boolean(projection.spiderDecisionId) &&
    Boolean(projection.mockResultId)
  );
}

export async function submitDemoProtectionJourney(
  baseUrl: string,
  declaredObjective: string,
  idempotencyKey: string,
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
    body: JSON.stringify({ declaredObjective }),
  });
  if (!response.ok) {
    throw await readApiError(response);
  }
  return (await response.json()) as DemoJourneyProjection;
}
