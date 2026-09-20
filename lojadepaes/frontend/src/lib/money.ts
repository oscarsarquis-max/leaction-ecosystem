export function formatCents(cents: number): string {
  const negative = cents < 0;
  const absolute = negative ? -cents : cents;
  const whole = Math.trunc(absolute / 100);
  const fraction = absolute % 100;
  const grouped = whole.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return `${negative ? "-" : ""}R$ ${grouped},${fraction.toString().padStart(2, "0")}`;
}

export function parseBrlToCents(raw: string): number | null {
  const text = raw.trim();
  if (!text) {
    return null;
  }
  if (!/^(?:\d{1,3}(?:\.\d{3})*|\d+),\d{2}$|^\d+$/.test(text)) {
    throw new Error("informe o preço como 24,90");
  }
  if (text.includes(",")) {
    const [wholeRaw, fractionRaw] = text.split(",");
    const whole = Number.parseInt(wholeRaw.replaceAll(".", ""), 10);
    const fraction = Number.parseInt(fractionRaw, 10);
    const cents = whole * 100 + fraction;
    if (cents <= 0) {
      throw new Error("preço deve ser maior que zero");
    }
    return cents;
  }
  const cents = Number.parseInt(text, 10) * 100;
  if (cents <= 0) {
    throw new Error("preço deve ser maior que zero");
  }
  return cents;
}

export function lineTotalCents(unitCents: number, quantity: number): number {
  return unitCents * quantity;
}

export function sumCents(values: number[]): number {
  return values.reduce((total, value) => total + value, 0);
}
