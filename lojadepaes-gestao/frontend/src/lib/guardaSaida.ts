/** Pergunta antes de sair da receita com rascunho pendente. Devolve true se pode sair. */
let guarda: (() => boolean) | null = null;

export function definirGuardaSaida(proxima: (() => boolean) | null): void {
  guarda = proxima;
}

export function podeSair(): boolean {
  if (!guarda) return true;
  return guarda();
}
