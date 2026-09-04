import type { LoginEditorialPayload } from "./schema";

export interface LoginEditorialContentProvider {
  load(): Promise<LoginEditorialPayload | null>;
}

export function futureActionHubAdapterNote(): string {
  return "O adaptador do Action Hub opera no backend Panne; o frontend só consome GET /api/v1/public/login-editorial.";
}
