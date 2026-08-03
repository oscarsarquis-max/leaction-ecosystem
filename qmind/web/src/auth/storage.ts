/**
 * Local persistence policy:
 * - NEVER persist tokens or tenant payloads (assessments, memberships, etc.)
 * - Preferred organization id may live in sessionStorage only (UUID preference)
 */

const PREFERRED_ORG_KEY = "qmind.preferredOrganizationId";

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function readPreferredOrganizationId(): string | null {
  try {
    const v = sessionStorage.getItem(PREFERRED_ORG_KEY);
    if (!v || !UUID_RE.test(v)) return null;
    return v;
  } catch {
    return null;
  }
}

export function writePreferredOrganizationId(organizationId: string | null): void {
  try {
    if (!organizationId) {
      sessionStorage.removeItem(PREFERRED_ORG_KEY);
      return;
    }
    if (!UUID_RE.test(organizationId)) {
      throw new Error("preferred organization id must be a UUID");
    }
    sessionStorage.setItem(PREFERRED_ORG_KEY, organizationId);
  } catch {
    // private mode / disabled storage — ignore
  }
}

export function clearAllLocalPersistence(): void {
  try {
    sessionStorage.removeItem(PREFERRED_ORG_KEY);
  } catch {
    // ignore
  }
  // Defense: ensure we never left tokens under qmind.* keys
  try {
    const keys: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k?.startsWith("qmind.")) keys.push(k);
    }
    for (const k of keys) localStorage.removeItem(k);
  } catch {
    // ignore
  }
}

/** Assert no token-like values are stored under qmind keys (for tests/gates). */
export function assertNoSensitiveLocalPersistence(): void {
  const forbidden = ["token", "access", "refresh", "id_token", "membership", "assessment"];
  const scan = (store: Storage) => {
    for (let i = 0; i < store.length; i++) {
      const k = store.key(i);
      if (!k?.startsWith("qmind.")) continue;
      const lower = k.toLowerCase();
      for (const f of forbidden) {
        if (f !== "organization" && lower.includes(f) && !lower.includes("preferredorganization")) {
          throw new Error(`Forbidden persistence key: ${k}`);
        }
      }
      const v = store.getItem(k) || "";
      if (v.includes("eyJ") || v.length > 80) {
        throw new Error(`Suspicious persistence value under ${k}`);
      }
    }
  };
  scan(sessionStorage);
  scan(localStorage);
}
