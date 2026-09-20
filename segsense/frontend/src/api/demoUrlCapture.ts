import { CORRELATION_HEADER, newCorrelationId } from './systemInfo';
import { readApiError } from './errors';

export type UrlCaptureElement = {
  key: string;
  value: string;
  evidence: string;
  origin: string;
  rule?: string;
  startOffset?: string;
  endOffset?: string;
  windowKind?: string;
};

export type UrlCaptureProjection = {
  captureId: string;
  publicStatus: string;
  message: string;
  nextStep: string;
  requestedUrl?: string | null;
  finalUrl?: string | null;
  finalHost?: string | null;
  capturedAt?: string | null;
  title?: string | null;
  excerpt?: string | null;
  normalizedText?: string | null;
  extractedElementsJson?: string | null;
  technical?: {
    resultCode?: string;
    httpStatus?: number | null;
    contentType?: string | null;
    bytesSha256?: string | null;
    textSha256?: string | null;
    extractorVersion?: string | null;
    selectionStrategy?: string | null;
    detectedLanguage?: string | null;
    correlationId?: string | null;
  };
};

export type UrlCaptureConfirmation = {
  confirmationId: string;
  captureId: string;
  publicStatus: string;
  message: string;
  nextStep: string;
  confirmedAt?: string;
  confirmedElementsJson?: string;
  correctionsJson?: string;
};

export async function capturePublicUrl(
  baseUrl: string,
  url: string,
  signal?: AbortSignal,
): Promise<UrlCaptureProjection> {
  const response = await fetch(`${baseUrl}/api/v1/public/demo/url-captures`, {
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
  return (await response.json()) as UrlCaptureProjection;
}

export async function confirmPublicUrlCapture(
  baseUrl: string,
  captureId: string,
  payload?: {
    confirmedKeys?: string[];
    corrections?: Record<string, string>;
    declaredNote?: string;
  },
  signal?: AbortSignal,
): Promise<UrlCaptureConfirmation> {
  const response = await fetch(`${baseUrl}/api/v1/public/demo/url-captures/${captureId}/confirmations`, {
    method: 'POST',
    credentials: 'omit',
    signal,
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      [CORRELATION_HEADER]: newCorrelationId(),
    },
    body: JSON.stringify(payload ?? {}),
  });
  if (!response.ok) {
    throw await readApiError(response);
  }
  return (await response.json()) as UrlCaptureConfirmation;
}

export function parseCaptureElements(json: string | null | undefined): UrlCaptureElement[] {
  if (!json) {
    return [];
  }
  try {
    const parsed = JSON.parse(json) as { elements?: UrlCaptureElement[] };
    return Array.isArray(parsed.elements) ? parsed.elements : [];
  } catch {
    return [];
  }
}
