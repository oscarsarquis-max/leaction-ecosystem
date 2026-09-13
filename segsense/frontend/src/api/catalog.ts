import { readApiError } from './errors';
import { CORRELATION_HEADER, newCorrelationId } from './systemInfo';

export type LifecycleStatus = 'DRAFT' | 'ACTIVE' | 'SUSPENDED';
export type ChannelType =
  | 'WEBSITE'
  | 'WEB_APPLICATION'
  | 'MOBILE_APPLICATION'
  | 'PARTNER_PORTAL';
export type EnvironmentType =
  | 'ARTICLE'
  | 'PAGE'
  | 'APPLICATION_SCREEN'
  | 'EMBEDDED_COMPONENT';

export type Publisher = {
  id: string;
  key: string;
  name: string;
  status: LifecycleStatus;
  version: number;
  createdAt: string;
  updatedAt: string;
  createdBy: string;
  updatedBy: string;
  effectivelyAvailable: boolean;
};

export type Channel = {
  id: string;
  publisherId: string;
  key: string;
  name: string;
  type: ChannelType;
  status: LifecycleStatus;
  version: number;
  createdAt: string;
  updatedAt: string;
  createdBy: string;
  updatedBy: string;
  effectivelyAvailable: boolean;
};

export type ContextualEnvironment = {
  id: string;
  publisherId: string;
  channelId: string;
  key: string;
  name: string;
  type: EnvironmentType;
  canonicalUrl: string | null;
  status: LifecycleStatus;
  version: number;
  createdAt: string;
  updatedAt: string;
  createdBy: string;
  updatedBy: string;
  effectivelyAvailable: boolean;
};

export type CatalogPage<T> = {
  items: T[];
  page: {
    size: number;
    next: string | null;
  };
};

function isStatus(value: unknown): value is LifecycleStatus {
  return value === 'DRAFT' || value === 'ACTIVE' || value === 'SUSPENDED';
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object';
}

function parsePublisher(payload: unknown): Publisher {
  if (!isRecord(payload)) {
    throw new Error('invalid publisher');
  }
  if (
    typeof payload['id'] !== 'string' ||
    typeof payload['key'] !== 'string' ||
    typeof payload['name'] !== 'string' ||
    !isStatus(payload['status']) ||
    typeof payload['version'] !== 'number' ||
    typeof payload['effectivelyAvailable'] !== 'boolean'
  ) {
    throw new Error('invalid publisher');
  }
  return payload as unknown as Publisher;
}

function parseChannel(payload: unknown): Channel {
  if (!isRecord(payload) || typeof payload['publisherId'] !== 'string' || typeof payload['type'] !== 'string') {
    throw new Error('invalid channel');
  }
  if (
    typeof payload['id'] !== 'string' ||
    typeof payload['key'] !== 'string' ||
    typeof payload['name'] !== 'string' ||
    !isStatus(payload['status']) ||
    typeof payload['effectivelyAvailable'] !== 'boolean'
  ) {
    throw new Error('invalid channel');
  }
  return payload as unknown as Channel;
}

function parseEnvironment(payload: unknown): ContextualEnvironment {
  if (!isRecord(payload) || typeof payload['channelId'] !== 'string' || typeof payload['type'] !== 'string') {
    throw new Error('invalid environment');
  }
  if (
    typeof payload['id'] !== 'string' ||
    typeof payload['key'] !== 'string' ||
    typeof payload['name'] !== 'string' ||
    !isStatus(payload['status']) ||
    typeof payload['effectivelyAvailable'] !== 'boolean'
  ) {
    throw new Error('invalid environment');
  }
  return payload as unknown as ContextualEnvironment;
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

async function catalogFetch(url: string, signal?: AbortSignal): Promise<Response> {
  const response = await fetch(url, {
    signal,
    headers: {
      Accept: 'application/json',
      [CORRELATION_HEADER]: newCorrelationId(),
    },
  });
  if (!response.ok) {
    throw await readApiError(response);
  }
  return response;
}

export async function fetchPublishers(baseUrl: string, signal?: AbortSignal): Promise<CatalogPage<Publisher>> {
  const response = await catalogFetch(`${baseUrl}/api/v1/admin/publishers?page[size]=20`, signal);
  return parsePage(await response.json(), parsePublisher);
}

export async function fetchChannels(
  baseUrl: string,
  publisherId: string,
  signal?: AbortSignal,
): Promise<CatalogPage<Channel>> {
  const response = await catalogFetch(
    `${baseUrl}/api/v1/admin/publishers/${publisherId}/channels?page[size]=20`,
    signal,
  );
  return parsePage(await response.json(), parseChannel);
}

export async function fetchEnvironments(
  baseUrl: string,
  publisherId: string,
  channelId: string,
  signal?: AbortSignal,
): Promise<CatalogPage<ContextualEnvironment>> {
  const response = await catalogFetch(
    `${baseUrl}/api/v1/admin/publishers/${publisherId}/channels/${channelId}/environments?page[size]=20`,
    signal,
  );
  return parsePage(await response.json(), parseEnvironment);
}

export const CHANNEL_TYPES: ChannelType[] = [
  'WEBSITE',
  'WEB_APPLICATION',
  'MOBILE_APPLICATION',
  'PARTNER_PORTAL',
];

export const ENVIRONMENT_TYPES: EnvironmentType[] = [
  'ARTICLE',
  'PAGE',
  'APPLICATION_SCREEN',
  'EMBEDDED_COMPONENT',
];

export const STATUS_LABEL: Record<LifecycleStatus, string> = {
  DRAFT: 'Rascunho',
  ACTIVE: 'Ativo',
  SUSPENDED: 'Suspenso',
};

export const CHANNEL_TYPE_LABEL: Record<ChannelType, string> = {
  WEBSITE: 'Site',
  WEB_APPLICATION: 'Aplicação web',
  MOBILE_APPLICATION: 'Aplicativo',
  PARTNER_PORTAL: 'Portal parceiro',
};

export const ENVIRONMENT_TYPE_LABEL: Record<EnvironmentType, string> = {
  ARTICLE: 'Artigo',
  PAGE: 'Página',
  APPLICATION_SCREEN: 'Tela de aplicativo',
  EMBEDDED_COMPONENT: 'Componente embutido',
};
