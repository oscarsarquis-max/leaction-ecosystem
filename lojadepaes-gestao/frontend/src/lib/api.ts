export type SessaoInfo = {
  usuario: string;
  nome: string;
  papel: "dono" | "operador" | "somente_leitura" | string;
  permissoes: string[];
  csrf: string;
  fuso: string;
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

export type Hoje = {
  hoje: string;
  ate: string;
  dias: number;
  compatibilidade: {
    ok: boolean;
    versao_loja: string | null;
    versao_conhecida: boolean | null;
    mensagem: string | null;
  };
  fornadas: Fornada[];
  total_paes_fisicos: number;
};

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
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

async function mensagemDe(resposta: Response): Promise<string> {
  try {
    const dados = (await resposta.json()) as { detail?: unknown };
    return typeof dados.detail === "string" ? dados.detail : "";
  } catch {
    return "";
  }
}

async function pedir<T>(method: string, caminho: string, corpo?: unknown, tentouDeNovo = false): Promise<T> {
  const resposta = await chamar(method, caminho, corpo);
  if (resposta.ok) {
    return (await resposta.json()) as T;
  }
  // O CSRF muda quando outra aba recarrega a sessão: busca um novo e tenta uma vez mais.
  if (resposta.status === 403 && method !== "GET" && !tentouDeNovo) {
    const nova = await chamar("GET", "/auth/sessao?rotacionar=true");
    if (nova.ok) {
      definirCsrf(((await nova.json()) as SessaoInfo).csrf);
      return pedir<T>(method, caminho, corpo, true);
    }
  }
  if (resposta.status === 401 && caminho !== "/auth/entrar" && caminho !== "/auth/sessao") {
    onSessaoPerdida?.();
  }
  throw new ApiError(resposta.status, await mensagemDe(resposta));
}

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

export async function sair(): Promise<void> {
  try {
    await pedir<{ status: string }>("POST", "/auth/sair");
  } finally {
    definirCsrf("");
  }
}

export function carregarHoje(dias: number): Promise<Hoje> {
  return pedir<Hoje>("GET", `/hoje?dias=${dias}`);
}
