import type { EstadoEtapa } from "../lib/api";

const TEXTO: Record<string, string> = { em_dia: "em dia", atencao: "atenção", falta: "falta" };

/** Bolinha de estado de uma etapa: em dia, atenção, falta. Vazia (oca) = etapa que ainda não existe. */
export function Ponto({ estado }: { estado: EstadoEtapa }) {
  return (
    <span className={`ponto ponto-${estado ?? "breve"}`}>
      <span className="sr-only">{estado ? TEXTO[estado] : "em breve"}</span>
    </span>
  );
}
