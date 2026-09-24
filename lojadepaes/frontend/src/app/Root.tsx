import { useEffect, useState } from "react";
import { ActivatePasswordPage } from "../components/ActivatePasswordPage";
import { AdminApp } from "../admin/AdminApp";
import { safeAdminNext, storefrontAccessUrl } from "../admin/safePath";
import { StorefrontLayout } from "../components/StorefrontLayout";
import { CheckoutPage } from "../shop/CheckoutPage";
import { OrderStatusPage } from "../shop/OrderStatusPage";
import { ProductPage } from "../shop/ProductPage";
import { trackPageview } from "../shop/tracking";
import { App } from "./App";

function productSlug(path: string): string | null {
  const match = path.match(/^\/paes\/([^/]+)\/?$/);
  return match ? decodeURIComponent(match[1]) : null;
}

function normalizedPath(): string {
  return window.location.pathname.replace(/\/+$/, "") || "/";
}

export function Root() {
  const [path, setPath] = useState(normalizedPath);

  useEffect(() => {
    const onPop = () => setPath(normalizedPath());
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  useEffect(() => {
    trackPageview(path);
  }, [path]);

  useEffect(() => {
    if (path !== "/admin/login") {
      return;
    }
    const params = new URLSearchParams(window.location.search);
    const url = storefrontAccessUrl(safeAdminNext(params.get("next")));
    window.history.replaceState({}, "", url);
    setPath("/");
  }, [path]);

  if (path === "/admin/login") {
    return <App />;
  }
  if (path.startsWith("/ativar")) {
    return <ActivatePasswordPage />;
  }
  if (path.startsWith("/admin")) {
    return <AdminApp />;
  }
  const slug = productSlug(path);
  if (slug) {
    return (
      <StorefrontLayout>
        <ProductPage slug={slug} />
      </StorefrontLayout>
    );
  }
  if (path === "/pedido/novo") {
    return (
      <StorefrontLayout>
        <CheckoutPage />
      </StorefrontLayout>
    );
  }
  const orderMatch = path.match(/^\/pedido\/([^/]+)\/?$/);
  if (orderMatch) {
    return (
      <StorefrontLayout>
        <OrderStatusPage reference={decodeURIComponent(orderMatch[1])} />
      </StorefrontLayout>
    );
  }
  return <App />;
}
