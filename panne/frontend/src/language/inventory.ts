/** Saldos e elegibilidade de estoque (R026-004-b + R026-009 + R026-010). */

import { formatDate, todayIso } from "../format";
import { formatOperationalQuantity } from "./quantities";

export type BalanceLike = {
  physical_quantity?: unknown;
  reserved_quantity?: unknown;
  available_quantity?: unknown;
  unreserved_quantity?: unknown;
  eligible_quantity?: unknown;
  impeded_quantity?: unknown;
  unit_code?: unknown;
  lot_status?: unknown;
  production_eligible?: unknown;
};

export type UnitTotals = {
  unit: string;
  physical: number;
  reserved: number;
  /** physical − reserved (legado `available_quantity`). */
  unreserved: number;
  /** Não reservado e elegível (status + validade). */
  eligible: number;
  /** Não reservado inelegível (bloqueado / quarentena / vencido). */
  impeded: number;
  lines: number;
  /** Alias legado para testes R026-004. */
  available: number;
};

function asNumber(value: unknown): number | null {
  if (value == null || value === "") return null;
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
}

/**
 * Soma apenas dentro da mesma unidade.
 * Impedido ⊆ não reservado; elegível + impedido = não reservado (quando ≥ 0).
 */
export function aggregateBalancesByUnit(items: BalanceLike[]): UnitTotals[] {
  const map = new Map<string, UnitTotals>();
  for (const row of items) {
    const unit = String(row.unit_code ?? "").trim() || "unidade não informada";
    const physical = asNumber(row.physical_quantity);
    const reserved = asNumber(row.reserved_quantity);
    const unreserved =
      asNumber(row.unreserved_quantity) ?? asNumber(row.available_quantity);
    const eligible = asNumber(row.eligible_quantity);
    const impeded = asNumber(row.impeded_quantity);
    if (
      physical == null &&
      reserved == null &&
      unreserved == null &&
      eligible == null &&
      impeded == null
    ) {
      continue;
    }
    const current =
      map.get(unit) ??
      ({
        unit,
        physical: 0,
        reserved: 0,
        unreserved: 0,
        eligible: 0,
        impeded: 0,
        lines: 0,
        available: 0,
      } satisfies UnitTotals);
    current.physical += physical ?? 0;
    current.reserved += reserved ?? 0;
    current.unreserved += unreserved ?? 0;
    current.eligible += eligible ?? 0;
    current.impeded += impeded ?? 0;
    current.available = current.unreserved;
    current.lines += 1;
    map.set(unit, current);
  }
  return [...map.values()].sort((a, b) => a.unit.localeCompare(b.unit, "pt-BR"));
}

export const MOVEMENT_TYPE_LABEL: Record<string, string> = {
  receipt: "Recebimento",
  transfer_out: "Transferência (saída)",
  transfer_in: "Transferência (entrada)",
  production_consume: "Consumo na produção",
  production_return: "Devolução da produção",
  waste: "Perda / descarte",
  supplier_return: "Devolução ao fornecedor",
  adjust_plus: "Ajuste (entrada)",
  adjust_minus: "Ajuste (saída)",
  reverse: "Reversão",
  opening: "Abertura de saldo",
  // legado / aliases
  issue: "Saída",
  transfer: "Transferência",
  adjustment: "Ajuste",
  consume: "Consumo",
  return: "Devolução",
};

export const MOVEMENT_ORIGIN_LABEL: Record<string, string> = {
  opening: "Abertura de saldo",
  manual: "Movimento manual",
  production_material_consumption: "Consumo de material na produção",
  inventory_count_session: "Sessão de inventário",
  procurement_receipt: "Recebimento de compra",
  procurement_return: "Devolução de compra",
};

export function movementTypeLabel(value: string | null | undefined): string {
  if (!value) return "—";
  return MOVEMENT_TYPE_LABEL[value] ?? "Movimento não catalogado";
}

export function movementOriginLabel(value: string | null | undefined): string {
  if (!value) return "—";
  return MOVEMENT_ORIGIN_LABEL[value] ?? "Origem não catalogada";
}

/** Quantidade com sinal operacional (+ entrada / − saída). Usa `sign` do contrato. */
export function formatSignedMovementQuantity(
  quantity: unknown,
  sign: unknown,
  unit?: unknown,
): string {
  const abs = formatOperationalQuantity(
    quantity == null ? null : String(quantity),
    unit == null ? null : String(unit),
  );
  if (abs === "—") return abs;
  const s = Number(sign);
  if (s < 0) return `−${abs.replace(/^−/, "")}`;
  if (s > 0) return `+${abs}`;
  return abs;
}

export function locationPassageLabel(
  fromLabel: unknown,
  toLabel: unknown,
): string {
  const from = fromLabel == null || fromLabel === "" ? null : String(fromLabel);
  const to = toLabel == null || toLabel === "" ? null : String(toLabel);
  if (from && to) return `${from} → ${to}`;
  if (to) return to;
  if (from) return from;
  return "—";
}

/** Flag `adopted`: reserva de ordem anterior à política de estoque, com adoção explícita. */
export function historicalAdoptionCaption(adopted: unknown): string | null {
  if (adopted !== true) return null;
  return "Registro histórico incorporado à organização";
}

export function historicalAdoptionHelp(): string {
  return "A ordem já existia antes da política de estoque vigente. A reserva foi registrada com adoção humana explícita e motivo auditável — não é preenchimento automático.";
}

/** Data operacional: preferir `as_of` da API; sem fallback no relógio do navegador. */
export function resolveInventoryAsOf(apiAsOf: string | null | undefined): string | null {
  if (typeof apiAsOf === "string" && /^\d{4}-\d{2}-\d{2}$/.test(apiAsOf.trim())) {
    return apiAsOf.trim();
  }
  return null;
}

/**
 * @deprecated Preferir `resolveInventoryAsOf` a partir do payload da API.
 * Mantido para superfícies fora de estoque (ex.: quadro) que ainda usam config local.
 */
export function inventoryOperationalDate(
  demoMode: boolean,
  demoAnchorDate: string,
  today: string = todayIso(),
): string {
  if (demoMode && /^\d{4}-\d{2}-\d{2}$/.test(demoAnchorDate)) return demoAnchorDate;
  return today;
}

/** Nota visível só no modo demo — data deve ser a mesma do `as_of` da API. */
export function demoExpiryReferenceNote(
  demoMode: boolean,
  asOfIso: string | null | undefined,
): string | null {
  if (!demoMode) return null;
  const asOf = resolveInventoryAsOf(asOfIso);
  if (!asOf) return null;
  return `Referência da demonstração: ${formatDate(asOf)}. Os indicadores “vence em” e “vencido há” usam esta data.`;
}

/** URL compartilhável da posição filtrada pelo código público do lote. */
export function positionLotHref(lotCode: string): string {
  const code = lotCode.trim();
  if (!code) return "/componentes/estoque/posicao";
  return `/componentes/estoque/posicao?lot=${encodeURIComponent(code)}`;
}

function parseIsoDate(value: string): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value.trim());
  if (!match) return null;
  return new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])));
}

function daysBetween(fromIso: string, toIso: string): number | null {
  const from = parseIsoDate(fromIso);
  const to = parseIsoDate(toIso);
  if (!from || !to) return null;
  return Math.round((to.getTime() - from.getTime()) / 86_400_000);
}

/** Indicador relativo de validade (pt-BR). Ausência ≠ vencido. Sem as_of: só data absoluta. */
export function formatExpiryCaption(
  expiresOn: string | null | undefined,
  asOfIso: string | null | undefined,
): string {
  if (!expiresOn) return "Validade ausente";
  const asOf = resolveInventoryAsOf(asOfIso);
  if (!asOf) return formatDate(expiresOn);
  const delta = daysBetween(asOf, expiresOn);
  if (delta == null) return formatDate(expiresOn);
  const local = formatDate(expiresOn);
  if (delta === 0) return `${local} · vence hoje`;
  if (delta > 0) {
    if (delta === 1) return `${local} · vence em 1 dia`;
    return `${local} · vence em ${delta} dias`;
  }
  const overdue = Math.abs(delta);
  if (overdue === 1) return `${local} · vencido há 1 dia`;
  return `${local} · vencido há ${overdue} dias`;
}

export function eligibilitySurfaceLabel(row: {
  production_eligible?: unknown;
  lot_status?: unknown;
  eligibility_reason?: unknown;
  status?: unknown;
}): string {
  if (row.production_eligible === true) return "Elegível para produção";
  const status = String(row.lot_status ?? row.status ?? "");
  if (status === "blocked") return "Impedido · Bloqueado";
  if (status === "quarantined") return "Impedido · Em quarentena";
  if (status === "expired" || row.eligibility_reason === "expired_calendar") {
    return "Impedido · Vencido";
  }
  if (status === "exhausted") return "Impedido · Esgotado";
  if (status === "closed") return "Impedido · Encerrado";
  return "Impedido";
}
