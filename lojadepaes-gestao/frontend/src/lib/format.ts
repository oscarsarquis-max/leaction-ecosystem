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

export function dinheiro(valor: number): string {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(valor);
}

export function dataBr(iso: string): string {
  const { y, m, d } = partes(iso);
  return `${String(d).padStart(2, "0")}/${String(m).padStart(2, "0")}/${y}`;
}

/** Saldo na unidade base (g, ml, un) escrito como a pessoa lê: 25 kg, 1,5 L, 600 g, 12 un. */
export function quantidadeBase(valor: number, base: string): string {
  const num = (n: number, casas = 2) =>
    new Intl.NumberFormat("pt-BR", { maximumFractionDigits: casas }).format(n);
  if (base === "g") return Math.abs(valor) >= 1000 ? `${num(valor / 1000)} kg` : `${num(valor)} g`;
  if (base === "ml") return Math.abs(valor) >= 1000 ? `${num(valor / 1000)} L` : `${num(valor)} ml`;
  return `${num(valor)} un`;
}

/** Custo por unidade base (R$/g, R$/ml, R$/un) escrito por kg, L ou unidade. */
export function custoPorUnidade(valorPorBase: number, base: string): string {
  if (base === "g") return `${dinheiro(valorPorBase * 1000)} por kg`;
  if (base === "ml") return `${dinheiro(valorPorBase * 1000)} por L`;
  return `${dinheiro(valorPorBase)} por un`;
}

export function diasAte(hojeIso: string, validadeIso: string): string {
  const dias = distanciaEmDias(hojeIso, validadeIso);
  if (dias < 0) return `venceu há ${-dias} ${-dias === 1 ? "dia" : "dias"}`;
  if (dias === 0) return "vence hoje";
  if (dias === 1) return "vence amanhã";
  return `vence em ${dias} dias`;
}

export const MOTIVOS: Record<string, string> = {
  contagem: "Contagem de estoque",
  compra_sem_nota: "Compra sem nota",
  bonificacao: "Bonificação",
  outro: "Outro",
};

export const PAPEIS: Record<string, string> = {
  dono: "Dono",
  operador: "Operador",
  somente_leitura: "Somente leitura",
};

export const UNIDADE_CONTROLE: Record<string, string> = {
  massa: "Massa (g, kg)",
  volume: "Volume (ml, L)",
  embalagem: "Embalagem",
};