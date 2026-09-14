import { CORRELATION_HEADER, newCorrelationId } from './systemInfo';
import { readApiError } from './errors';

export type GovernedContextSource = {
  id: string;
  slug: string;
  title: string;
  sourceLabel: string;
  version: string;
  capturedAt: string;
  revoked: boolean;
  url: string;
  path?: string;
  authorizedExcerpt?: string;
  elements?: Record<string, string>;
};

export async function listDemoContextSources(baseUrl: string): Promise<GovernedContextSource[]> {
  const response = await fetch(`${baseUrl}/api/v1/public/demo/context-sources`, {
    method: 'GET',
    credentials: 'omit',
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) {
    throw await readApiError(response);
  }
  return (await response.json()) as GovernedContextSource[];
}

export async function resolveDemoContextSource(
  baseUrl: string,
  url: string,
  signal?: AbortSignal,
): Promise<GovernedContextSource> {
  const response = await fetch(`${baseUrl}/api/v1/public/demo/context-sources/resolve`, {
    method: 'POST',
    credentials: 'omit',
    signal,
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      [CORRELATION_HEADER]: newCorrelationId(),
    },
    body: JSON.stringify({ url }),
  });
  if (!response.ok) {
    throw await readApiError(response);
  }
  return (await response.json()) as GovernedContextSource;
}
