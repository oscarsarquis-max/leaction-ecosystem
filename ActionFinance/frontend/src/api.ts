import { dropUnknownWriteIfActorChanged, getUnknownWrite, markReviewBeforeRelogin, rememberUnknownWrite } from "./pendingWrites";
import { getGeneration, getSession, setSession, setSessionNotice, type Company, type Session } from "./session";

export type ApiError = {
  status: number;
  code?: string;
  message: string;
  fields?: Record<string, string>;
  timeout?: boolean;
  unknown?: boolean;
};

export type Title = {
  id: string;
  reference: string;
  direction: "RECEIVABLE" | "PAYABLE";
  status: "DRAFT" | "OPEN" | "CANCELLED";
  description: string;
  counterpartyId: string | null;
  counterpartyName: string | null;
  counterpartyActive: boolean;
  categoryId: string | null;
  categoryName: string | null;
  categoryActive: boolean;
  amountMinor: string | null;
  currency: string;
  competenceDate: string | null;
  dueDate: string | null;
  overdue: boolean;
  settledAmountMinor: string;
  outstandingAmountMinor: string;
  settlementStatus: "UNSETTLED" | "PARTIAL" | "SETTLED" | "NOT_APPLICABLE";
  originKind: string;
  sourceReference: string | null;
  version: number;
  demoCompany: boolean;
  businessDate: string;
};

export type TitleList = {
  items: Title[];
  totalItems: number;
  page: number;
  size: number;
  summary: {
    openCount: number;
    openAmountMinor: string;
    overdueCount: number;
    overdueAmountMinor: string;
    draftCount: number;
  };
  businessDate: string;
};

export type HistoryItem = {
  id: string;
  titleVersion: number;
  action: string;
  actorDisplayName: string;
  occurredAt: string;
  reason: string | null;
  changesJson: string;
};

export type FinancialAccount = {
  id: string;
  code: string;
  name: string;
  type: "BANK" | "CASH" | "OTHER";
  currency: string;
  active: boolean;
  openedOn: string;
  currentBalanceMinor: string;
  companyName: string;
  version: number;
};

export type Settlement = {
  id: string;
  titleId: string;
  titleReference: string;
  titleDescription: string;
  counterpartyName: string | null;
  direction: "RECEIVABLE" | "PAYABLE";
  accountId: string;
  accountName: string;
  accountActive: boolean;
  amountMinor: string;
  currency: string;
  effectiveDate: string;
  method: string;
  note: string | null;
  originKind: string;
  recordedAt: string;
  actorDisplayName: string;
  reversed: boolean;
  reversalId: string | null;
  reversalEffectiveDate: string | null;
  reversalReason: string | null;
  reversalRecordedAt: string | null;
  reversalActorDisplayName: string | null;
  movementId: string | null;
  reversalMovementId: string | null;
  titleSettledAmountMinor: string;
  titleOutstandingAmountMinor: string;
  titleVersion: number;
};

export type MovementPage = {
  items: {
    id: string;
    kind: string;
    effectiveDate: string;
    recordedAt: string;
    recordedBy: string;
    description: string;
    inflowMinor: string;
    outflowMinor: string;
    balanceAfterMinor: string;
    settlementId: string | null;
    reversalId: string | null;
  }[];
  totalItems: number;
  page: number;
  size: number;
  previousBalanceMinor: string;
  periodEndBalanceMinor: string;
  currentBalanceMinor: string;
  from: string;
  to: string;
};

export type CatalogItem = {
  id: string;
  code: string;
  name: string;
  role?: string;
  direction?: string;
  active: boolean;
  version: number;
};

export type PendingWrite = {
  key: string;
  path: string;
  method: string;
  body: string;
  companyId: string;
  actorId: string;
  unknownOutcome?: boolean;
};

export type SignOutResult = { confirmed: true } | { confirmed: false; message: string };

export type RequestOptions = {
  retryOfUnknown?: boolean;
};

const DEFINITIVE_STATUSES = new Set([400, 401, 403, 404, 409, 422]);

function isApiError(error: unknown): error is ApiError {
  return Boolean(error && typeof error === "object" && "status" in error && "message" in error);
}

export function isUnknownWriteOutcome(error: unknown): boolean {
  if (!isApiError(error)) {
    return true;
  }
  if (error.code === "STALE") {
    return false;
  }
  if (error.timeout || error.unknown || error.code === "UNKNOWN_WRITE") {
    return true;
  }
  if (error.status === 0 || error.status >= 500 || error.status === 408 || error.status === 429) {
    return true;
  }
  return false;
}

export function isDefinitiveBusinessError(error: unknown): boolean {
  if (!isApiError(error)) {
    return false;
  }
  if (error.code === "STALE") {
    return true;
  }
  return DEFINITIVE_STATUSES.has(error.status) && !error.unknown;
}

function unknownWrite(): ApiError {
  return {
    status: 0,
    unknown: true,
    code: "UNKNOWN_WRITE",
    message: "Não foi possível confirmar o resultado.",
  };
}

let csrfToken = "";
let csrfHeader = "X-XSRF-TOKEN";

export async function refreshCsrf(): Promise<void> {
  const response = await fetch("/api/v1/access/csrf", { credentials: "include", headers: { Accept: "application/json" } });
  if (!response.ok) {
    csrfToken = "";
    return;
  }
  const body = (await response.json()) as { token?: string; headerName?: string };
  csrfToken = body.token ?? "";
  csrfHeader = body.headerName ?? "X-XSRF-TOKEN";
}

function headers(extra?: Record<string, string>, method = "GET"): HeadersInit {
  const session = getSession();
  const write = method !== "GET" && method !== "HEAD";
  return {
    Accept: "application/json",
    ...(session?.token ? { Authorization: `Bearer ${session.token}` } : {}),
    ...(write && csrfToken ? { [csrfHeader]: csrfToken } : {}),
    ...extra,
  };
}

async function parse(response: Response): Promise<unknown> {
  let text: string;
  try {
    text = await response.text();
  } catch {
    throw unknownWrite();
  }
  if (!text) {
    return {};
  }
  try {
    return JSON.parse(text);
  } catch {
    throw unknownWrite();
  }
}

function staleError(): ApiError {
  return { status: 0, message: "Contexto alterado.", code: "STALE" };
}

export async function request<T>(
  path: string,
  init: RequestInit = {},
  gen = getGeneration(),
  options: RequestOptions = {},
): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), 15000);
  try {
    const method = (init.method ?? "GET").toUpperCase();
    const response = await fetch(path, {
      ...init,
      credentials: "include",
      headers: { ...headers(init.headers as Record<string, string>, method), ...(init.headers ?? {}) },
      signal: controller.signal,
    });
    if (gen !== getGeneration()) {
      throw staleError();
    }
    if (response.status === 401) {
      if (options.retryOfUnknown) {
        throw {
          status: 401,
          code: "UNKNOWN_WRITE_UNCONFIRMED",
          unknown: true,
          message: "O resultado anterior não foi confirmado. Confira os registros antes de lançar de novo.",
        } satisfies ApiError;
      }
      setSession(null);
      setSessionNotice({
        kind: "expired",
        message: "Sessão expirada. Entre novamente.",
      });
      throw {
        status: 401,
        code: "SESSION_EXPIRED",
        message: "Sessão expirada. Entre novamente.",
      } satisfies ApiError;
    }
    const body = (await parse(response)) as { code?: string; message?: string; fields?: Record<string, string> };
    if (gen !== getGeneration()) {
      throw staleError();
    }
    if (!response.ok) {
      const definitive = DEFINITIVE_STATUSES.has(response.status);
      throw {
        status: response.status,
        code: body.code,
        unknown: !definitive,
        message:
          response.status === 403
            ? body.message ?? "O acesso a esta empresa ou operação não está mais disponível."
            : body.message ?? "Não foi possível concluir a operação.",
        fields: body.fields,
      } satisfies ApiError;
    }
    return body as T;
  } catch (error) {
    if (isApiError(error)) {
      throw error;
    }
    if (error instanceof DOMException && error.name === "AbortError") {
      throw { status: 0, timeout: true, unknown: true, code: "UNKNOWN_WRITE", message: "Não foi possível confirmar o resultado." } satisfies ApiError;
    }
    throw unknownWrite();
  } finally {
    window.clearTimeout(timer);
  }
}

export async function sendPending<T>(pending: PendingWrite, gen = getGeneration()): Promise<T> {
  const session = getSession();
  if (!session || session.companyId !== pending.companyId || session.actorId !== pending.actorId) {
    throw { status: 0, code: "STALE", message: "Contexto alterado. A operação anterior não será reenviada." } satisfies ApiError;
  }
  try {
    const result = await request<T>(
      pending.path,
      {
        method: pending.method,
        headers: { "Content-Type": "application/json", "Idempotency-Key": pending.key },
        body: pending.body,
      },
      gen,
      { retryOfUnknown: Boolean(pending.unknownOutcome) },
    );
    return result;
  } catch (error) {
    if (isUnknownWriteOutcome(error)) {
      rememberUnknownOutcome(pending);
    }
    throw error;
  }
}

export function freezeWrite(path: string, method: string, body: unknown, existing?: PendingWrite | null): PendingWrite {
  if (existing) {
    return existing;
  }
  const session = getSession();
  return {
    key: crypto.randomUUID(),
    path,
    method,
    body: typeof body === "string" ? body : JSON.stringify(body),
    companyId: session?.companyId ?? "",
    actorId: session?.actorId ?? "",
  };
}

export function rememberUnknownOutcome(pending: PendingWrite): PendingWrite {
  const next = { ...pending, unknownOutcome: true };
  rememberUnknownWrite(next);
  return next;
}

function sessionFromMe(
  body: {
    actorId: string;
    displayName: string;
    accessState?: string;
    permissions: string[];
    permissionsByCompany?: Record<string, string[]>;
    authorizedCompanies: { id: string; tenantId: string; name: string; active: boolean; demo: boolean }[];
    authorizedCompanyDetails?: {
      id: string;
      tenantId: string;
      name: string;
      active: boolean;
      demo: boolean;
      role?: string;
      permissions?: string[];
    }[];
  },
  mode: Session["mode"],
  token?: string,
): Session {
  const details = body.authorizedCompanyDetails ?? [];
  const companies: Company[] = (body.authorizedCompanies ?? []).map((company) => {
    const detail = details.find((item) => item.id === company.id);
    const granted =
      detail?.permissions ??
      body.permissionsByCompany?.[company.id] ??
      [];
    return {
      ...company,
      role: detail?.role,
      permissions: granted,
    };
  });
  const companyId = companies[0]?.id ?? "";
  dropUnknownWriteIfActorChanged(body.actorId);
  return {
    token,
    mode,
    actorId: body.actorId,
    displayName: body.displayName,
    accessState: body.accessState,
    permissions: companies[0]?.permissions ?? [],
    companies,
    companyId,
  };
}

export async function signIn(token: string): Promise<Session> {
  const response = await fetch("/api/v1/access/me", {
    credentials: "include",
    headers: { Accept: "application/json", Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    throw { status: response.status, message: "Token local não reconhecido." } satisfies ApiError;
  }
  const next = sessionFromMe((await response.json()) as Parameters<typeof sessionFromMe>[0], "demo", token);
  setSession(next);
  return next;
}

export async function restoreOidcSession(): Promise<Session | null> {
  const response = await fetch("/api/v1/access/me", {
    credentials: "include",
    headers: { Accept: "application/json" },
  });
  if (response.status === 401) {
    return null;
  }
  if (!response.ok) {
    throw { status: response.status, message: "Não foi possível recuperar a sessão." } satisfies ApiError;
  }
  await refreshCsrf();
  const next = sessionFromMe((await response.json()) as Parameters<typeof sessionFromMe>[0], "oidc");
  setSession(next);
  return next;
}

export async function signOut(): Promise<SignOutResult> {
  try {
    await refreshCsrf();
    const response = await fetch("/logout", {
      method: "POST",
      credentials: "include",
      headers: { Accept: "application/json", ...(csrfToken ? { [csrfHeader]: csrfToken } : {}) },
    });
    if (response.status === 204 || response.ok) {
      csrfToken = "";
      setSession(null);
      return { confirmed: true };
    }
    return { confirmed: false, message: "Não foi possível confirmar a saída. Tente novamente." };
  } catch {
    return { confirmed: false, message: "Não foi possível confirmar a saída. Tente novamente." };
  }
}

export function startOidcLogin(): void {
  if (getUnknownWrite()) {
    markReviewBeforeRelogin();
  }
  window.location.assign("/oauth2/authorization/actionfinance");
}

export type AccessMode = "DEMO" | "OIDC" | "NONE";

export async function loadAccessMode(): Promise<AccessMode> {
  const response = await fetch("/api/v1/system/info", { credentials: "include", headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new Error("info");
  }
  const body = (await response.json()) as { accessMode?: string };
  if (body.accessMode === "OIDC" || body.accessMode === "DEMO" || body.accessMode === "NONE") {
    return body.accessMode;
  }
  return "NONE";
}

export function companyQuery(extra = ""): string {
  const session = getSession();
  const base = `companyId=${encodeURIComponent(session?.companyId ?? "")}`;
  return extra ? `${base}&${extra}` : base;
}
