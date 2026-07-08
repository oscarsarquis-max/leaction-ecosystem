import type {
  DailyLog,
  DailyLogPayload,
  MonthCalendar,
  ProjectSite,
} from '../types';

const DEFAULT_TENANT = 'tenant-demo';

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

const apiRoot = `${import.meta.env.BASE_URL}api`.replace(/\/*$/, '');

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiRoot}${path}`, {
      headers: { 'Content-Type': 'application/json', ...(options?.headers || {}) },
      ...options,
    });
  } catch {
    throw new ApiError(
      'API indisponível. Inicie o backend na porta 6010 (python run.py).',
      0,
    );
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(data.error || `Erro HTTP ${response.status}`, response.status);
  }
  return data as T;
}

export function getDefaultTenantId() {
  return localStorage.getItem('rdo_tenant_id') || DEFAULT_TENANT;
}

export async function listSites(tenantId?: string) {
  const query = tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}` : '';
  const data = await request<{ sites: ProjectSite[] }>(`/rdo/sites${query}`);
  return data.sites;
}

export async function createSite(payload: {
  tenant_id: string;
  name: string;
  location?: string;
  rt_engineer_name?: string;
}) {
  const data = await request<{ site: ProjectSite }>('/rdo/sites', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  return data.site;
}

export async function fetchMonthCalendar(projectId: string, year: number, month: number) {
  const data = await request<MonthCalendar>(
    `/rdo/logs/${projectId}/month?year=${year}&month=${month}`,
  );
  return data;
}

export async function fetchLogByDay(projectId: string, date: string) {
  const data = await request<{ log: DailyLog | null; is_editable?: boolean }>(
    `/rdo/logs/${projectId}/day?date=${encodeURIComponent(date)}`,
  );
  return data;
}

export async function createDailyLogDraft(payload: DailyLogPayload) {
  const data = await request<{ log: DailyLog }>('/rdo/logs', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  return data.log;
}

export async function updateDailyLog(logId: string, payload: Partial<DailyLogPayload>) {
  const data = await request<{ log: DailyLog }>(`/rdo/logs/${logId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
  return data.log;
}

export function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export function isPastDate(iso: string) {
  return iso < todayIso();
}
