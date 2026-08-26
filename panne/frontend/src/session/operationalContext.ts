import { todayIso } from "../format";

export type OperationalContext = {
  operational_date: string;
  establishment_id: string;
  establishment_name: string;
  shift: string;
  area: string;
};

const PREFIX = "panne.operationalContext.";

function key(organizationId: string, userHint: string): string {
  return `${PREFIX}${organizationId}.${userHint || "anon"}`;
}

export function readOperationalContext(organizationId: string, userHint: string): OperationalContext | null {
  try {
    const raw = sessionStorage.getItem(key(organizationId, userHint));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as OperationalContext;
    if (!parsed.operational_date || !parsed.establishment_id) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function writeOperationalContext(
  organizationId: string,
  userHint: string,
  value: OperationalContext | null,
): void {
  try {
    if (!value) sessionStorage.removeItem(key(organizationId, userHint));
    else sessionStorage.setItem(key(organizationId, userHint), JSON.stringify(value));
  } catch {
    /* sessão local não sensível */
  }
}

export function clearOperationalContext(): void {
  try {
    const doomed: string[] = [];
    for (let i = 0; i < sessionStorage.length; i += 1) {
      const item = sessionStorage.key(i);
      if (item?.startsWith(PREFIX)) doomed.push(item);
    }
    doomed.forEach((item) => sessionStorage.removeItem(item));
  } catch {
    /* ignore */
  }
}

export function defaultDate(): string {
  return todayIso();
}
