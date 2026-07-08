export const SSO_TOKEN_KEY = 'rdo_sso_token';
export const RDO_TENANT_KEY = 'rdo_tenant_id';
export const RDO_USER_NAME_KEY = 'rdo_user_name';

export function getRdoUserName() {
  return localStorage.getItem(RDO_USER_NAME_KEY) || '';
}

export function clearRdoSession() {
  localStorage.removeItem(SSO_TOKEN_KEY);
  localStorage.removeItem(RDO_TENANT_KEY);
  localStorage.removeItem(RDO_USER_NAME_KEY);
}

export function getChamelleonExitUrl() {
  const base = (import.meta.env.VITE_CHAMELLEON_URL || 'http://localhost:5173').replace(/\/$/, '');
  return `${base}/acesso?logout=1&from=rdo`;
}

/** Encerra sessão local do RDO e volta ao login do Chamelleon. */
export function exitToChamelleon() {
  clearRdoSession();
  window.location.replace(getChamelleonExitUrl());
}
