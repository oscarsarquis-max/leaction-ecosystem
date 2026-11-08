import type { Catalogo, ControleUnidade, LinhaEnvio, ModoCusto } from "./api";

export type LinhaForm = {
  chave: string;
  itemId: string | null;
  itemTexto: string;
  /** Só há ingrediente quando a pessoa escolheu um que existe (nunca é criado pela entrada). */
  ingredienteId: string | null;
  /** O nome do ingrediente escolhido ou, sem escolha, o que veio da planilha (vira a busca do campo). */
  ingredienteTexto: string;
  ingredienteCategoria: string;
  ingredienteBase: "" | "g" | "ml" | "un";
  marca: string;
  quantidade: string;
  unidade: string;
  conteudo: string;
  lote: string;
  validade: string;
  semValidade: boolean;
  custo: string;
  decisaoItem: "novo" | null;
};

export const UNIDADES: { valor: string; rotulo: string; controle: ControleUnidade }[] = [
  { valor: "kg", rotulo: "kg", controle: "massa" },
  { valor: "g", rotulo: "g", controle: "massa" },
  { valor: "l", rotulo: "L", controle: "volume" },
  { valor: "ml", rotulo: "ml", controle: "volume" },
  { valor: "emb", rotulo: "embalagem", controle: "embalagem" },
];

const PADRAO_DO_CONTROLE: Record<ControleUnidade, string> = { massa: "kg", volume: "l", embalagem: "emb" };

export function controleDaUnidade(unidade: string): ControleUnidade | null {
  return UNIDADES.find((u) => u.valor === unidade)?.controle ?? null;
}

export function unidadePadrao(controle: ControleUnidade): string {
  return PADRAO_DO_CONTROLE[controle];
}

export const CUSTO_POR: Record<ControleUnidade, string> = {
  massa: "R$ por kg",
  volume: "R$ por L",
  embalagem: "R$ por embalagem",
};

/** Como a coluna de custo é preenchida: o que se sabe é quanto foi pago, então o valor pago é o padrão. */
export const MODOS_CUSTO: { valor: ModoCusto; rotulo: string }[] = [
  { valor: "valor_pago", rotulo: "Valor pago" },
  { valor: "preco_unidade", rotulo: "Preço por unidade" },
];

const CHAVE_MODO_CUSTO = "gestao.entrada.modoCusto";

/** A última escolha da pessoa (vale para a entrada toda e para o colar); sem escolha, o valor pago. */
export function modoLembrado(): ModoCusto {
  try {
    const guardado = window.localStorage.getItem(CHAVE_MODO_CUSTO);
    return guardado === "preco_unidade" ? "preco_unidade" : "valor_pago";
  } catch {
    return "valor_pago";
  }
}

export function lembrarModo(modo: ModoCusto): void {
  try {
    window.localStorage.setItem(CHAVE_MODO_CUSTO, modo);
  } catch {
    /* sem armazenamento: só não lembra */
  }
}

let contador = 0;
export function novaChave(): string {
  contador += 1;
  return `linha-${Date.now().toString(36)}-${contador}`;
}

export function novaLinha(): LinhaForm {
  return {
    chave: novaChave(),
    itemId: null,
    itemTexto: "",
    ingredienteId: null,
    ingredienteTexto: "",
    ingredienteCategoria: "",
    ingredienteBase: "",
    marca: "",
    quantidade: "",
    unidade: "",
    conteudo: "",
    lote: "",
    validade: "",
    semValidade: false,
    custo: "",
    decisaoItem: null,
  };
}

export function linhaVazia(l: LinhaForm): boolean {
  return (
    !l.itemId &&
    !l.itemTexto.trim() &&
    !l.ingredienteTexto.trim() &&
    !l.quantidade.trim() &&
    !l.marca.trim() &&
    !l.lote.trim() &&
    !l.validade.trim() &&
    !l.custo.trim()
  );
}

/** "1.234,56" ou "1234.56" ou "12,5" -> número. Vazio ou lixo -> null. */
export function numero(texto: string): number | null {
  const t = texto.trim().replace(/\s/g, "").replace(/^R\$/, "");
  if (!t) return null;
  const normal = t.includes(",") ? t.replace(/\./g, "").replace(",", ".") : t;
  const n = Number(normal);
  return Number.isFinite(n) ? n : null;
}

export function rotuloItem(nome: string, marca: string): string {
  return marca ? `${nome} — ${marca}` : nome;
}

/** `modo` diz o que está escrito na coluna de custo: o total pago (padrão) ou o preço de uma unidade. */
export function paraEnvio(l: LinhaForm, catalogo: Catalogo | null, modo: ModoCusto = "valor_pago"): LinhaEnvio {
  const valor = numero(l.custo);
  const item = l.itemId ? catalogo?.itens.find((i) => i.id === l.itemId) : undefined;
  const controle = item ? item.unidade_controle : controleDaUnidade(l.unidade);
  return {
    item_id: l.itemId,
    item_nome: l.itemId ? "" : l.itemTexto.trim(),
    marca: l.itemId ? "" : l.marca.trim(),
    unidade_controle: l.itemId ? null : controle,
    conteudo_embalagem: l.itemId ? null : numero(l.conteudo),
    ingrediente_id: l.itemId ? null : l.ingredienteId,
    decisao_item: l.decisaoItem,
    quantidade: numero(l.quantidade),
    unidade: l.unidade,
    lote_codigo: l.lote.trim(),
    validade: l.semValidade ? null : l.validade || null,
    sem_validade: l.semValidade,
    custo: modo === "preco_unidade" ? valor : null,
    valor_pago: modo === "valor_pago" ? valor : null,
  };
}

/** "02/11/2026" ou "2026-11-02" -> "2026-11-02". Outra coisa -> "". */
export function dataIso(texto: string): string {
  const t = texto.trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(t)) return t;
  const m = t.match(/^(\d{1,2})[/.-](\d{1,2})[/.-](\d{2}|\d{4})$/);
  if (!m) return "";
  const ano = m[3].length === 2 ? `20${m[3]}` : m[3];
  return `${ano}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}`;
}

const SINONIMOS_UNIDADE: Record<string, string> = {
  kg: "kg",
  quilo: "kg",
  quilos: "kg",
  g: "g",
  grama: "g",
  gramas: "g",
  l: "l",
  litro: "l",
  litros: "l",
  ml: "ml",
  emb: "emb",
  embalagem: "emb",
  embalagens: "emb",
  un: "emb",
  pacote: "emb",
  caixa: "emb",
};

/**
 * Cola de planilha (colunas separadas por TAB, uma linha por item), na ordem da tela:
 * item · ingrediente · marca · quantidade · unidade · conteúdo da embalagem · lote · validade · custo.
 * A coluna de custo entra como foi copiada; vale como o valor pago ou como o preço por unidade conforme o modo
 * escolhido na tela (`paraEnvio`), igual ao que foi digitado à mão.
 */
export function linhasDaColagem(texto: string, catalogo: Catalogo | null): LinhaForm[] {
  const saida: LinhaForm[] = [];
  for (const bruta of texto.replace(/\r/g, "").split("\n")) {
    if (!bruta.trim()) continue;
    const c = bruta.split("\t").map((x) => x.trim());
    const [item = "", ingrediente = "", marca = "", quantidade = "", unidade = "", conteudo = "", lote = "", validade = "", custo = ""] = c;
    const linha = novaLinha();
    linha.itemTexto = item;
    linha.ingredienteTexto = ingrediente;
    linha.marca = marca;
    linha.quantidade = quantidade;
    linha.unidade = SINONIMOS_UNIDADE[unidade.toLowerCase()] ?? "";
    linha.conteudo = conteudo;
    linha.lote = lote;
    if (/sem\s*validade/i.test(validade)) linha.semValidade = true;
    else linha.validade = dataIso(validade);
    linha.custo = custo;
    saida.push(reconhecer(linha, catalogo));
  }
  return saida;
}

/** Sem acento, sem caixa e sem espaço sobrando: para dizer que dois textos são "exatamente" o mesmo nome. */
export function textoSimples(texto: string): string {
  return texto
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

/** Escolher um ingrediente que existe: ele vira o ingrediente da linha (nome, categoria e unidade base). */
export function escolherIngrediente(
  l: LinhaForm,
  ing: { id: string; nome: string; categoria?: string; unidade_base: string },
): LinhaForm {
  return {
    ...l,
    ingredienteId: ing.id,
    ingredienteTexto: ing.nome,
    ingredienteCategoria: ing.categoria ?? "",
    ingredienteBase: ing.unidade_base as LinhaForm["ingredienteBase"],
  };
}

/** O × do chip: volta a ser "a decidir" (o texto da busca some). */
export function trocarIngrediente(l: LinhaForm): LinhaForm {
  return { ...l, ingredienteId: null, ingredienteTexto: "", ingredienteCategoria: "", ingredienteBase: "" };
}

/** Se o que foi escrito é exatamente um item (ou ingrediente) que já existe, usa o que existe. */
export function reconhecer(l: LinhaForm, catalogo: Catalogo | null): LinhaForm {
  if (!catalogo) return l;
  let linha = { ...l };
  if (!linha.itemId) {
    const alvo = linha.itemTexto.trim().toLowerCase();
    const achado = catalogo.itens.find(
      (i) =>
        rotuloItem(i.nome, i.marca).toLowerCase() === alvo ||
        // nome igual e a marca já digitada igual: só então, para não sequestrar quem ainda digita o nome
        (i.nome.toLowerCase() === alvo && linha.marca.trim() !== "" && i.marca.toLowerCase() === linha.marca.trim().toLowerCase()),
    );
    if (achado) linha = usarItem(linha, achado.id, catalogo);
  }
  if (!linha.itemId && !linha.ingredienteId && linha.ingredienteTexto.trim()) {
    // da planilha: só liga quando bate exatamente com o nome ou com um apelido; senão fica "a decidir"
    const alvo = textoSimples(linha.ingredienteTexto);
    const achado = catalogo.ingredientes.find(
      (i) => textoSimples(i.nome) === alvo || (i.apelidos ?? []).some((a) => textoSimples(a) === alvo),
    );
    if (achado) linha = escolherIngrediente(linha, achado);
  }
  return linha;
}

export function usarItem(l: LinhaForm, itemId: string, catalogo: Catalogo | null): LinhaForm {
  const item = catalogo?.itens.find((i) => i.id === itemId);
  if (!item) return l;
  const unidadeValida = controleDaUnidade(l.unidade) === item.unidade_controle;
  return {
    ...l,
    itemId: item.id,
    itemTexto: rotuloItem(item.nome, item.marca),
    marca: item.marca,
    ingredienteId: item.ingrediente_id,
    ingredienteTexto: item.ingrediente,
    ingredienteCategoria: item.ingrediente_categoria ?? "",
    ingredienteBase: item.unidade_base as LinhaForm["ingredienteBase"],
    conteudo: item.conteudo_embalagem !== null ? String(item.conteudo_embalagem) : "",
    unidade: unidadeValida ? l.unidade : unidadePadrao(item.unidade_controle),
    decisaoItem: null,
  };
}

/** Para voltar de "item que existe" a "item novo" (a pessoa mexeu no nome). */
export function soltarItem(l: LinhaForm): LinhaForm {
  return {
    ...l,
    itemId: null,
    ingredienteId: null,
    ingredienteTexto: "",
    ingredienteCategoria: "",
    ingredienteBase: "",
    conteudo: "",
    decisaoItem: null,
  };
}
