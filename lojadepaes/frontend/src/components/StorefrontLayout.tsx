import { useEffect, useState, type ReactNode } from "react";
import { currentPathname } from "../app/homeHash";
import { CartProvider } from "../shop/CartContext";
import { fetchOperations, type OperationsStatus } from "../shop/operationsApi";
import { SelectionDrawer } from "../shop/SelectionDrawer";
import { Footer } from "./Footer";
import { Header } from "./Header";
import { HomeReturn } from "./HomeReturn";

export function StorefrontLayout({ children }: { children: ReactNode }) {
  const [operations, setOperations] = useState<OperationsStatus | null>(null);
  const [path, setPath] = useState(currentPathname);

  useEffect(() => {
    const onPop = () => setPath(currentPathname());
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  useEffect(() => {
    fetchOperations()
      .then(setOperations)
      .catch(() => setOperations(null));
  }, []);

  return (
    <CartProvider>
      <div className="topline">FEITO À MÃO. FERMENTADO COM TEMPO. COMPARTILHADO COM AFETO.</div>
      {operations?.message ? <p className="prep-banner">{operations.message}</p> : null}
      <Header accompanimentsVisible={operations?.accompaniments_visible === true} />
      {path !== "/" ? <HomeReturn /> : null}
      {children}
      <Footer />
      <SelectionDrawer ordersEnabled={operations?.orders_enabled === true} />
    </CartProvider>
  );
}
