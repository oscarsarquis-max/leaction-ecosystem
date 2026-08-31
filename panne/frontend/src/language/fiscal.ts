/**
 * Linguagem da entrada de mercadoria por documento fiscal (CURSOR-028-D).
 * Nenhum enum de contrato chega à tela: tudo passa por um rótulo humano.
 */
import { formatDecimal } from "../format";
import type {
  FiscalDocumentCard,
  FiscalDocumentItem,
  FiscalSummary,
  FiscalSupplierRef,
} from "../api/types";

type Tone = "sucesso" | "atencao" | "erro" | "info" | "neutro";

/** Situação da entrada, do registro até o estoque atualizado. */
export const FISCAL_STATUS_LABEL: Record<string, string> = {
  draft: "Rascunho",
  captured: "Documento recebido",
  awaiting_xml: "Aguardando XML",
  awaiting_match: "Aguardando correspondência",
  awaiting_check: "Aguardando conferência",
  partially_received: "Recebida em parte",
  divergent: "Com divergência",
  received: "Entrada confirmada",
  confirmed: "Entrada confirmada",
  cancelled: "Cancelada",
  refused: "Recusada",
  superseded: "Substituída",
};

/** Como o documento entrou na Panne. */
export const FISCAL_ORIGIN_LABEL: Record<string, string> = {
  access_key: "Chave de acesso",
  xml: "Arquivo XML",
  scan: "Foto ou anexo do DANFE",
  manual: "Digitação manual",
  distribution: "Consulta à Fazenda (simulação)",
};

/** Correspondência entre a linha do fornecedor e o cadastro da Panne. */
export const FISCAL_MATCH_LABEL: Record<string, string> = {
  matched: "Correspondência confirmada",
  suggested: "Correspondência sugerida",
  unmatched: "Sem correspondência",
  ignored: "Fora do estoque",
};

/** Resultado da conferência física do que chegou. */
export const FISCAL_CHECK_LABEL: Record<string, string> = {
  ok: "Conferido sem divergência",
  shortage: "Chegou a menos",
  excess: "Chegou a mais",
  damaged: "Chegou avariado",
  missing: "Não chegou",
};

export const FISCAL_ATTACHMENT_LABEL: Record<string, string> = {
  xml: "Arquivo XML da nota",
  pdf: "DANFE em PDF",
  image: "Foto do documento",
  other: "Anexo do documento",
};

export const FISCAL_NEXT_ACTION_LABEL: Record<string, string> = {
  match_items: "Fazer a correspondência dos itens com o cadastro da Panne.",
  record_physical: "Registrar o que realmente chegou.",
  resolve_divergence: "Resolver as divergências apontadas na conferência.",
  confirm_receipt: "Confirmar a entrada e atualizar o estoque.",
  none: "Nada pendente nesta entrada.",
};

function labelFrom(map: Record<string, string>, value: string | null | undefined, fallback: string): string {
  if (!value) return "—";
  return map[value] ?? fallback;
}

export function fiscalStatusLabel(status: string | null | undefined): string {
  return labelFrom(FISCAL_STATUS_LABEL, status, "Situação ainda não catalogada");
}

export function fiscalStatusTone(status: string | null | undefined): Tone {
  if (status === "confirmed" || status === "received") return "sucesso";
  if (status === "divergent") return "erro";
  if (status === "cancelled" || status === "refused" || status === "superseded") return "neutro";
  if (
    status === "partially_received" ||
    status === "awaiting_check" ||
    status === "awaiting_match" ||
    status === "awaiting_xml"
  ) {
    return "atencao";
  }
  return "info";
}

export function fiscalOriginLabel(origin: string | null | undefined): string {
  return labelFrom(FISCAL_ORIGIN_LABEL, origin, "Origem ainda não catalogada");
}

export function fiscalMatchLabel(status: string | null | undefined): string {
  return labelFrom(FISCAL_MATCH_LABEL, status, "Correspondência ainda não catalogada");
}

export function fiscalMatchTone(status: string | null | undefined): Tone {
  if (status === "matched") return "sucesso";
  if (status === "suggested") return "atencao";
  if (status === "ignored") return "neutro";
  return "erro";
}

export function fiscalCheckLabel(result: string | null | undefined): string {
  if (!result) return "Ainda não conferido";
  return FISCAL_CHECK_LABEL[result] ?? "Resultado ainda não catalogado";
}

export function fiscalCheckTone(result: string | null | undefined): Tone {
  if (result === "ok") return "sucesso";
  if (result === "missing" || result === "damaged") return "erro";
  if (!result) return "neutro";
  return "atencao";
}

export function fiscalAttachmentLabel(kind: string | null | undefined): string {
  return labelFrom(FISCAL_ATTACHMENT_LABEL, kind, "Anexo do documento");
}

export function fiscalNextActionLabel(
  code: string | null | undefined,
  given: string | null | undefined,
): string {
  const ready = given?.trim();
  if (ready) return ready;
  if (!code) return "Nenhuma ação pendente nesta entrada.";
  return FISCAL_NEXT_ACTION_LABEL[code] ?? "Revisar a entrada e decidir o próximo passo.";
}

/** Chave de acesso em blocos de quatro, como no DANFE. */
export function formatAccessKey(value: string | null | undefined): string {
  if (!value) return "Não informada";
  const digits = value.replace(/\D/g, "");
  if (digits.length !== 44) return value;
  return digits.replace(/(\d{4})(?=\d)/g, "$1 ").trim();
}

/** CNPJ mascarado; CPF quando vier com 11 dígitos. */
export function formatTaxId(value: string | null | undefined): string {
  if (!value) return "Não informado";
  const digits = value.replace(/\D/g, "");
  if (digits.length === 14) {
    return digits.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, "$1.$2.$3/$4-$5");
  }
  if (digits.length === 11) {
    return digits.replace(/^(\d{3})(\d{3})(\d{3})(\d{2})$/, "$1.$2.$3-$4");
  }
  return value;
}

/** Identificação humana do documento; nunca o identificador técnico. */
export function fiscalDocumentTitle(
  document: Pick<FiscalDocumentCard, "document_number" | "series" | "access_key" | "public_code">,
): string {
  const number = document.document_number?.trim();
  const series = document.series?.trim();
  if (number) return series ? `Nota ${number} · série ${series}` : `Nota ${number}`;
  const code = document.public_code?.trim();
  if (code) return `Entrada ${code}`;
  const key = document.access_key?.replace(/\D/g, "");
  if (key && key.length === 44) return `Nota da chave ${key.slice(-8)}`;
  return "Entrada sem número informado";
}

export function fiscalSupplierLabel(supplier: FiscalSupplierRef | null | undefined): string {
  const name = supplier?.display_name?.trim();
  return name || "Fornecedor não identificado";
}

export function fiscalSupplierRegistrationLabel(
  supplier: FiscalSupplierRef | null | undefined,
): string {
  if (!supplier) return "Emitente ainda não identificado nesta entrada.";
  return supplier.registered
    ? "Fornecedor já cadastrado na Panne."
    : "Emitente ainda sem cadastro de fornecedor na Panne.";
}

/** Valor monetário; devolve frase neutra quando o perfil não recebeu o número. */
export function fiscalMoney(
  value: string | null | undefined,
  currency: string | null | undefined = "BRL",
): string {
  if (value == null || value === "") return "Não informado";
  const symbol = currency === "BRL" || !currency ? "R$" : currency;
  return `${symbol} ${formatDecimal(value)}`;
}

export function fiscalQuantityLabel(
  value: string | null | undefined,
  unit: string | null | undefined,
): string {
  if (value == null || value === "") return "Não informada";
  const amount = formatDecimal(value);
  return unit ? `${amount} ${unit}` : amount;
}

/** Frase de progresso do documento, sem expor contadores crus fora de contexto. */
export function fiscalProgressSentence(document: FiscalDocumentCard): string {
  const total = document.item_count;
  if (total === 0) return "Documento ainda sem itens informados.";
  return [
    `${document.matched_item_count} de ${total} item(ns) com correspondência`,
    `${document.checked_item_count} conferido(s) fisicamente`,
    document.divergence_count > 0
      ? `${document.divergence_count} divergência(s)`
      : "sem divergência registrada",
  ].join(" · ");
}

export function fiscalStockLabel(applied: boolean, summary: string | null | undefined): string {
  const detail = summary?.trim();
  if (applied) return detail || "Estoque atualizado por esta entrada.";
  return detail || "Estoque ainda não foi atualizado por esta entrada.";
}

export function fiscalItemTitle(item: FiscalDocumentItem): string {
  const described = item.supplier_description?.trim();
  return described || `Item ${item.sequence} do documento`;
}

/** Resumo da caixa de entrada para a etapa 1 do fluxo. */
export function fiscalSummarySentence(summary: FiscalSummary): string {
  return [
    `${summary.total} entrada(s) registrada(s)`,
    `${summary.awaiting_match} aguardando correspondência`,
    `${summary.awaiting_check} aguardando conferência`,
    `${summary.divergent} com divergência`,
  ].join(" · ");
}

/**
 * Filtros da caixa de entrada. O endereço usa palavra em português (`?situacao=`)
 * e o contrato recebe o código de estado correspondente.
 */
export const FISCAL_STATUS_FILTERS: Array<{ slug: string; label: string; status?: string }> = [
  { slug: "", label: "Todas as situações" },
  { slug: "aguardando-correspondencia", label: "Aguardando correspondência", status: "awaiting_match" },
  { slug: "aguardando-conferencia", label: "Aguardando conferência", status: "awaiting_check" },
  { slug: "parcial", label: "Recebida em parte", status: "partially_received" },
  { slug: "divergencia", label: "Com divergência", status: "divergent" },
  { slug: "confirmada", label: "Entrada confirmada", status: "confirmed" },
  { slug: "historico", label: "Histórico completo" },
];

export function fiscalStatusFromSlug(slug: string | null | undefined): string | undefined {
  if (!slug) return undefined;
  return FISCAL_STATUS_FILTERS.find((row) => row.slug === slug)?.status;
}

export function fiscalFilterLabel(slug: string | null | undefined): string {
  const found = FISCAL_STATUS_FILTERS.find((row) => row.slug === (slug ?? ""));
  return found?.label ?? "Todas as situações";
}

/**
 * As quatro maneiras de abrir uma entrada (adendo Fazenda).
 * Ordem fixa: manual → XML → PDF/foto → Fazenda (preparada/desativada).
 */
export const FISCAL_ENTRY_OPTIONS = [
  {
    slug: "manual",
    title: "Preencher manualmente",
    summary:
      "Sem XML e sem consulta automática: informe fornecedor, número e data para abrir a entrada agora.",
    action: "Abrir entrada",
  },
  {
    slug: "xml",
    title: "Importar XML",
    summary:
      "Envie o arquivo XML enviado pelo fornecedor. Itens, quantidades e valores vêm preenchidos.",
    action: "Importar arquivo",
  },
  {
    slug: "foto",
    title: "Enviar PDF ou foto",
    summary:
      "Anexe o DANFE em PDF ou fotografe o papel. A captura é assistida; a conferência continua humana.",
    action: "Enviar arquivo",
  },
  {
    slug: "fazenda",
    title: "Buscar documentos da Fazenda",
    summary:
      "Consulta automática preparada, mas ainda não ativada para este estabelecimento.",
    action: "Abrir simulação",
  },
] as const;

export type FiscalEntryOptionSlug = (typeof FISCAL_ENTRY_OPTIONS)[number]["slug"];

export function isFiscalEntryOption(value: string | null | undefined): value is FiscalEntryOptionSlug {
  return FISCAL_ENTRY_OPTIONS.some((row) => row.slug === value);
}
