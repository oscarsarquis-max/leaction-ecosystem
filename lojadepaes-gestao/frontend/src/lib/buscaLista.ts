/** Busca da lista: sem acento, sem caixa, e o hífen do lote fica (assim "-12" acha "E20261103-12"). */

export function textoBusca(valor: string): string {
  return valor
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

export function casaBusca(consulta: string, textos: (string | null | undefined)[]): boolean {
  const q = textoBusca(consulta);
  if (!q) return true;
  return textos.some((t) => t != null && t !== "" && textoBusca(t).includes(q));
}

/** O trecho casa com o código do lote, hífen inclusive. "-12" não casa com a data "20261112". */
export function casaLote(consulta: string, codigo: string): boolean {
  const q = textoBusca(consulta);
  return q !== "" && textoBusca(codigo).includes(q);
}

/** "A", "A e B" ou "A, B e mais N". Nomes repetidos entram uma vez. */
export function rotuloItens(nomes: string[]): string {
  const unicos: string[] = [];
  for (const nome of nomes) {
    if (nome && !unicos.includes(nome)) unicos.push(nome);
  }
  if (unicos.length <= 1) return unicos[0] ?? "";
  if (unicos.length === 2) return `${unicos[0]} e ${unicos[1]}`;
  return `${unicos[0]}, ${unicos[1]} e mais ${unicos.length - 2}`;
}

/**
 * "E20261103-12", ou "E20261103-12 a -14" quando os números são seguidos e o prefixo é o mesmo.
 * Códigos soltos ficam separados por vírgula.
 */
export function rotuloLotes(codigos: string[]): string {
  const unicos = [...new Set(codigos.filter(Boolean))];
  if (unicos.length <= 1) return unicos[0] ?? "";
  const re = /^(.*)-(\d+)$/;
  const grupos = new Map<string, { n: number; codigo: string }[]>();
  const soltos: string[] = [];
  for (const codigo of unicos) {
    const casa = re.exec(codigo);
    if (!casa) {
      soltos.push(codigo);
      continue;
    }
    const lista = grupos.get(casa[1]) ?? [];
    lista.push({ n: Number(casa[2]), codigo });
    grupos.set(casa[1], lista);
  }
  const partes: string[] = [];
  for (const [prefixo, lista] of grupos) {
    lista.sort((a, b) => a.n - b.n);
    let i = 0;
    while (i < lista.length) {
      let j = i;
      while (j + 1 < lista.length && lista[j + 1].n === lista[j].n + 1) j += 1;
      if (j === i) partes.push(lista[i].codigo);
      else partes.push(`${lista[i].codigo} a -${lista[j].codigo.slice(prefixo.length + 1)}`);
      i = j + 1;
    }
  }
  return [...partes, ...soltos].join(", ");
}
