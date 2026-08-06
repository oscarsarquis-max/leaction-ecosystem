import type { GuidedAnswer, GuidedQuestion } from "@/api/guidedTypes";

type ShowWhen =
  | null
  | {
      answer?: string;
      in?: string[];
      all?: ShowWhen[];
      any?: ShowWhen[];
    };

function matches(
  showWhen: ShowWhen | Record<string, unknown> | null | undefined,
  answers: GuidedAnswer[],
): boolean {
  if (showWhen == null) return true;
  if (typeof showWhen !== "object") return true;

  const rule = showWhen as ShowWhen & Record<string, unknown>;
  if (Array.isArray(rule.all)) {
    return rule.all.every((c) => matches(c, answers));
  }
  if (Array.isArray(rule.any)) {
    return rule.any.some((c) => matches(c, answers));
  }

  const qid = typeof rule.answer === "string" ? rule.answer : null;
  const allowed = Array.isArray(rule.in) ? rule.in : null;
  if (!qid || !allowed) return true;
  const current = answers.find((a) => a.question_id === qid)?.answer_value;
  return current != null && allowed.includes(current);
}

export function visibleGuidedQuestions(
  questions: GuidedQuestion[],
  answers: GuidedAnswer[] | undefined,
): GuidedQuestion[] {
  return questions.filter((q) => matches(q.show_when, answers ?? []));
}

/** Major clause number from "4.1" → "4". */
export function clauseMajor(clauseRef: string): string {
  const m = /^(\d+)/.exec(clauseRef.trim());
  return m?.[1] ?? clauseRef;
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
