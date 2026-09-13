import { CORRELATION_HEADER, newCorrelationId } from './systemInfo';
import { readApiError } from './errors';

export type PublishedBlock = {
  position: number;
  title: string;
  body: string;
};

export type PublishedReference = {
  url: string;
  consultedOn: string;
  verificationStatus: string;
};

export type PublishedDemonstration = {
  key: string;
  title: string;
  summary: string;
  intendedAudience: string;
  scopeNote: string;
  revisionNumber: number;
  publishedAt: string;
  blocks: PublishedBlock[];
  references: PublishedReference[];
};

export class DemonstrationAbsenceError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'DemonstrationAbsenceError';
    this.status = status;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object';
}

function parsePublished(payload: unknown): PublishedDemonstration {
  if (!isRecord(payload)) {
    throw new Error('invalid payload');
  }
  const blocks = payload['blocks'];
  const references = payload['references'];
  if (
    typeof payload['key'] !== 'string' ||
    typeof payload['title'] !== 'string' ||
    typeof payload['summary'] !== 'string' ||
    typeof payload['intendedAudience'] !== 'string' ||
    typeof payload['scopeNote'] !== 'string' ||
    typeof payload['revisionNumber'] !== 'number' ||
    typeof payload['publishedAt'] !== 'string' ||
    !Array.isArray(blocks) ||
    !Array.isArray(references)
  ) {
    throw new Error('invalid payload');
  }
  return {
    key: payload['key'],
    title: payload['title'],
    summary: payload['summary'],
    intendedAudience: payload['intendedAudience'],
    scopeNote: payload['scopeNote'],
    revisionNumber: payload['revisionNumber'],
    publishedAt: payload['publishedAt'],
    blocks: blocks.filter(isRecord).map((block) => ({
      position: Number(block['position']),
      title: typeof block['title'] === 'string' ? block['title'] : '',
      body: typeof block['body'] === 'string' ? block['body'] : '',
    })),
    references: references.filter(isRecord).map((reference) => ({
      url: typeof reference['url'] === 'string' ? reference['url'] : '',
      consultedOn: typeof reference['consultedOn'] === 'string' ? reference['consultedOn'] : '',
      verificationStatus:
        typeof reference['verificationStatus'] === 'string'
          ? reference['verificationStatus']
          : '',
    })),
  };
}

export async function fetchPublishedDemonstration(
  baseUrl: string,
  key: string,
  signal?: AbortSignal,
): Promise<PublishedDemonstration | null> {
  let response: Response;
  try {
    response = await fetch(`${baseUrl}/api/v1/public/demonstrations/${key}`, {
      signal,
      headers: {
        Accept: 'application/json',
        [CORRELATION_HEADER]: newCorrelationId(),
      },
    });
  } catch {
    throw new DemonstrationAbsenceError(0, 'network');
  }
  if (response.status === 404) {
    return null;
  }
  if (response.status >= 500) {
    throw new DemonstrationAbsenceError(response.status, 'unavailable');
  }
  if (!response.ok) {
    throw await readApiError(response);
  }
  return parsePublished(await response.json());
}
