/**
 * Caminho crítico do fluxo — R028-003.
 * Distingue etapa em foco (consulta) da posição real (primeiro bloqueio aplicável).
 */
import type { ProductCard } from "../api/types";
import { fiscalSummarySentence } from "../language/fiscal";
import { productsSummarySentence } from "../language/products";
import { canAccessCosting, type FlowEvidence, type ResolvedFlowStep } from "./resolve";
import type { FlowSituation, FlowStepDef, FlowStepId } from "./steps";
import { FLOW_STEPS } from "./steps";

export type FlowViewMode = "org" | "product";

export type ProductJourneyContext = {
  code: string;
  displayName: string;
  supplyMode: string;
  purpose: string;
  hasPublishedRecipe: boolean;
  recipesCount: number;
  ordersCount: number;
  /** Origem explícita quando supply_mode=mixed. */
  mixedOrigin: "purchased" | "produced" | null;
};

/** Estado estrutural (sem “Você está aqui”). */
export type StructuralSituation = Exclude<FlowSituation, "Em andamento"> | FlowSituation;

export type MapStepView = {
  def: FlowStepDef;
  /** Estado estrutural / de preparação. */
  situation: FlowSituation;
  /** Rótulo principal no mapa (pode ser “Você está aqui”). */
  mapLabel: string;
  pending: string;
  nextAction: string;
  hasAccess: boolean;
  applicable: boolean;
  isCriticalPosition: boolean;
  isFocus: boolean;
  profileEmphasis: boolean;
};

export type CriticalPathResult = {
  mode: FlowViewMode;
  steps: MapStepView[];
  focusId: FlowStepId;
  criticalPositionId: FlowStepId | null;
  readyTitles: string[];
  blockingTitle: string | null;
  blockingPending: string | null;
  notApplicableTitles: string[];
  limitations: string[];
  orgPreparationNote: string | null;
  modalityNote: string | null;
};

function hasAny(hasPermission: (code: string) => boolean, codes: string[]): boolean {
  if (codes.length === 0) return true;
  return codes.some((code) => hasPermission(code));
}

export function effectiveSupplyMode(product: ProductJourneyContext): string {
  if (product.supplyMode === "mixed") {
    return product.mixedOrigin ?? "mixed";
  }
  return product.supplyMode;
}

function accessFor(
  def: FlowStepDef,
  hasPermission: (code: string) => boolean,
): { hasAccess: boolean; hide: boolean } {
  const access =
    def.id === 8 ? canAccessCosting(hasPermission) : hasAny(hasPermission, def.accessAnyOf);
  return { hasAccess: access, hide: def.hideWithoutAccess && !access };
}

/** Aplicabilidade da etapa na jornada do produto. */
export function stepApplicableForProduct(
  stepId: FlowStepId,
  product: ProductJourneyContext,
): { applicable: boolean; reason: string | null } {
  const mode = effectiveSupplyMode(product);

  if (mode === "mixed") {
    if (stepId === 4 || stepId === 5 || stepId === 6) {
      return {
        applicable: true,
        reason: "Requer decisão — informe a origem deste abastecimento (comprado ou produzido).",
      };
    }
  }

  if (mode === "purchased") {
    if (stepId === 4 || stepId === 5 || stepId === 6) {
      return {
        applicable: false,
        reason: "Não se aplica — produto comprado.",
      };
    }
  }

  if (mode === "combo") {
    if (stepId === 4) {
      return {
        applicable: false,
        reason: "Não se aplica — combo virtual não é tratado como receita.",
      };
    }
    if (stepId === 5 || stepId === 6) {
      return {
        applicable: false,
        reason: "Não se aplica — combo usa disponibilidade/separação dos componentes, não ordem de produção.",
      };
    }
  }

  if (mode === "intermediate" && stepId === 7) {
    return {
      applicable: false,
      reason: "Não se aplica diretamente à vitrine — preparo intermediário costuma alimentar outra receita.",
    };
  }

  if (mode === "mixed" || mode === "combo") {
    // Modalidades ainda parciais no produto.
    if (stepId === 6 && mode === "combo") {
      return { applicable: false, reason: "Modalidade combo ainda em preparação nesta fase." };
    }
  }

  return { applicable: true, reason: null };
}

function resolveOrgStep(
  def: FlowStepDef,
  hasPermission: (code: string) => boolean,
  evidence: FlowEvidence,
): { situation: FlowSituation; pending: string; nextAction: string; hasAccess: boolean; applicable: boolean } {
  const { hasAccess, hide } = accessFor(def, hasPermission);
  if (hide) {
    return {
      situation: "Sem acesso",
      pending: "Etapa oculta sem permissão de custos.",
      nextAction: "Continuar pelas etapas disponíveis.",
      hasAccess: false,
      applicable: false,
    };
  }
  if (!hasAccess) {
    return {
      situation: "Sem acesso",
      pending: "Seu perfil não inclui esta etapa.",
      nextAction: "Siga para uma etapa disponível no fluxo.",
      hasAccess: false,
      applicable: true,
    };
  }

  if (def.id === 1 && evidence.fiscal != null) {
    const attention =
      evidence.fiscal.awaiting_match + evidence.fiscal.awaiting_check + evidence.fiscal.divergent;
    return {
      situation: attention > 0 ? "Requer atenção" : evidence.fiscal.total > 0 ? "Pronto" : "Não iniciado",
      pending: fiscalSummarySentence(evidence.fiscal),
      nextAction:
        attention > 0
          ? "Abrir as entradas pendentes e concluir a conferência."
          : evidence.fiscal.total === 0
            ? "Registrar a primeira entrada de mercadoria."
            : "Registrar a próxima entrada de mercadoria.",
      hasAccess: true,
      applicable: true,
    };
  }

  if (def.id === 2) {
    if ((evidence.ingredientsTotal ?? 0) > 0 || (evidence.inventoryItemsTotal ?? 0) > 0) {
      const parts: string[] = [];
      if (evidence.ingredientsTotal != null) parts.push(`${evidence.ingredientsTotal} ingrediente(s)`);
      if (evidence.inventoryItemsTotal != null) parts.push(`${evidence.inventoryItemsTotal} item(ns) de estoque`);
      return {
        situation: "Pronto",
        pending: `Estrutura disponível: ${parts.join(" · ")}.`,
        nextAction: "Revisar ingredientes ou conferir o estoque.",
        hasAccess: true,
        applicable: true,
      };
    }
    return {
      situation: "Não iniciado",
      pending: "Ainda sem evidência de ingredientes ou estoque nesta organização.",
      nextAction: "Cadastrar ingredientes ou conferir o estoque.",
      hasAccess: true,
      applicable: true,
    };
  }

  if (def.id === 3 && evidence.products != null) {
    return {
      situation: evidence.products.total > 0 ? "Pronto" : "Não iniciado",
      pending: productsSummarySentence(evidence.products),
      nextAction: "Abrir produtos, cadastrar um novo ou revisar as famílias.",
      hasAccess: true,
      applicable: true,
    };
  }

  if (def.id === 4) {
    if (evidence.products != null && evidence.products.produced_without_recipe > 0) {
      return {
        situation: "Requer atenção",
        pending: `${evidence.products.produced_without_recipe} produto(s) produzido(s) ainda sem receita vigente.`,
        nextAction: "Abrir receitas e vincular o produto produzido.",
        hasAccess: true,
        applicable: true,
      };
    }
    if ((evidence.recipesTotal ?? 0) > 0) {
      return {
        situation: "Pronto",
        pending: `Estrutura disponível: ${evidence.recipesTotal} receita(s) cadastrada(s).`,
        nextAction: "Abrir receitas ou seguir para planejamento.",
        hasAccess: true,
        applicable: true,
      };
    }
    return {
      situation: "Não iniciado",
      pending: "Ainda sem evidência de receitas nesta organização.",
      nextAction: "Abrir receitas.",
      hasAccess: true,
      applicable: true,
    };
  }

  if (def.id === 5) {
    if ((evidence.ordersTotal ?? 0) > 0) {
      return {
        situation: "Pronto",
        pending: `Estrutura disponível: ${evidence.ordersTotal} ordem(ns) na listagem.`,
        nextAction: "Abrir ordens ou o quadro do turno.",
        hasAccess: true,
        applicable: true,
      };
    }
    return {
      situation: "Não iniciado",
      pending: "Ainda sem planejamento/ordens evidentes nesta organização.",
      nextAction: "Criar planejamento ou abrir ordens.",
      hasAccess: true,
      applicable: true,
    };
  }

  if (def.id === 6) {
    if ((evidence.ordersTotal ?? 0) > 0) {
      return {
        situation: "Pronto",
        pending: "Há ordens na organização — a execução depende da ordem escolhida.",
        nextAction: "Escolher ordem para executar.",
        hasAccess: true,
        applicable: true,
      };
    }
    return {
      situation: "Não iniciado",
      pending: "Sem ordens para executar nesta visão geral.",
      nextAction: "Criar planejamento/ordem antes da execução.",
      hasAccess: true,
      applicable: true,
    };
  }

  if (def.id === 7) {
    return {
      situation: "Pronto",
      pending: def.structureNote || "Conformidade e rotulagem disponíveis para consulta.",
      nextAction: "Abrir conformidade e rotulagem.",
      hasAccess: true,
      applicable: true,
    };
  }

  if (def.id === 8) {
    return {
      situation: "Não iniciado",
      pending: "Custos e preços dependem do produto e dos movimentos realizados.",
      nextAction: "Abrir custos e preços.",
      hasAccess: true,
      applicable: true,
    };
  }

  return {
    situation: "Não iniciado",
    pending: "Ainda sem evidência carregada para esta etapa.",
    nextAction: def.primary?.label ?? "Seguir para a próxima etapa.",
    hasAccess: true,
    applicable: true,
  };
}

function resolveProductStep(
  def: FlowStepDef,
  hasPermission: (code: string) => boolean,
  evidence: FlowEvidence,
  product: ProductJourneyContext,
): { situation: FlowSituation; pending: string; nextAction: string; hasAccess: boolean; applicable: boolean } {
  const { hasAccess, hide } = accessFor(def, hasPermission);
  if (hide) {
    return {
      situation: "Sem acesso",
      pending: "Etapa oculta sem permissão de custos.",
      nextAction: "Continuar pelas etapas disponíveis.",
      hasAccess: false,
      applicable: false,
    };
  }
  if (!hasAccess) {
    return {
      situation: "Sem acesso",
      pending: "Seu perfil não inclui esta etapa.",
      nextAction: "Siga para uma etapa disponível.",
      hasAccess: false,
      applicable: true,
    };
  }

  const appl = stepApplicableForProduct(def.id, product);
  if (!appl.applicable) {
    return {
      situation: "Não se aplica",
      pending: appl.reason ?? "Não se aplica a este produto.",
      nextAction: "Seguir para a próxima etapa aplicável.",
      hasAccess: true,
      applicable: false,
    };
  }

  const mode = effectiveSupplyMode(product);

  if (mode === "mixed" && (def.id === 4 || def.id === 5 || def.id === 6)) {
    return {
      situation: "Requer atenção",
      pending: "Requer decisão — informe a origem deste abastecimento (comprado ou produzido).",
      nextAction: "Escolher origem comprada ou produzida para continuar.",
      hasAccess: true,
      applicable: true,
    };
  }

  if (def.id === 1) {
    if (evidence.fiscal != null) {
      const attention =
        evidence.fiscal.awaiting_match + evidence.fiscal.awaiting_check + evidence.fiscal.divergent;
      if (attention > 0) {
        return {
          situation: "Requer atenção",
          pending: fiscalSummarySentence(evidence.fiscal),
          nextAction: "Abrir as entradas pendentes e concluir a conferência.",
          hasAccess: true,
          applicable: true,
        };
      }
      if (evidence.fiscal.total === 0) {
        if ((evidence.inventoryItemsTotal ?? 0) > 0 || (evidence.ingredientsTotal ?? 0) > 0) {
          return {
            situation: "Pronto",
            pending:
              "Sem documento fiscal nesta organização; há ingredientes/estoque disponíveis para o abastecimento neste recorte.",
            nextAction: "Seguir no caminho do produto ou registrar entrada quando houver documento.",
            hasAccess: true,
            applicable: true,
          };
        }
        return {
          situation: "Não iniciado",
          pending: "Nenhuma entrada de mercadoria foi registrada ainda.",
          nextAction: "Registrar a primeira entrada de mercadoria.",
          hasAccess: true,
          applicable: true,
        };
      }
      return {
        situation: "Pronto",
        pending: fiscalSummarySentence(evidence.fiscal),
        nextAction: "Consultar entradas ou seguir no caminho do produto.",
        hasAccess: true,
        applicable: true,
      };
    }
    return {
      situation: "Não iniciado",
      pending: "Nenhuma entrada de mercadoria foi registrada ainda.",
      nextAction: "Registrar entrada.",
      hasAccess: true,
      applicable: true,
    };
  }

  if (def.id === 2) {
    if ((evidence.ingredientsTotal ?? 0) > 0 || (evidence.inventoryItemsTotal ?? 0) > 0) {
      return {
        situation: "Pronto",
        pending: "Ingredientes/estoque disponíveis para este contexto.",
        nextAction: "Conferir estoque relacionado ao produto.",
        hasAccess: true,
        applicable: true,
      };
    }
    return {
      situation: "Não iniciado",
      pending: "Ainda sem evidência de estoque/ingredientes.",
      nextAction: "Conferir ingredientes e estoque.",
      hasAccess: true,
      applicable: true,
    };
  }

  if (def.id === 3) {
    return {
      situation: "Pronto",
      pending: `Produto ${product.code} — ${product.displayName} (${product.supplyMode}).`,
      nextAction: "Revisar o cadastro do produto.",
      hasAccess: true,
      applicable: true,
    };
  }

  if (def.id === 4) {
    if (mode === "produced" || mode === "intermediate") {
      if (!product.hasPublishedRecipe) {
        return {
          situation: "Requer atenção",
          pending: "Produto produzido sem receita vigente.",
          nextAction: "Vincular receita.",
          hasAccess: true,
          applicable: true,
        };
      }
      return {
        situation: "Pronto",
        pending: "Receita vigente vinculada a este produto.",
        nextAction: "Abrir receitas ou seguir para planejamento.",
        hasAccess: true,
        applicable: true,
      };
    }
  }

  if (def.id === 5) {
    if (product.ordersCount > 0) {
      return {
        situation: "Pronto",
        pending: `Há ${product.ordersCount} ordem(ns) ligada(s) a este produto.`,
        nextAction: "Abrir ordens ou o quadro.",
        hasAccess: true,
        applicable: true,
      };
    }
    return {
      situation: "Não iniciado",
      pending: "Receita pronta sem planejamento/ordem para este produto.",
      nextAction: "Criar planejamento.",
      hasAccess: true,
      applicable: true,
    };
  }

  if (def.id === 6) {
    if (product.ordersCount > 0) {
      return {
        situation: "Requer atenção",
        pending: "Ordem liberada — execute o preparo.",
        nextAction: "Executar.",
        hasAccess: true,
        applicable: true,
      };
    }
    return {
      situation: "Não iniciado",
      pending: "Sem ordem liberada para execução deste produto.",
      nextAction: "Abrir ordem.",
      hasAccess: true,
      applicable: true,
    };
  }

  if (def.id === 7) {
    return {
      situation: "Não iniciado",
      pending: "Rotulagem/acabamento ainda não confirmados para este produto nesta visão.",
      nextAction: "Revisar rotulagem.",
      hasAccess: true,
      applicable: true,
    };
  }

  if (def.id === 8) {
    return {
      situation: "Não iniciado",
      pending: "Custo/preço ainda não fechados para este produto nesta visão.",
      nextAction: "Calcular custo/preço.",
      hasAccess: true,
      applicable: true,
    };
  }

  return {
    situation: "Não iniciado",
    pending: "Ainda sem evidência para esta etapa neste produto.",
    nextAction: def.primary?.label ?? "Seguir.",
    hasAccess: true,
    applicable: true,
  };
}

/** Primeira etapa aplicável que ainda impede o avanço. */
export function findCriticalPosition(
  steps: Array<{ id: FlowStepId; situation: FlowSituation; applicable: boolean; hasAccess: boolean }>,
): FlowStepId | null {
  for (const step of steps) {
    if (!step.applicable || !step.hasAccess) continue;
    if (step.situation === "Não se aplica" || step.situation === "Sem acesso") continue;
    if (step.situation === "Pronto") continue;
    return step.id;
  }
  return null;
}

export function buildCriticalPath(input: {
  mode: FlowViewMode;
  evidence: FlowEvidence;
  hasPermission: (code: string) => boolean;
  focusId: FlowStepId;
  profileFocus: Set<FlowStepId>;
  product: ProductJourneyContext | null;
}): CriticalPathResult {
  const raw = FLOW_STEPS.map((def) => {
    const resolved =
      input.mode === "product" && input.product
        ? resolveProductStep(def, input.hasPermission, input.evidence, input.product)
        : resolveOrgStep(def, input.hasPermission, input.evidence);
    return { def, ...resolved };
  }).filter((row) => !(row.def.hideWithoutAccess && !row.hasAccess));

  const criticalPositionId = findCriticalPosition(
    raw.map((row) => ({
      id: row.def.id,
      situation: row.situation,
      applicable: row.applicable,
      hasAccess: row.hasAccess,
    })),
  );

  const focusId = raw.some((row) => row.def.id === input.focusId)
    ? input.focusId
    : (raw[0]?.def.id ?? 1);

  const steps: MapStepView[] = raw.map((row) => {
    const isCritical = criticalPositionId === row.def.id;
    return {
      def: row.def,
      situation: row.situation,
      mapLabel: isCritical ? "Você está aqui" : row.situation,
      pending: row.pending,
      nextAction: row.nextAction,
      hasAccess: row.hasAccess,
      applicable: row.applicable,
      isCriticalPosition: isCritical,
      isFocus: row.def.id === focusId,
      profileEmphasis: input.profileFocus.has(row.def.id),
    };
  });

  const readyTitles = steps
    .filter((s) => s.situation === "Pronto" && s.applicable)
    .map((s) => s.def.title);
  const notApplicableTitles = steps
    .filter((s) => s.situation === "Não se aplica" || !s.applicable)
    .map((s) => s.def.title);
  const blocker = steps.find((s) => s.isCriticalPosition) ?? null;

  const limitations: string[] = [];
  if (input.mode === "org") {
    limitations.push(
      "Etapas “Prontas” aqui significam preparação da organização, não um único produto pronto para o balcão.",
    );
  }
  if (input.product?.supplyMode === "mixed" && !input.product.mixedOrigin) {
    limitations.push("Produto misto: a origem do abastecimento ainda não foi informada.");
  }
  if (input.product?.supplyMode === "combo" || input.product?.supplyMode === "mixed") {
    limitations.push("Combos e mistos seguem o estado real do recorte — parte da operação ainda está em preparação.");
  }
  const step7 = FLOW_STEPS.find((s) => s.id === 7);
  if (step7?.structureNote) limitations.push(step7.structureNote);

  let modalityNote: string | null = null;
  if (input.product) {
    const mode = effectiveSupplyMode(input.product);
    if (mode === "purchased") {
      modalityNote = "Jornada de produto comprado: receita, planejamento e execução não se aplicam.";
    } else if (mode === "produced") {
      modalityNote = "Jornada de produto produzido: exige receita vigente antes do planejamento.";
    } else if (mode === "intermediate") {
      modalityNote = "Preparo intermediário: pode alimentar outra receita em vez de ir à vitrine.";
    } else if (mode === "combo") {
      modalityNote = "Combo virtual: componentes e disponibilidade — não trate como receita.";
    } else if (mode === "mixed") {
      modalityNote = "Produto misto: escolha a origem comprada ou produzida para calcular o caminho.";
    }
  }

  return {
    mode: input.mode,
    steps,
    focusId,
    criticalPositionId,
    readyTitles,
    blockingTitle: blocker?.def.title ?? null,
    blockingPending: blocker?.pending ?? null,
    notApplicableTitles,
    limitations,
    orgPreparationNote:
      input.mode === "org"
        ? "Esta visão indica a preparação geral da organização. Escolha um produto para acompanhar uma jornada específica."
        : null,
    modalityNote,
  };
}

export function productJourneyFromCard(
  card: ProductCard,
  mixedOrigin: "purchased" | "produced" | null = null,
): ProductJourneyContext {
  return {
    code: card.code,
    displayName: card.display_name,
    supplyMode: card.supply_mode,
    purpose: card.purpose,
    hasPublishedRecipe: Boolean(card.has_published_recipe),
    recipesCount: card.links?.recipes_count ?? (card.has_published_recipe ? 1 : 0),
    ordersCount: card.links?.orders_count ?? 0,
    mixedOrigin: card.supply_mode === "mixed" ? mixedOrigin : null,
  };
}

/** Compat: resolveVisibleSteps antigo ainda usado por testes/coach — mapeia path step só como ênfase. */
export function toResolvedFlowSteps(path: CriticalPathResult): ResolvedFlowStep[] {
  return path.steps.map((row) => ({
    def: row.def,
    situation: row.situation,
    pending: row.pending,
    nextAction: row.nextAction,
    hasAccess: row.hasAccess,
    visible: true,
    inFocus: row.profileEmphasis,
  }));
}
