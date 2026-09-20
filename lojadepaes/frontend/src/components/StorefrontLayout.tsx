import { CartProvider } from "../shop/CartContext";
import { SelectionDrawer } from "../shop/SelectionDrawer";
import { Footer } from "./Footer";
import { Header } from "./Header";
import type { ReactNode } from "react";

export function StorefrontLayout({ children }: { children: ReactNode }) {
  return (
    <CartProvider>
      <div className="topline">FEITO À MÃO. FERMENTADO COM TEMPO. COMPARTILHADO COM AFETO.</div>
      <Header />
      {children}
      <Footer />
      <SelectionDrawer />
    </CartProvider>
  );
}
