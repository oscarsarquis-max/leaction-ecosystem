import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchOperations } from "../../shop/operationsApi";
import {
  bakerTip,
  canAdvanceEssence,
  canComplete,
  createInitialState,
  earliestDate,
  earliestFromBusinessDate,
  goBack,
  goNext,
  inclusionWarning,
  receiptLines,
  summaryText,
  type BreadBuilderState,
  type CompatibleOption,
} from "./state";

export function useBreadBuilder() {
  const [state, setState] = useState<BreadBuilderState>(() => createInitialState());
  const [businessDate, setBusinessDate] = useState<string | null>(null);
  useEffect(() => {
    fetchOperations()
      .then((status) => {
        if (status.business_date) {
          setBusinessDate(status.business_date);
        }
      })
      .catch(() => undefined);
  }, []);
  const earliest = useMemo(
    () => (businessDate ? earliestFromBusinessDate(businessDate) : earliestDate()),
    [businessDate],
  );

  const selectMass = useCallback((massId: string, massName: string, extras: CompatibleOption[] = []) => {
    setState((current) => ({
      ...current,
      massId,
      massName,
      inclusionNotice: inclusionWarning(massId, extras),
    }));
  }, []);

  const selectFlour = useCallback((flourId: string, flourName: string) => {
    setState((current) => ({ ...current, flourId, flourName }));
  }, []);

  const toggleIngredient = useCallback((id: string, name: string) => {
    setState((current) => {
      const index = current.extraIds.indexOf(id);
      if (index >= 0) {
        return {
          ...current,
          extraIds: current.extraIds.filter((item) => item !== id),
          extraNames: current.extraNames.filter((_, itemIndex) => itemIndex !== index),
        };
      }
      return { ...current, extraIds: [...current.extraIds, id], extraNames: [...current.extraNames, name] };
    });
  }, []);

  const selectShape = useCallback((shapeId: string, shapeName: string) => {
    setState((current) => ({ ...current, shapeId, shapeName }));
  }, []);

  const selectDate = useCallback((date: string) => {
    setState((current) => ({ ...current, date }));
  }, []);

  const setFreeText = useCallback((freeText: string) => {
    setState((current) => ({ ...current, freeText: freeText.slice(0, 500) }));
  }, []);

  const setQuantity = useCallback((quantity: number) => {
    setState((current) => ({ ...current, quantity: Math.min(20, Math.max(1, quantity)) }));
  }, []);

  const setPrice = useCallback((priceCents: number, weightGrams: number) => {
    setState((current) => ({ ...current, priceCents, weightGrams }));
  }, []);

  const shiftMonth = useCallback((delta: number) => {
    setState((current) => {
      const month = new Date(current.month);
      month.setMonth(month.getMonth() + delta);
      return { ...current, month };
    });
  }, []);

  const next = useCallback(() => {
    setState((current) => goNext(current));
  }, []);

  const back = useCallback(() => {
    setState((current) => goBack(current));
  }, []);

  const restart = useCallback(() => {
    setState((current) => ({ ...createInitialState(), priceCents: current.priceCents, weightGrams: current.weightGrams }));
  }, []);

  const applyResume = useCallback((partial: Partial<BreadBuilderState>, notice?: string) => {
    setState((current) => ({
      ...current,
      ...partial,
      step: 0,
      finished: false,
      inclusionNotice: notice ?? current.inclusionNotice,
    }));
  }, []);

  return {
    state,
    earliest,
    selectMass,
    selectFlour,
    toggleIngredient,
    selectShape,
    selectDate,
    setFreeText,
    setQuantity,
    setPrice,
    shiftMonth,
    next,
    back,
    restart,
    applyResume,
    canFinish: canComplete(state),
    canAdvance: canAdvanceEssence(state),
    tip: bakerTip(state.extraIds.length),
    summary: summaryText(state),
    receipt: receiptLines(state),
  };
}
