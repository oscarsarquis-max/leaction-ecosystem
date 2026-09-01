/**
 * Catálogo central de linguagem de superfície.
 * Inglês não consagrado não aparece para a pessoa. Códigos públicos e auditoria recolhida seguem iguais.
 * Chaves permanecem no contrato persistido; só o texto exibido muda.
 */

export const SURFACE_PHRASES = {
  movementsImmutable:
    "Movimentações confirmadas não podem ser editadas. Para corrigir um lançamento, registre uma reversão.",
  priceRecordHint:
    "Simular não grava. Só a confirmação registra um novo preço. O anterior permanece no histórico e não pode ser editado.",
  priceRecordConfirm:
    "Será registrado um novo preço. O anterior permanece no histórico e não pode ser editado.",
  notesHistory:
    "Observações do histórico (mais recente primeiro). O que já foi registrado não se edita.",
  movementsGuideGoal: "Ler as movimentações confirmadas, sem editar o passado.",
  costingMemoryPurpose: "Ler composição, lacunas e memória de cálculo.",
  markupDerived:
    "Cada política tem uma entrada (fator de markup ou taxa de margem). A outra métrica é derivada pelo sistema com arredondamento comercial.",
} as const;

/** Tradução humana dos tokens pedidos no adendo. Valores persistidos não mudam. */
export const SURFACE_ENUM_LABEL: Record<string, string> = {
  "append-only": "não se edita o passado",
  active: "Ativo",
  inactive: "Inativo",
  missing: "Ausente",
  source: "Fonte",
  payload: "conteúdo",
  backend: "servidor",
  frontend: "tela",
  planned: "Planejada",
  released: "Liberada",
  ready: "Pronta",
  "in progress": "Em execução",
  in_progress: "Em execução",
  completed: "Concluída",
  blocked: "Bloqueada",
  morning: "Manhã",
  afternoon: "Tarde",
  night: "Noite",
};

export const FORBIDDEN_SURFACE_ENGLISH =
  /\b(append-only|append only|backend|frontend|payload|inactive|missing|planned|released|ready|completed|blocked|morning|afternoon|night|active|source)\b|\bin progress\b/i;

const CONTRACT_TOKEN = /^[a-z][a-z0-9_.-]*$/;

export function surfaceEnumLabel(value: string | null | undefined): string {
  if (!value) return "—";
  return SURFACE_ENUM_LABEL[value] ?? SURFACE_ENUM_LABEL[value.replaceAll("_", " ")] ?? value;
}

export function isContractToken(value: string): boolean {
  return CONTRACT_TOKEN.test(value) && !value.includes(" ");
}

export function assertSurfaceLanguage(surface: string, origin = "superfície"): void {
  const match = surface.match(FORBIDDEN_SURFACE_ENGLISH);
  if (match) {
    throw new Error(`${origin}: inglês não consagrado na superfície (“${match[0]}”).`);
  }
}
