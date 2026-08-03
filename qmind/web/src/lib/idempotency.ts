/** Client idempotency key for create/command operations (ADR-003). */
export function newIdempotencyKey(prefix = "qmind"): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}
