import { useCallback, useEffect, useMemo, useState } from "react";
import { HomeReturn } from "../components/HomeReturn";
import { FidelityParticipants } from "./FidelityParticipants";
import { AttendanceHistoryPanel, AttendanceSummaryPanel } from "./AttendanceSummary";
import { ProductionAgenda } from "./ProductionAgenda";
import { DateRequestDetailView } from "./DateRequestDetail";
import { OrderDetailView } from "./OrderDetail";
import { OrdersList } from "./OrdersList";
import { ProductEditor } from "./ProductEditor";
import { ProductsList } from "./ProductsList";
import { AccompanimentsAdmin } from "./AccompanimentsAdmin";
import { GigioNotes } from "./GigioNotes";
import { PairingRefs } from "./PairingRefs";
import { WeekRecipeEditor } from "./WeekRecipeEditor";
import { WeekRecipesList } from "./WeekRecipesList";
import type { WeekRecipeAdmin } from "../shop/weekRecipe";
import { SchedulePage } from "./SchedulePage";
import { AdminApiError, adminRequest, clearSession, rememberSession, unpaidProductionPrompt } from "./api";
import { replaceWithPath, storefrontAccessUrl } from "./safePath";
import { AdminShell } from "./shell/AdminShell";
import type { AdminProductList } from "./productTypes";
import type { AttendanceSummary, DateRequestDetail, OrderDetail, OrderFilters, OrderListResponse, SessionInfo, UnpaidProductionPrompt } from "./types";
import "./admin.css";

const EMPTY_FILTERS: OrderFilters = {
  reference: "",
  status: "",
  created_from: "",
  created_to: "",
  modality: "",
  lens: "",
};

function currentPath(): string {
  return window.location.pathname.replace(/\/+$/, "") || "/";
}

function go(to: string): void {
  window.history.pushState({}, "", to);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

function dateRequestIdFromPath(path: string): string | null {
  const match = path.match(/^\/admin\/pedidos\/solicitacao\/([^/]+)$/);
  return match ? match[1] : null;
}

function orderIdFromPath(path: string): string | null {
  if (path.includes("/solicitacao/")) {
    return null;
  }
  const match = path.match(/^\/admin\/pedidos\/([^/]+)$/);
  return match ? match[1] : null;
}

function productRoute(path: string): "list" | "new" | string | null {
  if (
    path.startsWith("/admin/produtos/receitas") ||
    path.startsWith("/admin/produtos/gigio") ||
    path.startsWith("/admin/produtos/complementos")
  ) {
    return null;
  }
  if (path === "/admin/produtos") {
    return "list";
  }
  if (path === "/admin/produtos/novo") {
    return "new";
  }
  const match = path.match(/^\/admin\/produtos\/([^/]+)$/);
  return match ? match[1] : null;
}

function recipeRoute(path: string): "list" | "new" | string | null {
  if (path === "/admin/produtos/receitas") {
    return "list";
  }
  if (path === "/admin/produtos/receitas/nova") {
    return "new";
  }
  const match = path.match(/^\/admin\/produtos\/receitas\/([^/]+)$/);
  return match ? match[1] : null;
}

function errorMessage(error: unknown): string {
  if (error instanceof AdminApiError) {
    if (error.status === 503) {
      return "Gestão indisponível. Use a configuração local documentada e reinicie a API.";
    }
    return error.message;
  }
  return "Algo deu errado.";
}

export function AdminApp() {
  const [path, setPath] = useState(currentPath);
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [sessionChecked, setSessionChecked] = useState(false);
  const [filters, setFilters] = useState<OrderFilters>(EMPTY_FILTERS);
  const [applied, setApplied] = useState<OrderFilters>(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [list, setList] = useState<OrderListResponse | null>(null);
  const [listLoading, setListLoading] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [detail, setDetail] = useState<OrderDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [conflict, setConflict] = useState(false);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [productionPrompt, setProductionPrompt] = useState<UnpaidProductionPrompt | null>(null);
  const [noteError, setNoteError] = useState<string | null>(null);
  const [productFilters, setProductFilters] = useState({ query: "", status: "", available: "" });
  const [appliedProducts, setAppliedProducts] = useState({ query: "", status: "", available: "" });
  const [productPage, setProductPage] = useState(1);
  const [products, setProducts] = useState<AdminProductList | null>(null);
  const [productsLoading, setProductsLoading] = useState(false);
  const [productsError, setProductsError] = useState<string | null>(null);
  const [recipes, setRecipes] = useState<WeekRecipeAdmin[]>([]);
  const [recipesLoading, setRecipesLoading] = useState(false);
  const [recipesError, setRecipesError] = useState<string | null>(null);
  const [recipeBusy, setRecipeBusy] = useState<string | null>(null);
  const [dateRequest, setDateRequest] = useState<DateRequestDetail | null>(null);
  const [dateRequestLoading, setDateRequestLoading] = useState(false);
  const [dateRequestError, setDateRequestError] = useState<string | null>(null);
  const [summary, setSummary] = useState<AttendanceSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  const [noticesOpen, setNoticesOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const orderId = orderIdFromPath(path);
  const dateRequestId = dateRequestIdFromPath(path);
  const productPath = productRoute(path);
  const recipePath = recipeRoute(path);
  const ordersHome = path === "/admin" || path === "/admin/pedidos";

  useEffect(() => {
    const onPop = () => setPath(currentPath());
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  useEffect(() => {
    let cancelled = false;
    adminRequest<SessionInfo>("/api/v1/admin/session")
      .then((info) => {
        if (cancelled) {
          return;
        }
        if (info.csrf_token) {
          rememberSession(info.csrf_token, info.bakery_timezone);
        }
        setSession(info);
      })
      .catch(() => {
        if (cancelled) {
          return;
        }
        clearSession();
        setSession(null);
      })
      .finally(() => {
        if (!cancelled) {
          setSessionChecked(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const loadList = useCallback(async () => {
    setListLoading(true);
    setListError(null);
    const params = new URLSearchParams();
    params.set("page", String(page));
    params.set("page_size", "20");
    if (applied.reference.trim()) {
      params.set("reference", applied.reference.trim());
    }
    if (applied.status) {
      params.set("status", applied.status);
    }
    if (applied.modality) {
      params.set("modality", applied.modality);
    }
    if (applied.created_from) {
      params.set("created_from", applied.created_from);
    }
    if (applied.created_to) {
      params.set("created_to", applied.created_to);
    }
    if (applied.lens) {
      params.set("lens", applied.lens);
    }
    try {
      const data = await adminRequest<OrderListResponse>(`/api/v1/admin/orders?${params.toString()}`);
      setList(data);
    } catch (error) {
      if (error instanceof AdminApiError && error.status === 401) {
        setSession(null);
        return;
      }
      setListError(errorMessage(error));
    } finally {
      setListLoading(false);
    }
  }, [applied, page]);

  const loadProducts = useCallback(async () => {
    setProductsLoading(true);
    setProductsError(null);
    const params = new URLSearchParams();
    params.set("page", String(productPage));
    params.set("page_size", "20");
    if (appliedProducts.query.trim()) {
      params.set("query", appliedProducts.query.trim());
    }
    if (appliedProducts.status) {
      params.set("status", appliedProducts.status);
    }
    if (appliedProducts.available) {
      params.set("available", appliedProducts.available);
    }
    try {
      const data = await adminRequest<AdminProductList>(`/api/v1/admin/products?${params.toString()}`);
      setProducts(data);
    } catch (error) {
      if (error instanceof AdminApiError && error.status === 401) {
        setSession(null);
        return;
      }
      setProductsError(errorMessage(error));
    } finally {
      setProductsLoading(false);
    }
  }, [appliedProducts, productPage]);

  const loadRecipes = useCallback(async () => {
    setRecipesLoading(true);
    setRecipesError(null);
    try {
      const data = await adminRequest<{ items: WeekRecipeAdmin[] }>("/api/v1/admin/week-recipes");
      setRecipes(data.items);
    } catch (error) {
      if (error instanceof AdminApiError && error.status === 401) {
        setSession(null);
        return;
      }
      setRecipesError(errorMessage(error));
    } finally {
      setRecipesLoading(false);
    }
  }, []);

  async function recipeAction(id: string, action: string) {
    setRecipeBusy(id);
    setRecipesError(null);
    try {
      await adminRequest(`/api/v1/admin/week-recipes/${id}/${action}`, { method: "POST" });
      await loadRecipes();
    } catch (error) {
      setRecipesError(errorMessage(error));
    } finally {
      setRecipeBusy(null);
    }
  }

  const loadSummary = useCallback(async () => {
    setSummaryLoading(true);
    setSummaryError(null);
    try {
      const data = await adminRequest<AttendanceSummary>("/api/v1/admin/ops/attendance-summary");
      setSummary(data);
    } catch (error) {
      if (error instanceof AdminApiError && error.status === 401) {
        setSession(null);
        return;
      }
      setSummaryError(errorMessage(error));
    } finally {
      setSummaryLoading(false);
    }
  }, []);

  const loadDateRequest = useCallback(async (id: string) => {
    setDateRequestLoading(true);
    setDateRequestError(null);
    try {
      const data = await adminRequest<DateRequestDetail>(`/api/v1/admin/date-requests/${id}`);
      setDateRequest(data);
    } catch (error) {
      if (error instanceof AdminApiError && error.status === 401) {
        setSession(null);
        return;
      }
      setDateRequest(null);
      setDateRequestError(errorMessage(error));
    } finally {
      setDateRequestLoading(false);
    }
  }, []);

  const loadDetail = useCallback(async (id: string) => {
    setDetailLoading(true);
    setDetailError(null);
    setProductionPrompt(null);
    try {
      const data = await adminRequest<OrderDetail>(`/api/v1/admin/orders/${id}`);
      setDetail(data);
      setConflict(false);
    } catch (error) {
      if (error instanceof AdminApiError && error.status === 401) {
        setSession(null);
        return;
      }
      setDetail(null);
      setDetailError(errorMessage(error));
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!sessionChecked || session) {
      return;
    }
    const current = currentPath();
    replaceWithPath(storefrontAccessUrl(current === "/admin/login" ? "/admin/produtos" : current));
  }, [session, sessionChecked]);

  useEffect(() => {
    if (!session || !ordersHome) {
      return;
    }
    void loadSummary();
  }, [session, ordersHome, loadSummary]);

  useEffect(() => {
    if (!session) {
      return;
    }
    if (dateRequestId) {
      void loadDateRequest(dateRequestId);
      return;
    }
    if (orderId) {
      void loadDetail(orderId);
      return;
    }
    if (productPath === "list") {
      void loadProducts();
      return;
    }
    if (recipePath === "list") {
      void loadRecipes();
      return;
    }
    if (path === "/admin/pedidos" || path === "/admin") {
      void loadList();
    }
  }, [session, path, orderId, dateRequestId, productPath, recipePath, loadList, loadDetail, loadDateRequest, loadProducts, loadRecipes]);

  const emptyHint = useMemo(() => {
    if (listError || !list || listLoading || list.items.length > 0 || list.orders_error || list.date_requests_error) {
      return null;
    }
    const filtered = Boolean(
      applied.reference ||
        applied.status ||
        applied.modality ||
        applied.created_from ||
        applied.created_to ||
        applied.lens
    );
    return filtered ? "filtered" : "none";
  }, [applied, list, listError, listLoading]);

  async function handleAction(action: string, reason?: string, unpaidException = false) {
    if (!detail) {
      return;
    }
    const paths: Record<string, string> = {
      confirm: "confirm",
      start_production: "start-production",
      confirm_delivery: "confirm-delivery",
      mark_ready: "mark-ready",
      complete: "complete",
      cancel: "cancel",
    };
    const suffix = paths[action];
    if (!suffix) {
      return;
    }
    setBusyAction(action);
    setDetailError(null);
    setConflict(false);
    try {
      const updated = await adminRequest<OrderDetail>(`/api/v1/admin/orders/${detail.id}/${suffix}`, {
        method: "POST",
        body:
          action === "cancel"
            ? JSON.stringify({ reason })
            : action === "start_production" && unpaidException
              ? JSON.stringify({ unpaid_exception: true })
              : undefined,
      });
      setProductionPrompt(null);
      setDetail(updated);
    } catch (error) {
      if (error instanceof AdminApiError) {
        const prompt = unpaidProductionPrompt(error);
        if (prompt) {
          setProductionPrompt(prompt);
          setConflict(false);
          setDetailError(null);
          return;
        }
      }
      if (error instanceof AdminApiError && error.status === 409 && error.code !== "schedule") {
        setConflict(true);
      }
      setDetailError(errorMessage(error));
    } finally {
      setBusyAction(null);
    }
  }

  async function handleNote(body: string) {
    if (!detail) {
      return;
    }
    setNoteError(null);
    try {
      await adminRequest(`/api/v1/admin/orders/${detail.id}/notes`, {
        method: "POST",
        body: JSON.stringify({ body }),
      });
      await loadDetail(detail.id);
    } catch (error) {
      setNoteError(errorMessage(error));
    }
  }

  async function handleDateRequestAction(
    action: "propose" | "close" | "accept" | "request_completion",
    payload: {
      proposed_date?: string | null;
      note?: string | null;
      address?: {
        delivery_street: string;
        delivery_number: string;
        delivery_complement: string;
        delivery_district: string;
        delivery_city: string;
        delivery_state: string;
        delivery_postal_code: string;
      } | null;
      lines?: Array<{ variant_id: string; quantity: number }>;
    },
  ) {
    if (!dateRequest) {
      return;
    }
    setBusyAction(action);
    setDateRequestError(null);
    try {
      const updated = await adminRequest<DateRequestDetail>(`/api/v1/admin/date-requests/${dateRequest.id}`, {
        method: "POST",
        body: JSON.stringify({
          action,
          proposed_date: payload.proposed_date || null,
          note: payload.note || null,
          address: payload.address || null,
          lines: payload.lines || [],
        }),
      });
      setDateRequest(updated);
    } catch (error) {
      setDateRequestError(errorMessage(error));
    } finally {
      setBusyAction(null);
    }
  }

  async function handleCommercialPreview(lines: Array<{ variant_id: string; quantity: number }>) {
    if (!dateRequest) {
      throw new Error("solicitação ausente");
    }
    return adminRequest<NonNullable<DateRequestDetail["accept_preview"]>>(
      `/api/v1/admin/date-requests/${dateRequest.id}/commercial-preview`,
      {
        method: "POST",
        body: JSON.stringify({ lines }),
      },
    );
  }

  async function handleOutboxRetry(outboxId: string) {
    setBusyAction("retry");
    setDateRequestError(null);
    try {
      await adminRequest(`/api/v1/admin/ops/outbox/${outboxId}/retry`, { method: "POST" });
      if (dateRequestId) {
        await loadDateRequest(dateRequestId);
      }
    } catch (error) {
      setDateRequestError(errorMessage(error));
    } finally {
      setBusyAction(null);
    }
  }

  async function handleEvaluate(itemId: string, decision: string, response: string) {
    if (!detail) {
      return;
    }
    setBusyAction("adaptation");
    setDetailError(null);
    try {
      const updated = await adminRequest<OrderDetail>(
        `/api/v1/admin/orders/${detail.id}/items/${itemId}/adaptation`,
        {
          method: "POST",
          body: JSON.stringify({ decision, response }),
        },
      );
      setDetail(updated);
    } catch (error) {
      setDetailError(errorMessage(error));
    } finally {
      setBusyAction(null);
    }
  }

  if (!sessionChecked) {
    return (
      <div className="admin-shell">
        <HomeReturn native />
        <p className="admin-muted">Verificando sessão…</p>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="admin-shell">
        <HomeReturn native />
        <p className="admin-muted">Redirecionando ao acesso do cabeçalho…</p>
      </div>
    );
  }

  const trailDetail = orderId
    ? detail?.public_reference
    : dateRequestId
      ? dateRequest?.public_reference
      : null;

  return (
    <div className="admin-shell">
      <AdminShell
        path={path}
        onNavigate={go}
        session={session}
        noticesOpen={noticesOpen}
        onToggleNotices={() => setNoticesOpen((open) => !open)}
        trailDetail={trailDetail}
      >
      {ordersHome ? (
        <>
          <ProductionAgenda
            refreshToken={summary?.updated_at ?? ""}
            onOpen={(href) => go(href)}
          />
          <AttendanceSummaryPanel
            data={summary}
            loading={summaryLoading}
            error={summaryError}
            onRefresh={() => void loadSummary()}
            activeLens={applied.lens || ""}
            onOpenHistory={() => setHistoryOpen(true)}
            onSelectLens={(lens) => {
              const next = { ...EMPTY_FILTERS, lens };
              setFilters(next);
              setApplied(next);
              setPage(1);
              go("/admin/pedidos");
            }}
          />
        </>
      ) : null}
      <main>
        {dateRequestId ? (
          <DateRequestDetailView
            request={dateRequest}
            loading={dateRequestLoading}
            error={dateRequestError}
            busyAction={busyAction}
            onBack={() => go("/admin/pedidos")}
            onReload={() => void loadDateRequest(dateRequestId)}
            onAct={(action, payload) => void handleDateRequestAction(action, payload)}
            onRetry={(id) => void handleOutboxRetry(id)}
            onQuote={(lines) => handleCommercialPreview(lines)}
          />
        ) : orderId ? (
          <OrderDetailView
            order={detail}
            loading={detailLoading}
            error={detailError}
            conflict={conflict}
            busyAction={busyAction}
            noteError={noteError}
            onBack={() => go("/admin/pedidos")}
            onReload={() => void loadDetail(orderId)}
            onAction={(action, reason) => void handleAction(action, reason)}
            productionPrompt={productionPrompt}
            onDismissProduction={() => setProductionPrompt(null)}
            onConfirmUnpaidProduction={() => void handleAction("start_production", undefined, true)}
            onNote={(body) => void handleNote(body)}
            onEvaluateAdaptation={(itemId, decision, response) => void handleEvaluate(itemId, decision, response)}
          />
        ) : productPath === "new" || (productPath && productPath !== "list") ? (
          <ProductEditor
            productId={productPath === "new" ? null : productPath}
            onBack={() => go("/admin/produtos")}
            onSaved={(id) => go(`/admin/produtos/${id}`)}
            onDeleted={() => go("/admin/produtos")}
          />
        ) : path === "/admin/agenda" ? (
          <SchedulePage />
        ) : path === "/admin/fidelidade" ? (
          <FidelityParticipants />
        ) : recipePath === "new" || (recipePath && recipePath !== "list") ? (
          <WeekRecipeEditor
            recipeId={recipePath === "new" ? null : recipePath}
            onBack={() => go("/admin/produtos/receitas")}
            onSaved={(id) => go(`/admin/produtos/receitas/${id}`)}
          />
        ) : path === "/admin/produtos/gigio" ? (
          <GigioNotes />
        ) : path === "/admin/produtos/gigio/harmonizacoes" ? (
          <PairingRefs />
        ) : path === "/admin/produtos/complementos" ? (
          <AccompanimentsAdmin />
        ) : recipePath === "list" ? (
          <WeekRecipesList
            items={recipes}
            loading={recipesLoading}
            error={recipesError}
            busyId={recipeBusy}
            onNew={() => go("/admin/produtos/receitas/nova")}
            onOpen={(id) => go(`/admin/produtos/receitas/${id}`)}
            onPublish={(id) => void recipeAction(id, "publish")}
            onFeature={(id) => void recipeAction(id, "feature")}
            onUnfeature={(id) => void recipeAction(id, "unfeature")}
            onArchive={(id) => void recipeAction(id, "archive")}
          />
        ) : productPath === "list" ? (
          <ProductsList
            filters={productFilters}
            data={products}
            loading={productsLoading}
            error={productsError}
            onChange={setProductFilters}
            onSubmit={(event) => {
              event.preventDefault();
              setProductPage(1);
              setAppliedProducts({ ...productFilters });
            }}
            onNew={() => go("/admin/produtos/novo")}
            onOpen={(id) => go(`/admin/produtos/${id}`)}
            onPage={setProductPage}
            onRefresh={() => void loadProducts()}
          />
        ) : (
          <>
          <OrdersList
            filters={filters}
            data={list}
            loading={listLoading}
            error={listError}
            emptyHint={emptyHint}
            onChange={setFilters}
            onSubmit={(event) => {
              event.preventDefault();
              const next = { ...filters };
              if (next.status || next.reference.trim()) {
                next.lens = "";
              }
              setFilters(next);
              setPage(1);
              setApplied(next);
            }}
            onRefresh={() => void loadList()}
            onClearFilters={() => {
              setFilters(EMPTY_FILTERS);
              setApplied(EMPTY_FILTERS);
              setPage(1);
            }}
            onOpen={(item) =>
              go(
                item.source === "date_request"
                  ? `/admin/pedidos/solicitacao/${item.id}`
                  : `/admin/pedidos/${item.id}`,
              )
            }
            onPage={setPage}
          />
          {ordersHome ? (
            <AttendanceHistoryPanel
              data={summary}
              error={summaryError}
              open={historyOpen}
              activeLens={applied.lens || ""}
              onToggle={() => setHistoryOpen((open) => !open)}
              onSelectLens={(lens) => {
                const next = { ...EMPTY_FILTERS, lens };
                setFilters(next);
                setApplied(next);
                setPage(1);
                go("/admin/pedidos");
              }}
            />
          ) : null}
          </>
        )}
      </main>
      </AdminShell>
    </div>
  );
}
