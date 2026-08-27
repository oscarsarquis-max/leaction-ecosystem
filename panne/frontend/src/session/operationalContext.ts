import { todayIso } from "../format";

export type OperationalContext = {
  operational_date: string;
  establishment_id: string;
  establishment_name: string;
  shift: string;
  area: string;
};

const PREFIX = "panne.operationalContext.";

/** Query keys do Quadro que amarram contexto/filtros à organização. */
export const BOARD_QUERY_KEYS = [
  "operational_date",
  "establishment_id",
  "shift",
  "area",
  "product_id",
  "status",
  "priority",
  "q",
] as const;

export function stripBoardQueryParams(source: URLSearchParams): URLSearchParams {
  const next = new URLSearchParams(source);
  for (const key of BOARD_QUERY_KEYS) next.delete(key);
  return next;
}

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
