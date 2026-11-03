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

export type Hoje = {
  hoje: string;
  ate: string;
  dias: number;
  fonte_loja: boolean;
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
  valor: number | null;
  valor_parcial: boolean;
  situacao: "completa" | "pendente";
};

export type EntradaLinhaDetalhe = {
  posicao: number;
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
  custo: number | null;
  custo_por: string | null;
  valor_total: number | null;
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

export type LinhaEnvio = {
  item_id?: string | null;
  item_nome?: string;
  marca?: string;
  unidade_controle?: ControleUnidade | null;
  conteudo_embalagem?: number | null;
  ingrediente_id?: string | null;
  ingrediente_nome?: string;
  ingrediente_unidade_base?: "g" | "ml" | "un" | null;
  decisao_item?: "novo" | null;
  decisao_ingrediente?: "novo" | null;
  quantidade?: number | null;
  unidade?: string;
  lote_codigo?: string;
  validade?: string | null;
  sem_validade?: boolean;
  custo?: number | null;
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
  ingrediente_igual: IngredienteRef | null;
  ingrediente_parecidos: IngredienteRef[];
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
  ingredientes: IngredienteRef[];
  itens: {
    id: string;
    nome: string;
    marca: string;
    unidade_controle: ControleUnidade;
    conteudo_embalagem: number | null;
    ingrediente_id: string;
    ingrediente: string;
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
  ativo: boolean;
  saldo: number;
  itens: number;
  lotes: number;
  vence_primeiro: string | null;
  vence_em_7_dias: boolean;
};

export type ParecidoPar = {
  a: { id: string; nome: string };
  b: { id: string; nome: string };
  unidade_base: string;
};

export type IngredientesLista = { ingredientes: IngredienteLinha[]; pares_parecidos: ParecidoPar[] };

export type Movimento = {
  id: string;
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
    codigo: string;
    item: string;
    marca: string;
    local: string;
    validade: string | null;
    sem_validade: boolean;
    saldo: number;
    custo_unidade_base: number | null;
  }[];
  movimentos: Movimento[];
  juntado_em_id: string | null;
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

export const listarIngredientes = (filtro: FiltroIngredientes) =>
  pedir<IngredientesLista>("GET", `/ingredientes?filtro=${filtro}`);
export const detalheIngrediente = (id: string) => pedir<IngredienteDetalhe>("GET", `/ingredientes/${id}`);
export const criarIngrediente = (nome: string, unidade_base: string, confirmar_novo = false) =>
  pedir<IngredienteDetalhe>("POST", "/ingredientes", { nome, unidade_base, confirmar_novo });
export const editarIngrediente = (id: string, corpo: { nome?: string; unidade_base?: string }) =>
  pedir<IngredienteDetalhe>("PATCH", `/ingredientes/${id}`, corpo);
export const ajustarSaldo = (id: string, corpo: { lote_id: string; saldo_contado_base: number; motivo: string }) =>
  pedir<IngredienteDetalhe>("POST", `/ingredientes/${id}/ajustes`, corpo);
export const juntarIngredientes = (mantem_id: string, remove_id: string) =>
  pedir<IngredienteDetalhe>("POST", "/ingredientes/juntar", { mantem_id, remove_id });
export const marcarDistintos = (a_id: string, b_id: string) =>
  pedir<void>("POST", "/ingredientes/distintos", { a_id, b_id });

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
