import { config } from "../config";
import { ApiError, errorFromResponse } from "./errors";
import type {
  BoardCard,
  BoardContextCatalog,
  BoardFilters,
  Catalog,
  CatalogItem,
  Consumption,
  IngredientCard,
  IngredientDossier,
  IngredientPage,
  IngredientVersion,
  ApprovalRow,
  NutritionPreview,
  RecipeCard,
  RecipeDossier,
  RecipePage,
  RecipeAiProposal,
  LabelingDossier,
  CostingCalculation,
  CostingPolicy,
  PracticedPrice,
  PricingSimulation,
  ReportPayload,
  ReportSnapshot,
  SavedReportView,
  RecipeReferenceLink,
  RecipeVersion,
  ScaleRow,
  TrialRow,
  SupplierCard,
  SupplierItemCard,
  Dependency,
  Envelope,
  EventRow,
  ExecutionView,
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

  getBoardContext() {
    return this.orgGet<Envelope<BoardContextCatalog>>("/board/context");
  }

  getCatalog() {
    return this.orgGet<Envelope<Catalog>>("/catalog");
  }

  getExecution(orderId: string) {
    return this.orgGet<Envelope<ExecutionView>>(`/orders/${orderId}/execution`, {}, false);
  }

  listIngredients(query: Query = {}) {
    return this.catalogGet<IngredientPage>("/ingredients", query);
  }

  getIngredient(ingredientId: string) {
    return this.catalogGet<Envelope<IngredientCard & { versions: IngredientVersion[] }>>(
      `/ingredients/${ingredientId}`,
    );
  }

  getIngredientVersion(ingredientId: string, versionId: string) {
    return this.catalogGet<Envelope<IngredientDossier>>(`/ingredients/${ingredientId}/versions/${versionId}`);
  }

  listIngredientItems(ingredientId: string) {
    return this.catalogGet<{ data: SupplierItemCard[] }>(`/ingredients/${ingredientId}/items`);
  }

  listSuppliers(query: Query = {}) {
    return this.catalogGet<{ data: SupplierCard[] }>("/suppliers", query);
  }

  getCatalogUnits() {
    return this.catalogGet<{ data: CatalogItem[] }>("/catalog/units");
  }

  getCatalogNutrients() {
    return this.catalogGet<{ data: CatalogItem[] }>("/catalog/nutrients");
  }

  getCatalogAllergens() {
    return this.catalogGet<{ data: CatalogItem[] }>("/catalog/allergens");
  }

  getCatalogSources() {
    return this.catalogGet<{ data: CatalogItem[] }>("/catalog/sources");
  }

  listRecipes(query: Query = {}) {
    return this.catalogGet<RecipePage>("/recipes", query);
  }

  getRecipe(recipeId: string) {
    return this.catalogGet<Envelope<RecipeCard & { versions: RecipeVersion[] }>>(
      `/recipes/${recipeId}`,
    );
  }

  getRecipeVersion(recipeId: string, versionId: string) {
    return this.catalogGet<Envelope<RecipeDossier>>(`/recipes/${recipeId}/versions/${versionId}`);
  }

  getRecipeSheet(recipeId: string, versionId: string) {
    return this.catalogGet<Envelope<Record<string, unknown>>>(
      `/recipes/${recipeId}/versions/${versionId}/sheet`,
    );
  }

  listRecipeAiProposals() {
    return this.catalogGet<{ items: RecipeAiProposal[]; total: number }>("/recipe-ai/proposals");
  }

  getRecipeAiProposal(proposalId: string) {
    return this.catalogGet<Envelope<RecipeAiProposal>>(`/recipe-ai/proposals/${proposalId}`);
  }

  getRecipeAiGrounding(proposalId: string) {
    return this.catalogGet<Envelope<{ results: Array<Record<string, string | null>> }>>(
      `/recipe-ai/proposals/${proposalId}/grounding`,
    );
  }

  getRecipeAiComparison(proposalId: string) {
    return this.catalogGet<Envelope<{ changes: RecipeAiProposal["changes"] }>>(
      `/recipe-ai/proposals/${proposalId}/comparison`,
    );
  }

  listRecipeReferences(query: Query = {}) {
    return this.catalogGet<{ data: Array<{ id: string; title: string; source_type: string }> }>(
      "/recipe-references",
      query,
    );
  }

  getRecipeTrials(recipeId: string, versionId: string) {
    return this.catalogGet<{ data: TrialRow[] }>(`/recipes/${recipeId}/versions/${versionId}/trials`);
  }

  getRecipeNutrition(recipeId: string, versionId: string) {
    return this.catalogGet<{ data: NutritionPreview | null; disclaimer?: string }>(
      `/recipes/${recipeId}/versions/${versionId}/nutrition`,
    );
  }

  getRecipeApprovals(recipeId: string, versionId: string) {
    return this.catalogGet<{ data: ApprovalRow[] }>(
      `/recipes/${recipeId}/versions/${versionId}/approvals`,
    );
  }

  getRecipeScales(recipeId: string, versionId: string) {
    return this.catalogGet<{ data: ScaleRow[] }>(`/recipes/${recipeId}/versions/${versionId}/scales`);
  }

  getLinkedReferences(recipeId: string) {
    return this.catalogGet<{ data: RecipeReferenceLink[] }>(`/recipes/${recipeId}/references`);
  }

  listLabelingDossiers() {
    return this.catalogGet<{ items: LabelingDossier[]; total: number }>("/labeling/dossiers");
  }

  getLabelingDossier(dossierId: string) {
    return this.catalogGet<Envelope<LabelingDossier>>(`/labeling/dossiers/${dossierId}`);
  }

  listLabelingAssessments() {
    return this.catalogGet<{ items: Array<{ id: string; proposal_summary: string; status: string }>; total: number }>(
      "/labeling/assessments",
    );
  }

  listLabelingCandidates() {
    return this.catalogGet<{ items: Array<{ id: string; watermark: string; payload_sha256: string }>; total: number }>(
      "/labeling/candidates",
    );
  }

  listLabelingSources() {
    return this.catalogGet<{ items: Array<Record<string, string | boolean>> }>("/labeling/sources");
  }

  listCostingPolicies() {
    return this.catalogGet<{ items: CostingPolicy[] }>("/costing/policies");
  }

  listCostingCalculations(kind?: string) {
    return this.catalogGet<{ items: CostingCalculation[] }>("/costing/calculations", kind ? { kind } : {});
  }

  getCostingCalculation(id: string) {
    return this.catalogGet<Envelope<CostingCalculation>>(`/costing/calculations/${id}`);
  }

  compareCostingCalculations(leftId: string, rightId: string) {
    return this.catalogGet<{ data: Record<string, string | null | Record<string, string>> }>(
      `/costing/calculations/${leftId}/compare/${rightId}`,
    );
  }

  listPricingSimulations() {
    return this.catalogGet<{ items: PricingSimulation[] }>("/pricing/simulations");
  }

  listPracticedPrices() {
    return this.catalogGet<{ items: PracticedPrice[] }>("/pricing/practiced");
  }

  listInventory<T = Record<string, unknown>>(path: string, query: Query = {}) {
    return this.catalogGet<{ items: T[] }>(path, query);
  }

  reportingCatalog() {
    return this.catalogGet<{ items: Array<{ code: string; name: string; description: string }> }>("/reporting/catalog");
  }

  reportingReport(code: string, query: Query = {}) {
    return this.catalogGet<Envelope<ReportPayload>>(`/reporting/reports/${code}`, query, false);
  }

  reportingDrillDown(report: string, metric: string, query: Query = {}) {
    return this.catalogGet<{ data: { rows: Array<Record<string, unknown>>; reconciled: boolean } }>(
      `/reporting/reports/${report}/metrics/${metric}/drill-down`,
      query,
      false,
    );
  }

  reportingSnapshots() {
    return this.catalogGet<{ items: ReportSnapshot[] }>("/reporting/snapshots");
  }

  reportingSavedViews() {
    return this.catalogGet<{ items: SavedReportView[] }>("/reporting/saved-views");
  }

  listLabelingPortions() {
    return this.catalogGet<{ items: Array<Record<string, string | boolean>> }>("/labeling/portions");
  }

  compareLabelingVersions(dossierId: string, left: string, right: string) {
    return this.catalogGet<{ data: { left: unknown; right: unknown } }>(
      `/labeling/dossiers/${dossierId}/compare`,
      { left, right },
      false,
    );
  }

  catalogCommand<T>(
    path: string,
    options: {
      method?: "POST" | "PATCH" | "DELETE";
      body?: unknown;
      idempotencyKey?: string;
      ifMatch?: number | null;
    },
  ): Promise<T> {
    return this.request<T>(this.catalogPath(path), {
      method: options.method ?? "POST",
      body: options.body,
      headers: {
        "Content-Type": "application/json",
        ...(options.idempotencyKey ? { "Idempotency-Key": options.idempotencyKey } : {}),
        ...(options.ifMatch != null ? { "If-Match": String(options.ifMatch) } : {}),
      },
      cache: false,
    }).then((result) => {
      this.clear();
      return result;
    });
  }

  command<T>(
    path: string,
    options: {
      method?: "POST" | "PATCH" | "DELETE";
      body?: unknown;
      idempotencyKey: string;
      ifMatch?: number | null;
    },
  ): Promise<T> {
    return this.request<T>(this.orgPath(path), {
      method: options.method ?? "POST",
      body: options.body,
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": options.idempotencyKey,
        ...(options.ifMatch != null ? { "If-Match": String(options.ifMatch) } : {}),
      },
      cache: false,
    }).then((result) => {
      this.clear();
      return result;
    });
  }

  private orgPath(path: string): string {
    if (!this.organizationId) {
      throw new ApiError("nao_autorizado", "Selecione uma organização.", 403);
    }
    return `/api/v1/organizations/${this.organizationId}/production${path}`;
  }

  private catalogPath(path: string): string {
    if (!this.organizationId) {
      throw new ApiError("nao_autorizado", "Selecione uma organização.", 403);
    }
    return `/api/v1/organizations/${this.organizationId}${path}`;
  }

  private catalogGet<T>(path: string, query: Query = {}, cache = true): Promise<T> {
    return this.request<T>(this.catalogPath(path), { query, cache });
  }

  private orgGet<T>(path: string, query: Query = {}, cache = true): Promise<T> {
    return this.request<T>(this.orgPath(path), { query, cache });
  }

  private async request<T>(
    path: string,
    options: {
      query?: Query;
      headers?: Record<string, string>;
      cache?: boolean;
      method?: string;
      body?: unknown;
    } = {},
  ): Promise<T> {
    const url = this.url(path, options.query);
    const method = options.method ?? "GET";
    const cacheKey = `${method}:${url}`;
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
      const response = await fetch(url, {
        method,
        headers,
        signal: controller.signal,
        body: options.body === undefined ? undefined : JSON.stringify(options.body),
      });
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
