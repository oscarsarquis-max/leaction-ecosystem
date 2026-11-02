const MESES = [
  "janeiro",
  "fevereiro",
  "março",
  "abril",
  "maio",
  "junho",
  "julho",
  "agosto",
  "setembro",
  "outubro",
  "novembro",
  "dezembro",
];
const DIAS = ["domingo", "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado"];

/** "2026-11-03" → data sem fuso (evita voltar um dia por causa do UTC). */
function partes(iso: string): { y: number; m: number; d: number } {
  const [y, m, d] = iso.split("-").map(Number);
  return { y, m, d };
}

function serial(iso: string): number {
  const { y, m, d } = partes(iso);
  return Date.UTC(y, m - 1, d) / 86_400_000;
}

export function diaDaSemana(iso: string): string {
  const { y, m, d } = partes(iso);
  return DIAS[new Date(Date.UTC(y, m - 1, d)).getUTCDay()];
}

export function dataLonga(iso: string): string {
  const { m, d } = partes(iso);
  return `${diaDaSemana(iso)}, ${d} de ${MESES[m - 1]}`;
}

export function dataCurta(iso: string): string {
  const { m, d } = partes(iso);
  return `${String(d).padStart(2, "0")}/${String(m).padStart(2, "0")}`;
}

export function distanciaEmDias(hojeIso: string, alvoIso: string): number {
  return serial(alvoIso) - serial(hojeIso);
}

export function quando(hojeIso: string, alvoIso: string): string {
  const dias = distanciaEmDias(hojeIso, alvoIso);
  if (dias === 0) return "Hoje";
  if (dias === 1) return "Amanhã";
  if (dias < 0) return `${-dias} ${-dias === 1 ? "dia" : "dias"} atrás`;
  return `Em ${dias} dias`;
}

export function inteiro(valor: number): string {
  return new Intl.NumberFormat("pt-BR").format(valor);
}

export function pluralPaes(valor: number): string {
  return `${inteiro(valor)} ${valor === 1 ? "pão" : "pães"}`;
}
