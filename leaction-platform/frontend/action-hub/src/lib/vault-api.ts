'use client';

import axios, { type AxiosInstance } from 'axios';

const DEFAULT_VAULT = 'http://127.0.0.1:4020';
export const VAULT_TOKEN_KEY = 'ah_vault_token';

export function getVaultApiBase(): string {
  const env = (process.env.NEXT_PUBLIC_VAULT_API_URL || '').trim();
  if (env) return env.replace(/\/$/, '');
  return DEFAULT_VAULT;
}

export type VaultSistema = {
  sistema: string;
  rotation_webhook_url: string | null;
  has_rotation_secret: boolean;
  suporta_rotacao_automatica: boolean;
  conta_webhook_url?: string | null;
  has_conta_secret?: boolean;
};

export type VaultSecretMeta = {
  id: number;
  sistema: string;
  tipo: string;
  versao: number;
  status: string;
  criado_em?: string;
  atualizado_em?: string;
  atualizado_por?: string;
  expira_em?: string | null;
  usuario_email?: string | null;
};

export type VaultContaNivel = 'admin' | 'gestor_produtivo' | 'usuario_executor';

export class VaultSessionExpiredError extends Error {
  constructor() {
    super('Sessão do cofre expirada. Entre de novo.');
    this.name = 'VaultSessionExpiredError';
  }
}

function createVaultClient(token?: string): AxiosInstance {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  return axios.create({
    baseURL: getVaultApiBase(),
    timeout: 20000,
    headers,
  });
}

export function parseVaultApiErrors(err: unknown): string[] {
  if (err instanceof VaultSessionExpiredError) return [err.message];
  const ax = err as {
    response?: { status?: number; data?: unknown };
    code?: string;
    message?: string;
  };
  const status = ax.response?.status;
  const data = ax.response?.data;
  const out: string[] = [];
  const push = (value: unknown) => {
    if (typeof value === 'string') {
      const text = value.trim();
      if (text && text !== '[object Object]') out.push(text);
      return;
    }
    if (Array.isArray(value)) {
      value.forEach(push);
      return;
    }
    if (value && typeof value === 'object') {
      const rec = value as Record<string, unknown>;
      if (typeof rec.error === 'string') push(rec.error);
      if (typeof rec.detalhe === 'string') push(rec.detalhe);
      if (typeof rec.message === 'string' && rec.message !== rec.error) {
        push(rec.message);
      }
    }
  };
  if (data && typeof data === 'object') push(data);
  else if (typeof data === 'string') push(data);
  const unique = [...new Set(out)];

  if (status === 401) {
    return unique.length ? unique : ['Sessão do cofre expirada. Entre de novo.'];
  }
  if (status === 400) {
    return unique.length
      ? unique
      : ['Dados inválidos. Verifique os campos e tente de novo.'];
  }
  if (status === 409) {
    return unique.length
      ? unique
      : ['Já existe um registro ativo ou pendente para este item.'];
  }
  if (status === 502) {
    return unique.length
      ? unique
      : ['Falha ao aplicar no sistema externo. A versão anterior permanece como estava.'];
  }
  if (status === 404) {
    return unique.length ? unique : ['Registro não encontrado no cofre.'];
  }
  if (status === 403) {
    return unique.length ? unique : ['Acesso negado pelo cofre.'];
  }

  if (!ax.response) {
    if (ax.code === 'ECONNABORTED') {
      return ['O cofre demorou demais para responder.'];
    }
    if (ax.code === 'ERR_NETWORK' || ax.message === 'Network Error') {
      return [`Não foi possível conectar ao cofre em ${getVaultApiBase()}.`];
    }
  }

  if (unique.length) return unique;
  const fallback = err instanceof Error ? err.message.trim() : '';
  if (fallback && fallback !== 'Network Error') return [fallback];
  return ['Falha inesperada no cofre'];
}

function throwIfExpired(err: unknown): never {
  const status = (err as { response?: { status?: number } })?.response?.status;
  if (status === 401) throw new VaultSessionExpiredError();
  throw err;
}

export async function vaultLogin(
  email: string,
  senha: string
): Promise<{ access_token: string; admin: { id: number; email: string } }> {
  const client = createVaultClient();
  try {
    const { data } = await client.post('/api/auth/login', { email, senha });
    return data;
  } catch (err) {
    throw err;
  }
}

export async function fetchVaultSistemas(token: string): Promise<VaultSistema[]> {
  const client = createVaultClient(token);
  try {
    const { data } = await client.get<{ sistemas: VaultSistema[] }>('/api/sistemas');
    return Array.isArray(data?.sistemas) ? data.sistemas : [];
  } catch (err) {
    throwIfExpired(err);
  }
}

export async function upsertVaultSistema(
  token: string,
  body: {
    sistema: string;
    rotation_webhook_url?: string | null;
    rotation_secret?: string | null;
    suporta_rotacao_automatica?: boolean;
  }
): Promise<VaultSistema> {
  const client = createVaultClient(token);
  try {
    const { data } = await client.post<{ sistema: VaultSistema }>('/api/sistemas', body);
    return data.sistema;
  } catch (err) {
    throwIfExpired(err);
  }
}

export async function fetchVaultSecrets(
  token: string,
  sistema: string
): Promise<VaultSecretMeta[]> {
  const client = createVaultClient(token);
  try {
    const { data } = await client.get<{ secrets: VaultSecretMeta[] }>('/api/secrets', {
      params: { sistema },
    });
    return Array.isArray(data?.secrets) ? data.secrets : [];
  } catch (err) {
    throwIfExpired(err);
  }
}

export async function createVaultSecret(
  token: string,
  body: { sistema: string; tipo: string; valor: string }
): Promise<VaultSecretMeta> {
  const client = createVaultClient(token);
  try {
    const { data } = await client.post<{ secret: VaultSecretMeta }>('/api/secrets', body);
    return data.secret;
  } catch (err) {
    throwIfExpired(err);
  }
}

export async function revelarVaultSecret(
  token: string,
  id: number
): Promise<{ secret: VaultSecretMeta; valor: string }> {
  const client = createVaultClient(token);
  try {
    const { data } = await client.get<{ secret: VaultSecretMeta; valor: string }>(
      `/api/secrets/${id}/revelar`
    );
    return data;
  } catch (err) {
    throwIfExpired(err);
  }
}

export async function rotacionarVaultSecret(
  token: string,
  id: number,
  novoValor?: string
): Promise<{
  secret: VaultSecretMeta;
  anterior?: { id: number; versao: number; status: string };
  modo?: string;
  valor?: string;
  error?: string;
  detalhe?: string;
}> {
  const client = createVaultClient(token);
  try {
    const { data } = await client.post(`/api/secrets/${id}/rotacionar`, {
      novo_valor: novoValor || undefined,
    });
    return data;
  } catch (err) {
    const status = (err as { response?: { status?: number } })?.response?.status;
    if (status === 401) throw new VaultSessionExpiredError();
    throw err;
  }
}

export async function confirmarVaultSecret(
  token: string,
  id: number
): Promise<VaultSecretMeta> {
  const client = createVaultClient(token);
  try {
    const { data } = await client.post<{ secret: VaultSecretMeta }>(
      `/api/secrets/${id}/confirmar-aplicacao`
    );
    return data.secret;
  } catch (err) {
    throwIfExpired(err);
  }
}

export async function fetchVaultContas(
  token: string,
  sistema: string
): Promise<VaultSecretMeta[]> {
  const client = createVaultClient(token);
  try {
    const { data } = await client.get<{ contas: VaultSecretMeta[] }>('/api/contas', {
      params: { sistema },
    });
    return Array.isArray(data?.contas) ? data.contas : [];
  } catch (err) {
    throwIfExpired(err);
  }
}

export async function createVaultConta(
  token: string,
  body: {
    sistema: string;
    email: string;
    nivel: VaultContaNivel;
    funcao?: string;
    senha?: string;
  }
): Promise<{ secret: VaultSecretMeta; modo?: string; valor?: string }> {
  const client = createVaultClient(token);
  try {
    const { data } = await client.post('/api/contas', body);
    return data;
  } catch (err) {
    throwIfExpired(err);
  }
}

export async function fetchVaultHistorico(
  token: string,
  id: number
): Promise<{ sistema: string; tipo: string; versoes: VaultSecretMeta[] }> {
  const client = createVaultClient(token);
  try {
    const { data } = await client.get(`/api/secrets/${id}/historico`);
    return {
      sistema: data.sistema,
      tipo: data.tipo,
      versoes: Array.isArray(data.versoes) ? data.versoes : [],
    };
  } catch (err) {
    throwIfExpired(err);
  }
}
