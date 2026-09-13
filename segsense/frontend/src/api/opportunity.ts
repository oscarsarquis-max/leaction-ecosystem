import { readApiError } from './errors';
import { CORRELATION_HEADER, newCorrelationId } from './systemInfo';
import { type CatalogPage } from './catalog';

export type ContextMode = 'STATIC' | 'DYNAMIC' | 'HYBRID';
export type ContextFieldType = 'TEXT' | 'NUMBER' | 'BOOLEAN' | 'DATE' | 'ENUM';
export type ContextFieldSource = 'PUBLISHER' | 'USER' | 'EITHER';

export type ContextField = {
  key: string;
  label: string;
  type: ContextFieldType;
  required: boolean;
  source: ContextFieldSource;
  classification: 'NON_PERSONAL';
  position: number;
  allowedValues: string[];
};

export type OpportunityRevisionSnapshot = {
  id: string;
  revisionNumber: number;
  createdAt: string;
  createdBy: string;
  title: string;
  contextMode: ContextMode;
  contextSummaryTemplate: string;
  objectiveTemplate: string;
  callToActionLabel: string;
  validFrom: string | null;
  validUntil: string | null;
  contextFields: ContextField[];
};

export type OpportunityStatus =
  | 'DRAFT'
  | 'UNDER_REVIEW'
  | 'APPROVED'
  | 'PUBLISHED'
  | 'PAUSED'
  | 'REVOKED'
  | 'EXPIRED';

export type ContextualOpportunity = {
  id: string;
  publisherId: string;
  channelId: string;
  environmentId: string;
  key: string;
  status: OpportunityStatus;
  submittedRevision?: number | null;
  approvedRevision?: number | null;
  currentRevision: number;
  version: number;
  createdAt: string;
  updatedAt: string;
  createdBy: string;
  updatedBy: string;
  effectivelyAvailable: boolean;
  effectivelyPublishable?: boolean;
  effectivelyPublished?: boolean;
  current: OpportunityRevisionSnapshot;
};

export type OpportunityDraft = {
  key?: string;
  title: string;
  contextMode: ContextMode;
  contextSummaryTemplate: string;
  objectiveTemplate: string;
  callToActionLabel: string;
  validFrom?: string | null;
  validUntil?: string | null;
  contextFields: Array<{
    key: string;
    label: string;
    type: ContextFieldType;
    required: boolean;
    source: ContextFieldSource;
    classification: 'NON_PERSONAL';
    allowedValues: string[];
  }>;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object';
}

function isMode(value: unknown): value is ContextMode {
  return value === 'STATIC' || value === 'DYNAMIC' || value === 'HYBRID';
}

function parseField(payload: unknown): ContextField {
  if (!isRecord(payload) || typeof payload['key'] !== 'string' || typeof payload['label'] !== 'string') {
    throw new Error('invalid field');
  }
  const allowed = payload['allowedValues'];
  return {
    key: payload['key'],
    label: payload['label'],
    type: payload['type'] as ContextFieldType,
    required: Boolean(payload['required']),
    source: payload['source'] as ContextFieldSource,
    classification: 'NON_PERSONAL',
    position: typeof payload['position'] === 'number' ? payload['position'] : 0,
    allowedValues: Array.isArray(allowed) ? allowed.map((item) => String(item)) : [],
  };
}

function parseRevision(payload: unknown): OpportunityRevisionSnapshot {
  if (!isRecord(payload) || !isMode(payload['contextMode']) || !Array.isArray(payload['contextFields'])) {
    throw new Error('invalid revision');
  }
  return {
    id: String(payload['id']),
    revisionNumber: Number(payload['revisionNumber']),
    createdAt: String(payload['createdAt']),
    createdBy: String(payload['createdBy']),
    title: String(payload['title']),
    contextMode: payload['contextMode'],
    contextSummaryTemplate: String(payload['contextSummaryTemplate']),
    objectiveTemplate: String(payload['objectiveTemplate']),
    callToActionLabel: String(payload['callToActionLabel']),
    validFrom: typeof payload['validFrom'] === 'string' ? payload['validFrom'] : null,
    validUntil: typeof payload['validUntil'] === 'string' ? payload['validUntil'] : null,
    contextFields: payload['contextFields'].map(parseField),
  };
}

function isStatus(value: unknown): value is OpportunityStatus {
  return (
    value === 'DRAFT' ||
    value === 'UNDER_REVIEW' ||
    value === 'APPROVED' ||
    value === 'PUBLISHED' ||
    value === 'PAUSED' ||
    value === 'REVOKED' ||
    value === 'EXPIRED'
  );
}

function parseOpportunity(payload: unknown): ContextualOpportunity {
  if (!isRecord(payload) || !isStatus(payload['status']) || typeof payload['key'] !== 'string') {
    throw new Error('invalid opportunity');
  }
  return {
    id: String(payload['id']),
    publisherId: String(payload['publisherId']),
    channelId: String(payload['channelId']),
    environmentId: String(payload['environmentId']),
    key: payload['key'],
    status: payload['status'],
    submittedRevision:
      typeof payload['submittedRevision'] === 'number' ? payload['submittedRevision'] : null,
    approvedRevision:
      typeof payload['approvedRevision'] === 'number' ? payload['approvedRevision'] : null,
    currentRevision: Number(payload['currentRevision']),
    version: Number(payload['version']),
    createdAt: String(payload['createdAt']),
    updatedAt: String(payload['updatedAt']),
    createdBy: String(payload['createdBy']),
    updatedBy: String(payload['updatedBy']),
    effectivelyAvailable: Boolean(payload['effectivelyAvailable']),
    effectivelyPublishable:
      typeof payload['effectivelyPublishable'] === 'boolean'
        ? payload['effectivelyPublishable']
        : undefined,
    effectivelyPublished:
      typeof payload['effectivelyPublished'] === 'boolean'
        ? payload['effectivelyPublished']
        : undefined,
    current: parseRevision(payload['current']),
  };
}

function parsePage<T>(payload: unknown, item: (value: unknown) => T): CatalogPage<T> {
  if (!isRecord(payload) || !Array.isArray(payload['items']) || !isRecord(payload['page'])) {
    throw new Error('invalid page');
  }
  const page = payload['page'];
  const next = page['next'];
  if (typeof page['size'] !== 'number' || (next !== null && typeof next !== 'string')) {
    throw new Error('invalid page');
  }
  return {
    items: payload['items'].map(item),
    page: { size: page['size'], next },
  };
}

async function opportunityFetch(url: string, init?: RequestInit): Promise<Response> {
  const headers = new Headers();
  headers.set('Accept', 'application/json');
  headers.set(CORRELATION_HEADER, newCorrelationId());
  if (init?.headers) {
    new Headers(init.headers).forEach((value, name) => {
      headers.set(name, value);
    });
  }
  const response = await fetch(url, {
    method: init?.method,
    body: init?.body,
    signal: init?.signal,
    headers,
  });
  if (!response.ok) {
    throw await readApiError(response);
  }
  return response;
}

function collectionUrl(
  baseUrl: string,
  publisherId: string,
  channelId: string,
  environmentId: string,
): string {
  return `${baseUrl}/api/v1/admin/publishers/${publisherId}/channels/${channelId}/environments/${environmentId}/opportunities`;
}

export async function fetchOpportunities(
  baseUrl: string,
  publisherId: string,
  channelId: string,
  environmentId: string,
  signal?: AbortSignal,
): Promise<CatalogPage<ContextualOpportunity>> {
  const response = await opportunityFetch(
    `${collectionUrl(baseUrl, publisherId, channelId, environmentId)}?page[size]=20`,
    { signal },
  );
  return parsePage(await response.json(), parseOpportunity);
}

export async function fetchOpportunity(
  baseUrl: string,
  publisherId: string,
  channelId: string,
  environmentId: string,
  opportunityId: string,
): Promise<ContextualOpportunity> {
  const response = await opportunityFetch(
    `${collectionUrl(baseUrl, publisherId, channelId, environmentId)}/${opportunityId}`,
  );
  return parseOpportunity(await response.json());
}

export async function fetchOpportunityRevisions(
  baseUrl: string,
  publisherId: string,
  channelId: string,
  environmentId: string,
  opportunityId: string,
): Promise<CatalogPage<OpportunityRevisionSnapshot>> {
  const response = await opportunityFetch(
    `${collectionUrl(baseUrl, publisherId, channelId, environmentId)}/${opportunityId}/revisions?page[size]=20`,
  );
  return parsePage(await response.json(), parseRevision);
}

export async function createOpportunity(
  baseUrl: string,
  publisherId: string,
  channelId: string,
  environmentId: string,
  draft: OpportunityDraft,
): Promise<ContextualOpportunity> {
  const response = await opportunityFetch(
    collectionUrl(baseUrl, publisherId, channelId, environmentId),
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(draft),
    },
  );
  return parseOpportunity(await response.json());
}

export async function createOpportunityRevision(
  baseUrl: string,
  publisherId: string,
  channelId: string,
  environmentId: string,
  opportunityId: string,
  expectedVersion: number,
  baseRevision: number,
  draft: OpportunityDraft,
): Promise<ContextualOpportunity> {
  const response = await opportunityFetch(
    `${collectionUrl(baseUrl, publisherId, channelId, environmentId)}/${opportunityId}/revisions`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...draft, expectedVersion, baseRevision }),
    },
  );
  return parseOpportunity(await response.json());
}

export function declaredPlaceholders(draft: {
  title: string;
  contextSummaryTemplate: string;
  objectiveTemplate: string;
  callToActionLabel: string;
}): string[] {
  const text = `${draft.title} ${draft.contextSummaryTemplate} ${draft.objectiveTemplate} ${draft.callToActionLabel}`;
  const found = text.match(/\{\{[a-z][a-zA-Z0-9]{1,39}\}\}/g) ?? [];
  return [...new Set(found)];
}

export function datetimeLocalToUtcIso(value: string): string | null {
  const trimmed = value.trim();
  if (trimmed.length === 0) {
    return null;
  }
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$/.test(trimmed)) {
    throw new Error('INVALID_DATETIME');
  }
  const withSeconds = trimmed.length === 16 ? `${trimmed}:00` : trimmed;
  return `${withSeconds}.000Z`;
}

export function utcIsoToDatetimeLocal(value: string | null): string {
  if (value == null || value.length < 16) {
    return '';
  }
  return value.slice(0, 16);
}

export const GOVERNANCE_ACTION_LABEL: Record<GovernanceAction, string> = {
  SUBMIT: 'Submeter revisão',
  RETURN_FOR_CHANGES: 'Devolver para alterações',
  APPROVE: 'Aprovar',
  REJECT: 'Rejeitar',
  ACTIVATE: 'Ativar autorização de publicação',
  PAUSE: 'Pausar',
  RESUME: 'Retomar',
  EXPIRE: 'Expirar',
  REVOKE: 'Revogar',
};

export type GovernanceAction =
  | 'SUBMIT'
  | 'RETURN_FOR_CHANGES'
  | 'APPROVE'
  | 'REJECT'
  | 'ACTIVATE'
  | 'PAUSE'
  | 'RESUME'
  | 'EXPIRE'
  | 'REVOKE';

export type OpportunityGovernance = {
  opportunityId: string;
  status: OpportunityStatus;
  currentRevision: number;
  submittedRevision: number | null;
  approvedRevision: number | null;
  openSubmissionId: string | null;
  submittedBy: string | null;
  approvedBy: string | null;
  version: number;
  effectivelyAvailable: boolean;
  effectivelyPublishable: boolean;
  effectivelyPublished: boolean;
  windowOpen: boolean;
  windowExpired: boolean;
  publishedMeans: string;
  latestDecision: {
    id: string;
    submissionId: string;
    revisionNumber: number;
    outcome: string;
    decidedAt: string;
    decidedBy: string;
    justification: string | null;
  } | null;
  availableActions: GovernanceAction[];
};

export type LifecycleEvent = {
  id: string;
  opportunityId: string;
  revisionNumber: number;
  eventType: string;
  previousStatus: string;
  newStatus: string;
  actorSubjectId: string;
  occurredAt: string;
  justification: string | null;
  correlationId: string;
};

function parseGovernance(payload: unknown): OpportunityGovernance {
  if (!isRecord(payload) || !isStatus(payload['status']) || !Array.isArray(payload['availableActions'])) {
    throw new Error('invalid governance');
  }
  const decision = payload['latestDecision'];
  return {
    opportunityId: String(payload['opportunityId']),
    status: payload['status'],
    currentRevision: Number(payload['currentRevision']),
    submittedRevision:
      typeof payload['submittedRevision'] === 'number' ? payload['submittedRevision'] : null,
    approvedRevision:
      typeof payload['approvedRevision'] === 'number' ? payload['approvedRevision'] : null,
    openSubmissionId:
      typeof payload['openSubmissionId'] === 'string' ? payload['openSubmissionId'] : null,
    submittedBy: typeof payload['submittedBy'] === 'string' ? payload['submittedBy'] : null,
    approvedBy: typeof payload['approvedBy'] === 'string' ? payload['approvedBy'] : null,
    version: Number(payload['version']),
    effectivelyAvailable: Boolean(payload['effectivelyAvailable']),
    effectivelyPublishable: Boolean(payload['effectivelyPublishable']),
    effectivelyPublished: Boolean(payload['effectivelyPublished']),
    windowOpen: Boolean(payload['windowOpen']),
    windowExpired: Boolean(payload['windowExpired']),
    publishedMeans:
      typeof payload['publishedMeans'] === 'string'
        ? payload['publishedMeans']
        : 'INTERNAL_AUTHORIZATION_ONLY',
    latestDecision:
      isRecord(decision) && typeof decision['outcome'] === 'string'
        ? {
            id: String(decision['id']),
            submissionId: String(decision['submissionId']),
            revisionNumber: Number(decision['revisionNumber']),
            outcome: decision['outcome'],
            decidedAt: String(decision['decidedAt']),
            decidedBy: String(decision['decidedBy']),
            justification:
              typeof decision['justification'] === 'string' ? decision['justification'] : null,
          }
        : null,
    availableActions: payload['availableActions'].filter(
      (action): action is GovernanceAction => typeof action === 'string',
    ),
  };
}

function parseEvent(payload: unknown): LifecycleEvent {
  if (!isRecord(payload) || typeof payload['eventType'] !== 'string') {
    throw new Error('invalid event');
  }
  return {
    id: String(payload['id']),
    opportunityId: String(payload['opportunityId']),
    revisionNumber: Number(payload['revisionNumber']),
    eventType: payload['eventType'],
    previousStatus: String(payload['previousStatus']),
    newStatus: String(payload['newStatus']),
    actorSubjectId: String(payload['actorSubjectId']),
    occurredAt: String(payload['occurredAt']),
    justification: typeof payload['justification'] === 'string' ? payload['justification'] : null,
    correlationId: String(payload['correlationId']),
  };
}

function opportunityItemUrl(
  baseUrl: string,
  publisherId: string,
  channelId: string,
  environmentId: string,
  opportunityId: string,
): string {
  return `${collectionUrl(baseUrl, publisherId, channelId, environmentId)}/${opportunityId}`;
}

export async function fetchOpportunityGovernance(
  baseUrl: string,
  publisherId: string,
  channelId: string,
  environmentId: string,
  opportunityId: string,
): Promise<OpportunityGovernance> {
  const response = await opportunityFetch(
    `${opportunityItemUrl(baseUrl, publisherId, channelId, environmentId, opportunityId)}/governance`,
  );
  return parseGovernance(await response.json());
}

export async function fetchOpportunityGovernanceEvents(
  baseUrl: string,
  publisherId: string,
  channelId: string,
  environmentId: string,
  opportunityId: string,
): Promise<CatalogPage<LifecycleEvent>> {
  const response = await opportunityFetch(
    `${opportunityItemUrl(baseUrl, publisherId, channelId, environmentId, opportunityId)}/governance/events?page[size]=20`,
  );
  return parsePage(await response.json(), parseEvent);
}

export async function postOpportunityGovernance(
  baseUrl: string,
  publisherId: string,
  channelId: string,
  environmentId: string,
  opportunityId: string,
  action: GovernanceAction,
  expectedVersion: number,
  revisionNumber?: number | null,
  justification?: string,
): Promise<OpportunityGovernance> {
  const path = governancePath(action);
  const response = await opportunityFetch(
    `${opportunityItemUrl(baseUrl, publisherId, channelId, environmentId, opportunityId)}${path}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        expectedVersion,
        revisionNumber: revisionNumber ?? undefined,
        justification,
      }),
    },
  );
  return parseGovernance(await response.json());
}

function governancePath(action: GovernanceAction): string {
  switch (action) {
    case 'SUBMIT':
      return '/governance/submit';
    case 'RETURN_FOR_CHANGES':
      return '/governance/return-for-changes';
    case 'APPROVE':
      return '/governance/approve';
    case 'REJECT':
      return '/governance/reject';
    case 'ACTIVATE':
      return '/publication/activate';
    case 'PAUSE':
      return '/publication/pause';
    case 'RESUME':
      return '/publication/resume';
    case 'EXPIRE':
      return '/publication/expire';
    case 'REVOKE':
      return '/publication/revoke';
  }
}

export const CONTEXT_MODES: ContextMode[] = ['STATIC', 'DYNAMIC', 'HYBRID'];
export const FIELD_TYPES: ContextFieldType[] = ['TEXT', 'NUMBER', 'BOOLEAN', 'DATE', 'ENUM'];
export const FIELD_SOURCES: ContextFieldSource[] = ['PUBLISHER', 'USER', 'EITHER'];

export const OPPORTUNITY_STATUS_LABEL: Record<OpportunityStatus, string> = {
  DRAFT: 'Rascunho',
  UNDER_REVIEW: 'Em revisão',
  APPROVED: 'Aprovada',
  PUBLISHED: 'Publicação autorizada',
  PAUSED: 'Pausada',
  REVOKED: 'Revogada',
  EXPIRED: 'Expirada',
};
