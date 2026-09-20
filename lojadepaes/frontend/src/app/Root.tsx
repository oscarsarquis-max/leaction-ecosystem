import { useEffect, useState } from "react";
import { AdminApp } from "../admin/AdminApp";
import { safeAdminNext, storefrontAccessUrl } from "../admin/safePath";
import { StorefrontLayout } from "../components/StorefrontLayout";
import { ProductPage } from "../shop/ProductPage";
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
  return <App />;
}
