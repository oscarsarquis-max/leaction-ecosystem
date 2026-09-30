export type Company = {
  id: string;
  tenantId: string;
  name: string;
  active: boolean;
  demo: boolean;
  role?: string;
  permissions: string[];
};

export type Session = {
  token?: string;
  mode: "demo" | "oidc";
  actorId: string;
  displayName: string;
  accessState?: string;
  permissions: string[];
  companies: Company[];
  companyId: string;
};

export type SessionNotice = {
  kind: "expired" | "logout-unconfirmed" | "review-records";
  message: string;
} | null;

type SessionListener = () => void;

let session: Session | null = null;
let generation = 0;
let notice: SessionNotice = null;
let hideProtectedData = false;
const listeners = new Set<SessionListener>();

export function getSession(): Session | null {
  return session;
}

export function getGeneration(): number {
  return generation;
}

export function getSessionNotice(): SessionNotice {
  return notice;
}

export function isProtectedDataHidden(): boolean {
  return hideProtectedData;
}

export function subscribeSession(listener: SessionListener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function emit() {
  generation += 1;
  listeners.forEach((listener) => listener());
}

export function setSession(next: Session | null): void {
  session = next;
  if (next) {
    hideProtectedData = false;
  }
  emit();
}

export function setSessionNotice(next: SessionNotice): void {
  notice = next;
  emit();
}

export function hideProtectedFinancialData(): void {
  hideProtectedData = true;
  emit();
}

export function selectedCompany(current: Session | null = session): Company | undefined {
  if (!current) {
    return undefined;
  }
  return current.companies.find((company) => company.id === current.companyId);
}

export function permissionsOf(current: Session | null, companyId: string): string[] {
  return current?.companies.find((company) => company.id === companyId)?.permissions ?? [];
}

export function canWrite(): boolean {
  return Boolean(selectedCompany()?.permissions.includes("titles:write"));
}

export function canWriteCatalogs(): boolean {
  return Boolean(selectedCompany()?.permissions.includes("catalogs:write"));
}

export function canReadAccounts(): boolean {
  return Boolean(selectedCompany()?.permissions.includes("financial-accounts:read"));
}

export function canWriteAccounts(): boolean {
  return Boolean(selectedCompany()?.permissions.includes("financial-accounts:write"));
}

export function canReadSettlements(): boolean {
  return Boolean(selectedCompany()?.permissions.includes("settlements:read"));
}

export function canWriteSettlements(): boolean {
  return Boolean(selectedCompany()?.permissions.includes("settlements:write"));
}

export function canReverseSettlements(): boolean {
  return Boolean(selectedCompany()?.permissions.includes("settlements:reverse"));
}

export function withCompanyPermissions(current: Session, companyId: string): Session {
  return {
    ...current,
    companyId,
    permissions: permissionsOf(current, companyId),
  };
}
