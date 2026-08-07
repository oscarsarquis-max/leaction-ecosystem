/** Rótulos compreensíveis para gestor sem jargão ISO/técnico. */

const CLAUSE_PT: Record<string, string> = {
  "4": "Contexto da organização",
  "5": "Liderança",
  "6": "Planejamento",
  "7": "Apoio",
  "8": "Operação",
  "9": "Avaliação de desempenho",
  "10": "Melhoria",
};

/** "Requisito 4 — Context of the organization (ref)" → português legível. */
export function humanizeScopeLabel(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) return trimmed;
  const m = trimmed.match(/^Requisito\s+(\d+(?:\.\d+)*)/i);
  if (!m) return trimmed;
  const clause = m[1];
  const major = clause.split(".")[0] ?? clause;
  const title = CLAUSE_PT[major];
  return title ? `Cláusula ${clause} — ${title}` : `Cláusula ${clause}`;
}

export function isDemoOrTestQuestion(code: string, prompt: string): boolean {
  return (
    /^Q-TEST/i.test(code) ||
    /test interview prompt/i.test(prompt) ||
    /^TEST[-_]/i.test(code)
  );
}

/** Prompt para o gestor: sem código interno; evita inglês cru quando possível. */
export function humanizeQuestionPrompt(code: string, prompt: string): string {
  const text = prompt.trim();
  if (isDemoOrTestQuestion(code, text)) {
    return "Pergunta de verificação interna (ignore na demonstração)";
  }
  // Heurística: prompts ISO em inglês → orientação em PT
  if (/^[A-Za-z]/.test(text) && /\b(how|what|does|organization|management)\b/i.test(text)) {
    const m = code.match(/(\d+)/);
    const clauseHint = m ? ` (cláusula ${m[1]})` : "";
    return `Pergunte com suas palavras como isso funciona na empresa${clauseHint}.`;
  }
  return text;
}
