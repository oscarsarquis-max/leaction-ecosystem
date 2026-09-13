import { readApiError } from './errors';
import { CORRELATION_HEADER, newCorrelationId } from './systemInfo';
import { type CatalogPage } from './catalog';
import { type ContextFieldType } from './opportunity';

export type EffectiveLinkStatus = 'ACTIVE' | 'REVOKED' | 'EXPIRED';

export type ContextLinkBinding = {
  fieldKey: string;
  type: ContextFieldType;
  value: string | number | boolean;
};

export type ContextLink = {
  id: string;
  placementKey: string;
  label: string;
  status: 'ACTIVE' | 'REVOKED';
  effectiveStatus: EffectiveLinkStatus;
  revisionNumber: number;
  issuedAt: string;
  issuedBy: string;
  expiresAt: string;
  revokedAt: string | null;
  revokedBy: string | null;
  revocationReason: string | null;
  version: number;
  tokenHint: string;
  publisherContext: ContextLinkBinding[];
};

export type IssuedContextLink = ContextLink & {
  token: string;
  publicUrl: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object';
}

function parseBinding(payload: unknown): ContextLinkBinding {
  if (!isRecord(payload) || typeof payload['fieldKey'] !== 'string' || typeof payload['type'] !== 'string') {
    throw new Error('invalid binding');
  }
  const value = payload['value'];
  if (typeof value !== 'string' && typeof value !== 'number' && typeof value !== 'boolean') {
    throw new Error('invalid binding');
  }
  return {
    fieldKey: payload['fieldKey'],
    type: payload['type'] as ContextFieldType,
    value,
  };
}

function parseLink(payload: unknown): ContextLink {
  if (!isRecord(payload) || typeof payload['id'] !== 'string' || typeof payload['placementKey'] !== 'string') {
    throw new Error('invalid link');
  }
  const bindings = payload['publisherContext'];
  return {
    id: payload['id'],
    placementKey: payload['placementKey'],
    label: String(payload['label']),
    status: payload['status'] === 'REVOKED' ? 'REVOKED' : 'ACTIVE',
    effectiveStatus: payload['effectiveStatus'] === 'REVOKED'
      ? 'REVOKED'
      : payload['effectiveStatus'] === 'EXPIRED'
        ? 'EXPIRED'
        : 'ACTIVE',
    revisionNumber: Number(payload['revisionNumber']),
    issuedAt: String(payload['issuedAt']),
    issuedBy: String(payload['issuedBy']),
    expiresAt: String(payload['expiresAt']),
    revokedAt: typeof payload['revokedAt'] === 'string' ? payload['revokedAt'] : null,
    revokedBy: typeof payload['revokedBy'] === 'string' ? payload['revokedBy'] : null,
    revocationReason:
      typeof payload['revocationReason'] === 'string' ? payload['revocationReason'] : null,
    version: Number(payload['version']),
    tokenHint: typeof payload['tokenHint'] === 'string' ? payload['tokenHint'] : '',
    publisherContext: Array.isArray(bindings) ? bindings.map(parseBinding) : [],
  };
}

function parseIssued(payload: unknown): IssuedContextLink {
  const link = parseLink(payload);
  if (!isRecord(payload) || typeof payload['token'] !== 'string' || typeof payload['publicUrl'] !== 'string') {
    throw new Error('invalid issued link');
  }
  return { ...link, token: payload['token'], publicUrl: payload['publicUrl'] };
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

async function linkFetch(url: string, init?: RequestInit): Promise<Response> {
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

function linksUrl(
  baseUrl: string,
  publisherId: string,
  channelId: string,
  environmentId: string,
  opportunityId: string,
): string {
  return `${baseUrl}/api/v1/admin/publishers/${publisherId}/channels/${channelId}/environments/${environmentId}/opportunities/${opportunityId}/links`;
}

export async function fetchContextLinks(
  baseUrl: string,
  publisherId: string,
  channelId: string,
  environmentId: string,
  opportunityId: string,
): Promise<CatalogPage<ContextLink>> {
  const response = await linkFetch(
    `${linksUrl(baseUrl, publisherId, channelId, environmentId, opportunityId)}?page[size]=20`,
  );
  return parsePage(await response.json(), parseLink);
}

export async function issueContextLink(
  baseUrl: string,
  publisherId: string,
  channelId: string,
  environmentId: string,
  opportunityId: string,
  body: {
    placementKey: string;
    label: string;
    expiresAt: string;
    publisherContext: Array<{ fieldKey: string; value: string | number | boolean }>;
  },
): Promise<IssuedContextLink> {
  const response = await linkFetch(
    linksUrl(baseUrl, publisherId, channelId, environmentId, opportunityId),
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
  );
  return parseIssued(await response.json());
}

export async function revokeContextLink(
  baseUrl: string,
  publisherId: string,
  channelId: string,
  environmentId: string,
  opportunityId: string,
  linkId: string,
  expectedVersion: number,
  justification: string,
): Promise<ContextLink> {
  const response = await linkFetch(
    `${linksUrl(baseUrl, publisherId, channelId, environmentId, opportunityId)}/${linkId}/revoke`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ expectedVersion, justification }),
    },
  );
  return parseLink(await response.json());
}

export const EFFECTIVE_LINK_STATUS_LABEL: Record<EffectiveLinkStatus, string> = {
  ACTIVE: 'Ativo',
  REVOKED: 'Revogado',
  EXPIRED: 'Expirado',
};
