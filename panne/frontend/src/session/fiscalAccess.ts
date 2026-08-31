/**
 * Permissões da entrada fiscal (CURSOR-028-D).
 *
 * Os códigos canônicos são os do domínio fiscal. O equivalente de compras entra como
 * alternativa para que nenhum perfil já concedido perca acesso enquanto os papéis não
 * recebem os códigos novos. Custo segue a mesma regra do backend: `fiscal.price.read`
 * ou `supplier.price.record`.
 */

type HasPermission = (code: string) => boolean;

function anyOf(hasPermission: HasPermission, codes: string[]): boolean {
  return codes.some((code) => hasPermission(code));
}

export const FISCAL_READ_CODES = ["fiscal.document.read", "procurement.read"];
export const FISCAL_CAPTURE_CODES = [
  "fiscal.document.capture",
  "procurement.receive",
  "procurement.order.manage",
];
export const FISCAL_MATCH_CODES = ["fiscal.document.match", "procurement.receive"];
export const FISCAL_CHECK_CODES = ["fiscal.document.check", "procurement.receive"];
export const FISCAL_CONFIRM_CODES = ["fiscal.document.confirm", "procurement.receive"];
export const FISCAL_PRICE_CODES = ["fiscal.price.read", "supplier.price.record"];

export function canReadFiscal(hasPermission: HasPermission): boolean {
  return anyOf(hasPermission, FISCAL_READ_CODES);
}

export function canCaptureFiscalDocument(hasPermission: HasPermission): boolean {
  return anyOf(hasPermission, FISCAL_CAPTURE_CODES);
}

export function canMatchFiscalItem(hasPermission: HasPermission): boolean {
  return anyOf(hasPermission, FISCAL_MATCH_CODES);
}

export function canCheckFiscalItem(hasPermission: HasPermission): boolean {
  return anyOf(hasPermission, FISCAL_CHECK_CODES);
}

export function canConfirmFiscalReceipt(hasPermission: HasPermission): boolean {
  return anyOf(hasPermission, FISCAL_CONFIRM_CODES);
}

export function canReadFiscalPrice(hasPermission: HasPermission): boolean {
  return anyOf(hasPermission, FISCAL_PRICE_CODES);
}

/** Alias usado pelas telas de revisão (mesmo critério de preço). */
export function canReadFiscalCost(hasPermission: HasPermission): boolean {
  return canReadFiscalPrice(hasPermission);
}

export function canCreateFiscalEntry(hasPermission: HasPermission): boolean {
  return canCaptureFiscalDocument(hasPermission);
}
