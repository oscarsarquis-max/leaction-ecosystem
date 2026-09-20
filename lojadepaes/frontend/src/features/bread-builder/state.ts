import { FORMS, MASSES } from "./catalog";

export type WizardStep = 0 | 1 | 2 | 3;

export type BreadBuilderState = {
  step: WizardStep;
  massIndex: number;
  extras: string[];
  shapeIndex: number;
  date: string;
  time: string;
  finished: boolean;
  month: Date;
};

export function earliestDate(from = new Date()): Date {
  const earliest = new Date(from);
  earliest.setDate(earliest.getDate() + 2);
  earliest.setHours(0, 0, 0, 0);
  return earliest;
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
    massIndex: 0,
    extras: [],
    shapeIndex: 0,
    date: "",
    time: "",
    finished: false,
    month: new Date(earliest.getFullYear(), earliest.getMonth(), 1),
  };
}

export function canComplete(state: Pick<BreadBuilderState, "date" | "time">): boolean {
  return Boolean(state.date && state.time);
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

export function toggleExtra(extras: string[], name: string): string[] {
  return extras.includes(name) ? extras.filter((item) => item !== name) : [...extras, name];
}

export function bakerTip(extras: string[]): string {
  if (extras.includes("Alecrim") && extras.includes("Damasco")) {
    return "O alecrim tem aroma intenso. Use pouco para deixar a doçura do damasco aparecer.";
  }
  if (extras.length > 2) {
    return "Muitos sabores na mesma massa? Experimente escolher dois para sentir cada ingrediente.";
  }
  if (extras.includes("Nozes")) {
    return "Nozes e damasco fazem uma dupla de textura e doçura.";
  }
  if (extras.includes("Alecrim")) {
    return "Alecrim e azeitonas combinam com uma fatia ainda morna.";
  }
  return "Até dois ingredientes costumam criar uma combinação equilibrada.";
}

export function shapeTip(shapeIndex: number): string {
  return shapeIndex === 0
    ? "O cesto dá apoio à massa e deixa as espirais de farinha na crosta. Um pão para compartilhar no centro da mesa."
    : "A forma sustenta o crescimento da massa. O resultado são fatias práticas para torradas e sanduíches.";
}

export function summaryText(state: BreadBuilderState): string {
  if (state.step === 0 && !state.finished) {
    return "Farinha, água, sal e um levain cheio de vida.";
  }
  const extrasLabel = state.extras.length ? state.extras.join(", ") : "Sem inclusões";
  const parts = [`${MASSES[state.massIndex].title} · ${extrasLabel}`];
  if (state.step >= 2 || state.finished) {
    parts[0] += ` · ${FORMS[state.shapeIndex].title}`;
  }
  if (state.date) parts.push(prettyDate(state.date));
  if (state.time) parts.push(state.time);
  return parts.join(" · ");
}

export function receiptLines(state: BreadBuilderState): string[] {
  return [
    MASSES[state.massIndex].title,
    state.extras.length ? state.extras.join(" + ") : "Sem inclusões",
    FORMS[state.shapeIndex].title,
    `${prettyDate(state.date)} · ${state.time}`,
  ];
}

export function isDayDisabled(day: Date, earliest: Date): boolean {
  return day < earliest;
}

export function monthStartLocked(month: Date, earliest: Date): boolean {
  const firstAllowed = new Date(earliest.getFullYear(), earliest.getMonth(), 1);
  return month <= firstAllowed;
}