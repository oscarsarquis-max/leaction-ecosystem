/**
 * Destino pós-login seguro (somente path relativo da app).
 * Nunca persiste tokens — só path + query + hash curtos.
 */

const RETURN_URL_KEY = "qmind.returnUrl";

const SAFE_PATH =
  /^\/(?:[A-Za-z0-9\-._~!$&'()*+,;=:@/%]*)?(?:\?[A-Za-z0-9\-._~!$&'()*+,;=:@/?%]*)?(?:#[A-Za-z0-9\-._~!$&'()*+,;=:@/?%]*)?$/;

const BLOCKED = new Set(["/login", "/auth/callback", "/"]);

export function isSafeReturnUrl(value: string | null | undefined): value is string {
  if (!value || value.length > 240) return false;
  if (!value.startsWith("/") || value.startsWith("//")) return false;
  if (!SAFE_PATH.test(value)) return false;
  const pathOnly = value.split(/[?#]/)[0] ?? value;
  if (BLOCKED.has(pathOnly)) return false;
  return true;
}

export function writeReturnUrl(path: string | null): void {
  try {
    if (!path || !isSafeReturnUrl(path)) {
      sessionStorage.removeItem(RETURN_URL_KEY);
      return;
    }
    sessionStorage.setItem(RETURN_URL_KEY, path);
  } catch {
    /* ignore */
  }
}

export function readReturnUrl(): string | null {
  try {
    const v = sessionStorage.getItem(RETURN_URL_KEY);
    if (!isSafeReturnUrl(v)) {
      sessionStorage.removeItem(RETURN_URL_KEY);
      return null;
    }
    return v;
  } catch {
    return null;
  }
}

export function consumeReturnUrl(fallback = "/assessments"): string {
  const v = readReturnUrl();
  try {
    sessionStorage.removeItem(RETURN_URL_KEY);
  } catch {
    /* ignore */
  }
  return v ?? fallback;
}

export function clearReturnUrl(): void {
  try {
    sessionStorage.removeItem(RETURN_URL_KEY);
  } catch {
    /* ignore */
  }
}
