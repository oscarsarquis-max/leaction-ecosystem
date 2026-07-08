import { ROLE_EXECUTOR } from '../config/rbac';

/** URL base do Diário de Obra (hotpage). Em produção usa o mesmo domínio do Chamelleon. */
export function getDiarioObraBaseUrl() {
  const envUrl = import.meta.env.VITE_DIARIO_OBRA_URL;
  if (envUrl) return String(envUrl).replace(/\/$/, '');

  if (typeof window !== 'undefined') {
    const { hostname, origin } = window.location;
    if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
      return `${origin}/diario-obra`;
    }
  }

  return 'http://localhost:6173';
}

/** Frameworks com Diário de Obra (Gemba) habilitado. */
export const CONSTRUCTION_FRAMEWORK_IDS = ['construcao-civil-v1'];

export function normalizeRole(role) {
  return String(role || '')
    .trim()
    .toLowerCase();
}

export function normalizeSectorText(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');
}

export function isExecutorRole(role) {
  return normalizeRole(role) === ROLE_EXECUTOR;
}

/** Diário de Obra disponível apenas para setor Construção Civil. */
export function isConstructionSectorUser(data = {}) {
  const frameworkId = normalizeSectorText(data.framework_id ?? data.frameworkId);
  if (
    CONSTRUCTION_FRAMEWORK_IDS.some(
      (id) => frameworkId === normalizeSectorText(id),
    )
  ) {
    return true;
  }

  const sector = normalizeSectorText(data.sector);
  if (!sector) return false;

  return (
    sector.includes('construcao') ||
    sector.includes('engenharia civil') ||
    sector.includes('obra') ||
    sector === 'civil'
  );
}

export function canAccessDiarioObra(data = {}) {
  return isConstructionSectorUser(data);
}

/**
 * Token SSO para o Diário de Obra.
 * Usa JWT da API quando disponível; senão envelope de sessão (dev).
 */
export function buildSsoToken(loginData) {
  if (loginData?.token) return loginData.token;

  const payload = {
    sub: loginData.user_id,
    name: loginData.user_name,
    email: loginData.email,
    role: loginData.system_role,
    tenant_id: loginData.tenant_id,
    tenant_name: loginData.tenant_name,
    iat: Math.floor(Date.now() / 1000),
    iss: 'chamelleon',
  };
  return btoa(unescape(encodeURIComponent(JSON.stringify(payload))));
}

export function getDiarioObraAuthUrl(loginData) {
  const token = buildSsoToken(loginData);
  return `${getDiarioObraBaseUrl()}/auth?token=${encodeURIComponent(token)}`;
}

export function redirectToDiarioObra(loginData) {
  window.location.replace(getDiarioObraAuthUrl(loginData));
}

/** Destino após login bem-sucedido. */
export function resolvePostLoginTarget(loginData) {
  const role = loginData?.system_role ?? loginData?.systemRole;
  const gemba = canAccessDiarioObra(loginData);

  if (isExecutorRole(role) && gemba) {
    return { type: 'external', href: getDiarioObraAuthUrl(loginData) };
  }
  if (isExecutorRole(role)) {
    return { type: 'internal', path: '/' };
  }
  return { type: 'internal', path: '/portal' };
}

export function applyPostLoginRedirect(loginData, navigate) {
  const target = resolvePostLoginTarget(loginData);
  if (target.type === 'external') {
    window.location.replace(target.href);
    return 'external';
  }
  navigate(target.path, { replace: true });
  return 'internal';
}

export function loginDataFromSession(session) {
  if (!session?.userId) return null;
  return {
    token: session.token,
    user_id: session.userId,
    user_name: session.userName,
    email: session.email,
    system_role: session.systemRole,
    tenant_id: session.tenantId,
    tenant_name: session.tenantName,
    framework_id: session.frameworkId,
    sector: session.sector,
  };
}
