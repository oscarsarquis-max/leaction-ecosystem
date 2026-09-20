import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  addToSelection,
  countItems,
  readSelection,
  removeLine,
  resolveSelection,
  setLineQuantity,
  writeSelection,
} from "./selection";
import type { ResolvedLine, SelectionLine } from "./types";

type CartContextValue = {
  lines: SelectionLine[];
  resolved: ResolvedLine[];
  totalCents: number;
  count: number;
  open: boolean;
  setOpen: (open: boolean) => void;
  add: (slug: string, variantId: string, quantity: number) => void;
  changeQuantity: (variantId: string, quantity: number) => void;
  remove: (variantId: string) => void;
  refresh: () => Promise<void>;
};

const CartContext = createContext<CartContextValue | null>(null);

export function CartProvider({ children }: { children: ReactNode }) {
  const [lines, setLines] = useState<SelectionLine[]>(() => (typeof window === "undefined" ? [] : readSelection()));
  const [resolved, setResolved] = useState<ResolvedLine[]>([]);
  const [totalCents, setTotalCents] = useState(0);
  const [open, setOpen] = useState(false);

  const refresh = useCallback(async () => {
    const current = readSelection();
    if (current.length === 0) {
      setResolved([]);
      setTotalCents(0);
      return;
    }
    const result = await resolveSelection(current);
    setResolved(result.lines);
    setTotalCents(result.totalCents);
  }, []);

  useEffect(() => {
    writeSelection(lines);
    void refresh();
  }, [lines, refresh]);

  const add = useCallback((slug: string, variantId: string, quantity: number) => {
    setLines((current) => addToSelection(current, slug, variantId, quantity));
    setOpen(true);
  }, []);

  const changeQuantity = useCallback((variantId: string, quantity: number) => {
    setLines((current) => setLineQuantity(current, variantId, quantity));
  }, []);

  const remove = useCallback((variantId: string) => {
    setLines((current) => removeLine(current, variantId));
  }, []);

  const value = useMemo(
    () => ({
      lines,
      resolved,
      totalCents,
      count: countItems(lines),
      open,
      setOpen,
      add,
      changeQuantity,
      remove,
      refresh,
    }),
    [add, changeQuantity, lines, open, refresh, remove, resolved, totalCents],
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart(): CartContextValue {
  const value = useContext(CartContext);
  if (!value) {
    throw new Error("carrinho fora do provedor");
  }
  return value;
}
