/**
 * Geometry for indicator charts, computed without ever turning a measurement
 * into a JavaScript number.
 *
 * A measurement is audit evidence. `Number("0.30000000000000004")` and
 * `Number("123456789012345678901234567890")` both silently change the value,
 * and a value large enough becomes `Infinity` — so the series is scaled with
 * BigInt arithmetic and only the resulting 0..1 position, which is bounded by
 * construction, is turned into a number for the SVG path.
 */

type Exact = { digits: bigint; scale: number };

const DECIMAL = /^[+-]?(\d+)(?:\.(\d+))?$/;

/** A decimal string as an exact integer plus the number of fraction digits. */
function parseExact(value: string): Exact | null {
  const text = value.trim();
  const match = DECIMAL.exec(text);
  if (!match) return null;
  const negative = text.startsWith("-");
  const fraction = match[2] ?? "";
  const digits = BigInt(match[1] + fraction);
  return { digits: negative ? -digits : digits, scale: fraction.length };
}

function rescale(exact: Exact, scale: number): bigint {
  return exact.digits * 10n ** BigInt(scale - exact.scale);
}

const PRECISION = 10_000n;

/**
 * Where each value sits between the smallest and the largest, as a fraction
 * from 0 to 1. Returns `null` when any value is not a plain decimal, so the
 * caller can fall back to the table alone instead of drawing a wrong line.
 */
export function seriesPositions(values: readonly string[]): number[] | null {
  if (values.length === 0) return null;
  const parsed: Exact[] = [];
  for (const value of values) {
    const exact = parseExact(value);
    if (!exact) return null;
    parsed.push(exact);
  }

  const scale = parsed.reduce((max, e) => Math.max(max, e.scale), 0);
  const scaled = parsed.map((e) => rescale(e, scale));
  let min = scaled[0];
  let max = scaled[0];
  for (const n of scaled) {
    if (n < min) min = n;
    if (n > max) max = n;
  }

  const span = max - min;
  if (span === 0n) return scaled.map(() => 0.5);
  return scaled.map(
    (n) => Number(((n - min) * PRECISION) / span) / Number(PRECISION),
  );
}
