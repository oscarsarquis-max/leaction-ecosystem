import type {
  GuidedAnswer,
  GuidedContext,
  GuidedQuestion,
} from "@/api/guidedTypes";

export type ShowWhenRule =
  | null
  | {
      all?: ShowWhenRule[];
      any?: ShowWhenRule[];
      answer?: string;
      context?: string;
      in?: unknown[];
      equals?: unknown;
      not_equals?: unknown;
      not_empty?: boolean;
    };

function isEmpty(value: unknown): boolean {
  if (value == null) return true;
  if (typeof value === "string") return value.trim().length === 0;
  if (Array.isArray(value)) return value.length === 0;
  if (typeof value === "object") return Object.keys(value as object).length === 0;
  return false;
}

function resolvePath(root: unknown, path: string): unknown {
  let cur: unknown = root;
  for (const part of path.split(".")) {
    if (cur == null || typeof cur !== "object") return undefined;
    cur = (cur as Record<string, unknown>)[part];
  }
  return cur;
}

function compareLeaf(
  rule: NonNullable<ShowWhenRule> & Record<string, unknown>,
  value: unknown,
): boolean {
  if ("not_empty" in rule) {
    const want = Boolean(rule.not_empty);
    const empty = isEmpty(value);
    return want ? !empty : empty;
  }
  if ("equals" in rule) return value === rule.equals;
  if ("not_equals" in rule) return value !== rule.not_equals;
  if (Array.isArray(rule.in)) return rule.in.includes(value);
  return true;
}

export function matchesShowWhen(
  showWhen: ShowWhenRule | Record<string, unknown> | null | undefined,
  answers: GuidedAnswer[],
  context?: GuidedContext | Record<string, unknown> | null,
): boolean {
  if (showWhen == null) return true;
  if (typeof showWhen !== "object") return true;

  const rule = showWhen as NonNullable<ShowWhenRule> & Record<string, unknown>;

  if (Array.isArray(rule.all)) {
    return rule.all.every((c) => matchesShowWhen(c, answers, context));
  }
  if (Array.isArray(rule.any)) {
    return rule.any.some((c) => matchesShowWhen(c, answers, context));
  }

  if (typeof rule.answer === "string") {
    const current = answers.find((a) => a.question_id === rule.answer)?.answer_value;
    return compareLeaf(rule, current ?? null);
  }

  if (typeof rule.context === "string") {
    return compareLeaf(rule, resolvePath(context ?? {}, rule.context));
  }

  return true;
}

export function visibleGuidedQuestions(
  questions: GuidedQuestion[],
  answers: GuidedAnswer[] | undefined,
  context?: GuidedContext | Record<string, unknown> | null,
): GuidedQuestion[] {
  return questions.filter((q) =>
    matchesShowWhen(q.show_when, answers ?? [], context),
  );
}

/** Major clause number from "4.1" → "4". */
export function clauseMajor(clauseRef: string): string {
  const m = /^(\d+)/.exec(clauseRef.trim());
  return m?.[1] ?? clauseRef;
}

export const CLAUSE_NAV_ORDER = ["4", "5", "6", "7", "8", "9", "10"] as const;

export const CLAUSE_PLAIN: Record<
  string,
  { shortLabel: string; explanation: string }
> = {
  "4": {
    shortLabel: "Compreender a organização",
    explanation:
      "Contexto, partes interessadas, escopo e processos — o mapa de como a empresa funciona.",
  },
  "5": {
    shortLabel: "Liderança e direção",
    explanation:
      "Como a gestão conduz a qualidade, o foco no cliente e as responsabilidades.",
  },
  "6": {
    shortLabel: "Planejar resultados",
    explanation:
      "Riscos, oportunidades, objetivos e mudanças com prioridades acompanháveis.",
  },
  "7": {
    shortLabel: "Criar capacidade para entregar",
    explanation:
      "Pessoas, recursos, comunicação, medição e informação que sustentam a execução.",
  },
  "8": {
    shortLabel: "Entregar ao cliente com controle",
    explanation:
      "Do requisito à entrega: planejamento, fornecedores, execução, liberação e não conformes.",
  },
  "9": {
    shortLabel: "Medir, analisar e decidir",
    explanation:
      "Indicadores, satisfação, avaliação interna e análise da direção.",
  },
  "10": {
    shortLabel: "Corrigir e melhorar",
    explanation:
      "Problemas, causas, eficácia das ações e melhoria contínua deliberada.",
  },
};

export type ClauseProgress = {
  major: string;
  shortLabel: string;
  explanation: string;
  applicable: number;
  answered: number;
  pending: number;
  pct: number;
};

export function clauseProgressList(
  visibleQuestions: GuidedQuestion[],
  answers: GuidedAnswer[] | undefined,
): ClauseProgress[] {
  const answeredIds = new Set(
    (answers ?? [])
      .filter((a) => a.answer_value != null)
      .map((a) => a.question_id),
  );

  return CLAUSE_NAV_ORDER.map((major) => {
    const qs = visibleQuestions.filter((q) => clauseMajor(q.clause_ref) === major);
    const applicable = qs.length;
    const answered = qs.filter((q) => answeredIds.has(q.id)).length;
    const pending = Math.max(applicable - answered, 0);
    const meta = CLAUSE_PLAIN[major]!;
    return {
      major,
      shortLabel: meta.shortLabel,
      explanation: meta.explanation,
      applicable,
      answered,
      pending,
      pct: applicable === 0 ? 100 : Math.round((answered / applicable) * 100),
    };
  });
}

export function groupQuestionsByClause(
  questions: GuidedQuestion[],
): { major: string; questions: GuidedQuestion[] }[] {
  const order: string[] = [];
  const map = new Map<string, GuidedQuestion[]>();
  for (const q of questions) {
    const major = clauseMajor(q.clause_ref);
    if (!map.has(major)) {
      map.set(major, []);
      order.push(major);
    }
    map.get(major)!.push(q);
  }
  return order.map((major) => ({ major, questions: map.get(major)! }));
}
