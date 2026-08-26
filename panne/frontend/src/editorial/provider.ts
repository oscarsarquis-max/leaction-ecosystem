import type { LoginEditorialPayload } from "./schema";

export interface LoginEditorialContentProvider {
  load(): Promise<LoginEditorialPayload | null>;
}

export function futureActionHubAdapterNote(): string {
  return "O adaptador futuro do Action Hub conecta-se aqui, atrás desta porta. Sem URL, token ou schema proprietário neste ciclo.";
}
