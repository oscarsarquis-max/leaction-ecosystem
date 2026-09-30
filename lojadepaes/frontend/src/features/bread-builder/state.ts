export const BUILDER_RESUME_KEY = "lojadepaes_builder_resume";

export function writeBuilderResume(payload: Record<string, unknown>): void {
  sessionStorage.setItem(BUILDER_RESUME_KEY, JSON.stringify(payload));
}

export type WizardStep = 0 | 1 | 2 | 3;

export type BreadBuilderState = {
  step: WizardStep;
  massId: string;
  massName: string;
  flourId: string;
  flourName: string;
  extraIds: string[];
  extraNames: string[];
  shapeId: string;
  shapeName: string;
  freeText: string;
  quantity: number;
  date: string;
  finished: boolean;
  month: Date;
  priceCents: number;
  weightGrams: number;
  inclusionNotice: string;
};

export type CompatibleOption = {
  id: string;
  name: string;
  compatible_dough_ids?: string[];
};

export function earliestDate(from = new Date()): Date {
  const earliest = new Date(from);
  earliest.setDate(earliest.getDate() + 1);
  earliest.setHours(0, 0, 0, 0);
  return earliest;
}

export function earliestFromBusinessDate(iso: string): Date {
  const [year, month, day] = iso.split("-").map(Number);
  return earliestDate(new Date(year, month - 1, day));
}

export function dateKey(value: Date): string {
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
}

export function prettyDate(isoDate: string): string {
  if (!isoDate) return "";
  return new Date(`${isoDate}T12:00:00`).toLocaleDateString("pt-BR", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });
}

export function createInitialState(now = new Date()): BreadBuilderState {
  const earliest = earliestDate(now);
  return {
    step: 0,
    massId: "",
    massName: "",
    flourId: "",
    flourName: "",
    extraIds: [],
    extraNames: [],
    shapeId: "",
    shapeName: "",
    freeText: "",
    quantity: 1,
    date: "",
    finished: false,
    month: new Date(earliest.getFullYear(), earliest.getMonth(), 1),
    priceCents: 0,
    weightGrams: 500,
    inclusionNotice: "",
  };
}

export function canAdvanceEssence(state: Pick<BreadBuilderState, "massId" | "flourId">): boolean {
  return Boolean(state.massId && state.flourId);
}

export function canComplete(state: Pick<BreadBuilderState, "date" | "massId" | "shapeId" | "quantity">): boolean {
  return Boolean(state.date && state.massId && state.shapeId && state.quantity >= 1);
}

export function goNext(state: BreadBuilderState): BreadBuilderState {
  if (state.finished) return state;
  if (state.step < 3) {
    return { ...state, step: (state.step + 1) as WizardStep };
  }
  if (!canComplete(state)) return state;
  return { ...state, finished: true };
}

export function goBack(state: BreadBuilderState): BreadBuilderState {
  if (state.finished || state.step === 0) return state;
  return { ...state, step: (state.step - 1) as WizardStep };
}

export function toggleExtra(ids: string[], id: string): string[] {
  return ids.includes(id) ? ids.filter((item) => item !== id) : [...ids, id];
}

export function bakerTip(count: number): string {
  if (count > 2) {
    return "Muitos sabores na mesma massa? Experimente escolher dois para sentir cada ingrediente.";
  }
  return "Até dois ingredientes costumam criar uma combinação equilibrada.";
}

export function formatLoafPrice(cents: number, grams: number): string {
  if (cents <= 0) {
    return "Preço do pão personalizado pendente de configuração";
  }
  const amount = (cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  return `${grams} g · ${amount}`;
}

export function formatCommercialLine(cents: number, grams: number): string {
  if (cents <= 0) {
    return "Pão personalizado: preço pendente de configuração.";
  }
  const amount = (cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  return `Pão personalizado: ${grams} g · ${amount} por unidade.`;
}

export function inclusionWarning(massId: string, extras: CompatibleOption[]): string {
  const blocked = extras.filter(
    (item) =>
      Boolean(item.compatible_dough_ids?.length) && !item.compatible_dough_ids?.includes(massId),
  );
  if (!blocked.length) return "";
  const names = blocked.map((item) => item.name).join(", ");
  return `A inclusão ${names} ficou para avaliação com esta massa. A Loja confirma no aceite. Não removemos a sua escolha.`;
}

export function chosenIngredientIds(state: Pick<BreadBuilderState, "flourId" | "extraIds">): string[] {
  return [state.flourId, ...state.extraIds].filter(Boolean);
}

export function chosenIngredientNames(
  state: Pick<BreadBuilderState, "flourName" | "extraNames">,
): string[] {
  return [state.flourName, ...state.extraNames].filter(Boolean);
}

function baseLabel(state: Pick<BreadBuilderState, "massName" | "flourName">): string {
  return [state.flourName, state.massName].filter(Boolean).join(" · ") || "Farinha e preparo";
}

export function summaryText(state: BreadBuilderState): string {
  if (state.step === 0 && !state.finished) {
    if (!state.flourName && !state.massName) {
      return "Escolha a farinha e o preparo da massa.";
    }
    if (!state.flourName) return "Escolha a farinha.";
    if (!state.massName) return "Escolha a fermentação e o preparo.";
    return `${state.flourName} · ${state.massName}`;
  }
  const extras = [...state.extraNames];
  if (state.freeText.trim()) extras.push(state.freeText.trim());
  const extrasLabel = extras.length ? extras.join(", ") : "Sem inclusões";
  const parts = [`${baseLabel(state)} · ${extrasLabel}`];
  if (state.step >= 2 || state.finished) {
    parts[0] += state.shapeName ? ` · ${state.shapeName}` : "";
  }
  if (state.date) parts.push(prettyDate(state.date));
  if (state.quantity > 1 || state.finished) parts.push(`${state.quantity} pão(ões)`);
  if (state.priceCents > 0 && (state.step === 3 || state.finished)) {
    parts.push(formatLoafPrice(state.priceCents, state.weightGrams));
  }
  return parts.join(" · ");
}

export function receiptLines(state: BreadBuilderState): string[] {
  const extras = [...state.extraNames];
  if (state.freeText.trim()) extras.push(state.freeText.trim());
  return [
    baseLabel(state),
    extras.length ? extras.join(" + ") : "Sem inclusões",
    state.shapeName,
    `${prettyDate(state.date)} · ${state.quantity} × ${formatLoafPrice(state.priceCents, state.weightGrams)}`,
  ];
}

export function isDayDisabled(day: Date, earliest: Date): boolean {
  return day < earliest;
}

export function monthStartLocked(month: Date, earliest: Date): boolean {
  const firstAllowed = new Date(earliest.getFullYear(), earliest.getMonth(), 1);
  return month <= firstAllowed;
}
