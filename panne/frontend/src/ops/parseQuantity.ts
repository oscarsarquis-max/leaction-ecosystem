export function parseQuantityInput(raw: string): string | null {
  const trimmed = raw.trim().replace(/\s/g, "");
  if (!trimmed) return null;
  const normalized = trimmed.includes(",")
    ? trimmed.replace(/\./g, "").replace(",", ".")
    : trimmed;
  if (!/^-?\d+(?:\.\d+)?$/.test(normalized)) return null;
  return normalized;
}
