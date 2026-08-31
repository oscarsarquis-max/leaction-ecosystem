/**
 * Contrato de orientação determinística do fluxo (CURSOR adendo Gigio).
 * Preparado para futura complementação por IA; a navegação não depende dela.
 */
import type { FiscalSummary, ProductSummary } from "../api/types";
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
  /** Bloqueios explícitos já conhecidos pela tela. */
  blocks: string[];
  /** Alertas não bloqueantes. */
  alerts: string[];
};

export type OrientationAction = {
  label: string;
  to: string;
  /** Só true quando a ação existe e o perfil pode executar. */
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
  /** Chave estável para limpar orientação ao trocar de org. */
  scopeKey: string;
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

export function buildOrientation(input: OrientationInput): OrientationResult {
  const stepId = input.stepId;
  const purpose = stepId ? STEP_PURPOSE[stepId] : "Escolher a próxima etapa do fluxo produtivo.";
  const youAreOn = stepId && input.stepTitle
    ? `Você está na etapa ${stepId} — ${input.stepTitle}.`
    : "Você está no fluxo produtivo.";

  const statusLine = input.situation
    ? `Situação: ${input.situation}.`
    : "Situação ainda não determinada.";

  let mainPending = input.pending?.trim() || "Nenhuma pendência registrada nesta etapa.";
  if (input.blocks.length) {
    mainPending = input.blocks[0]!;
  } else if (input.fiscal && stepId === 1) {
    const awaiting =
      input.fiscal.awaiting_match + input.fiscal.awaiting_check + input.fiscal.divergent;
    if (input.fiscal.awaiting_match > 0) {
      mainPending = `Há item(ns) da nota ainda sem correspondência (${input.fiscal.awaiting_match}).`;
    } else if (input.fiscal.awaiting_check > 0) {
      mainPending = `Há documento(s) aguardando conferência física (${input.fiscal.awaiting_check}).`;
    } else if (input.fiscal.divergent > 0) {
      mainPending = `Há divergência(s) a resolver na entrada (${input.fiscal.divergent}).`;
    } else if (awaiting === 0 && input.fiscal.total > 0) {
      mainPending = "Entradas registradas; nada urgente na conferência agora.";
    }
  } else if (input.productModality === "produced" && stepId === 4 && (input.recipesTotal ?? 0) === 0) {
    mainPending = "Este produto produzido ainda não possui receita vigente.";
  }

  const recommended = recommendAction(input);
  const modalityNote = modalityNoteFor(input.productModality, stepId);

  return {
    youAreOn,
    purpose,
    statusLine,
    mainPending,
    recommended,
    modalityNote,
    calculatorSlot:
      stepId === 4 || stepId === 8 ? "reserved" : "hidden",
    scopeKey: `${input.organizationId ?? "none"}:${stepId ?? "fluxo"}`,
  };
}

function recommendAction(input: OrientationInput): OrientationAction | null {
  const codes = input.permissions;
  const stepId = input.stepId;

  if (stepId === 1) {
    if (input.fiscal && input.fiscal.awaiting_match > 0 && hasAny(codes, ["fiscal.document.match", "procurement.receive"])) {
      return {
        label: "Abrir entradas aguardando correspondência",
        to: "/gestao/compras/entradas?situacao=aguardando-correspondencia",
        allowed: true,
      };
    }
    if (input.fiscal && input.fiscal.awaiting_check > 0 && hasAny(codes, ["fiscal.document.check", "procurement.receive"])) {
      return {
        label: "Abrir documentos aguardando conferência",
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
      return {
        label: "Seguir para acabamento ou gestão",
        to: "/fluxo?etapa=7",
        allowed: true,
      };
    }
    if (has(codes, "recipe.read")) {
      return { label: "Abrir receitas", to: "/receitas", allowed: true };
    }
  }

  if (stepId === 5 && hasAny(codes, ["production.order.read", "production.plan.read"])) {
    return { label: "Abrir ordens", to: "/ordens", allowed: has(codes, "production.order.read") };
  }

  if (stepId === 6 && has(codes, "production.order.read")) {
    return { label: "Escolher ordem para executar", to: "/ordens", allowed: true };
  }

  if (stepId === 7 && has(codes, "labeling.read")) {
    return { label: "Abrir conformidade", to: "/conformidade", allowed: true };
  }

  if (stepId === 8) {
    if (!hasAny(codes, ["costing.read", "pricing.review", "pricing.simulation.manage"])) {
      return {
        label: "Continuar pelo acabamento",
        to: "/fluxo?etapa=7",
        allowed: has(codes, "labeling.read"),
      };
    }
    return { label: "Abrir custos e preços", to: "/gestao/custos", allowed: has(codes, "costing.read") };
  }

  if (input.nextAction && stepId) {
    // Sem rota concreta segura — não inventa botão morto.
    return null;
  }
  return { label: "Voltar ao fluxo", to: "/fluxo", allowed: true };
}
