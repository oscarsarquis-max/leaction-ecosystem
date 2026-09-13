import { readApiError } from './errors';
import { apiBaseUrl } from './systemInfo';

export type PublisherBindingView = {
  fieldKey: string;
  label: string;
  type: string;
  value: string | number | boolean;
};

export type UserFieldView = {
  key: string;
  label: string;
  type: string;
  required: boolean;
  allowedValues: string[];
};

export type PublicContextEnvelope = {
  title: string;
  callToActionLabel: string;
  contextSummary: {
    template: string;
    publisherValues: Record<string, unknown>;
  };
  publisherBindings: PublisherBindingView[];
  userFields: UserFieldView[];
  effectiveValidFrom: string | null;
  effectiveValidUntil: string | null;
  quotationPerformed: boolean;
  eligibilityEvaluated: boolean;
  recommendationPerformed: boolean;
  continuity: ContinuityView;
};

export type ContinuityView = {
  available: boolean;
  noticeVersion: number | null;
  purposeTitle: string | null;
  purposeDescription: string | null;
  transparencyText: string | null;
  noExternalSharingStatement: string | null;
};

export type CollectibleFieldView = {
  key: string;
  label: string;
  type: string;
  required: boolean;
  allowedValues: string[];
  value: string | number | boolean | null;
};

export type ContextInstanceView = {
  status: string;
  expectedVersion: number;
  expiresAt: string;
  noticeVersion: number;
  valuesUnavailable: boolean;
  credentialIssued: boolean;
  instanceCredential: string | null;
  sessionEndsOnReload: boolean;
  collectibleFields: CollectibleFieldView[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object';
}

function parseBinding(payload: unknown): PublisherBindingView {
  if (!isRecord(payload) || typeof payload['label'] !== 'string') {
    throw new Error('invalid binding');
  }
  const value = payload['value'];
  if (typeof value !== 'string' && typeof value !== 'number' && typeof value !== 'boolean') {
    throw new Error('invalid binding');
  }
  return {
    fieldKey: typeof payload['fieldKey'] === 'string' ? payload['fieldKey'] : '',
    label: payload['label'],
    type: typeof payload['type'] === 'string' ? payload['type'] : '',
    value,
  };
}

function parseUserField(payload: unknown): UserFieldView {
  if (!isRecord(payload) || typeof payload['label'] !== 'string') {
    throw new Error('invalid field');
  }
  const allowed = payload['allowedValues'];
  return {
    key: typeof payload['key'] === 'string' ? payload['key'] : '',
    label: payload['label'],
    type: typeof payload['type'] === 'string' ? payload['type'] : '',
    required: Boolean(payload['required']),
    allowedValues: Array.isArray(allowed) ? allowed.map((item) => String(item)) : [],
  };
}

function parseEnvelope(payload: unknown): PublicContextEnvelope {
  if (!isRecord(payload) || typeof payload['title'] !== 'string' || !isRecord(payload['contextSummary'])) {
    throw new Error('invalid envelope');
  }
  const summary = payload['contextSummary'];
  const template = summary['template'];
  const values = summary['publisherValues'];
  if (typeof template !== 'string' || !isRecord(values)) {
    throw new Error('invalid envelope');
  }
  const bindings = payload['publisherBindings'];
  const userFields = payload['userFields'];
  return {
    title: payload['title'],
    callToActionLabel:
      typeof payload['callToActionLabel'] === 'string' ? payload['callToActionLabel'] : '',
    contextSummary: {
      template,
      publisherValues: values,
    },
    publisherBindings: Array.isArray(bindings) ? bindings.map(parseBinding) : [],
    userFields: Array.isArray(userFields) ? userFields.map(parseUserField) : [],
    effectiveValidFrom:
      typeof payload['effectiveValidFrom'] === 'string' ? payload['effectiveValidFrom'] : null,
    effectiveValidUntil:
      typeof payload['effectiveValidUntil'] === 'string' ? payload['effectiveValidUntil'] : null,
    quotationPerformed: Boolean(payload['quotationPerformed']),
    eligibilityEvaluated: Boolean(payload['eligibilityEvaluated']),
    recommendationPerformed: Boolean(payload['recommendationPerformed']),
    continuity: parseContinuity(payload['continuity']),
  };
}

function parseContinuity(payload: unknown): ContinuityView {
  if (!isRecord(payload) || payload['available'] !== true) {
    return {
      available: false,
      noticeVersion: null,
      purposeTitle: null,
      purposeDescription: null,
      transparencyText: null,
      noExternalSharingStatement: null,
    };
  }
  return {
    available: true,
    noticeVersion: typeof payload['noticeVersion'] === 'number' ? payload['noticeVersion'] : null,
    purposeTitle: typeof payload['purposeTitle'] === 'string' ? payload['purposeTitle'] : null,
    purposeDescription:
      typeof payload['purposeDescription'] === 'string' ? payload['purposeDescription'] : null,
    transparencyText:
      typeof payload['transparencyText'] === 'string' ? payload['transparencyText'] : null,
    noExternalSharingStatement:
      typeof payload['noExternalSharingStatement'] === 'string'
        ? payload['noExternalSharingStatement']
        : null,
  };
}

export async function fetchPublicContextLink(
  opaqueToken: string,
  signal?: AbortSignal,
): Promise<PublicContextEnvelope> {
  const response = await fetch(
    `${apiBaseUrl()}/api/v1/public/context-links/${opaqueToken}`,
    {
      method: 'GET',
      credentials: 'omit',
      signal,
      headers: { Accept: 'application/json' },
    },
  );
  if (!response.ok) {
    throw await readApiError(response);
  }
  return parseEnvelope(await response.json());
}

const CREDENTIAL_HEADER = 'X-SegSense-Instance-Credential';

function parseInstance(payload: unknown): ContextInstanceView {
  if (!isRecord(payload) || typeof payload['status'] !== 'string') {
    throw new Error('invalid instance');
  }
  const fields = payload['collectibleFields'];
  return {
    status: payload['status'],
    expectedVersion: typeof payload['expectedVersion'] === 'number' ? payload['expectedVersion'] : 0,
    expiresAt: typeof payload['expiresAt'] === 'string' ? payload['expiresAt'] : '',
    noticeVersion: typeof payload['noticeVersion'] === 'number' ? payload['noticeVersion'] : 0,
    valuesUnavailable: Boolean(payload['valuesUnavailable']),
    credentialIssued: Boolean(payload['credentialIssued']),
    instanceCredential:
      typeof payload['instanceCredential'] === 'string' ? payload['instanceCredential'] : null,
    sessionEndsOnReload: payload['sessionEndsOnReload'] !== false,
    collectibleFields: Array.isArray(fields)
      ? fields.map((item) => {
          if (!isRecord(item) || typeof item['key'] !== 'string' || typeof item['label'] !== 'string') {
            throw new Error('invalid field');
          }
          const value = item['value'];
          return {
            key: item['key'],
            label: item['label'],
            type: typeof item['type'] === 'string' ? item['type'] : 'TEXT',
            required: Boolean(item['required']),
            allowedValues: Array.isArray(item['allowedValues'])
              ? item['allowedValues'].map((entry) => String(entry))
              : [],
            value:
              typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean'
                ? value
                : null,
          };
        })
      : [],
  };
}

async function instanceFetch(
  url: string,
  init: RequestInit & { credential?: string | null },
): Promise<ContextInstanceView> {
  const headers = new Headers();
  headers.set('Accept', 'application/json');
  if (init.body) {
    headers.set('Content-Type', 'application/json');
  }
  if (init.credential) {
    headers.set(CREDENTIAL_HEADER, init.credential);
  }
  if (init.headers) {
    new Headers(init.headers).forEach((value, name) => {
      headers.set(name, value);
    });
  }
  const response = await fetch(url, {
    method: init.method,
    body: init.body,
    signal: init.signal,
    credentials: 'omit',
    headers,
  });
  if (!response.ok) {
    throw await readApiError(response);
  }
  return parseInstance(await response.json());
}

export async function createContextInstance(
  opaqueToken: string,
  idempotencyKey: string,
): Promise<ContextInstanceView> {
  return instanceFetch(`${apiBaseUrl()}/api/v1/public/context-links/${opaqueToken}/context-instances`, {
    method: 'POST',
    headers: { 'Idempotency-Key': idempotencyKey },
  });
}

export async function fetchCurrentContextInstance(
  opaqueToken: string,
  credential: string,
): Promise<ContextInstanceView> {
  return instanceFetch(
    `${apiBaseUrl()}/api/v1/public/context-links/${opaqueToken}/context-instances/current`,
    { method: 'GET', credential },
  );
}

export async function putContextInstanceValues(
  opaqueToken: string,
  credential: string,
  expectedVersion: number,
  values: Array<{ key: string; type: string; value: string | number | boolean }>,
): Promise<ContextInstanceView> {
  return instanceFetch(
    `${apiBaseUrl()}/api/v1/public/context-links/${opaqueToken}/context-instances/current/values`,
    {
      method: 'PUT',
      credential,
      body: JSON.stringify({ expectedVersion, values }),
    },
  );
}

export async function authorizeContextInstance(
  opaqueToken: string,
  credential: string,
  expectedVersion: number,
  noticeVersion: number,
): Promise<ContextInstanceView> {
  return instanceFetch(
    `${apiBaseUrl()}/api/v1/public/context-links/${opaqueToken}/context-instances/current/authorize`,
    {
      method: 'POST',
      credential,
      body: JSON.stringify({ expectedVersion, noticeVersion, acknowledged: true }),
    },
  );
}

export async function withdrawContextInstance(
  opaqueToken: string,
  credential: string,
  expectedVersion: number,
): Promise<ContextInstanceView> {
  return instanceFetch(
    `${apiBaseUrl()}/api/v1/public/context-links/${opaqueToken}/context-instances/current/withdraw`,
    {
      method: 'POST',
      credential,
      body: JSON.stringify({ expectedVersion }),
    },
  );
}
