import { useEffect, useState, type ReactNode } from "react";
import { CartProvider } from "../shop/CartContext";
import { fetchOperations, type OperationsStatus } from "../shop/operationsApi";
import { SelectionDrawer } from "../shop/SelectionDrawer";
import { Footer } from "./Footer";
import { Header } from "./Header";

export function StorefrontLayout({ children }: { children: ReactNode }) {
  const [operations, setOperations] = useState<OperationsStatus | null>(null);

  useEffect(() => {
    fetchOperations()
      .then(setOperations)
      .catch(() => setOperations(null));
  }, []);

  return (
    <CartProvider>
      <div className="topline">FEITO À MÃO. FERMENTADO COM TEMPO. COMPARTILHADO COM AFETO.</div>
      {operations?.message ? <p className="prep-banner">{operations.message}</p> : null}
      <Header />
      {children}
      <Footer />
      <SelectionDrawer ordersEnabled={operations?.orders_enabled === true} />
    </CartProvider>
  );
}
