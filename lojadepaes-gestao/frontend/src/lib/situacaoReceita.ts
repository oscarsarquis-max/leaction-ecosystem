/** Situação da receita de um produto produzido, como aparece em Produtos, no painel e no editor. */
export type ResumoReceita = {
  situacao: string;
  versao: number;
  publicada: boolean;
  linhas: number;
};

export type SeloReceita = { stage: "ok" | "warning" | "cancelled"; label: string };

/**
 * Publicada vN: está valendo. Rascunho vN+1 ao lado: há mudanças ainda não publicadas (a vN continua valendo).
 * Rascunho sozinho: tem linhas, mas nunca foi publicada; não vale para custo nem produção.
 */
export function selosDaReceita(receita: ResumoReceita | null | undefined): SeloReceita[] {
  if (!receita || (!receita.publicada && receita.linhas === 0)) return [{ stage: "cancelled", label: "Sem receita" }];
  if (receita.situacao === "publicada") return [{ stage: "ok", label: `Publicada v${receita.versao}` }];
  if (receita.publicada) {
    return [
      { stage: "ok", label: `Publicada v${receita.versao - 1}` },
      { stage: "warning", label: `Rascunho v${receita.versao}` },
    ];
  }
  return [{ stage: "warning", label: "Rascunho" }];
}

/** A mesma situação em uma frase, para o painel do produto. */
export function fraseDaReceita(receita: ResumoReceita | null | undefined): string {
  if (!receita || (!receita.publicada && receita.linhas === 0)) return "Ainda sem receita";
  if (receita.situacao === "publicada") return `Publicada · versão ${receita.versao}`;
  if (receita.publicada) return `Versão ${receita.versao - 1} valendo · rascunho da ${receita.versao} não publicado`;
  return "Rascunho, ainda não vale · publique em Revisar";
}
