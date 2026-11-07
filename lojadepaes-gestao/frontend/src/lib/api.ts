export type Papel = "dono" | "operador" | "somente_leitura";

export type Organizacao = {
  id: string;
  nome: string;
  nome_curto: string;
  cnpj: string;
  cnpj_formatado: string;
  fonte_loja: boolean;
  papel: Papel | string;
};

export type SessaoInfo = {
  usuario: string;
  nome: string;
  admin_plataforma: boolean;
  papel: Papel | string | null;
  permissoes: string[];
  csrf: string;
  fuso: string;
  organizacao: Organizacao | null;
  organizacoes: Organizacao[];
  precisa_escolher_organizacao: boolean;
};

export type EstadoEtapa = "em_dia" | "atencao" | "falta" | null;

export type Etapa = {
  id: string;
  nome: string;
  pergunta: string;
  estado: EstadoEtapa;
  frase: string;
  href: string | null;
};

export type ProximoPasso = {
  etapa: string;
  estado: "falta" | "atencao";
  titulo: string;
  texto: string;
  acao: string;
  href: string;
};

export type Fluxo = {
  etapas: Etapa[];
  proximo_passo: ProximoPasso | null;
  entradas_total: number;
  entradas_pendentes: number;
};

export type ItemDemanda = {
  origem: "catalogo" | "criador" | string;
  produto_ou_massa: string | null;
  variante_ou_forma: string | null;
  receita_base: string | null;
  quantidade: number;
  paes_fisicos: number;
  linhas_unidades_pendentes: number;
};

export type Fornada = {
  data: string;
  paes_fisicos: number;
  quantidade: number;
  unidades_pendentes: number;
  itens: ItemDemanda[];
};

export type VenceEm7Dias = {
  lote_id: string;
  ingrediente_id: string;
  ingrediente: string;
  item: string;
  codigo: string;
  validade: string;
  dias: number;
  saldo: number;
  unidade_base: string;
};

export type ProducaoHoje = {
  fornada_id: string;
  fornada: string;
  horario: string;
  unidades: number;
  ordens: number;
  pedido_mudou: boolean;
};

export type Hoje = {
  hoje: string;
  ate: string;
  dias: number;
  fonte_loja: boolean;
  producao_hoje: ProducaoHoje[];
  compatibilidade: {
    ok: boolean;
    versao_loja: string | null;
    versao_conhecida: boolean | null;
    mensagem: string | null;
  };
  fornadas: Fornada[];
  total_paes_fisicos: number;
  fluxo: Fluxo;
  vence_em_7_dias: VenceEm7Dias[];
  sem_saldo: { id: string; nome: string }[];
};

// ---------------------------------------------------------------- entradas

export type FiltroEntradas = "todas" | "com_nota" | "sem_nota" | "pendentes";

export type EntradaResumo = {
  id: string;
  data: string;
  tipo: "sem_nota" | "com_nota";
  motivo: string;
  motivo_detalhe: string | null;
  fornecedor: string | null;
  itens: number;
  /** Nomes dos itens, na ordem da entrada. A linha da lista mostra os dois primeiros. */
  itens_nomes?: string[];
  /** Ingredientes de cada linha, na mesma ordem. Entram na busca. */
  ingredientes?: string[];
  /** Códigos dos lotes, na ordem da entrada. */
  lotes?: string[];
  valor: number | null;
  valor_parcial: boolean;
  situacao: "completa" | "pendente";
};

export type EntradaLinhaDetalhe = {
  posicao: number;
  item_id?: string;
  item: string;
  marca: string;
  ingrediente_id: string;
  ingrediente: string;
  quantidade: number;
  unidade: string;
  quantidade_base: number;
  unidade_base: string;
  lote_id: string;
  lote: string;
  validade: string | null;
  sem_validade: boolean;
  validade_pendente: boolean;
  /** Modo "preço por unidade": o que foi digitado (R$ por kg, L ou embalagem). */
  custo: number | null;
  custo_por: string | null;
  /** Modo "valor pago": o total pago pela linha, como foi digitado. */
  valor_pago?: number | null;
  modo_custo?: ModoCusto | null;
  /** O custo vigente do lote (R$ por g, ml ou un): pode ter sido corrigido depois. */
  custo_unidade_base?: number | null;
  valor_total: number | null;
  custo_corrigido?: boolean;
  custo_antes?: number | null;
  custo_depois?: number | null;
};

export type EntradaDetalhe = {
  id: string;
  data: string;
  tipo: string;
  motivo: string;
  motivo_detalhe: string | null;
  fornecedor: string | null;
  observacao: string | null;
  local: string | null;
  lancada_por: string | null;
  linhas: EntradaLinhaDetalhe[];
  valor: number | null;
  valor_parcial: boolean;
  situacao: "completa" | "pendente";
};

export type ControleUnidade = "massa" | "volume" | "embalagem";

/** Como o custo da linha é informado: o total pago (padrão) ou o preço de uma unidade. */
export type ModoCusto = "valor_pago" | "preco_unidade";

export type LinhaEnvio = {
  item_id?: string | null;
  item_nome?: string;
  marca?: string;
  unidade_controle?: ControleUnidade | null;
  conteudo_embalagem?: number | null;
  ingrediente_id?: string | null;
  decisao_item?: "novo" | null;
  quantidade?: number | null;
  unidade?: string;
  lote_codigo?: string;
  validade?: string | null;
  sem_validade?: boolean;
  /** Modo "preço por unidade": R$ por kg, L ou embalagem. */
  custo?: number | null;
  /** Modo "valor pago": o total pago pela linha (R$). Um OU outro, nunca os dois. */
  valor_pago?: number | null;
};

export type IngredienteRef = { id: string; nome: string; unidade_base: string };

export type Candidato = {
  id: string;
  nome: string;
  marca: string;
  unidade_controle: string | null;
  conteudo_embalagem: number | null;
  ingrediente: IngredienteRef | null;
  unidade_base: string | null;
};

export type Pendencia = { codigo: string; mensagem: string; bloqueia: boolean };

export type AnaliseLinha = {
  posicao: number;
  item_existente: Candidato | null;
  item_igual: Candidato | null;
  item_parecidos: Candidato[];
  ingrediente_existente: IngredienteRef | null;
  unidade_controle: string | null;
  conteudo_embalagem: number | null;
  unidade_base: string | null;
  unidades_validas: string[];
  custo_por: string | null;
  pendencias: Pendencia[];
  a_decidir: boolean;
  incompleta: boolean;
  quantidade_base: number | null;
  valor_total: number | null;
  /** O custo que a linha vai gravar: para mostrar "= R$ 45,98/kg" embaixo do campo. */
  modo_custo?: ModoCusto | null;
  custo_unidade_base?: number | null;
  custo_embalagem?: number | null;
};

export type EntradaEnvio = {
  chave: string;
  data: string;
  local_id: string;
  tipo: "sem_nota";
  motivo: "contagem" | "compra_sem_nota" | "bonificacao" | "outro";
  motivo_detalhe: string;
  fornecedor: string;
  observacao: string;
  linhas: LinhaEnvio[];
};

export type Catalogo = {
  ingredientes: (IngredienteRef & { categoria?: string; apelidos?: string[] })[];
  itens: {
    id: string;
    nome: string;
    marca: string;
    unidade_controle: ControleUnidade;
    conteudo_embalagem: number | null;
    ingrediente_id: string;
    ingrediente: string;
    ingrediente_categoria?: string;
    unidade_base: string;
  }[];
  locais: { id: string; nome: string; padrao: boolean }[];
};

// ---------------------------------------------------------------- ingredientes

export type FiltroIngredientes = "todos" | "com_saldo" | "sem_saldo" | "vence7";

export type IngredienteLinha = {
  id: string;
  nome: string;
  unidade_base: "g" | "ml" | "un" | string;
  categoria: string;
  apelidos: string[];
  ativo: boolean;
  saldo: number;
  itens: number;
  /** Nomes dos itens deste ingrediente. Entram na busca. */
  itens_nomes?: string[];
  lotes: number;
  /** Códigos de todos os lotes, com ou sem saldo. Entram na busca. */
  lotes_codigos?: string[];
  vence_primeiro: string | null;
  vence_em_7_dias: boolean;
};

export type ParecidoPar = {
  a: { id: string; nome: string };
  b: { id: string; nome: string };
  unidade_base: string;
};

export type IngredientesLista = {
  ingredientes: IngredienteLinha[];
  pares_parecidos: ParecidoPar[];
  categorias: { nome: string; total: number }[];
};

/** Um ingrediente que a padaria já tem, como a busca e a sugestão o devolvem. */
export type IngredienteBusca = {
  id: string;
  nome: string;
  categoria: string;
  unidade_base: string;
  apelidos: string[];
  saldo: number;
  itens: number;
  pontuacao?: number;
  achado_por?: string | null;
};

/** Uma entrada do catálogo de referência (só sugere; ainda não existe na padaria). */
export type CatalogoSugerido = {
  id: string;
  nome: string;
  categoria: string;
  unidade_base: string;
  apelidos: string[];
  pontuacao?: number;
};

/** Ingrediente juntado ou inativo: a busca não o oferece; a tela pode reativar. */
export type Juntado = {
  id: string;
  nome: string;
  destino_id: string | null;
  destino_nome: string | null;
  /** Dia da junção, AAAA-MM-DD, no fuso da padaria. */
  juntado_em: string | null;
};

export type BuscaIngredientes = {
  q: string;
  da_padaria: IngredienteBusca[];
  do_catalogo: CatalogoSugerido[];
  juntados?: Juntado[];
};

export type Sugestao = {
  origem: "item_existente" | "item_parecido" | "ingrediente" | "catalogo";
  /** Ordem de confiança: 1 o item já existe; 2 o nome está no item; 3 item parecido; 4 semelhança. */
  nivel: number;
  motivo: string;
  travado: boolean;
  /** Só a 1ª, e só com certeza (nível 1 ou 2, claramente à frente): vem pré-preenchida para clique ou Enter. */
  destaque: boolean;
  ingrediente: IngredienteBusca | null;
  catalogo: CatalogoSugerido | null;
};

export type NovoIngrediente = {
  nome: string;
  unidade_base: string;
  categoria: string;
  apelidos?: string[];
};

export type Movimento = {
  id: string;
  /** Junção que na verdade foi "Trocar ingrediente" de um item. */
  troca?: boolean;
  /** Junção que na verdade devolveu o ingrediente à lista, sem mover itens. */
  reativacao?: boolean;
  tipo: "entrada" | "ajuste" | "juncao" | string;
  quando: string;
  quantidade_base: number;
  motivo: string | null;
  lote: string | null;
  item: string | null;
  de: string | null;
  para: string | null;
};

export type IngredienteDetalhe = IngredienteLinha & {
  custo_medio_base: number | null;
  lotes_com_custo: number;
  lotes_com_saldo: number;
  itens_detalhe: {
    id: string;
    nome: string;
    marca: string;
    unidade_controle: string;
    conteudo_embalagem: number | null;
    saldo: number;
  }[];
  lotes_detalhe: {
    id: string;
    item_id?: string;
    codigo: string;
    item: string;
    marca: string;
    local: string;
    validade: string | null;
    sem_validade: boolean;
    saldo: number;
    custo_unidade_base: number | null;
    /** Tudo o que entrou neste lote por entrada (unidade base) e quanto custou, com o custo gravado. */
    quantidade_comprada_base?: number;
    valor_do_lote?: number | null;
    vence_em_7_dias?: boolean;
    custo_corrigido?: boolean;
    custo_antes?: number | null;
    custo_depois?: number | null;
  }[];
  movimentos: Movimento[];
  correcoes_custo?: CorrecaoDeCusto[];
  juntado_em_id: string | null;
};

/** Uma correção de custo de lote (histórico: quem, quando, antes, depois, motivo). */
export type CorrecaoDeCusto = {
  id: string;
  quando: string;
  quem: string | null;
  lote?: string;
  item?: string;
  modo: ModoCusto;
  valor_pago: number | null;
  preco_informado?: number | null;
  /** R$ por g, ml ou un. Antes vazio = o custo era desconhecido. */
  custo_antes: number | null;
  custo_depois: number;
  quantidade_base: number;
  motivo: string;
};

/** O lote para o diálogo "Corrigir custo": o que foi comprado, o custo de hoje e o histórico. */
export type CustoDoLote = {
  id: string;
  codigo: string;
  item: string;
  marca: string;
  ingrediente_id: string;
  ingrediente: string;
  unidade_base: "g" | "ml" | "un" | string;
  unidade_controle: ControleUnidade;
  conteudo_embalagem: number | null;
  quantidade_comprada_base: number;
  custo_unidade_base: number | null;
  valor_pago_atual: number | null;
  historico: CorrecaoDeCusto[];
};

export type Local = { id: string; nome: string; padrao: boolean; ativo: boolean };

export type Membro = {
  id: string;
  usuario: string;
  nome: string;
  papel: Papel | string;
  ativo: boolean;
  email_contato: string | null;
  voce: boolean;
};

// ---------------------------------------------------------------- base

export class ApiError extends Error {
  status: number;
  codigo: string;
  detalhe: unknown;
  constructor(status: number, message: string, codigo = "", detalhe: unknown = null) {
    super(message);
    this.status = status;
    this.codigo = codigo;
    this.detalhe = detalhe;
  }
}

let csrf = "";
let onSessaoPerdida: (() => void) | null = null;

export function definirCsrf(valor: string) {
  csrf = valor;
}

export function aoPerderSessao(callback: (() => void) | null) {
  onSessaoPerdida = callback;
}

async function chamar(method: string, caminho: string, corpo?: unknown): Promise<Response> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (corpo !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (method !== "GET") {
    headers["X-CSRF-Token"] = csrf;
  }
  return fetch(`/api/v1${caminho}`, {
    method,
    headers,
    credentials: "same-origin",
    body: corpo === undefined ? undefined : JSON.stringify(corpo),
  });
}

/** O servidor responde `{detail: "texto"}` ou `{detail: {codigo, mensagem, ...}}` ou (422 do Pydantic) uma lista. */
async function lerErro(resposta: Response): Promise<ApiError> {
  try {
    const dados = (await resposta.json()) as { detail?: unknown };
    const d = dados.detail;
    if (typeof d === "string") {
      return new ApiError(resposta.status, d);
    }
    if (d && typeof d === "object" && !Array.isArray(d)) {
      const obj = d as { codigo?: string; mensagem?: string };
      return new ApiError(resposta.status, obj.mensagem ?? "", obj.codigo ?? "", d);
    }
    if (Array.isArray(d)) {
      return new ApiError(resposta.status, "Confira os dados informados.", "dados_invalidos", d);
    }
  } catch {
    // corpo vazio ou não JSON
  }
  return new ApiError(resposta.status, "");
}

async function pedir<T>(method: string, caminho: string, corpo?: unknown, tentouDeNovo = false): Promise<T> {
  const resposta = await chamar(method, caminho, corpo);
  if (resposta.ok) {
    if (resposta.status === 204) {
      return undefined as T;
    }
    return (await resposta.json()) as T;
  }
  // O CSRF muda quando outra aba recarrega a sessão: busca um novo e tenta uma vez mais.
  const erro = await lerErro(resposta);
  // 403 sem código = CSRF vencido. Os 403 de regra (sem_organizacao, papel_insuficiente...) têm código.
  if (resposta.status === 403 && method !== "GET" && !tentouDeNovo && erro.codigo === "") {
    const nova = await chamar("GET", "/auth/sessao?rotacionar=true");
    if (nova.ok) {
      definirCsrf(((await nova.json()) as SessaoInfo).csrf);
      return pedir<T>(method, caminho, corpo, true);
    }
  }
  if (resposta.status === 401 && caminho !== "/auth/entrar" && caminho !== "/auth/sessao") {
    onSessaoPerdida?.();
  }
  throw erro;
}

export function textoDoErro(erro: unknown, padrao = "Não foi possível concluir agora. Tente de novo em instantes."): string {
  if (erro instanceof ApiError && erro.message) {
    return erro.message;
  }
  return padrao;
}

// ---------------------------------------------------------------- sessão

export async function carregarSessao(): Promise<SessaoInfo | null> {
  try {
    const sessao = await pedir<SessaoInfo>("GET", "/auth/sessao?rotacionar=true");
    definirCsrf(sessao.csrf);
    return sessao;
  } catch (erro) {
    if (erro instanceof ApiError && erro.status === 401) {
      return null;
    }
    throw erro;
  }
}

export async function entrar(usuario: string, senha: string): Promise<SessaoInfo> {
  const sessao = await pedir<SessaoInfo>("POST", "/auth/entrar", { usuario, senha });
  definirCsrf(sessao.csrf);
  return sessao;
}

export async function escolherOrganizacao(organizacaoId: string): Promise<SessaoInfo> {
  const sessao = await pedir<SessaoInfo>("POST", "/auth/organizacao", { organizacao_id: organizacaoId });
  definirCsrf(sessao.csrf);
  return sessao;
}

export async function sair(): Promise<void> {
  try {
    await pedir<{ status: string }>("POST", "/auth/sair");
  } finally {
    definirCsrf("");
  }
}

// ---------------------------------------------------------------- telas

export const carregarHoje = (dias: number) => pedir<Hoje>("GET", `/hoje?dias=${dias}`);
export const carregarFluxo = () => pedir<Fluxo>("GET", "/fluxo");
export const carregarCatalogo = () => pedir<Catalogo>("GET", "/catalogo");

export const listarEntradas = (filtro: FiltroEntradas) =>
  pedir<{ filtro: string; entradas: EntradaResumo[] }>("GET", `/entradas?filtro=${filtro}`).then((r) => r.entradas);
export const detalheEntrada = (id: string) => pedir<EntradaDetalhe>("GET", `/entradas/${id}`);
export const verificarEntrada = (linhas: LinhaEnvio[]) =>
  pedir<{ linhas: AnaliseLinha[] }>("POST", "/entradas/verificar", { linhas }).then((r) => r.linhas);
export const lancarEntrada = (corpo: EntradaEnvio) => pedir<EntradaDetalhe>("POST", "/entradas", corpo);
export const informarValidade = (loteId: string, corpo: { validade?: string; sem_validade?: boolean }) =>
  pedir<{ id: string }>("PATCH", `/lotes/${loteId}`, corpo);

export const listarIngredientes = (filtro: FiltroIngredientes, categoria = "") =>
  pedir<IngredientesLista>("GET", `/ingredientes?filtro=${filtro}${categoria ? `&categoria=${encodeURIComponent(categoria)}` : ""}`);
export const buscarIngredientes = (q: string) =>
  pedir<BuscaIngredientes>("GET", `/ingredientes/busca?q=${encodeURIComponent(q)}`);
export const sugerirIngrediente = (item: string, marca = "", soCatalogo = false, exceto = "") =>
  pedir<{ item: string; sugestoes: Sugestao[] }>(
    "GET",
    `/ingredientes/sugestao?item=${encodeURIComponent(item)}&marca=${encodeURIComponent(marca)}${soCatalogo ? "&so_catalogo=true" : ""}${exceto ? `&exceto=${encodeURIComponent(exceto)}` : ""}`,
  ).then((r) => r.sugestoes);
export const detalheIngrediente = (id: string) => pedir<IngredienteDetalhe>("GET", `/ingredientes/${id}`);
/** Só depois do diálogo "Confirmo que não existe, cadastrar": o servidor grava quem confirmou e quando. */
export const criarIngrediente = (corpo: NovoIngrediente) =>
  pedir<IngredienteDetalhe>("POST", "/ingredientes", { ...corpo, confirmado_inexistente: true });
export const editarIngrediente = (
  id: string,
  corpo: { nome?: string; unidade_base?: string; categoria?: string; apelidos?: string[] },
) =>
  pedir<IngredienteDetalhe>("PATCH", `/ingredientes/${id}`, corpo);
export const ajustarSaldo = (id: string, corpo: { lote_id: string; saldo_contado_base: number; motivo: string }) =>
  pedir<IngredienteDetalhe>("POST", `/ingredientes/${id}/ajustes`, corpo);
export const custoDoLote = (loteId: string) => pedir<CustoDoLote>("GET", `/lotes/${loteId}/custo`);
/** Informe `valor_pago` (total, R$) OU `preco_unidade` (R$ por kg, L ou embalagem). Nunca muda o saldo. */
export const corrigirCusto = (
  loteId: string,
  corpo: { valor_pago?: number; preco_unidade?: number; motivo: string },
) => pedir<CustoDoLote>("POST", `/lotes/${loteId}/custo`, corpo);
/** Liga o item a outro ingrediente (os lotes e o saldo vão junto). Devolve o ingrediente que passou a ter o item. */
export const trocarIngrediente = (itemId: string, corpo: { ingrediente_id: string; motivo: string }) =>
  pedir<IngredienteDetalhe>("POST", `/itens/${itemId}/trocar-ingrediente`, corpo);
export const juntarIngredientes = (mantem_id: string, remove_id: string) =>
  pedir<IngredienteDetalhe>("POST", "/ingredientes/juntar", { mantem_id, remove_id });
/** Deixa o ingrediente disponível de novo. Não move os itens de volta. */
export const reativarIngrediente = (id: string, motivo: string) =>
  pedir<IngredienteDetalhe>("POST", `/ingredientes/${id}/reativar`, { motivo });
export const marcarDistintos = (a_id: string, b_id: string) =>
  pedir<void>("POST", "/ingredientes/distintos", { a_id, b_id });

// ---------------------------------------------------------------- produtos

export type FiltroProdutos = "todos" | "produzidos" | "comprados" | "componentes" | "pendentes";

export type ProdutoLinha = {
  id: string;
  nome: string;
  codigo: string | null;
  modalidade: "produzido" | "comprado";
  uso_venda: boolean;
  uso_componente: boolean;
  familia_id: string | null;
  familia: string | null;
  unidade_venda: "un" | "kg";
  ativo: boolean;
  selos: string[];
  pendente: boolean;
  foto_url: string | null;
  tem_foto: boolean;
  foto_enviada_em: string | null;
};

export type ItemDeProduto = {
  id: string;
  nome: string;
  marca: string;
  saldo: number;
  unidade_base: string;
  custo_medio_base?: number | null;
  ingrediente_id: string;
  ingrediente: string;
};

export type LinhaReceita = {
  id: string;
  nome: string;
  componente: boolean;
  quantidade: number | null;
  unidade: string;
};

export type ProdutoDetalhe = ProdutoLinha & {
  observacao: string | null;
  peso_unidade_g: number | null;
  unidade_base: "g" | "ml" | "un" | null;
  receita: {
    id: string;
    situacao: string;
    versao: number;
    publicada: boolean;
    linhas: LinhaReceita[];
    custo_por_unidade: number | null;
    custo_parcial: boolean;
    linhas_sem_custo: number;
  } | null;
  ingrediente_id: string | null;
  ingrediente: string | null;
  item: ItemDeProduto | null;
  usado_em: { id: string; nome: string }[];
  importado_em: string | null;
};

export type ProdutosLista = {
  filtro: string;
  produtos: ProdutoLinha[];
  familias: { id: string; nome: string; total: number }[];
};

export type FamiliasLista = {
  familias: { id: string; nome: string }[];
  sugestoes: string[];
};

export type ProdutoEnvio = {
  nome: string;
  modalidade?: "produzido" | "comprado";
  uso_venda: boolean;
  uso_componente: boolean;
  familia_id: string | null;
  unidade_venda: "un" | "kg";
  unidade_base?: "g" | "ml" | "un" | null;
  item_estoque_id?: string | null;
  confirmado_inexistente?: boolean;
};

export type UnidadeReceita = "g" | "kg" | "ml" | "l" | "un";
export type FiltroReceitas = "todas" | "rascunhos" | "publicadas" | "custo_parcial";
export type AbaReceita = "ingredientes" | "modo" | "rendimento" | "revisar";

export type LinhaReceitaEditor = {
  id: string;
  ingrediente_id: string | null;
  nome: string;
  categoria: string | null;
  componente: boolean;
  unidade_base: string | null;
  texto: string | null;
  a_decidir: boolean;
  quantidade: number | null;
  unidade: UnidadeReceita;
  ordem: number;
  observacao: string | null;
  percentual_padeiro: number | null;
  custo: number | null;
  origem: "manual" | "estimado" | "conferido";
  faixa_min: number | null;
  faixa_max: number | null;
  funcao?: FuncaoLinha;
};

export type FuncaoLinha = "massa" | "recheio" | "cobertura" | "finalizacao";
export type FormatoPao = "forma" | "forma_enriquecida" | "livre" | "assadeira" | "pequeno";

export type ExplicacaoPerda = {
  faixa: string;
  fonte: string | null;
  fonte_url: string | null;
  nota: string | null;
  n_medicoes: number;
  desvio_processo: number | null;
  desvio_coccao: number | null;
  medicoes: {
    data: string | null;
    massa_total_g: number;
    pecas: number;
    peso_cru_medio_g: number;
    peso_final_medio_g: number;
  }[];
};

export type PerdaResolvida = {
  percentual: number | null;
  origem: "medido" | "padrao" | "referencia" | "manual" | null;
  rotulo: string;
  motivo: string | null;
  explicacao: ExplicacaoPerda;
};

export type PerdasReceita = {
  formato: FormatoPao | null;
  peso_final_g: number | null;
  unidades_desejadas: number | null;
  processo: PerdaResolvida;
  coccao: PerdaResolvida;
  peso_cru_g: number | null;
  unidades: number | null;
  massa_necessaria_g: number | null;
};

export type ReceitaFicha = {
  id: string;
  produto_id: string;
  produto: string;
  situacao: "rascunho" | "publicada";
  versao: number;
  rendimento_quantidade: number | null;
  rendimento_unidade: UnidadeReceita | null;
  rendimento: string | null;
  peso_unidade_g: number | null;
  perda_percentual: number | null;
  formato?: FormatoPao | null;
  unidades_desejadas?: number | null;
  modo_fazer: string[];
  selos: string[];
  publicada: { versao: number; linhas: { quantidade: number; unidade: string; nome: string }[] } | null;
  linhas: LinhaReceitaEditor[];
  total_massa_g: number | null;
  custo_total: number | null;
  custo_parcial: boolean;
  linhas_sem_custo: number;
  custo_por_unidade: number | null;
  verificacoes?: { pendencias: { codigo: string; mensagem: string }[]; avisos: { codigo: string; mensagem: string }[] };
  perdas?: PerdasReceita;
};

export type ReceitaListaItem = {
  id: string;
  produto_id: string;
  nome: string;
  rendimento: string | null;
  custo_por_unidade: number | null;
  custo_parcial: boolean;
  situacao: string;
  selos: string[];
  versao: number;
};

export const listarReceitas = (filtro: FiltroReceitas) =>
  pedir<{ filtro: string; receitas: ReceitaListaItem[] }>("GET", `/receitas?filtro=${filtro}`);
export const detalheReceita = (produtoId: string) => pedir<ReceitaFicha>("GET", `/receitas/${produtoId}`);
export const salvarReceita = (
  produtoId: string,
  corpo: {
    linhas: {
      ingrediente_id?: string | null;
      texto?: string | null;
      quantidade: number;
      unidade: UnidadeReceita;
      observacao?: string | null;
      origem?: "manual" | "estimado" | "conferido";
      faixa_min?: number | null;
      faixa_max?: number | null;
      funcao?: FuncaoLinha;
    }[];
    rendimento_quantidade?: number | null;
    rendimento_unidade?: UnidadeReceita | null;
    peso_unidade_g: number | null;
    perda_percentual: number;
    modo_fazer: string[];
    formato?: FormatoPao | null;
    unidades_desejadas?: number | null;
    processo?: { percentual?: number | null; origem: "manual" | null; motivo?: string | null };
    coccao?: { percentual?: number | null; origem: "manual" | null; motivo?: string | null };
  },
) => pedir<ReceitaFicha>("PUT", `/receitas/${produtoId}`, corpo);
export const publicarReceita = (produtoId: string, confirmarSemFermento = false) =>
  pedir<ReceitaFicha>("POST", `/receitas/${produtoId}/publicar`, {
    confirmar_sem_fermento: confirmarSemFermento,
  });

export type GigioSituacao = { disponivel: boolean; motivo: string | null; usadas: number; limite: number };
export type LinhaSugestao = {
  ingrediente_id: string | null;
  nome: string;
  texto: string | null;
  a_decidir: boolean;
  quantidade: number;
  unidade: UnidadeReceita;
  percentual: number | null;
  faixa_min: number | null;
  faixa_max: number | null;
  confianca: "alta" | "media" | "baixa";
  motivo: string;
  fixa: boolean;
  origem: "manual" | "estimado" | "conferido";
  fora_estoque?: boolean;
  funcao?: FuncaoLinha;
};
export type SubstituicaoGigio = {
  nome: string;
  percentual: number;
  quantidade_g: number;
  motivo: string;
  confianca: "alta" | "media" | "baixa";
};
export type VerificacaoGigio = { codigo: string; mensagem: string };
export type SugestaoGigio = {
  id: string;
  linhas: LinhaSugestao[];
  substituicoes?: SubstituicaoGigio[];
  rendimento_g: number | null;
  perda_pct: number | null;
  modo_de_fazer: string[];
  observacoes: string;
  avisos: string[];
  verificacoes?: { pendencias: VerificacaoGigio[]; avisos: VerificacaoGigio[] };
};
export const situacaoGigio = () => pedir<GigioSituacao>("GET", "/gigio/situacao");
export const sugerirGigio = (
  produtoId: string,
  corpo: {
    descricao: string;
    massa_base_id: string | null;
    massa_base_quantidade: number | null;
    linhas_fixas: { ingrediente_id: string | null; texto: string | null; quantidade: number; unidade: UnidadeReceita }[];
    rendimento_quantidade: number | null;
    rendimento_unidade: UnidadeReceita | null;
  },
) => pedir<SugestaoGigio>("POST", `/receitas/${produtoId}/sugestao-gigio`, corpo);
export const aplicarSugestao = (
  produtoId: string,
  corpo: {
    linhas: {
      ingrediente_id: string | null;
      texto: string | null;
      quantidade: number;
      unidade: UnidadeReceita;
      origem: "manual" | "estimado" | "conferido";
      faixa_min: number | null;
      faixa_max: number | null;
      fixa: boolean;
      funcao?: FuncaoLinha;
    }[];
    substituicoes?: { nome: string; percentual: number; quantidade_g: number }[];
    confirmar_sem_fermento?: boolean;
    rendimento_g: number | null;
    perda_pct: number | null;
    modo_de_fazer: string[];
  },
) => pedir<ReceitaFicha>("POST", `/receitas/${produtoId}/aplicar-sugestao`, corpo);

export type PadraoPadaria = {
  id: string;
  nome: string;
  termo: string;
  ingrediente_id: string | null;
  ingrediente: string | null;
  percentual: number;
  observacao: string | null;
  ativo: boolean;
};
export const listarPadroes = () => pedir<{ padroes: PadraoPadaria[] }>("GET", "/padroes").then((r) => r.padroes);
export const salvarPadrao = (id: string, corpo: Omit<PadraoPadaria, "id" | "ingrediente">) =>
  pedir<PadraoPadaria>("PATCH", `/padroes/${id}`, corpo);
export const criarPadrao = (corpo: Omit<PadraoPadaria, "id" | "ingrediente">) =>
  pedir<PadraoPadaria>("POST", "/padroes", corpo);

export type PadraoPerda = {
  id: string;
  tipo: string;
  tipo_rotulo: string;
  formato: string | null;
  formato_rotulo: string;
  faixa: string;
  rotulo: string;
  observacao: string;
  ativo: boolean;
};
export type ReferenciaPerda = {
  id: string;
  tipo_rotulo: string;
  formato_rotulo: string;
  faixa: string;
  sugerido: string;
  fonte: string;
  fonte_url: string | null;
  nota: string | null;
};
export const listarPerdas = () => pedir<{ padroes: PadraoPerda[]; referencias: ReferenciaPerda[] }>("GET", "/perdas");

export const listarProdutos = (filtro: FiltroProdutos, familiaId = "") =>
  pedir<ProdutosLista>(
    "GET",
    `/produtos?filtro=${filtro}${familiaId ? `&familia_id=${encodeURIComponent(familiaId)}` : ""}`,
  );
export const detalheProduto = (id: string) => pedir<ProdutoDetalhe>("GET", `/produtos/${id}`);
export const criarProduto = (corpo: ProdutoEnvio) => pedir<ProdutoDetalhe>("POST", "/produtos", corpo);
export const editarProduto = (id: string, corpo: Omit<ProdutoEnvio, "modalidade">) =>
  pedir<ProdutoDetalhe>("PATCH", `/produtos/${id}`, corpo);
export const inativarProduto = (id: string) => pedir<{ id: string; ativo: boolean }>("POST", `/produtos/${id}/inativar`);
export const removerFoto = (id: string) => pedir<ProdutoDetalhe>("DELETE", `/produtos/${id}/foto`);

export function enviarFoto(id: string, arquivo: File, aoProgresso: (pct: number) => void): Promise<ProdutoDetalhe> {
  const tentar = (jaTentou: boolean): Promise<ProdutoDetalhe> =>
    new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `/api/v1/produtos/${id}/foto`);
      xhr.withCredentials = true;
      xhr.setRequestHeader("Accept", "application/json");
      xhr.setRequestHeader("X-CSRF-Token", csrf);
      xhr.upload.onprogress = (ev) => {
        if (ev.lengthComputable) aoProgresso(Math.round((ev.loaded / ev.total) * 100));
      };
      xhr.onerror = () => reject(new ApiError(0, "Não foi possível enviar a foto."));
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(JSON.parse(xhr.responseText) as ProdutoDetalhe);
          return;
        }
        let erro = new ApiError(xhr.status, "");
        try {
          const dados = JSON.parse(xhr.responseText) as { detail?: { codigo?: string; mensagem?: string } };
          const d = dados.detail;
          if (d && typeof d === "object") erro = new ApiError(xhr.status, d.mensagem ?? "", d.codigo ?? "", d);
        } catch {
          /* corpo vazio */
        }
        if (xhr.status === 403 && erro.codigo === "" && !jaTentou) {
          void pedir<SessaoInfo>("GET", "/auth/sessao?rotacionar=true")
            .then((sessao) => {
              definirCsrf(sessao.csrf);
              return tentar(true);
            })
            .then(resolve, reject);
          return;
        }
        reject(erro);
      };
      const corpo = new FormData();
      corpo.append("arquivo", arquivo);
      xhr.send(corpo);
    });
  return tentar(false);
}
export const listarFamilias = () => pedir<FamiliasLista>("GET", "/familias");
export const criarFamilia = (nome: string) => pedir<{ id: string; nome: string }>("POST", "/familias", { nome });
export const apagarFamilia = (id: string) => pedir<void>("DELETE", `/familias/${id}`);
export const dispensarSugestoesFamilia = () => pedir<void>("POST", "/familias/dispensar-sugestoes");
export const buscarItensEstoque = (q: string) =>
  pedir<{ itens: ItemDeProduto[] }>("GET", `/produtos/itens?q=${encodeURIComponent(q)}`).then((r) => r.itens);

export const listarLocais = () => pedir<Local[]>("GET", "/locais");
export const criarLocal = (nome: string) => pedir<Local>("POST", "/locais", { nome });
export const alterarLocal = (id: string, corpo: { nome?: string; ativo?: boolean; padrao?: boolean }) =>
  pedir<Local>("PATCH", `/locais/${id}`, corpo);

export const listarMembros = () => pedir<Membro[]>("GET", "/usuarios");
export const criarMembro = (corpo: {
  usuario: string;
  nome: string;
  papel: string;
  senha: string;
  email_contato?: string;
}) => pedir<Membro>("POST", "/usuarios", corpo);
export const alterarMembro = (id: string, corpo: { papel?: string; ativo?: boolean }) =>
  pedir<Membro>("PATCH", `/usuarios/${id}`, corpo);

export type FornadaProducao = {
  id: string;
  nome: string;
  horario: string;
  ordem: number;
  ativa: boolean;
};

export type OrdemProducao = {
  id: string;
  data: string;
  fornada_id: string;
  produto_id: string;
  produto: string;
  unidades: number;
  origem: "programada" | "loja" | "avulsa" | string;
  origem_rotulo: string;
  situacao: string;
  situacao_rotulo: string;
  pecas: string | null;
  massa_necessaria_g: number | null;
  massa: string | null;
  sem_receita: boolean;
  aviso: string | null;
  demanda_diferenca: number | null;
  diferenca_texto: string | null;
  observacao: string | null;
  via: number;
  comanda_numero: number | null;
};

export type CalendarioProducao = {
  hoje: string;
  de: string;
  ate: string;
  fornadas: FornadaProducao[];
  ordens: OrdemProducao[];
};

export type Programacao = {
  id: string;
  produto_id: string;
  produto: string;
  quantidade_por_fornada: number;
  fornada_ids: string[];
  dias_semana: number[];
  inicio: string | null;
  fim: string | null;
  ativa: boolean;
};

export type SemVinculo = {
  data: string;
  nome: string;
  unidades: number;
  pedidos: string[];
};

export type LinhaComanda = {
  nome: string;
  funcao: string;
  funcao_rotulo: string;
  quantidade_g: string;
  texto: string;
  componente: boolean;
  filhos: LinhaComanda[];
};

export type Comanda = {
  data: string;
  fornada: FornadaProducao;
  numero: number | null;
  via: number;
  via_rotulo: string | null;
  impressa_em: string | null;
  impressa_por: string | null;
  produtos: {
    ordem_id: string;
    produto: string;
    unidades: number;
    pecas: string | null;
    massa: string | null;
    sem_receita: boolean;
    aviso: string | null;
    linhas: LinhaComanda[];
    modo_fazer: string[];
    observacao: string | null;
  }[];
  pesagem: { nome: string; quantidade_g: string; texto: string }[];
};

export const carregarProducao = (consulta: { data?: string; de?: string; ate?: string }) => {
  const q = new URLSearchParams();
  if (consulta.data) q.set("data", consulta.data);
  if (consulta.de) q.set("de", consulta.de);
  if (consulta.ate) q.set("ate", consulta.ate);
  const suffix = q.toString();
  return pedir<CalendarioProducao>("GET", `/producao${suffix ? `?${suffix}` : ""}`);
};
export const listarFornadas = () => pedir<{ fornadas: FornadaProducao[] }>("GET", "/producao/fornadas");
export const salvarFornada = (id: string | null, corpo: Omit<FornadaProducao, "id">) =>
  id ? pedir<FornadaProducao>("PATCH", `/producao/fornadas/${id}`, corpo) : pedir<FornadaProducao>("POST", "/producao/fornadas", corpo);
export const listarProgramacoes = () => pedir<{ programacoes: Programacao[] }>("GET", "/producao/programacoes");
export const salvarProgramacao = (id: string | null, corpo: Omit<Programacao, "id" | "produto">) =>
  id
    ? pedir<Programacao>("PATCH", `/producao/programacoes/${id}`, corpo)
    : pedir<Programacao>("POST", "/producao/programacoes", corpo);
export const criarOrdem = (corpo: { data: string; fornada_id: string; produto_id: string; unidades: number; observacao?: string }) =>
  pedir<OrdemProducao>("POST", "/producao/ordens", corpo);
export const alterarOrdem = (id: string, corpo: { unidades?: number; fornada_id?: string; observacao?: string }) =>
  pedir<OrdemProducao>("PATCH", `/producao/ordens/${id}`, corpo);
export const cancelarOrdem = (id: string) => pedir<OrdemProducao>("POST", `/producao/ordens/${id}/cancelar`);
export const trazerLoja = (de: string, ate: string) =>
  pedir<{ sem_vinculo: SemVinculo[]; fornada_id: string }>("POST", "/producao/trazer-loja", { de, ate });
export const carregarComanda = (data: string, fornada: string) =>
  pedir<Comanda>("GET", `/producao/comanda?data=${encodeURIComponent(data)}&fornada=${encodeURIComponent(fornada)}`);
export const imprimirComanda = (data: string, fornada_id: string) =>
  pedir<Comanda>("POST", "/producao/comanda/imprimir", { data, fornada_id });
