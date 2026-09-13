import { readApiError } from './errors';
import { CORRELATION_HEADER, newCorrelationId } from './systemInfo';

export type ConsentNoticeSnapshot = {
  versionNumber: number;
  purposeTitle: string;
  purposeDescription: string;
  transparencyText: string;
  noExternalSharingText: string;
  createdAt: string;
  fields: Array<{
    key: string;
    label: string;
    type: string;
    source: string;
    required: boolean;
    allowedValues: string[];
  }>;
};

export type ConsentNotice = {
  id: string;
  opportunityId: string;
  revisionNumber: number;
  currentVersion: number;
  approvedVersion: number | null;
  status: 'DRAFT' | 'APPROVED' | 'RETIRED';
  version: number;
  current: ConsentNoticeSnapshot;
};

function noticeUrl(
  baseUrl: string,
  publisherId: string,
  channelId: string,
  environmentId: string,
  opportunityId: string,
): string {
  return `${baseUrl}/api/v1/admin/publishers/${publisherId}/channels/${channelId}/environments/${environmentId}/opportunities/${opportunityId}/consent-notice`;
}

async function noticeFetch(url: string, init?: RequestInit): Promise<Response> {
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

export async function fetchConsentNotice(
  baseUrl: string,
  publisherId: string,
  channelId: string,
  environmentId: string,
  opportunityId: string,
): Promise<ConsentNotice> {
  const response = await noticeFetch(
    noticeUrl(baseUrl, publisherId, channelId, environmentId, opportunityId),
  );
  return (await response.json()) as ConsentNotice;
}

export async function postConsentNotice(
  baseUrl: string,
  publisherId: string,
  channelId: string,
  environmentId: string,
  opportunityId: string,
  path: '' | '/draft' | '/approve' | '/retire',
  body: Record<string, unknown>,
): Promise<ConsentNotice> {
  const response = await noticeFetch(
    noticeUrl(baseUrl, publisherId, channelId, environmentId, opportunityId) + path,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
  );
  return (await response.json()) as ConsentNotice;
}
