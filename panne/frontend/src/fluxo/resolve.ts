import type { FiscalSummary, ProductSummary } from "../api/types";
import { fiscalSummarySentence } from "../language/fiscal";
import { productsSummarySentence } from "../language/products";
import type { FlowSituation, FlowStepDef, FlowStepId } from "./steps";
import { FLOW_STEPS } from "./steps";

export type FlowEvidence = {
  ingredientsTotal: number | null;
  recipesTotal: number | null;
  ordersTotal: number | null;
  inventoryItemsTotal: number | null;
  products: ProductSummary | null;
  fiscal: FiscalSummary | null;
};

export type ResolvedFlowStep = {
  def: FlowStepDef;
  situation: FlowSituation;
  pending: string;
  nextAction: string;
  hasAccess: boolean;
  visible: boolean;
  inFocus: boolean;
};

function hasAny(hasPermission: (code: string) => boolean, codes: string[]): boolean {
  if (codes.length === 0) return true;
  return codes.some((code) => hasPermission(code));
}

export function canAccessCosting(hasPermission: (code: string) => boolean): boolean {
  return (
    hasPermission("costing.read")
    || hasPermission("pricing.review")
    || hasPermission("pricing.simulation.manage")
  );
}

export function resolveStepSituation(
  def: FlowStepDef,
  hasPermission: (code: string) => boolean,
  evidence: FlowEvidence,
  currentPathStep: FlowStepId | null,
): { situation: FlowSituation; pending: string; nextAction: string; hasAccess: boolean } {
  const access =
    def.id === 8 ? canAccessCosting(hasPermission) : hasAny(hasPermission, def.accessAnyOf);

  if (def.id === 8 && !access) {
    return {
      situation: "Não se aplica",
      pending: "Você não possui acesso aos custos; continue pelo acabamento.",
      nextAction: "Seguir para conformidade ou voltar ao fluxo.",
      hasAccess: false,
    };
  }

  if (!access) {
    return {
      situation: "Sem acesso",
      pending: "Seu perfil não inclui esta etapa.",
      nextAction: "Siga para uma etapa disponível no fluxo.",
      hasAccess: false,
    };
  }

  if (currentPathStep === def.id) {
    return {
      situation: "Em andamento",
      pending: "Você está nesta etapa agora.",
      nextAction: def.primary ? `Continuar em ${def.primary.label.replace(/^Abrir /i, "")}.` : "Revisar esta etapa.",
      hasAccess: true,
    };
  }

  // Evidências leves — sem inventar “concluído”.
  if (def.id === 1 && evidence.fiscal != null) {
    const attention = evidence.fiscal.awaiting_match
      + evidence.fiscal.awaiting_check
      + evidence.fiscal.divergent;
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
    };
  }
  if (def.id === 2 && evidence.ingredientsTotal != null && evidence.ingredientsTotal > 0) {
    return {
      situation: "Pronto",
      pending: `${evidence.ingredientsTotal} ingrediente(s) no cadastro.`,
      nextAction: "Revisar ingredientes ou conferir o estoque.",
      hasAccess: true,
    };
  }
  if (def.id === 3 && evidence.products != null) {
    return {
      situation: evidence.products.total > 0 ? "Pronto" : "Não iniciado",
      pending: productsSummarySentence(evidence.products),
      nextAction: "Abrir produtos, cadastrar um novo ou revisar as famílias.",
      hasAccess: true,
    };
  }
  if (def.id === 4) {
    const purchasedHeavy =
      evidence.products != null
      && evidence.products.purchased > 0
      && evidence.products.purchased >= (evidence.products.total - evidence.products.purchased);
    if (purchasedHeavy && (evidence.recipesTotal ?? 0) === 0) {
      return {
        situation: "Não se aplica",
        pending: "Cadastro focado em produtos comprados; receita não é obrigatória neste recorte.",
        nextAction: "Seguir para acabamento ou gestão conforme o produto.",
        hasAccess: true,
      };
    }
    if (evidence.products != null && evidence.products.produced_without_recipe > 0) {
      return {
        situation: "Requer atenção",
        pending: `${evidence.products.produced_without_recipe} produto(s) produzido(s) ainda sem receita vigente.`,
        nextAction: "Abrir receitas e vincular o produto produzido.",
        hasAccess: true,
      };
    }
    if (evidence.recipesTotal != null && evidence.recipesTotal > 0) {
      return {
        situation: "Pronto",
        pending: `${evidence.recipesTotal} receita(s) cadastrada(s).`,
        nextAction: "Abrir receitas ou seguir para planejamento.",
        hasAccess: true,
      };
    }
  }
  if (def.id === 5 && evidence.ordersTotal != null && evidence.ordersTotal > 0) {
    return {
      situation: "Pronto",
      pending: `${evidence.ordersTotal} ordem(ns) na listagem atual.`,
      nextAction: "Abrir ordens ou o quadro do turno.",
      hasAccess: true,
    };
  }
  if (def.id === 2 && evidence.inventoryItemsTotal != null && evidence.inventoryItemsTotal > 0) {
    return {
      situation: "Pronto",
      pending: `Estoque com ${evidence.inventoryItemsTotal} item(ns).`,
      nextAction: "Conferir posição e lotes.",
      hasAccess: true,
    };
  }
  if (def.id === 7 && def.structureNote) {
    return {
      situation: "Pronto",
      pending: def.structureNote,
      nextAction: "Abrir conformidade e rotulagem.",
      hasAccess: true,
    };
  }

  return {
    situation: "Não iniciado",
    pending: "Ainda sem evidência carregada para esta etapa.",
    nextAction: def.primary ? def.primary.label : "Seguir para a próxima etapa.",
    hasAccess: true,
  };
}

export function resolveVisibleSteps(
  hasPermission: (code: string) => boolean,
  evidence: FlowEvidence,
  focus: Set<FlowStepId>,
  currentPathStep: FlowStepId | null,
): ResolvedFlowStep[] {
  return FLOW_STEPS.map((def) => {
    const resolved = resolveStepSituation(def, hasPermission, evidence, currentPathStep);
    const hide = def.hideWithoutAccess && !resolved.hasAccess;
    return {
      def,
      ...resolved,
      visible: !hide,
      inFocus: focus.has(def.id),
    };
  }).filter((row) => row.visible);
}

export function neighborSteps(
  visible: ResolvedFlowStep[],
  current: FlowStepId,
): { prev: FlowStepId | null; next: FlowStepId | null } {
  const ids = visible.map((row) => row.def.id);
  const index = ids.indexOf(current);
  if (index < 0) return { prev: null, next: ids[0] ?? null };
  return {
    prev: index > 0 ? ids[index - 1]! : null,
    next: index < ids.length - 1 ? ids[index + 1]! : null,
  };
}
