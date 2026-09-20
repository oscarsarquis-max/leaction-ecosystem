import { useCallback, useMemo, useState } from "react";
import {
  bakerTip,
  canComplete,
  createInitialState,
  earliestDate,
  goBack,
  goNext,
  receiptLines,
  shapeTip,
  summaryText,
  toggleExtra,
  type BreadBuilderState,
} from "./state";

export function useBreadBuilder() {
  const [state, setState] = useState<BreadBuilderState>(() => createInitialState());
  const earliest = useMemo(() => earliestDate(), []);

  const selectMass = useCallback((massIndex: number) => {
    setState((current) => ({ ...current, massIndex }));
  }, []);

  const toggleIngredient = useCallback((name: string) => {
    setState((current) => ({ ...current, extras: toggleExtra(current.extras, name) }));
  }, []);

  const selectShape = useCallback((shapeIndex: number) => {
    setState((current) => ({ ...current, shapeIndex }));
  }, []);

  const selectDate = useCallback((date: string) => {
    setState((current) => ({ ...current, date }));
  }, []);

  const selectTime = useCallback((time: string) => {
    setState((current) => ({ ...current, time }));
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
    setState(createInitialState());
  }, []);

  return {
    state,
    earliest,
    selectMass,
    toggleIngredient,
    selectShape,
    selectDate,
    selectTime,
    shiftMonth,
    next,
    back,
    restart,
    canFinish: canComplete(state),
    tip: bakerTip(state.extras),
    formTip: shapeTip(state.shapeIndex),
    summary: summaryText(state),
    receipt: receiptLines(state),
  };
}
