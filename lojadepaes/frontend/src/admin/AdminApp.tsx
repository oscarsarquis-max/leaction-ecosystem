import { useCallback, useEffect, useMemo, useState } from "react";
import { HeaderAccount } from "../components/HeaderAccount";
import { OrderDetailView } from "./OrderDetail";
import { OrdersList } from "./OrdersList";
import { ProductEditor } from "./ProductEditor";
import { ProductsList } from "./ProductsList";
import { AdminApiError, adminRequest, clearSession, rememberSession } from "./api";
import { replaceWithPath, storefrontAccessUrl } from "./safePath";
import type { AdminProductList } from "./productTypes";
import type { OrderDetail, OrderFilters, OrderListResponse, SessionInfo } from "./types";
import "./admin.css";

const EMPTY_FILTERS: OrderFilters = {
  reference: "",
  status: "",
  created_from: "",
  created_to: "",
  modality: "",
};

function currentPath(): string {
  return window.location.pathname.replace(/\/+$/, "") || "/";
}

function go(to: string): void {
  window.history.pushState({}, "", to);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

function orderIdFromPath(path: string): string | null {
  const match = path.match(/^\/admin\/pedidos\/([^/]+)$/);
  return match ? match[1] : null;
}

function productRoute(path: string): "list" | "new" | string | null {
  if (path === "/admin/produtos") {
    return "list";
  }
  if (path === "/admin/produtos/novo") {
    return "new";
  }
  const match = path.match(/^\/admin\/produtos\/([^/]+)$/);
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
  const [noteError, setNoteError] = useState<string | null>(null);
  const [productFilters, setProductFilters] = useState({ query: "", status: "", available: "" });
  const [appliedProducts, setAppliedProducts] = useState({ query: "", status: "", available: "" });
  const [productPage, setProductPage] = useState(1);
  const [products, setProducts] = useState<AdminProductList | null>(null);
  const [productsLoading, setProductsLoading] = useState(false);
  const [productsError, setProductsError] = useState<string | null>(null);

  const orderId = orderIdFromPath(path);
  const productPath = productRoute(path);

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
        rememberSession(info.csrf_token, info.bakery_timezone);
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

  const loadDetail = useCallback(async (id: string) => {
    setDetailLoading(true);
    setDetailError(null);
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
    if (!session) {
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
    if (path === "/admin/pedidos" || path === "/admin") {
      void loadList();
    }
  }, [session, path, orderId, productPath, loadList, loadDetail, loadProducts]);

  const emptyHint = useMemo(() => {
    if (!list || listLoading || list.items.length > 0) {
      return null;
    }
    const filtered = Boolean(
      applied.reference || applied.status || applied.modality || applied.created_from || applied.created_to
    );
    return filtered ? "filtered" : "none";
  }, [applied, list, listLoading]);

  async function handleAction(action: string, reason?: string) {
    if (!detail) {
      return;
    }
    const paths: Record<string, string> = {
      confirm: "confirm",
      start_production: "start-production",
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
        body: action === "cancel" ? JSON.stringify({ reason }) : undefined,
      });
      setDetail(updated);
    } catch (error) {
      if (error instanceof AdminApiError && error.status === 409) {
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

  if (!sessionChecked) {
    return (
      <div className="admin-shell">
        <p className="admin-muted">Verificando sessão…</p>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="admin-shell">
        <p className="admin-muted">Redirecionando ao acesso do cabeçalho…</p>
      </div>
    );
  }

  return (
    <div className="admin-shell">
      <header className="admin-top">
        <a className="admin-brand" href="/">
          Loja de Pães
        </a>
        <HeaderAccount afterLogin="stay" initialSession={session} />
      </header>
      <main>
        {orderId ? (
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
            onNote={(body) => void handleNote(body)}
          />
        ) : productPath === "new" || (productPath && productPath !== "list") ? (
          <ProductEditor
            productId={productPath === "new" ? null : productPath}
            onBack={() => go("/admin/produtos")}
            onSaved={(id) => go(`/admin/produtos/${id}`)}
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
          />
        ) : (
          <OrdersList
            filters={filters}
            data={list}
            loading={listLoading}
            error={listError}
            emptyHint={emptyHint}
            onChange={setFilters}
            onSubmit={(event) => {
              event.preventDefault();
              setPage(1);
              setApplied({ ...filters });
            }}
            onRefresh={() => void loadList()}
            onOpen={(id) => go(`/admin/pedidos/${id}`)}
            onPage={setPage}
          />
        )}
      </main>
    </div>
  );
}
