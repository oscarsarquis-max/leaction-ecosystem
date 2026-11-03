import { useEffect, useState } from "react";

const QUERY = "(max-width: 959px)";

/** Verdadeiro no celular e no tablet em pé (até 959 px), o ponto em que a Loja vira lista. */
export function useNarrow(): boolean {
  const [narrow, setNarrow] = useState(() =>
    typeof window.matchMedia === "function" ? window.matchMedia(QUERY).matches : false,
  );
  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const media = window.matchMedia(QUERY);
    const aplicar = () => setNarrow(media.matches);
    aplicar();
    media.addEventListener("change", aplicar);
    return () => media.removeEventListener("change", aplicar);
  }, []);
  return narrow;
}

/** Verdadeiro a partir de 1024 px, onde a Entrada sem nota vira tabela (uma linha por item). */
export function useTabela(): boolean {
  const consulta = "(min-width: 1024px)";
  const [largo, setLargo] = useState(() =>
    typeof window.matchMedia === "function" ? window.matchMedia(consulta).matches : false,
  );
  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const media = window.matchMedia(consulta);
    const aplicar = () => setLargo(media.matches);
    aplicar();
    media.addEventListener("change", aplicar);
    return () => media.removeEventListener("change", aplicar);
  }, []);
  return largo;
}

/** Data de hoje (AAAA-MM-DD) no fuso da padaria. */
export function hojeNoFuso(fuso: string): string {
  try {
    return new Intl.DateTimeFormat("en-CA", { timeZone: fuso, year: "numeric", month: "2-digit", day: "2-digit" }).format(
      new Date(),
    );
  } catch {
    return new Date().toISOString().slice(0, 10);
  }
}
