import { readApiError } from './errors';

export type OperationalState = 'UP' | 'DEGRADED';

export type SystemInfo = {
  name: string;
  version: string;
  applicationId: string;
  operationalState: OperationalState;
};

export const CORRELATION_HEADER = 'X-Correlation-ID';

export function apiBaseUrl(): string {
  const configured: unknown = import.meta.env['VITE_API_BASE_URL'];
  if (typeof configured === 'string' && configured.trim().length > 0) {
    return configured.replace(/\/$/, '');
  }
  return 'http://127.0.0.1:8088';
}

export function newCorrelationId(): string {
  return crypto.randomUUID();
}

function isOperationalState(value: unknown): value is OperationalState {
  return value === 'UP' || value === 'DEGRADED';
}

export function parseSystemInfo(payload: unknown): SystemInfo {
  if (payload === null || typeof payload !== 'object') {
    throw new Error('invalid payload');
  }
  const record = payload as Record<string, unknown>;
  const name = record['name'];
  const version = record['version'];
  const applicationId = record['applicationId'];
  const operationalState = record['operationalState'];
  if (
    typeof name !== 'string' ||
    typeof version !== 'string' ||
    typeof applicationId !== 'string' ||
    applicationId.trim().length === 0 ||
    !isOperationalState(operationalState)
  ) {
    throw new Error('invalid payload');
  }
  return { name, version, applicationId, operationalState };
}

export async function fetchSystemInfo(baseUrl: string, signal?: AbortSignal): Promise<SystemInfo> {
  const response = await fetch(`${baseUrl}/api/v1/system/info`, {
    signal,
    headers: {
      Accept: 'application/json',
      [CORRELATION_HEADER]: newCorrelationId(),
    },
  });
  if (!response.ok) {
    throw await readApiError(response);
  }
  return parseSystemInfo(await response.json());
}
