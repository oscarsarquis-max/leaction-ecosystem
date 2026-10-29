import { useEffect, useState } from "react";
import { ActivatePasswordPage } from "../components/ActivatePasswordPage";
import { AdminApp } from "../admin/AdminApp";
import { safeAdminNext, storefrontAccessUrl } from "../admin/safePath";
import { StorefrontLayout } from "../components/StorefrontLayout";
import { CheckoutPage } from "../shop/CheckoutPage";
import { DateRequestCompletePage } from "../shop/DateRequestCompletePage";
import { OrderStatusPage } from "../shop/OrderStatusPage";
import { AccompanimentsPage } from "../shop/AccompanimentsPage";
import { ProductPage } from "../shop/ProductPage";
import { RecipeArchivePage } from "../shop/RecipeArchivePage";
import { WeekRecipePage } from "../shop/WeekRecipePage";
import { GigioHost } from "../gigio/GigioHost";
import { trackPageview } from "../shop/tracking";
import { ArticlePage } from "../features/baker-library/ArticlePage";
import { CalculatorPage } from "../features/baker-library/CalculatorPage";
import { App } from "./App";

function productSlug(path: string): string | null {
  const match = path.match(/^\/paes\/([^/]+)\/?$/);
  return match ? decodeURIComponent(match[1]) : null;
}

function recipeSlug(path: string): string | null {
  const match = path.match(/^\/receitas\/([^/]+)\/?$/);
  return match ? decodeURIComponent(match[1]) : null;
}

function librarySlug(path: string): string | null {
  const match = path.match(/^\/biblioteca\/([^/]+)\/?$/);
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

  let page = <App />;
  if (path === "/admin/login") {
    page = <App />;
  } else if (path.startsWith("/ativar")) {
    page = <ActivatePasswordPage />;
  } else if (path.startsWith("/admin")) {
    page = <AdminApp />;
  } else if (path === "/acompanhar") {
    page = (
      <StorefrontLayout>
        <AccompanimentsPage />
      </StorefrontLayout>
    );
  } else if (path === "/biblioteca/calculadora") {
    page = (
      <StorefrontLayout>
        <CalculatorPage />
      </StorefrontLayout>
    );
  } else if (path === "/receitas") {
    page = (
      <StorefrontLayout>
        <RecipeArchivePage />
      </StorefrontLayout>
    );
  } else {
    const weekSlug = recipeSlug(path);
    const articleSlug = librarySlug(path);
    const slug = productSlug(path);
    const orderMatch = path.match(/^\/pedido\/([^/]+)\/?$/);
    const complementMatch = path.match(/^\/solicitacao\/([^/]+)\/?$/);
    if (articleSlug && articleSlug !== "calculadora") {
      page = (
        <StorefrontLayout>
          <ArticlePage slug={articleSlug} />
        </StorefrontLayout>
      );
    } else if (weekSlug) {
      page = (
        <StorefrontLayout>
          <WeekRecipePage slug={weekSlug} />
        </StorefrontLayout>
      );
    } else if (slug) {
      page = (
        <StorefrontLayout>
          <ProductPage slug={slug} />
        </StorefrontLayout>
      );
    } else if (path === "/pedido/novo") {
      page = (
        <StorefrontLayout>
          <CheckoutPage />
        </StorefrontLayout>
      );
    } else if (orderMatch) {
      page = (
        <StorefrontLayout>
          <OrderStatusPage reference={decodeURIComponent(orderMatch[1])} />
        </StorefrontLayout>
      );
    } else if (complementMatch) {
      page = (
        <StorefrontLayout>
          <DateRequestCompletePage />
        </StorefrontLayout>
      );
    }
  }
  return (
    <>
      {page}
      <GigioHost path={path} />
    </>
  );
}
