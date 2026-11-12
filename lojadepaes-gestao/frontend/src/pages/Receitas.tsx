import { Fragment, useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { definirGuardaSaida } from "../lib/guardaSaida";
import { useGestao } from "../contexto";
import {
  ApiError,
  buscarIngredientes,
  detalheReceita,
  listarReceitas,
  publicarReceita,
  salvarReceita,
  situacaoGigio,
  textoDoErro,
  type GigioSituacao,
  type AbaReceita,
  type FiltroReceitas,
  type FormatoPao,
  type FuncaoLinha,
  type PerdaResolvida,
  type ReceitaFicha,
  type ReceitaListaItem,
  type UnidadeReceita,
} from "../lib/api";
import { casaBusca } from "../lib/buscaLista";
import { dinheiro, quantidadeBase } from "../lib/format";
import { useTabela } from "../lib/useNarrow";
import { CampoIngrediente, type IngredienteEscolhido } from "../shell/CampoIngrediente";
import { Button } from "../shell/Button";
import { Card } from "../shell/Card";
import { Chips } from "../shell/Chips";
import { PageHeader } from "../shell/PageHeader";
import { SidePanel } from "../shell/SidePanel";
import { StatusChip } from "../shell/StatusChip";
import { PainelGigio } from "./GigioReceita";
import "./fluxo.css";

const FILTROS: { valor: FiltroReceitas; rotulo: string }[] = [
  { valor: "todas", rotulo: "Todas" },
  { valor: "rascunhos", rotulo: "Rascunhos" },
  { valor: "publicadas", rotulo: "Publicadas" },
  { valor: "custo_parcial", rotulo: "Custo parcial" },
];

const ABAS: { valor: AbaReceita; rotulo: string }[] = [
  { valor: "ingredientes", rotulo: "Ingredientes" },
  { valor: "modo", rotulo: "Modo de fazer" },
  { valor: "rendimento", rotulo: "Rendimento" },
  { valor: "revisar", rotulo: "Revisar" },
];

const FUNCOES: { valor: FuncaoLinha; rotulo: string }[] = [
  { valor: "inoculo", rotulo: "Inóculo" },
  { valor: "massa", rotulo: "Massa" },
  { valor: "recheio", rotulo: "Recheio" },
  { valor: "cobertura", rotulo: "Cobertura" },
  { valor: "finalizacao", rotulo: "Finalização" },
];

const FORMATOS: { valor: FormatoPao; rotulo: string }[] = [
  { valor: "forma", rotulo: "Forma" },
  { valor: "forma_enriquecida", rotulo: "Forma enriquecida" },
  { valor: "livre", rotulo: "Livre" },
  { valor: "assadeira", rotulo: "Assadeira" },
  { valor: "pequeno", rotulo: "Pequeno" },
];

const UNIDADES: { valor: UnidadeReceita; rotulo: string }[] = [
  { valor: "g", rotulo: "g" },
  { valor: "kg", rotulo: "kg" },
  { valor: "ml", rotulo: "ml" },
  { valor: "l", rotulo: "l" },
  { valor: "un", rotulo: "un" },
];

const SELOS: Record<string, string> = {
  rascunho: "Rascunho",
  custo_parcial: "Custo parcial",
  sem_linhas: "Sem linhas",
};

const UNIDADE_TEXTO: Record<string, UnidadeReceita> = {
  g: "g",
  gr: "g",
  grama: "g",
  gramas: "g",
  kg: "kg",
  quilo: "kg",
  quilos: "kg",
  ml: "ml",
  mililitro: "ml",
  mililitros: "ml",
  l: "l",
  litro: "l",
  litros: "l",
  un: "un",
  unidade: "un",
  unidades: "un",
};

type LinhaUi = {
  chave: string;
  ingrediente: IngredienteEscolhido | null;
  texto: string;
  quantidade: string;
  unidade: UnidadeReceita;
  observacao: string;
  percentual: number | null;
  custo: number | null;
  origem: "manual" | "estimado" | "conferido";
  faixaMin: number | null;
  faixaMax: number | null;
  funcao: FuncaoLinha;
  erro: string | null;
  obsAberta: boolean;
};

function chave() {
  return Math.random().toString(36).slice(2);
}

function linhaVazia(): LinhaUi {
  return {
    chave: chave(),
    ingrediente: null,
    texto: "",
    quantidade: "",
    unidade: "g",
    observacao: "",
    percentual: null,
    custo: null,
    origem: "manual",
    faixaMin: null,
    faixaMax: null,
    funcao: "massa",
    erro: null,
    obsAberta: false,
  };
}

function normalizar(texto: string): string {
  return texto
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function quantidadeDa(linha: LinhaUi): number {
  return Number(String(linha.quantidade).replace(",", "."));
}

function enviavel(linha: LinhaUi): boolean {
  const quantidade = quantidadeDa(linha);
  return Boolean(linha.ingrediente) && Number.isFinite(quantidade) && quantidade > 0;
}

function incompleta(linha: LinhaUi): boolean {
  const vazia = !linha.ingrediente && !linha.texto.trim() && !String(linha.quantidade).trim();
  return !vazia && !enviavel(linha);
}

function horaCurta(data: Date): string {
  return data.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

function linhasDaFicha(ficha: ReceitaFicha): LinhaUi[] {
  const linhas = ficha.linhas.map((linha) => ({
    chave: linha.id,
    ingrediente: linha.ingrediente_id
      ? {
          id: linha.ingrediente_id,
          nome: linha.nome,
          categoria: linha.categoria ?? "",
          unidade_base: linha.unidade_base ?? "g",
        }
      : null,
    texto: linha.a_decidir ? linha.nome || linha.texto || "" : "",
    quantidade: linha.quantidade == null ? "" : new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 3 }).format(linha.quantidade),
    unidade: linha.unidade,
    observacao: linha.observacao ?? "",
    percentual: linha.percentual_padeiro,
    custo: linha.custo,
    origem: linha.origem ?? "manual",
    faixaMin: linha.faixa_min,
    faixaMax: linha.faixa_max,
    funcao: linha.funcao ?? "massa",
    erro: null,
    obsAberta: false,
  }));
  return linhas.length ? linhas : [linhaVazia()];
}

/**
 * Depois da gravação automática, o servidor devolve só as linhas enviadas (completas), com ids novos.
 * A tela NÃO é trocada pela resposta: o que a pessoa digitou fica (linha sem quantidade, linha nova,
 * texto digitado durante a gravação), e a chave da linha não muda, para o campo não perder o foco.
 * Só o que o servidor calcula (% do padeiro, custo, faixa) é copiado, casando pela ordem do envio.
 */
function mesclarGravadas(atuais: LinhaUi[], enviadas: string[], nova: ReceitaFicha): LinhaUi[] {
  const doServidor = new Map<string, ReceitaFicha["linhas"][number]>();
  enviadas.forEach((chaveLocal, i) => {
    const linha = nova.linhas[i];
    if (linha) doServidor.set(chaveLocal, linha);
  });
  return atuais.map((linha) => {
    const servidor = doServidor.get(linha.chave);
    if (!servidor) return linha;
    return {
      ...linha,
      percentual: servidor.percentual_padeiro,
      custo: servidor.custo,
      faixaMin: servidor.faixa_min,
      faixaMax: servidor.faixa_max,
    };
  });
}

function filtroDaUrl(search: string): FiltroReceitas {
  const valor = new URLSearchParams(search).get("filtro");
  return FILTROS.some((f) => f.valor === valor) ? (valor as FiltroReceitas) : "todas";
}

function percento(valor: number | null): string {
  if (valor == null) return "—";
  return `${new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(valor)} %`;
}

function gramasInteiras(valor: number | null): string {
  if (valor == null) return "—";
  return `${new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 }).format(valor)} g`;
}

function seloDe(manual: boolean, resolvida: PerdaResolvida | undefined): { stage: string; label: string } {
  if (manual) return { stage: "warning", label: "ajuste manual" };
  if (resolvida?.origem === "padrao") return { stage: "ok", label: "padrão da casa" };
  if (resolvida?.origem === "medido") {
    const n = resolvida.explicacao.n_medicoes;
    return { stage: "accepted", label: `medido em ${n} ${n === 1 ? "produção" : "produções"}` };
  }
  if (resolvida?.origem === "referencia") {
    const extra = resolvida.rotulo.match(/referência \((.+)\)/)?.[1]?.replace(/, /g, " ").toLocaleLowerCase("pt-BR") ?? "";
    return { stage: "attention", label: extra ? `referência · ${extra}` : "referência" };
  }
  return { stage: "completed", label: "sem referência" };
}

function LinhaPerda({
  titulo,
  valor,
  manual,
  motivo,
  resolvida,
  aberta,
  onValor,
  onMotivo,
  onAbrir,
  onVoltar,
}: {
  titulo: string;
  valor: string;
  manual: boolean;
  motivo: string;
  resolvida: PerdaResolvida | undefined;
  aberta: boolean;
  onValor: (valor: string) => void;
  onMotivo: (valor: string) => void;
  onAbrir: () => void;
  onVoltar: () => void;
}) {
  const selo = seloDe(manual, resolvida);
  const explicacao = resolvida?.explicacao;
  return (
    <div className="perda-linha">
      <span className="campo-rotulo-fixo">{titulo}</span>
      <div className="perda-valor">
        <label className="gestao-field perda-pct">
          <input
            type="text"
            inputMode="decimal"
            aria-label={titulo}
            value={valor}
            onChange={(e) => onValor(e.target.value)}
          />
          <span className="perda-pct-sufixo" aria-hidden="true">%</span>
        </label>
        <div className="perda-selo">
          <StatusChip stage={selo.stage} label={selo.label} />
          <button type="button" className="link-acao" onClick={onAbrir}>
            ver de onde vem
          </button>
        </div>
      </div>
      {manual ? (
        <label className="gestao-field">
          <span>Motivo do ajuste</span>
          <input
            type="text"
            aria-label={`Motivo do ajuste, ${titulo}`}
            value={motivo}
            onChange={(e) => onMotivo(e.target.value)}
          />
        </label>
      ) : null}
      {manual ? (
        <button type="button" className="link-acao" onClick={onVoltar}>
          Voltar ao padrão
        </button>
      ) : null}
      {aberta && explicacao ? (
        <div className="perda-origem">
          <p>{explicacao.faixa}</p>
          {explicacao.fonte ? (
            <p>
              {explicacao.fonte_url ? (
                <a href={explicacao.fonte_url}>{explicacao.fonte}</a>
              ) : (
                explicacao.fonte
              )}
            </p>
          ) : null}
          {explicacao.nota ? <p>{explicacao.nota}</p> : null}
          {explicacao.n_medicoes > 0 ? (
            <p>
              {explicacao.n_medicoes} produções
              {explicacao.desvio_processo != null ? `, desvio de processo ${percento(explicacao.desvio_processo)}` : ""}
              {explicacao.desvio_coccao != null ? `, desvio de cocção ${percento(explicacao.desvio_coccao)}` : ""}.
            </p>
          ) : (
            <p>Ainda não há 3 produções medidas.</p>
          )}
          {explicacao.medicoes.length ? (
            <ul className="lista-avisos">
              {explicacao.medicoes.map((item) => (
                <li key={`${item.data}-${item.pecas}`}>
                  {item.data} · {item.pecas} peças · cru {gramasInteiras(item.peso_cru_medio_g)} · final {gramasInteiras(item.peso_final_medio_g)}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function MenuLinha({
  n,
  rotuloObservacao,
  onRemover,
  onObservacao,
  onConferir,
}: {
  n: number;
  rotuloObservacao: string;
  onRemover: () => void;
  onObservacao: () => void;
  onConferir?: () => void;
}) {
  const [aberto, setAberto] = useState(false);
  return (
    <div className="linha-menu">
      <button
        type="button"
        className="icone-remover linha-menu-botao"
        aria-label={`Mais ações da linha ${n}`}
        aria-expanded={aberto}
        onClick={() => setAberto((v) => !v)}
      >
        <svg width="18" height="18" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
          <circle cx="4.5" cy="10" r="1.6" fill="currentColor" />
          <circle cx="10" cy="10" r="1.6" fill="currentColor" />
          <circle cx="15.5" cy="10" r="1.6" fill="currentColor" />
        </svg>
      </button>
      {aberto ? (
        <div className="linha-menu-lista" role="menu">
          <button type="button" role="menuitem" onClick={() => { setAberto(false); onObservacao(); }}>
            {rotuloObservacao}
          </button>
          {onConferir ? (
            <button type="button" role="menuitem" onClick={() => { setAberto(false); onConferir(); }}>
              Marcar como conferido
            </button>
          ) : null}
          <button type="button" role="menuitem" className="perigo" onClick={() => { setAberto(false); onRemover(); }}>
            Remover
          </button>
        </div>
      ) : null}
    </div>
  );
}

export function Receitas() {
  const { search, navegar } = useGestao();
  const filtro = filtroDaUrl(search);
  const [dados, setDados] = useState<ReceitaListaItem[] | null>(null);
  const [falhou, setFalhou] = useState(false);
  const [busca, setBusca] = useState("");

  const carregar = useCallback(async (qual: FiltroReceitas) => {
    try {
      setDados((await listarReceitas(qual)).receitas);
      setFalhou(false);
    } catch {
      setFalhou(true);
    }
  }, []);

  useEffect(() => {
    void carregar(filtro);
  }, [carregar, filtro]);

  const consulta = busca.trim();
  const visiveis = (dados ?? []).filter((r) => casaBusca(consulta, [r.nome, r.rendimento]));

  return (
    <main className="fluxo-pagina">
      <PageHeader title="Receitas" description="Como eu faço?" />
      <label className="gestao-field busca-lista">
        <span>Buscar receita</span>
        <input type="search" value={busca} placeholder="Buscar receita" onChange={(e) => setBusca(e.target.value)} />
      </label>
      <Chips rotulo="Filtrar receitas" opcoes={FILTROS} valor={filtro} onChange={(v) => navegar(v === "todas" ? "/receitas" : `/receitas?filtro=${v}`)} />
      {falhou ? (
        <Card className="fluxo-vazio">
          <p role="alert">Não foi possível carregar as receitas agora.</p>
          <Button onClick={() => void carregar(filtro)}>Tentar de novo</Button>
        </Card>
      ) : null}
      {!dados && !falhou ? <p className="fluxo-estado">Carregando as receitas.</p> : null}
      {dados && dados.length === 0 ? (
        <Card className="fluxo-vazio">
          <p>
            <strong>{filtro === "todas" ? "Nenhum produto produzido ainda." : "Nenhuma receita neste filtro."}</strong>
          </p>
          {filtro === "todas" ? <Button variant="primary" onClick={() => navegar("/produtos")}>Ver produtos</Button> : null}
        </Card>
      ) : null}
      {visiveis.length > 0 ? (
        <Card className="fluxo-lista-card">
          <table className="lista-ingredientes" aria-label="Receitas">
            <thead>
              <tr>
                <th>Receita</th>
                <th>Rendimento</th>
                <th>Custo por unidade</th>
                <th>Situação</th>
              </tr>
            </thead>
            <tbody>
              {visiveis.map((r) => (
                <tr className="ing-linha" key={r.id}>
                  <td className="col-ing">
                    <button type="button" className="ing-nome" onClick={() => navegar(`/receitas/${r.produto_id}`)}>
                      <strong>{r.nome}</strong>
                    </button>
                  </td>
                  <td className="col-saldo">{r.rendimento ?? <span className="travessao">—</span>}</td>
                  <td className="col-meio">
                    {r.custo_parcial ? (
                      <span className="custo-parcial">
                        {r.custo_por_unidade == null ? "—" : `${dinheiro(r.custo_por_unidade)} parcial`}
                      </span>
                    ) : r.custo_por_unidade == null ? (
                      <span className="travessao">—</span>
                    ) : (
                      dinheiro(r.custo_por_unidade)
                    )}
                  </td>
                  <td className="col-sit">
                    {r.selos.length === 0 ? (
                      <span className="travessao">—</span>
                    ) : (
                      <span className="sels">
                        {r.selos.map((selo) => (
                          <StatusChip key={selo} stage="attention" label={SELOS[selo] ?? selo} />
                        ))}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ) : null}
    </main>
  );
}

export function EditorReceita({ produtoId }: { produtoId: string }) {
  const { navegar, definirTitulo, pode, atualizarFluxo } = useGestao();
  const tabela = useTabela();
  const [ficha, setFicha] = useState<ReceitaFicha | null>(null);
  const [linhas, setLinhas] = useState<LinhaUi[]>([linhaVazia()]);
  const [passos, setPassos] = useState<string[]>([""]);
  const [peso, setPeso] = useState("");
  const [formato, setFormato] = useState<FormatoPao | "">("");
  const [unidades, setUnidades] = useState("");
  const [processoTexto, setProcessoTexto] = useState("");
  const [coccaoTexto, setCoccaoTexto] = useState("");
  const [processoManual, setProcessoManual] = useState(false);
  const [coccaoManual, setCoccaoManual] = useState(false);
  const [processoMotivo, setProcessoMotivo] = useState("");
  const [coccaoMotivo, setCoccaoMotivo] = useState("");
  const [origemAberta, setOrigemAberta] = useState<"processo" | "coccao" | null>(null);
  const [semFermento, setSemFermento] = useState(false);
  const [aba, setAba] = useState<AbaReceita>("ingredientes");
  const [erro, setErro] = useState<string | null>(null);
  const [falhou, setFalhou] = useState(false);
  const [gravando, setGravando] = useState(false);
  const [colando, setColando] = useState(false);
  const [gigioAberto, setGigioAberto] = useState(false);
  const [gigio, setGigio] = useState<GigioSituacao | null>(null);
  const [pendente, setPendente] = useState(false);
  const [salvoEm, setSalvoEm] = useState<Date | null>(null);
  const [ecoTick, setEcoTick] = useState(0);
  const eco = useRef(false);
  const jaViu = useRef(false);
  const agora = useRef(false);
  const geracao = useRef(0);
  const timer = useRef<number | null>(null);
  const cauda = useRef<Promise<unknown>>(Promise.resolve());
  // O último corpo que o servidor confirmou e quantas gravações estão no ar: sem mudança enviável, não grava.
  const ultimoCorpo = useRef<string | null>(null);
  const emVoo = useRef(0);
  const fichaAtual = useRef<ReceitaFicha | null>(null);
  const manuais = useRef({ processo: false, coccao: false });
  manuais.current = { processo: processoManual, coccao: coccaoManual };
  // Preparo da casa (só componente): rende em gramas; não tem formato, peso por peça, unidades nem cocção.
  const porMassa = ficha?.modo_rendimento === "massa";

  const aplicar = useCallback((nova: ReceitaFicha) => {
    eco.current = true;
    setEcoTick((valor) => valor + 1);
    fichaAtual.current = nova;
    setFicha(nova);
    setLinhas(linhasDaFicha(nova));
    setPassos(nova.modo_fazer.length ? nova.modo_fazer : [""]);
    setPeso(nova.peso_unidade_g == null ? "" : String(nova.peso_unidade_g));
    setFormato(nova.formato ?? "");
    setUnidades(nova.unidades_desejadas == null ? "" : String(nova.unidades_desejadas));
    setProcessoTexto(nova.perdas?.processo.percentual == null ? "" : String(nova.perdas.processo.percentual));
    setCoccaoTexto(nova.perdas?.coccao.percentual == null ? "" : String(nova.perdas.coccao.percentual));
    setProcessoManual(nova.perdas?.processo.origem === "manual");
    setCoccaoManual(nova.perdas?.coccao.origem === "manual");
    setProcessoMotivo(nova.perdas?.processo.origem === "manual" ? nova.perdas.processo.motivo ?? "" : "");
    setCoccaoMotivo(nova.perdas?.coccao.origem === "manual" ? nova.perdas.coccao.motivo ?? "" : "");
    setSemFermento(false);
  }, []);

  useEffect(() => {
    let ativo = true;
    detalheReceita(produtoId)
      .then((nova) => {
        if (ativo) aplicar(nova);
      })
      .catch(() => {
        if (ativo) setFalhou(true);
      });
    return () => {
      ativo = false;
    };
  }, [produtoId, aplicar]);

  useEffect(() => {
    situacaoGigio().then(setGigio).catch(() => setGigio({ disponivel: false, motivo: "O Gigio ainda não está configurado nesta padaria.", usadas: 0, limite: 30 }));
  }, []);

  useEffect(() => {
    definirTitulo?.(ficha?.produto ?? null);
    return () => definirTitulo?.(null);
  }, [ficha?.produto, definirTitulo]);

  function corpo() {
    const enviadas = linhas.flatMap((linha) => {
      if (!enviavel(linha)) return [];
      const quantidade = quantidadeDa(linha);
      return [
        {
          ingrediente_id: linha.ingrediente?.id ?? null,
          texto: linha.ingrediente ? null : linha.texto.trim(),
          quantidade,
          unidade: linha.unidade,
          observacao: linha.observacao.trim() || null,
          origem: linha.origem,
          faixa_min: linha.faixaMin,
          faixa_max: linha.faixaMax,
          funcao: linha.funcao,
        },
      ];
    });
    const desejadas = unidades.trim() ? Number(unidades.replace(",", ".")) : null;
    const corpoBase = {
      linhas: enviadas,
      peso_unidade_g: !porMassa && peso.trim() ? Number(peso.replace(",", ".")) : null,
      perda_percentual: 0,
      modo_fazer: passos.map((p) => p.trim()).filter(Boolean),
      formato: porMassa ? null : formato || null,
      unidades_desejadas: !porMassa && desejadas != null && Number.isFinite(desejadas) ? desejadas : null,
    };
    return {
      ...corpoBase,
      ...(processoManual
        ? { processo: { percentual: Number(processoTexto.replace(",", ".")), origem: "manual" as const, motivo: processoMotivo.trim() } }
        : {}),
      ...(coccaoManual && !porMassa
        ? { coccao: { percentual: Number(coccaoTexto.replace(",", ".")), origem: "manual" as const, motivo: coccaoMotivo.trim() } }
        : {}),
    };
  }

  function marcarErroNaLinha(falha: unknown) {
    const texto = textoDoErro(falha);
    const indice =
      falha instanceof ApiError && falha.detalhe && typeof falha.detalhe === "object"
        ? (falha.detalhe as { linha?: number }).linha
        : undefined;
    if (!indice) return false;
    setLinhas((atuais) => {
      let vista = 0;
      return atuais.map((linha) => {
        if (!enviavel(linha)) return { ...linha, erro: null };
        vista += 1;
        return vista === indice ? { ...linha, erro: texto } : { ...linha, erro: null };
      });
    });
    return true;
  }

  async function gravar(): Promise<ReceitaFicha | null> {
    if (processoManual && !processoMotivo.trim()) {
      setErro("O ajuste manual da perda de processo precisa de um motivo.");
      setAba("rendimento");
      return null;
    }
    if (coccaoManual && !coccaoMotivo.trim()) {
      setErro("O ajuste manual da perda de cocção precisa de um motivo.");
      setAba("rendimento");
      return null;
    }
    const marca = geracao.current;
    const pedido = corpo();
    const texto = JSON.stringify(pedido);
    if (texto === ultimoCorpo.current && fichaAtual.current) {
      if (geracao.current === marca) setPendente(false);
      return fichaAtual.current;
    }
    const enviadas = linhas.filter(enviavel).map((linha) => linha.chave);
    emVoo.current += 1;
    setGravando(true);
    setErro(null);
    try {
      const nova = await salvarReceita(produtoId, pedido);
      ultimoCorpo.current = texto;
      fichaAtual.current = nova;
      setFicha(nova);
      setLinhas((atuais) => mesclarGravadas(atuais, enviadas, nova));
      // A perda no padrão é calculada no servidor (a cocção muda com formato e peso); a manual é da pessoa e fica.
      if (!manuais.current.processo) {
        setProcessoTexto(nova.perdas?.processo.percentual == null ? "" : String(nova.perdas.processo.percentual));
      }
      if (!manuais.current.coccao) {
        setCoccaoTexto(nova.perdas?.coccao.percentual == null ? "" : String(nova.perdas.coccao.percentual));
      }
      if (geracao.current === marca) {
        setPendente(false);
        setSalvoEm(new Date());
      }
      atualizarFluxo();
      return nova;
    } catch (falha) {
      const naLinha = marcarErroNaLinha(falha);
      if (!naLinha) setErro(textoDoErro(falha));
      return null;
    } finally {
      emVoo.current -= 1;
      setGravando(false);
    }
  }

  function enfileirar(): Promise<ReceitaFicha | null> {
    const exec = cauda.current.then(() => gravar());
    cauda.current = exec.then(
      () => undefined,
      () => undefined,
    );
    return exec;
  }

  function salvarAgora() {
    if (timer.current) window.clearTimeout(timer.current);
    setPendente(true);
    void enfileirar();
  }

  const assinatura = JSON.stringify({
    linhas: linhas.map((linha) => [
      linha.ingrediente?.id ?? "",
      linha.texto,
      linha.quantidade,
      linha.unidade,
      linha.observacao,
      linha.funcao,
      linha.origem,
    ]),
    passos,
    peso,
    formato,
    unidades,
    processoTexto,
    coccaoTexto,
    processoManual,
    coccaoManual,
    processoMotivo,
    coccaoMotivo,
  });
  useEffect(() => {
    if (!ficha) return;
    if (eco.current) {
      eco.current = false;
      jaViu.current = true;
      ultimoCorpo.current = JSON.stringify(corpo());
      return;
    }
    if (!jaViu.current) {
      jaViu.current = true;
      ultimoCorpo.current = JSON.stringify(corpo());
      return;
    }
    // Escolher o ingrediente sem quantidade, ou abrir uma linha nova, não muda o que vai ao servidor: não grava.
    if (emVoo.current === 0 && JSON.stringify(corpo()) === ultimoCorpo.current) {
      agora.current = false;
      if (timer.current) window.clearTimeout(timer.current);
      setPendente(false);
      return;
    }
    geracao.current += 1;
    setPendente(true);
    const espera = agora.current ? 0 : 1500;
    agora.current = false;
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => {
      void enfileirar();
    }, espera);
    return () => {
      if (timer.current) window.clearTimeout(timer.current);
    };
    // A assinatura é o rascunho. O erro na linha não entra nela, para não regravar a falha.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assinatura, ficha?.id, ecoTick]);

  const sujo = pendente || linhas.some((linha) => linha.erro);
  useEffect(() => {
    definirGuardaSaida(() => {
      if (!sujo) return true;
      return window.confirm("Há mudanças não salvas. Sair mesmo assim?");
    });
    const aviso = (evento: BeforeUnloadEvent) => {
      if (!sujo) return;
      evento.preventDefault();
      evento.returnValue = "Há mudanças não salvas. Sair mesmo assim?";
    };
    window.addEventListener("beforeunload", aviso);
    return () => {
      definirGuardaSaida(null);
      window.removeEventListener("beforeunload", aviso);
    };
  }, [sujo]);

  async function voltarPadrao(lado: "processo" | "coccao") {
    const outroSemMotivo = lado === "processo" ? coccaoManual && !coccaoMotivo.trim() : processoManual && !processoMotivo.trim();
    if (outroSemMotivo) {
      setErro("O outro ajuste manual precisa de um motivo antes de voltar ao padrão.");
      return;
    }
    setGravando(true);
    setErro(null);
    try {
      const nova = await salvarReceita(produtoId, { ...corpo(), [lado]: { origem: null } });
      aplicar(nova);
      atualizarFluxo();
    } catch (falha) {
      setErro(textoDoErro(falha));
    } finally {
      setGravando(false);
    }
  }

  async function publicar() {
    if (linhas.some(incompleta)) {
      setErro("Há linha incompleta. Informe a quantidade ou remova a linha antes de publicar.");
      setAba("ingredientes");
      return;
    }
    const gravada = await enfileirar();
    if (!gravada) return;
    if (gravada.linhas.some((l) => l.a_decidir)) {
      setErro("Há linha a decidir. Escolha o ingrediente antes de publicar.");
      setAba("ingredientes");
      return;
    }
    setGravando(true);
    try {
      const nova = await publicarReceita(produtoId, semFermento);
      aplicar(nova);
      atualizarFluxo();
    } catch (falha) {
      setErro(textoDoErro(falha));
    } finally {
      setGravando(false);
    }
  }

  async function colar(texto: string) {
    const pedacos = texto.split(/\r?\n/).map((l) => l.split("\t")).filter((c) => c.some((p) => p.trim()));
    const novas: LinhaUi[] = [];
    for (const colunas of pedacos) {
      const nome = (colunas[0] ?? "").trim();
      const quantidade = (colunas[1] ?? "").trim();
      const unidade = UNIDADE_TEXTO[normalizar(colunas[2] ?? "")] ?? null;
      if (!nome) continue;
      let ingrediente: IngredienteEscolhido | null = null;
      try {
        const busca = await buscarIngredientes(nome);
        const alvo = normalizar(nome);
        const achado = busca.da_padaria.find((i) => normalizar(i.nome) === alvo);
        if (achado) {
          ingrediente = { id: achado.id, nome: achado.nome, categoria: achado.categoria, unidade_base: achado.unidade_base };
        }
      } catch {
        ingrediente = null;
      }
      novas.push({
        ...linhaVazia(),
        ingrediente,
        texto: ingrediente ? "" : nome,
        quantidade,
        unidade: unidade ?? "g",
        erro: unidade ? null : "A unidade não é g, kg, ml, l ou un.",
      });
    }
    if (novas.length) {
      agora.current = true;
      setLinhas((atuais) => [...atuais.filter((l) => l.ingrediente || l.texto || l.quantidade), ...novas]);
    }
    setColando(false);
  }

  const grupos = FUNCOES.map((grupo) => ({
    ...grupo,
    linhas: linhas.filter((linha) => linha.funcao === grupo.valor),
  })).filter((grupo) => grupo.linhas.length);
  const faltaFermento = Boolean(ficha?.verificacoes?.pendencias.some((item) => item.codigo === "sem_fermento"));
  const bloqueada =
    linhas.some((l) => (l.texto.trim() && !l.ingrediente) || l.erro) ||
    (faltaFermento && !semFermento);
  const custo = porMassa ? ficha?.rendimento_massa?.custo_por_kg ?? null : ficha?.custo_por_unidade;
  const massa = ficha?.rendimento_massa ?? null;

  function campos(linha: LinhaUi, n: number) {
    const caixa = (classe: string, miolo: ReactNode) =>
      tabela ? <td className={`celula ${classe}`}>{miolo}</td> : <div className={`campo ${classe}`}>{miolo}</div>;
    return (
      <>
        {caixa(
          "campo-ingrediente",
          <>
          {!tabela ? <span>Ingrediente</span> : null}
          <CampoIngrediente
            rotulo={`Ingrediente, linha ${n}`}
            valor={
              linha.ingrediente
                ? {
                    nome:
                      linha.funcao === "inoculo"
                        ? `${linha.ingrediente.nome} · porção do preparo anterior`
                        : linha.ingrediente.nome,
                    categoria: linha.ingrediente.categoria,
                  }
                : null
            }
            textoInicial={linha.texto}
            placeholder={linha.texto ? linha.texto : "Buscar ingrediente"}
            nomeNaBusca={(ing) =>
              ficha?.cultura_viva && ficha.ingrediente_id && ing.id === ficha.ingrediente_id
                ? `${ing.nome} · porção do preparo anterior (inóculo)`
                : ing.nome
            }
            onEscolher={(ing) => {
              const inoculo = Boolean(ficha?.cultura_viva && ficha.ingrediente_id && ing.id === ficha.ingrediente_id);
              setLinhas((atuais) =>
                atuais.map((l) =>
                  l.chave === linha.chave
                    ? { ...l, ingrediente: ing, texto: "", erro: null, funcao: inoculo ? "inoculo" : l.funcao === "inoculo" ? "massa" : l.funcao }
                    : l,
                ),
              );
            }}
            onTrocar={() =>
              setLinhas((atuais) => atuais.map((l) => (l.chave === linha.chave ? { ...l, ingrediente: null, erro: null } : l)))
            }
          />
          {linha.texto && !linha.ingrediente ? <small className="sub">a decidir</small> : null}
          {incompleta(linha) ? <small className="sub">incompleta</small> : null}
          {linha.observacao.trim() ? <small className="obs-linha">{linha.observacao}</small> : null}
          {linha.origem === "estimado" ? (
            <small
              className="etiqueta-estimado"
              title={linha.faixaMin != null && linha.faixaMax != null ? `Faixa ${linha.faixaMin}–${linha.faixaMax} %` : "Estimado pelo Gigio"}
            >
              estimado
            </small>
          ) : null}
          </>,
        )}
        {caixa(
          "campo-qtd",
          <label>
            {!tabela ? <span>Quantidade</span> : null}
            <input
              type="text"
              inputMode="decimal"
              aria-label={`Quantidade, linha ${n}`}
              value={linha.quantidade}
              onChange={(e) =>
                setLinhas((atuais) =>
                  atuais.map((l) =>
                    l.chave === linha.chave
                      ? { ...l, quantidade: e.target.value, erro: null, origem: l.origem === "estimado" ? "conferido" : l.origem }
                      : l,
                  ),
                )
              }
              onBlur={() => {
                if (enviavel(linha)) salvarAgora();
              }}
            />
          </label>,
        )}
        {caixa(
          "campo-unidade",
          <label>
            {!tabela ? <span>Unidade</span> : null}
            <select
              aria-label={`Unidade, linha ${n}`}
              value={linha.unidade}
              onChange={(e) =>
                setLinhas((atuais) =>
                  atuais.map((l) =>
                    l.chave === linha.chave
                      ? { ...l, unidade: e.target.value as UnidadeReceita, erro: null, origem: l.origem === "estimado" ? "conferido" : l.origem }
                      : l,
                  ),
                )
              }
              onBlur={() => {
                if (enviavel(linha)) salvarAgora();
              }}
            >
              {UNIDADES.map((u) => (
                <option key={u.valor} value={u.valor}>
                  {u.rotulo}
                </option>
              ))}
            </select>
          </label>,
        )}
        {caixa("campo-conteudo", <>{!tabela ? <span>% do padeiro</span> : null}<span>{percento(linha.percentual)}</span></>)}
        {caixa("campo-custo", <>{!tabela ? <span>Custo</span> : null}<span>{linha.custo == null ? "—" : dinheiro(linha.custo)}</span></>)}
        {caixa(
          "campo-remover",
          <MenuLinha
            n={n}
            rotuloObservacao={linha.observacao.trim() ? "Editar observação" : "Observação"}
            onRemover={() => {
              agora.current = true;
              setLinhas((atuais) => atuais.filter((l) => l.chave !== linha.chave));
            }}
            onObservacao={() => setLinhas((atuais) => atuais.map((l) => (l.chave === linha.chave ? { ...l, obsAberta: true } : l)))}
            onConferir={
              linha.origem === "estimado"
                ? () => setLinhas((atuais) => atuais.map((l) => (l.chave === linha.chave ? { ...l, origem: "conferido" } : l)))
                : undefined
            }
          />,
        )}
      </>
    );
  }

  return (
    <main className={aba === "ingredientes" ? "entrada-pagina" : "fluxo-pagina"}>
      <PageHeader title={ficha?.produto ?? "Receita"} description="Como eu faço?" />
      {falhou ? (
        <Card className="fluxo-vazio">
          <p role="alert">Não foi possível abrir esta receita.</p>
          <Button onClick={() => navegar("/receitas")}>Voltar para Receitas</Button>
        </Card>
      ) : null}
      {ficha ? (
        <>
          <Chips
            rotulo="Partes da receita"
            opcoes={ABAS}
            valor={aba}
            onChange={(v) => {
              void enfileirar().then((gravada) => {
                if (gravada) setAba(v);
              });
            }}
          />
          {aba === "ingredientes" ? (
            <Card className="entrada-grade-card">
              <div className="painel-acoes">
                <Button onClick={() => { agora.current = true; setLinhas((atuais) => [...atuais, linhaVazia()]); }}>Adicionar linha</Button>
                <Button onClick={() => setColando(true)}>Colar da planilha</Button>
                {pode("lancar") ? (
                  <Button className="botao-gigio" disabled={!gigio?.disponivel} onClick={() => setGigioAberto(true)}>
                    <img className="avatar-gigio" src="/avatar_gigio.png" alt="" width={20} height={20} />
                    Sugerir com o Gigio
                  </Button>
                ) : null}
              </div>
              {pode("lancar") && gigio && !gigio.disponivel ? <p className="sub">{gigio.motivo}</p> : null}
              {tabela ? (
                <div className="entrada-tabela-rolagem">
                  <table className="entrada-tabela tabela-receita" aria-label="Ingredientes da receita">
                    <thead>
                      <tr>
                        <th className="campo-ingrediente">Ingrediente</th>
                        <th className="campo-qtd">Quantidade</th>
                        <th className="campo-unidade">Unidade</th>
                        <th className="campo-conteudo">% do padeiro</th>
                        <th className="campo-custo">Custo</th>
                        <th className="campo-remover"><span className="so-leitor">Ações</span></th>
                      </tr>
                    </thead>
                    <tbody>
                      {grupos.map((grupo) => (
                        <Fragment key={grupo.valor}>
                          <tr className="funcao-linha">
                            <th className="funcao-subtitulo" colSpan={6}>{grupo.rotulo}</th>
                          </tr>
                          {grupo.linhas.map((linha) => (
                            <Fragment key={linha.chave}>
                              <tr id={`linha-${linha.chave}`} data-erro-linha={linha.erro ? "" : undefined}>
                                {campos(linha, linhas.indexOf(linha) + 1)}
                              </tr>
                              {linha.obsAberta ? (
                                <tr className="linha-obs">
                                  <td colSpan={6}>
                                    <label className="gestao-field">
                                      <span>Observação</span>
                                      <input
                                        type="text"
                                        value={linha.observacao}
                                        onChange={(e) =>
                                          setLinhas((atuais) =>
                                            atuais.map((l) => (l.chave === linha.chave ? { ...l, observacao: e.target.value } : l)),
                                          )
                                        }
                                        onBlur={() => {
                                          if (enviavel(linha)) salvarAgora();
                                        }}
                                      />
                                    </label>
                                  </td>
                                </tr>
                              ) : null}
                              {linha.erro ? (
                                <tr>
                                  <td colSpan={6}>
                                    <p className="form-erro" role="alert">{linha.erro}</p>
                                  </td>
                                </tr>
                              ) : null}
                            </Fragment>
                          ))}
                        </Fragment>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <ul className="entrada-grade" aria-label="Ingredientes da receita">
                  {grupos.map((grupo) => (
                    <Fragment key={grupo.valor}>
                      <li className="funcao-subtitulo">{grupo.rotulo}</li>
                      {grupo.linhas.map((linha) => (
                        <li id={`linha-${linha.chave}`} key={linha.chave} data-erro-linha={linha.erro ? "" : undefined} className={`grade-linha${linha.texto && !linha.ingrediente ? " decidir" : ""}`}>
                          <div className="grade-campos">{campos(linha, linhas.indexOf(linha) + 1)}</div>
                          {linha.erro ? <p className="form-erro" role="alert">{linha.erro}</p> : null}
                          {linha.obsAberta ? (
                            <label className="gestao-field">
                              <span>Observação</span>
                              <input
                                type="text"
                                value={linha.observacao}
                                onChange={(e) =>
                                  setLinhas((atuais) => atuais.map((l) => (l.chave === linha.chave ? { ...l, observacao: e.target.value } : l)))
                                }
                                onBlur={() => {
                                  if (enviavel(linha)) salvarAgora();
                                }}
                              />
                            </label>
                          ) : null}
                        </li>
                      ))}
                    </Fragment>
                  ))}
                </ul>
              )}
              <p className="entrada-dica">
                Dica: cole de uma planilha as colunas, nesta ordem: ingrediente, quantidade, unidade. O que não bater exatamente fica “a decidir”.
              </p>
            </Card>
          ) : null}
          {aba === "modo" ? (
            <Card>
              <ol className="pares">
                {passos.map((passo, i) => (
                  <li key={i} className="item-com-menu">
                    <span>{i + 1}</span>
                    <label className="gestao-field">
                      <span className="so-leitor">Etapa {i + 1}</span>
                      <input
                        type="text"
                        value={passo}
                        onChange={(e) => setPassos((atuais) => atuais.map((p, n) => (n === i ? e.target.value : p)))}
                      />
                    </label>
                    <Button disabled={i === 0} onClick={() => setPassos((atuais) => {
                      const copia = [...atuais];
                      [copia[i - 1], copia[i]] = [copia[i], copia[i - 1]];
                      return copia;
                    })}>Subir</Button>
                    <Button disabled={i === passos.length - 1} onClick={() => setPassos((atuais) => {
                      const copia = [...atuais];
                      [copia[i + 1], copia[i]] = [copia[i], copia[i + 1]];
                      return copia;
                    })}>Descer</Button>
                    <Button onClick={() => setPassos((atuais) => atuais.filter((_, n) => n !== i))}>Remover</Button>
                  </li>
                ))}
              </ol>
              <Button onClick={() => setPassos((atuais) => [...atuais, ""])}>Adicionar etapa</Button>
            </Card>
          ) : null}
          {aba === "rendimento" && porMassa ? (
            <Card>
              <div className="cartao-corpo">
                <p className="sub">
                  {ficha.cultura_viva
                    ? "Preparo da casa, cultura viva: rende em peso. Uma parte fica guardada como inóculo da próxima alimentação."
                    : "Preparo da casa: rende em peso, sem forno e sem peças."}
                </p>
                <div className="perdas-par">
                  <LinhaPerda
                    titulo="Perda de processo"
                    valor={processoTexto}
                    manual={processoManual}
                    motivo={processoMotivo}
                    resolvida={ficha.perdas?.processo}
                    aberta={origemAberta === "processo"}
                    onValor={(valor) => {
                      setProcessoTexto(valor);
                      setProcessoManual(true);
                    }}
                    onMotivo={setProcessoMotivo}
                    onAbrir={() => setOrigemAberta((atual) => (atual === "processo" ? null : "processo"))}
                    onVoltar={() => void voltarPadrao("processo")}
                  />
                </div>
                <div className="rendimento-cartoes">
                  <article>
                    <h3>Rende</h3>
                    <p>{gramasInteiras(massa?.rende_g ?? null)}</p>
                    <p className="peca-apoio">de {gramasInteiras(massa?.massa_g ?? null)} de massa</p>
                  </article>
                  {ficha.cultura_viva ? (
                    <>
                      <article>
                        <h3>Reserva do inóculo</h3>
                        <p>{gramasInteiras(massa?.reserva_g ?? null)}</p>
                        <p className="peca-apoio">fica para a próxima alimentação</p>
                      </article>
                      <article>
                        <h3>Disponível para usar</h3>
                        <p>{gramasInteiras(massa?.disponivel_g ?? null)}</p>
                      </article>
                    </>
                  ) : null}
                  <article>
                    <h3>Custo por kg</h3>
                    <p>{custo == null ? "—" : ficha.custo_parcial ? `${dinheiro(custo)} parcial` : dinheiro(custo)}</p>
                  </article>
                </div>
                {massa?.disponivel_g != null && massa.disponivel_g < 0 ? (
                  <p className="form-erro" role="status">A reserva do inóculo é maior do que a receita rende.</p>
                ) : null}
              </div>
            </Card>
          ) : null}
          {aba === "rendimento" && !porMassa ? (
            <Card>
              <div className="cartao-corpo">
                <div className="rendimento-campos">
                  <label className="gestao-field">
                    <span>Formato</span>
                    <select value={formato} onChange={(e) => setFormato(e.target.value as FormatoPao | "")}>
                      <option value="">Escolha</option>
                      {FORMATOS.map((item) => (
                        <option key={item.valor} value={item.valor}>{item.rotulo}</option>
                      ))}
                    </select>
                  </label>
                  <label className="gestao-field">
                    <span>Peso final por unidade (g)</span>
                    <input type="text" inputMode="decimal" value={peso} onChange={(e) => setPeso(e.target.value)} />
                  </label>
                  <label className="gestao-field">
                    <span>Unidades desejadas</span>
                    <input type="text" inputMode="numeric" value={unidades} onChange={(e) => setUnidades(e.target.value)} />
                  </label>
                </div>
                <div className="perdas-par">
                  <LinhaPerda
                    titulo="Perda de processo"
                    valor={processoTexto}
                    manual={processoManual}
                    motivo={processoMotivo}
                    resolvida={ficha.perdas?.processo}
                    aberta={origemAberta === "processo"}
                    onValor={(valor) => {
                      setProcessoTexto(valor);
                      setProcessoManual(true);
                    }}
                    onMotivo={setProcessoMotivo}
                    onAbrir={() => setOrigemAberta((atual) => (atual === "processo" ? null : "processo"))}
                    onVoltar={() => void voltarPadrao("processo")}
                  />
                  <LinhaPerda
                    titulo="Perda de cocção"
                    valor={coccaoTexto}
                    manual={coccaoManual}
                    motivo={coccaoMotivo}
                    resolvida={ficha.perdas?.coccao}
                    aberta={origemAberta === "coccao"}
                    onValor={(valor) => {
                      setCoccaoTexto(valor);
                      setCoccaoManual(true);
                    }}
                    onMotivo={setCoccaoMotivo}
                    onAbrir={() => setOrigemAberta((atual) => (atual === "coccao" ? null : "coccao"))}
                    onVoltar={() => void voltarPadrao("coccao")}
                  />
                </div>
                <div className="rendimento-cartoes">
                  <article>
                    <h3 className="peca-linha">{ficha.perdas?.peso_cru_g == null ? "—" : `Peças de ${gramasInteiras(ficha.perdas.peso_cru_g)}`}</h3>
                    <p className="peca-apoio">divida a massa assim</p>
                  </article>
                  <article>
                    <h3>Unidades</h3>
                    <p>{ficha.perdas?.unidades == null ? "—" : `${ficha.perdas.unidades} com a massa atual`}</p>
                  </article>
                  <article>
                    <h3>Massa necessária</h3>
                    <p>{ficha.perdas?.massa_necessaria_g == null ? "—" : gramasInteiras(ficha.perdas.massa_necessaria_g)}</p>
                  </article>
                  <article>
                    <h3>Custo por unidade</h3>
                    <p>
                      {custo == null
                        ? "—"
                        : ficha.custo_parcial
                          ? `${dinheiro(custo)} parcial`
                          : dinheiro(custo)}
                    </p>
                  </article>
                </div>
              </div>
            </Card>
          ) : null}
          {aba === "revisar" ? (
            <Card>
              <div className="cartao-corpo revisar-corpo">
              <dl className="painel-fatos">
                <div>
                  <dt>Linhas</dt>
                  <dd>{ficha.linhas.length}</dd>
                </div>
                <div>
                  <dt>Rendimento</dt>
                  <dd>
                    {porMassa
                      ? gramasInteiras(massa?.rende_g ?? null)
                      : ficha.peso_unidade_g == null || ficha.perdas?.unidades == null
                        ? "—"
                        : `${ficha.perdas.unidades} un`}
                  </dd>
                </div>
                {ficha.hidratacao ? (
                  <div>
                    <dt>Hidratação</dt>
                    <dd>
                      {percento(ficha.hidratacao.percentual)}
                      <span className="sub">
                        {` · ${gramasInteiras(ficha.hidratacao.agua_g)} de água para ${gramasInteiras(ficha.hidratacao.farinha_g)} de farinha`}
                      </span>
                    </dd>
                  </div>
                ) : null}
                <div>
                  <dt>{porMassa ? "Custo por kg" : "Custo por unidade"}</dt>
                  <dd>
                    {ficha.custo_parcial ? (
                      <span className="custo-parcial">
                        {custo == null ? "—" : `${dinheiro(custo)} parcial`}
                        {` · ${ficha.linhas_sem_custo} ${ficha.linhas_sem_custo === 1 ? "linha" : "linhas"} sem custo`}
                      </span>
                    ) : custo == null ? (
                      "—"
                    ) : (
                      dinheiro(custo)
                    )}
                  </dd>
                </div>
              </dl>
              {ficha.verificacoes?.pendencias.map((item) => (
                <p key={item.codigo} className="form-erro" role="status">{item.mensagem}</p>
              ))}
              {ficha.verificacoes?.avisos.length ? (
                <ul className="lista-avisos">
                  {ficha.verificacoes.avisos.map((item) => (
                    <li key={item.mensagem}>{item.mensagem}</li>
                  ))}
                </ul>
              ) : null}
              {ficha.linhas.some((l) => l.a_decidir) ? <p className="form-erro">Há linha a decidir.</p> : null}
              {linhas.some((l) => l.origem === "estimado") ? (
                <p className="sub">
                  {linhas.filter((l) => l.origem === "estimado").length} linhas estimadas, ainda não conferidas.
                </p>
              ) : null}
              {faltaFermento ? (
                <label className="gigio-topo">
                  <input type="checkbox" checked={semFermento} onChange={(e) => setSemFermento(e.target.checked)} />
                  <span>Publicar mesmo assim, sem fermento</span>
                </label>
              ) : null}
              {erro ? <p role="alert" className="form-erro">{erro}</p> : null}
              {pode("lancar") ? (
                <Button variant="primary" disabled={bloqueada || gravando} onClick={() => void publicar()}>
                  {gravando ? "Publicando." : `Publicar versão ${ficha.versao}`}
                </Button>
              ) : null}
              </div>
            </Card>
          ) : null}
        </>
      ) : null}
      {aba === "ingredientes" && ficha ? (
        <div className="entrada-rodape" role="region" aria-label="Resumo da receita">
          <p className="rodape-numeros">
            <span><strong>{linhas.filter((l) => l.ingrediente || l.texto).length}</strong> linhas</span>
            {linhas.some((l) => l.origem === "estimado") ? (
              <span>{linhas.filter((l) => l.origem === "estimado").length} estimadas</span>
            ) : null}
            <span>Massa {ficha.total_massa_g == null ? "—" : quantidadeBase(ficha.total_massa_g, "g")}</span>
            <span className="rodape-total">
              {ficha.custo_parcial ? (
                <span className="custo-parcial">
                  Parcial: {ficha.custo_total == null ? "—" : dinheiro(ficha.custo_total)}
                  {` · ${ficha.linhas_sem_custo} ${ficha.linhas_sem_custo === 1 ? "linha" : "linhas"} sem custo`}
                </span>
              ) : ficha.custo_total == null ? null : (
                <strong>{dinheiro(ficha.custo_total)}</strong>
              )}
            </span>
          </p>
          {erro ? <p role="alert" className="form-erro">{erro}</p> : null}
          <p className={`salva-estado${linhas.some((l) => l.erro) || erro ? " salva-erro" : ""}`} role="status">
            {gravando ? "Salvando…" : linhas.some((l) => l.erro) ? (
              <>
                {`${linhas.filter((l) => l.erro).length} ${linhas.filter((l) => l.erro).length === 1 ? "linha não salva" : "linhas não salvas"} · `}
                <button
                  type="button"
                  className="salva-ver"
                  onClick={() => document.querySelector("[data-erro-linha]")?.scrollIntoView({ block: "center" })}
                >
                  ver
                </button>
              </>
            ) : erro ? (
              erro
            ) : salvoEm ? (
              `Tudo salvo · ${horaCurta(salvoEm)}`
            ) : (
              "Rascunho"
            )}
          </p>
          <Button disabled={!pendente} onClick={() => salvarAgora()}>Salvar rascunho</Button>
        </div>
      ) : null}
      {colando ? (
        <PainelColar onFechar={() => setColando(false)} onAdicionar={(texto) => void colar(texto)} />
      ) : null}
      {gigioAberto ? (
        <PainelGigio
          produtoId={produtoId}
          linhas={linhas
            .filter((l) => (l.ingrediente || l.texto) && Number(String(l.quantidade).replace(",", ".")) > 0)
            .map((l) => ({
              ingredienteId: l.ingrediente?.id ?? null,
              nome: l.ingrediente?.nome || l.texto,
              categoria: l.ingrediente?.categoria ?? "",
              quantidade: l.quantidade,
              unidade: l.unidade,
            }))}
          rendimento={ficha?.rendimento_quantidade == null ? "" : String(ficha?.rendimento_quantidade)}
          unidade={ficha?.rendimento_unidade ?? ""}
          onFechar={() => setGigioAberto(false)}
          onAplicada={(nova) => {
            aplicar(nova);
            setPendente(false);
            setSalvoEm(new Date());
            setGigioAberto(false);
            atualizarFluxo();
          }}
        />
      ) : null}
    </main>
  );
}

function PainelColar({ onFechar, onAdicionar }: { onFechar: () => void; onAdicionar: (texto: string) => void }) {
  const [texto, setTexto] = useState("");
  const quantas = texto.split("\n").filter((l) => l.trim()).length;
  return (
    <SidePanel
      titulo="Colar da planilha"
      subtitulo="Copie as células no Excel ou no Google Planilhas e cole aqui."
      onFechar={onFechar}
      rodape={
        <div className="painel-acoes">
          <Button onClick={onFechar}>Cancelar</Button>
          <Button variant="primary" disabled={quantas === 0} onClick={() => onAdicionar(texto)}>
            {quantas <= 1 ? "Adicionar a linha" : `Adicionar ${quantas} linhas`}
          </Button>
        </div>
      }
    >
      <label className="gestao-field">
        <span>Linhas copiadas</span>
        <textarea className="colar-texto" rows={8} value={texto} spellCheck={false} onChange={(e) => setTexto(e.target.value)} />
      </label>
      <p className="sub">As colunas, nesta ordem: ingrediente, quantidade, unidade. O que não bater exatamente fica “a decidir”.</p>
    </SidePanel>
  );
}
