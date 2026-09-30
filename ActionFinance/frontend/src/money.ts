const MAX_SAFE = "9007199254740991";

export function parseSignedBrlInput(raw: string): { minor?: string; error?: string } {
  const trimmed = raw.trim();
  if (!trimmed) {
    return { error: "Informe o saldo no início desse dia." };
  }
  const negative = trimmed.startsWith("-");
  const unsigned = negative ? trimmed.slice(1).trim() : trimmed;
  if (unsigned === "0" || unsigned === "0,00") {
    return { minor: "0" };
  }
  const parsed = parseBrlInput(unsigned);
  if (parsed.error || !parsed.minor) {
    return parsed.error ? parsed : { error: "Informe o saldo no início desse dia." };
  }
  return { minor: negative ? `-${parsed.minor}` : parsed.minor };
}

export function parseBrlInput(raw: string): { minor?: string; error?: string } {
  const trimmed = raw.trim();
  if (!trimmed) {
    return {};
  }
  if (!/^\d{1,3}(\.\d{3})*(,\d{1,2})?$|^\d+(,\d{1,2})?$/.test(trimmed)) {
    return { error: "Use o formato 1.234,56. No máximo duas casas." };
  }
  const [wholeRaw, fractionRaw] = trimmed.split(",");
  const whole = wholeRaw.replace(/\./g, "");
  if (!/^\d+$/.test(whole)) {
    return { error: "Valor inválido." };
  }
  if (fractionRaw && fractionRaw.length > 2) {
    return { error: "No máximo duas casas decimais." };
  }
  const fraction = (fractionRaw ?? "").padEnd(2, "0");
  const minor = (whole + fraction).replace(/^0+(?=\d)/, "");
  if (minor === "0" || minor === "") {
    return { error: "Informe um valor maior que zero." };
  }
  if (minor.length > 19) {
    return { error: "Valor acima do limite de representação." };
  }
  return { minor };
}

export function formatMinor(minor: string | null | undefined): string {
  if (minor == null || minor === "") {
    return "Não informado";
  }
  if (minor.startsWith("-")) {
    return formatMinor(minor.slice(1)).replace("R$ ", "R$ -");
  }
  if (minor === "0") {
    return "R$ 0,00";
  }
  const digits = minor.replace(/^0+(?=\d)/, "");
  const padded = digits.padStart(3, "0");
  const whole = padded.slice(0, -2).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  const fraction = padded.slice(-2);
  return `R$ ${whole},${fraction}`;
}

export function formatDateBr(value: string | null | undefined): string {
  if (!value) {
    return "Não informado";
  }
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  if (!match) {
    return value;
  }
  return `${match[3]}/${match[2]}/${match[1]}`;
}

export function formatMethodLabel(method: string): string {
  return { PIX: "Pix", BANK_TRANSFER: "Transferência", CASH: "Dinheiro", CARD: "Cartão", OTHER: "Outro" }[method] ?? method;
}

export function formatAccountType(type: string): string {
  return { BANK: "Banco", CASH: "Caixa físico", OTHER: "Outra" }[type] ?? type;
}

export function formatSettlementStatus(status: string, direction: string): string {
  if (status === "PARTIAL") {
    return direction === "PAYABLE" ? "Parcialmente pago" : "Parcialmente recebido";
  }
  if (status === "SETTLED") {
    return direction === "PAYABLE" ? "Pago" : "Recebido";
  }
  if (status === "UNSETTLED") {
    return "Em aberto";
  }
  return "Não se aplica";
}

export function formatMovementKind(kind: string): string {
  return { OPENING: "Abertura", SETTLEMENT: "Registro", REVERSAL: "Estorno" }[kind] ?? kind;
}

export function formatStatusLabel(status: string): string {
  if (status === "DRAFT") {
    return "Rascunho";
  }
  if (status === "OPEN") {
    return "Em aberto";
  }
  if (status === "CANCELLED") {
    return "Cancelado";
  }
  return status;
}

export function compactReference(reference: string): { short: string; full: string } {
  const dash = reference.indexOf("-");
  const prefix = dash > 0 ? reference.slice(0, dash) : reference;
  const rest = dash > 0 ? reference.slice(dash + 1) : "";
  const compactTail = rest.replace(/-/g, "").slice(-8);
  if (!compactTail) {
    return { short: reference, full: reference };
  }
  return { short: `${prefix}-${compactTail}`, full: reference };
}

export function formatHistoryValue(field: string, value: unknown): string {
  if (value == null || value === "") {
    return "Não informado";
  }
  if (typeof value === "object" && value && "name" in (value as object)) {
    return String((value as { name: string }).name);
  }
  const text = String(value);
  if (field === "amountMinor") {
    return formatMinor(text);
  }
  if (field === "status") {
    return formatStatusLabel(text);
  }
  if (field === "competenceDate" || field === "dueDate") {
    return formatDateBr(text);
  }
  return text;
}

export function isSafeIntegerDigits(minor: string): boolean {
  if (minor.length < MAX_SAFE.length) {
    return true;
  }
  if (minor.length > MAX_SAFE.length) {
    return false;
  }
  return minor <= MAX_SAFE;
}
