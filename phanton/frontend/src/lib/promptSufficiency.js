/**
 * Checagem de suficiência do pedido em linguagem natural — ANTES de gerar o Spec.
 * Critérios alinhados ao que a entrega final (HTML/doc/apresentação) precisa.
 */

const MIN_CHARS = 80

const CHECKS = [
  {
    id: 'length',
    label: 'Extensão mínima (~80 caracteres)',
    hint: 'Descreva o pedido com um parágrafo curto, não só um título.',
    test: (text) => text.trim().length >= MIN_CHARS,
  },
  {
    id: 'objective',
    label: 'O que construir (objetivo/produto)',
    hint: 'Ex.: plataforma, laboratório virtual, playbook, apresentação…',
    test: (text) =>
      /\b(construir|criar|desenvolver|montar|gerar|arquitetar|plataforma|sistema|app|aplica[cç][aã]o|laborat[oó]rio|playbook|produto|solu[cç][aã]o|ferramenta|portal|site)\b/i.test(
        text,
      ) || text.trim().split(/\s+/).length >= 18,
  },
  {
    id: 'audience',
    label: 'Para quem / contexto de uso',
    hint: 'Ex.: alunos, professores, gestores, coordenadores, líderes, corporativo…',
    test: (text) =>
      /\b(alunos?|professores?|escolas?|rede p[uú]blica|estudantes?|turmas?|gestores?|coordenadores?|l[ií]deres?|lideran[cç]a|corporativ[oa]s?|treinamentos?|comunidade|p[uú]blico|para\s+[oa]\s+\w+|destinado|voltad[oa]s?)\b/i.test(
        text,
      ),
  },
  {
    id: 'delivery',
    label: 'Formato da entrega final',
    hint: 'Ex.: HTML interativo, apresentação com slides, documento Markdown, protótipo…',
    test: (text) =>
      /\b(html|apresenta[cç][aã]o|slides?|pitch|deck|documento|relat[oó]rio|markdown|prot[oó]tipo|p[aá]gina|landing|interativ[oa]|pdf|playbook|roteiro)\b/i.test(
        text,
      ),
  },
  {
    id: 'constraints',
    label: 'Requisito ou restrição relevante',
    hint: 'Ex.: PBL, DUA, offline-first, acessibilidade, stack Python/React…',
    test: (text) =>
      /\b(pbl|dua|edu.?scrum|acessib|offline|conectividade|stack|python|react|requisito|deve|precisa|obrigat[oó]rio|restrit|metodolog|acessibilidade|w3c|wcag)\b/i.test(
        text,
      ),
  },
]

export const PROMPT_COMPOSITION_HINTS = [
  'Objetivo: o que deve ser construído',
  'Público e contexto de uso',
  'Formato da entrega (HTML, slides, documento…)',
  'Requisitos-chave (metodologia, stack, restrições)',
]

/**
 * @param {string} prompt
 * @returns {{ ok: boolean, passed: number, total: number, checks: Array<{id:string,label:string,hint:string,pass:boolean}> }}
 */
export function analyzePromptSufficiency(prompt = '') {
  const text = String(prompt || '')
  const checks = CHECKS.map((c) => ({
    id: c.id,
    label: c.label,
    hint: c.hint,
    pass: c.test(text),
  }))
  const passed = checks.filter((c) => c.pass).length
  // Suficiente: extensão + objetivo + formato da entrega (3 obrigatórios)
  // ou 4+ checks quaisquer incluindo length
  const must = ['length', 'objective', 'delivery']
  const mustOk = must.every((id) => checks.find((c) => c.id === id)?.pass)
  const ok = mustOk || (passed >= 4 && checks.find((c) => c.id === 'length')?.pass)
  return { ok: Boolean(ok), passed, total: checks.length, checks }
}

export function extractInitialPromptFromSpec(spec) {
  if (!spec || typeof spec !== 'object') return ''
  for (const key of ['user_prompt', 'pedido', 'description']) {
    const value = spec[key]
    if (typeof value === 'string' && value.trim()) return value.trim()
  }
  return ''
}
