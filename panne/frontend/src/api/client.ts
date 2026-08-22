import { config } from "../config";
import { ApiError, errorFromResponse } from "./errors";
import type {
  BoardCard,
  BoardFilters,
  Consumption,
  Dependency,
  Envelope,
  EventRow,
  MaterialsView,
  Me,
  Occurrence,
  Order,
  Page,
  Plan,
  PlanDetail,
  SheetIssue,
  SheetSummary,
  StepsView,
  Traceability,
  WeighingsView,
  YieldRow,
} from "./types";

export type TokenReader = () => string | null;

type Query = Record<string, string | undefined>;

export class ApiClient {
  private readonly tokenReader: TokenReader;
  private organizationId: string | null = null;
  private readonly cache = new Map<string, unknown>();
  private readonly inflight = new Map<string, AbortController>();

  constructor(tokenReader: TokenReader) {
    this.tokenReader = tokenReader;
  }

  setOrganization(organizationId: string | null): void {
    if (this.organizationId !== organizationId) {
      this.clear();
    }
    this.organizationId = organizationId;
  }

  clear(): void {
    for (const controller of this.inflight.values()) {
      controller.abort();
    }
    this.inflight.clear();
    this.cache.clear();
  }

  async me(organizationId?: string | null): Promise<Me> {
    const headers: Record<string, string> = {};
    if (organizationId) headers["X-Panne-Organization-Id"] = organizationId;
    return this.request<Me>("/api/v1/me", { headers, cache: false });
  }

  listPlans(query: Query = {}) {
    return this.orgGet<Page<Plan>>("/plans", query);
  }

  getPlan(planId: string) {
    return this.orgGet<Envelope<PlanDetail>>(`/plans/${planId}`);
  }

  listOrders(query: Query = {}) {
    return this.orgGet<Page<Order>>("/orders", query);
  }

  getOrder(orderId: string) {
    return this.orgGet<Envelope<Order>>(`/orders/${orderId}`);
  }

  getMaterials(orderId: string) {
    return this.orgGet<Envelope<MaterialsView>>(`/orders/${orderId}/materials`);
  }

  getSteps(orderId: string) {
    return this.orgGet<Envelope<StepsView>>(`/orders/${orderId}/steps`);
  }

  getDependencies(orderId: string) {
    return this.orgGet<Envelope<Dependency[]>>(`/orders/${orderId}/dependencies`);
  }

  getEvents(orderId: string, query: Query = {}) {
    return this.orgGet<Page<EventRow>>(`/orders/${orderId}/events`, query);
  }

  getWeighings(orderId: string) {
    return this.orgGet<Envelope<WeighingsView>>(`/orders/${orderId}/weighings`);
  }

  getConsumptions(orderId: string) {
    return this.orgGet<Envelope<Consumption[]>>(`/orders/${orderId}/consumptions`);
  }

  getYields(orderId: string) {
    return this.orgGet<Envelope<YieldRow[]>>(`/orders/${orderId}/yields`);
  }

  getOccurrences(orderId: string) {
    return this.orgGet<Envelope<Occurrence[]>>(`/orders/${orderId}/occurrences`);
  }

  getSheets(orderId: string) {
    return this.orgGet<Envelope<SheetSummary[]>>(`/orders/${orderId}/sheets`);
  }

  getSheet(orderId: string, issueId: string) {
    return this.orgGet<Envelope<SheetIssue>>(`/orders/${orderId}/sheets/${issueId}`);
  }

  getTraceability(orderId: string) {
    return this.orgGet<Envelope<Traceability>>(`/orders/${orderId}/traceability`);
  }

  getBoard(filters: BoardFilters) {
    const query: Query = { ...filters };
    return this.orgGet<Envelope<BoardCard[]>>("/board", query);
  }

  private orgPath(path: string): string {
    if (!this.organizationId) {
      throw new ApiError("nao_autorizado", "Selecione uma organização.", 403);
    }
    return `/api/v1/organizations/${this.organizationId}/production${path}`;
  }

  private orgGet<T>(path: string, query: Query = {}): Promise<T> {
    return this.request<T>(this.orgPath(path), { query });
  }

  private async request<T>(
    path: string,
    options: {
      query?: Query;
      headers?: Record<string, string>;
      cache?: boolean;
    } = {},
  ): Promise<T> {
    const url = this.url(path, options.query);
    const cacheKey = url;
    if (options.cache !== false && this.cache.has(cacheKey)) {
      return this.cache.get(cacheKey) as T;
    }
    this.inflight.get(cacheKey)?.abort();
    const controller = new AbortController();
    this.inflight.set(cacheKey, controller);
    const headers = new Headers({
      Accept: "application/json",
      "X-Correlation-Id": crypto.randomUUID(),
      ...options.headers,
    });
    const token = this.tokenReader();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    try {
      const response = await fetch(url, { headers, signal: controller.signal });
      const body = await readBody(response);
      if (!response.ok) {
        throw errorFromResponse(response.status, body);
      }
      if (options.cache !== false) {
        this.cache.set(cacheKey, body);
      }
      return body as T;
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        throw new ApiError("cancelado", "A consulta anterior foi substituída.", 0);
      }
      if (error instanceof ApiError) throw error;
      throw new ApiError("rede", "Não foi possível contactar a API.", 0);
    } finally {
      if (this.inflight.get(cacheKey) === controller) {
        this.inflight.delete(cacheKey);
      }
    }
  }

  private url(path: string, query: Query = {}): string {
    const base = config.apiBase.replace(/\/$/, "");
    const target = new URL(`${base}${path}`, window.location.origin);
    for (const [key, value] of Object.entries(query)) {
      if (value) target.searchParams.set(key, value);
    }
    return target.toString();
  }
}

async function readBody(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return { message: text };
  }
}

export function hasCostLeak(value: unknown): boolean {
  const text = JSON.stringify(value).toLowerCase();
  return (
    text.includes('"cost"') ||
    text.includes("preço") ||
    text.includes("preco") ||
    text.includes("margem")
  );
}
