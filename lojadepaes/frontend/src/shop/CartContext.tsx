import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  addCustomToSelection,
  applyProductAddition,
  countItems,
  readSelection,
  removeLine,
  resolveSelection,
  setLineAdaptation,
  setLineQuantity,
  writeSelection,
} from "./selection";
import type { AdaptationDraft, CustomSelection, ResolvedLine, SelectionLine } from "./types";

type CartContextValue = {
  lines: SelectionLine[];
  resolved: ResolvedLine[];
  totalCents: number;
  count: number;
  open: boolean;
  setOpen: (open: boolean) => void;
  add: (slug: string, variantId: string, quantity: number, adaptation?: AdaptationDraft | null) => void;
  addCustom: (custom: CustomSelection, quantity: number, adaptation?: AdaptationDraft | null) => void;
  changeQuantity: (lineKey: string, quantity: number) => void;
  changeAdaptation: (lineKey: string, adaptation: AdaptationDraft | null) => void;
  remove: (lineKey: string) => void;
  clear: () => void;
  refresh: () => Promise<void>;
  notice: string | null;
};

const CartContext = createContext<CartContextValue | null>(null);

export function CartProvider({ children }: { children: ReactNode }) {
  const [lines, setLines] = useState<SelectionLine[]>(() => (typeof window === "undefined" ? [] : readSelection()));
  const [resolved, setResolved] = useState<ResolvedLine[]>([]);
  const [totalCents, setTotalCents] = useState(0);
  const [open, setOpen] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const linesRef = useRef(lines);
  linesRef.current = lines;

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

  const add = useCallback(
    (slug: string, variantId: string, quantity: number, adaptation?: AdaptationDraft | null) => {
      const applied = applyProductAddition(linesRef.current, slug, variantId, quantity, adaptation);
      linesRef.current = applied.lines;
      setLines(applied.lines);
      setNotice(applied.message);
      setOpen(true);
    },
    [],
  );

  const addCustom = useCallback((custom: CustomSelection, quantity: number, adaptation?: AdaptationDraft | null) => {
    setLines((current) => addCustomToSelection(current, custom, quantity, adaptation));
    setOpen(false);
  }, []);

  const changeQuantity = useCallback((lineKey: string, quantity: number) => {
    setLines((current) => {
      const next = setLineQuantity(current, lineKey, quantity);
      linesRef.current = next;
      return next;
    });
    setNotice(null);
  }, []);

  const changeAdaptation = useCallback((lineKey: string, adaptation: AdaptationDraft | null) => {
    setLines((current) => setLineAdaptation(current, lineKey, adaptation));
  }, []);

  const remove = useCallback((lineKey: string) => {
    setLines((current) => removeLine(current, lineKey));
  }, []);

  const clear = useCallback(() => {
    setLines([]);
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
      addCustom,
      changeQuantity,
      changeAdaptation,
      remove,
      clear,
      refresh,
      notice,
    }),
    [add, addCustom, changeAdaptation, changeQuantity, clear, lines, notice, open, refresh, remove, resolved, totalCents],
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
