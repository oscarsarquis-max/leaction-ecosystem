/**
 * Orientação determinística do mapa (R028-003).
 * Sem IA generativa obrigatória.
 */
import type { FiscalSummary, ProductSummary } from "../api/types";
import type { CriticalPathResult, FlowViewMode, ProductJourneyContext } from "./criticalPath";
import type { FlowSituation, FlowStepId } from "./steps";

export type ProductModalityFocus =
  | "unknown"
  | "purchased"
  | "produced"
  | "mixed"
  | "combo"
  | "intermediate";

export type OrientationInput = {
  organizationId: string | null;
  organizationName: string | null;
  establishmentId: string | null;
  profile: string;
  stepId: FlowStepId | null;
  stepTitle: string | null;
  situation: FlowSituation | null;
  pending: string | null;
  nextAction: string | null;
  permissions: string[];
  productModality: ProductModalityFocus;
  products: ProductSummary | null;
  fiscal: FiscalSummary | null;
  recipesTotal: number | null;
  ordersTotal: number | null;
  ingredientsTotal: number | null;
  inventoryItemsTotal: number | null;
  blocks: string[];
  alerts: string[];
  /** R028-003 */
  mode?: FlowViewMode;
  criticalPath?: CriticalPathResult | null;
  product?: ProductJourneyContext | null;
};

export type OrientationAction = {
  label: string;
  to: string;
  allowed: boolean;
};

export type OrientationResult = {
  youAreOn: string;
  purpose: string;
  statusLine: string;
  mainPending: string;
  recommended: OrientationAction | null;
  modalityNote: string | null;
  calculatorSlot: "hidden" | "reserved";
  scopeKey: string;
  pathStoppedAt: string | null;
  consequence: string | null;
};

const STEP_PURPOSE: Record<FlowStepId, string> = {
  1: "Registrar a mercadoria que chega, conferir e só então atualizar o estoque.",
  2: "Manter ingredientes e acompanhar lotes, posição e movimentações.",
  3: "Definir a identidade do que se vende, estoca ou produz.",
  4: "Versionar como a produção transforma ingredientes e preparos.",
  5: "Organizar planos e ordens do turno.",
  6: "Executar no chão de fábrica: pesar, consumir e concluir.",
  7: "Conferir conformidade e rotulagem do acabado.",
  8: "Acompanhar custeio, markup, margem e preço.",
};

function has(codes: string[], code: string): boolean {
  return codes.includes(code);
}

function hasAny(codes: string[], list: string[]): boolean {
  return list.some((code) => codes.includes(code));
}

export function inferModality(products: ProductSummary | null): ProductModalityFocus {
  if (!products) return "unknown";
  const purchased = products.purchased ?? 0;
  const intermediate = products.intermediate ?? 0;
  const producedGap = products.produced_without_recipe ?? 0;
  const producedish = Math.max(0, (products.total ?? 0) - purchased - intermediate);
  if (intermediate > 0 && purchased === 0 && producedish === 0) return "intermediate";
  if (purchased > 0 && producedish === 0 && producedGap === 0) return "purchased";
  if (purchased === 0 && (producedish > 0 || producedGap > 0)) return "produced";
  if (purchased > 0 && (producedish > 0 || producedGap > 0)) return "mixed";
  return "unknown";
}

export function modalityNoteFor(
  modality: ProductModalityFocus,
  stepId: FlowStepId | null,
): string | null {
  if (!stepId) return null;
  if (modality === "purchased" && (stepId === 4 || stepId === 5 || stepId === 6)) {
    return "O produto é comprado; receita e ordem de produção não se aplicam a este abastecimento.";
  }
  if (modality === "combo" && stepId === 4) {
    return "Combo virtual não deve ser tratado como receita; monte a partir dos produtos componentes.";
  }
  if (modality === "produced" && stepId === 4) {
    return "Produto produzido precisa de receita vigente antes do planejamento.";
  }
  if (modality === "mixed") {
    return "Produto misto: escolha explicitamente a origem comprada ou produzida em cada abastecimento.";
  }
  return null;
}

function primaryActionForBlocker(
  stepId: FlowStepId,
  permissions: string[],
  path: CriticalPathResult | null | undefined,
): OrientationAction | null {
  const codes = permissions;
  const step = path?.steps.find((row) => row.def.id === stepId);
  if (step && (!step.hasAccess || step.situation === "Sem acesso")) return null;

  if (stepId === 1 && hasAny(codes, ["fiscal.document.capture", "procurement.receive", "procurement.read", "fiscal.document.read"])) {
    const fiscal = path ? null : null;
    void fiscal;
    return { label: "Registrar entrada", to: "/gestao/compras/entradas", allowed: true };
  }
  if (stepId === 2 && hasAny(codes, ["ingredient.read", "inventory.read"])) {
    return { label: "Conferir ingredientes e estoque", to: "/componentes/estoque", allowed: true };
  }
  if (stepId === 3 && has(codes, "product.create")) {
    return { label: "Cadastrar produto", to: "/produtos/novo", allowed: true };
  }
  if (stepId === 3 && has(codes, "product.read")) {
    return { label: "Abrir produtos", to: "/produtos", allowed: true };
  }
  if (stepId === 4 && has(codes, "recipe.read")) {
    return { label: "Vincular receita", to: "/receitas", allowed: true };
  }
  if (stepId === 5 && hasAny(codes, ["production.plan.read", "production.order.read"])) {
    return {
      label: "Criar planejamento",
      to: "/planejamento",
      allowed: has(codes, "production.plan.read"),
    };
  }
  if (stepId === 6 && has(codes, "production.order.read")) {
    return { label: "Executar", to: "/ordens", allowed: true };
  }
  if (stepId === 7 && has(codes, "labeling.read")) {
    return { label: "Revisar rotulagem", to: "/conformidade", allowed: true };
  }
  if (stepId === 8 && hasAny(codes, ["costing.read", "pricing.review"])) {
    return { label: "Abrir formação do custo", to: "/gestao/custos/formacao", allowed: has(codes, "costing.read") };
  }
  return null;
}

export function buildOrientation(input: OrientationInput): OrientationResult {
  const path = input.criticalPath ?? null;
  const criticalId = path?.criticalPositionId ?? null;
  const focusId = input.stepId;
  const focusStep = path?.steps.find((row) => row.def.id === focusId) ?? null;
  const criticalStep = path?.steps.find((row) => row.def.id === criticalId) ?? null;

  const purpose = focusId ? STEP_PURPOSE[focusId] : "Escolher a próxima etapa do fluxo produtivo.";

  let youAreOn: string;
  if (criticalStep) {
    youAreOn = `Seu caminho está parado em ${criticalStep.def.title}.`;
  } else if (path) {
    youAreOn = "Não há bloqueio urgente no caminho visível agora.";
  } else if (focusId && input.stepTitle) {
    // Coach em rotas da jornada (sem mapa completo).
    youAreOn = `Você está na etapa ${focusId} — ${input.stepTitle}.`;
  } else {
    youAreOn = "Você está no fluxo produtivo.";
  }

  const statusLine = focusStep
    ? focusStep.isCriticalPosition
      ? `Posição real e consulta: ${focusStep.def.title} (${focusStep.situation}).`
      : `Em foco para consulta: ${focusStep.def.title} (${focusStep.situation}). Posição real: ${
          criticalStep ? criticalStep.def.title : "sem bloqueio"
        }.`
    : input.situation
      ? `Situação: ${input.situation}.`
      : "Situação ainda não determinada.";

  let mainPending =
    criticalStep?.pending
    || input.pending?.trim()
    || "Nenhuma pendência registrada nesta etapa.";
  if (input.blocks.length) mainPending = input.blocks[0]!;

  const recommended =
    (criticalId ? primaryActionForBlocker(criticalId, input.permissions, path) : null)
    || recommendAction(input);

  const modalityNote =
    path?.modalityNote
    || modalityNoteFor(input.productModality, focusId)
    || (path?.orgPreparationNote ?? null);

  const consequence = criticalStep
    ? `Enquanto ${criticalStep.def.title} não avançar, as etapas seguintes não desbloqueiam o caminho crítico — mesmo que alguma estrutura posterior já exista.`
    : null;

  return {
    youAreOn,
    purpose,
    statusLine,
    mainPending,
    recommended,
    modalityNote,
    calculatorSlot: focusId === 4 || focusId === 8 ? "reserved" : "hidden",
    scopeKey: `${input.organizationId ?? "none"}:${input.mode ?? "org"}:${input.product?.code ?? ""}:${focusId ?? "fluxo"}`,
    pathStoppedAt: criticalStep?.def.title ?? null,
    consequence,
  };
}

function recommendAction(input: OrientationInput): OrientationAction | null {
  const codes = input.permissions;
  const stepId = input.stepId;

  if (stepId === 1) {
    if (input.fiscal && input.fiscal.awaiting_match > 0 && hasAny(codes, ["fiscal.document.match", "procurement.receive"])) {
      return {
        label: "Associar item",
        to: "/gestao/compras/entradas?situacao=aguardando-correspondencia",
        allowed: true,
      };
    }
    if (input.fiscal && input.fiscal.awaiting_check > 0 && hasAny(codes, ["fiscal.document.check", "procurement.receive"])) {
      return {
        label: "Conferir recebimento",
        to: "/gestao/compras/entradas?situacao=aguardando-conferencia",
        allowed: true,
      };
    }
    if (hasAny(codes, ["fiscal.document.capture", "procurement.receive", "procurement.read"])) {
      return { label: "Registrar entrada", to: "/gestao/compras/entradas", allowed: true };
    }
  }

  if (stepId === 3 && has(codes, "product.read")) {
    return { label: "Abrir produtos", to: "/produtos", allowed: true };
  }

  if (stepId === 4) {
    if (input.productModality === "purchased") {
      return { label: "Seguir para acabamento", to: "/fluxo?etapa=7", allowed: true };
    }
    if (has(codes, "recipe.read")) {
      return { label: "Vincular receita", to: "/receitas", allowed: true };
    }
  }

  if (stepId === 5 && hasAny(codes, ["production.order.read", "production.plan.read"])) {
    return { label: "Abrir ordens", to: "/ordens", allowed: has(codes, "production.order.read") };
  }

  if (stepId === 6 && has(codes, "production.order.read")) {
    return { label: "Executar", to: "/ordens", allowed: true };
  }

  if (stepId === 7 && has(codes, "labeling.read")) {
    return { label: "Revisar rotulagem", to: "/conformidade", allowed: true };
  }

  if (stepId === 8) {
    if (!hasAny(codes, ["costing.read", "pricing.review", "pricing.simulation.manage"])) {
      return {
        label: "Continuar pelo acabamento",
        to: "/fluxo?etapa=7",
        allowed: has(codes, "labeling.read"),
      };
    }
    return { label: "Abrir formação do custo", to: "/gestao/custos/formacao", allowed: has(codes, "costing.read") };
  }

  return { label: "Voltar ao mapa", to: "/fluxo", allowed: true };
}
