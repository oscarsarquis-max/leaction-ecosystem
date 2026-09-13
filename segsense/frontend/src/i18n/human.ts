import { ApiClientError } from '../api/errors';

export const AUTH_NOT_CONFIGURED =
  'A autenticação administrativa ainda não está configurada.';

export const ACCESS_NOT_ALLOWED = 'Seu acesso não permite realizar esta ação.';

export const ITEM_NOT_FOUND = 'Este item não foi encontrado neste contexto.';

export const CONFLICT_STALE =
  'Os dados mudaram enquanto você trabalhava. Atualize e tente novamente.';

export const SERVICE_UNAVAILABLE =
  'O serviço está indisponível agora. Tente novamente em instantes.';

export const PUBLIC_LOADING = 'Preparando este convite…';
export const PUBLIC_NOT_FOUND = 'Este endereço não está disponível.';
export const PUBLIC_REVOKED = 'Este convite não vale mais.';
export const PUBLIC_EXPIRED = 'Este convite não está mais vigente.';
export const PUBLIC_TERMINAL = 'Este convite não está mais disponível.';
export const PUBLIC_TEMPORARY =
  'Temporariamente indisponível. Tente novamente em instantes.';
export const PUBLIC_NETWORK =
  'Não foi possível carregar este convite agora. Tente novamente em instantes.';

export const CONTEXT_FALLBACK_SUMMARY =
  'Este conteúdo foi preparado para o contexto que você estava consultando.';

const TECHNICAL_CODE = /^[A-Z][A-Z0-9_]{3,}$/;

export function adminErrorMessage(error: unknown, fallback: string): string {
  if (!(error instanceof ApiClientError)) {
    return fallback;
  }
  if (error.authenticationRequired) {
    return AUTH_NOT_CONFIGURED;
  }
  if (error.accessDenied) {
    return ACCESS_NOT_ALLOWED;
  }
  if (error.status === 404) {
    return ITEM_NOT_FOUND;
  }
  if (error.status === 409) {
    return error.message && !TECHNICAL_CODE.test(error.message)
      ? error.message
      : CONFLICT_STALE;
  }
  if (error.status === 422 && error.message && !TECHNICAL_CODE.test(error.message)) {
    return error.message;
  }
  if (error.status >= 500) {
    return SERVICE_UNAVAILABLE;
  }
  if (error.message && !TECHNICAL_CODE.test(error.message)) {
    return error.message;
  }
  return fallback;
}

export function purposeFromCallToAction(label: string): string {
  const trimmed = label.trim();
  if (trimmed.length === 0) {
    return '';
  }
  const lowered = trimmed.toLowerCase();
  if (
    /contratar agora|cotar agora|compre agora|garantir agora|assine agora/.test(lowered)
  ) {
    return 'Finalidade deste convite: avaliar opções de proteção.';
  }
  return `Finalidade deste convite: ${trimmed}.`;
}

export function formatValidityPtBr(iso: string | null | undefined): string {
  if (iso == null || iso.length === 0) {
    return 'Sem data limite informada.';
  }
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return 'Sem data limite informada.';
  }
  const day = new Intl.DateTimeFormat('pt-BR', {
    day: 'numeric',
    timeZone: 'UTC',
  }).format(date);
  const monthYear = new Intl.DateTimeFormat('pt-BR', {
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(date);
  const dayLabel = day === '1' ? '1º' : day;
  return `Vigente até ${dayLabel} de ${monthYear}.`;
}
