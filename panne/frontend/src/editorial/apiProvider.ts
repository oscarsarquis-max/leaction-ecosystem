/** Provider FE: consome apenas a API pública Panne (nunca o Hub direto). */

import { config } from "../config";
import type { LoginEditorialContentProvider } from "./provider";
import { sanitizePayload } from "./sanitize";
import type { LoginEditorialPayload } from "./schema";
import { StaticLoginEditorialProvider } from "./staticProvider";

function apiBase(): string {
  const base = (config.apiBase || "").replace(/\/$/, "");
  return base || "";
}

export class ApiLoginEditorialProvider implements LoginEditorialContentProvider {
  constructor(private readonly mode: "ok" | "invalid" | "unavailable" = "ok") {}

  async load(): Promise<LoginEditorialPayload | null> {
    if (this.mode === "unavailable") {
      return new StaticLoginEditorialProvider("unavailable").load();
    }
    if (this.mode === "invalid") {
      return new StaticLoginEditorialProvider("invalid").load();
    }
    const base = apiBase();
    const url = `${base}/api/v1/public/login-editorial`;
    try {
      const ctrl = new AbortController();
      const timer = window.setTimeout(() => ctrl.abort(), 4000);
      const res = await fetch(url, { signal: ctrl.signal, credentials: "omit" });
      window.clearTimeout(timer);
      if (!res.ok) {
        return new StaticLoginEditorialProvider("ok").load();
      }
      const raw = await res.json();
      const cleaned = sanitizePayload(raw);
      if (cleaned) return cleaned;
      return new StaticLoginEditorialProvider("ok").load();
    } catch {
      return new StaticLoginEditorialProvider("ok").load();
    }
  }
}
