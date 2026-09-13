const OPAQUE_TOKEN = /^[A-Za-z0-9_-]{43}$/;

export function isOpaqueTokenShape(value: string): boolean {
  return OPAQUE_TOKEN.test(value);
}
