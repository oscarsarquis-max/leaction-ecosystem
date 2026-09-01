import type { LoginEditorialPayload } from "./schema";

export interface LoginEditorialContentProvider {
  load(): Promise<LoginEditorialPayload | null>;
}

export function futureActionHubAdapterNote(): string {
  return "O adaptador do Action Hub opera no servidor da Panne; a tela de entrada só lê o texto público de login.";
}
