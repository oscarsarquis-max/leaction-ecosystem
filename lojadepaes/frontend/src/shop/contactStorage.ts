const CONTACT_KEY = "lojadepaes_contact";

export type StoredContact = { name: string; email: string };

export function readStoredContact(): StoredContact {
  if (typeof sessionStorage === "undefined") {
    return { name: "", email: "" };
  }
  try {
    const raw = sessionStorage.getItem(CONTACT_KEY);
    if (!raw) {
      return { name: "", email: "" };
    }
    const parsed = JSON.parse(raw) as Partial<StoredContact>;
    return {
      name: typeof parsed.name === "string" ? parsed.name : "",
      email: typeof parsed.email === "string" ? parsed.email : "",
    };
  } catch {
    return { name: "", email: "" };
  }
}

export function writeStoredContact(name: string, email: string): void {
  sessionStorage.setItem(CONTACT_KEY, JSON.stringify({ name, email }));
}

export function newIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `lp-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}
