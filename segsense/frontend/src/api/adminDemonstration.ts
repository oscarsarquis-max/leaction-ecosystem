import { readApiError } from './errors';
import { CORRELATION_HEADER, newCorrelationId } from './systemInfo';

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const headers = new Headers();
  headers.set('Accept', 'application/json');
  headers.set('Content-Type', 'application/json');
  headers.set(CORRELATION_HEADER, newCorrelationId());
  const response = await fetch(url, {
    method: init?.method,
    body: init?.body,
    signal: init?.signal,
    headers,
  });
  if (!response.ok) {
    throw await readApiError(response);
  }
  return (await response.json()) as T;
}

export type AdminDemonstration = {
  id: string;
  key: string;
  workflowStatus: string;
  publicationStatus: string;
  currentRevision: number;
  publishedRevision: number | null;
  version: number;
  title: string;
  summary: string;
  intendedAudience: string;
  scopeNote: string;
  frozen: boolean;
  administrativePreview: boolean;
  blocks: { position: number; title: string; body: string }[];
  claims: { position: number; text: string; sourceId: string }[];
};

export type AdminSource = {
  id: string;
  key: string;
  url: string;
  consultedOn: string;
  accessKind: string;
  verificationStatus: string;
  summary: string;
};

export async function fetchDemonstrations(baseUrl: string, signal?: AbortSignal) {
  return request<AdminDemonstration[]>(`${baseUrl}/api/v1/admin/demonstrations`, { signal });
}

export async function fetchDemonstrationSources(baseUrl: string, signal?: AbortSignal) {
  return request<AdminSource[]>(`${baseUrl}/api/v1/admin/demonstrations/sources`, { signal });
}

export async function fetchDemonstration(baseUrl: string, key: string, signal?: AbortSignal) {
  return request<AdminDemonstration>(`${baseUrl}/api/v1/admin/demonstrations/${key}`, { signal });
}

export async function postDemonstration(
  baseUrl: string,
  path: string,
  body: unknown,
): Promise<AdminDemonstration> {
  return request<AdminDemonstration>(`${baseUrl}${path}`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

