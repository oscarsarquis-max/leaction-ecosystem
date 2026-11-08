import { custoTexto } from "../lib/format";

/** Selo do lote cujo custo já foi corrigido. O antes e o depois aparecem ao passar o mouse ou ao tocar. */
export function SeloCusto({
  antes,
  depois,
  base,
}: {
  antes: number | null;
  depois: number | null;
  base: string;
}) {
  const de = antes === null ? "sem custo" : custoTexto(antes, base);
  const para = depois === null ? "sem custo" : custoTexto(depois, base);
  const dica = `Antes ${de}. Depois ${para}.`;
  return (
    <button type="button" className="gestao-chip c-acc selo-corrigido" aria-label={`custo corrigido. ${dica}`}>
      <span className="dot" aria-hidden="true" />
      custo corrigido
      <span className="selo-dica">{dica}</span>
    </button>
  );
}
