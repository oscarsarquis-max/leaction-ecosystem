import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { useGestao } from "../contexto";
import {
  ApiError,
  detalheEntrada,
  informarValidade,
  listarEntradas,
  textoDoErro,
  trocarIngrediente,
  type EntradaDetalhe,
  type EntradaLinhaDetalhe,
  type EntradaResumo,
  type FiltroEntradas,
} from "../lib/api";
import { casaBusca, casaLote, rotuloItens, rotuloLotes } from "../lib/buscaLista";
import { custoTexto, dataBr, dinheiro, MOTIVOS, quantidadeBase } from "../lib/format";
import { Button } from "../shell/Button";
import { CampoIngrediente, type IngredienteEscolhido } from "../shell/CampoIngrediente";
import { Card } from "../shell/Card";
import { CorrigirCusto } from "../shell/CorrigirCusto";
import { Chips } from "../shell/Chips";
import { PageHeader } from "../shell/PageHeader";
import { SeloCusto } from "../shell/SeloCusto";
import { SidePanel } from "../shell/SidePanel";
import { StatusChip } from "../shell/StatusChip";
import "./fluxo.css";

const FILTROS: { valor: FiltroEntradas; rotulo: string }[] = [
  { valor: "todas", rotulo: "Todas" },
  { valor: "com_nota", rotulo: "Com nota" },
  { valor: "sem_nota", rotulo: "Sem nota" },
  { valor: "pendentes", rotulo: "Pendentes" },
];

function filtroDaUrl(search: string): FiltroEntradas {
  const valor = new URLSearchParams(search).get("filtro");
  return FILTROS.some((f) => f.valor === valor) ? (valor as FiltroEntradas) : "todas";
}

function motivoTexto(e: { motivo: string; motivo_detalhe: string | null; fornecedor: string | null }): string {
  const base = e.motivo === "outro" && e.motivo_detalhe ? e.motivo_detalhe : (MOTIVOS[e.motivo] ?? e.motivo);
  return e.fornecedor ? `${base} · ${e.fornecedor}` : base;
}

function valorTexto(valor: number | null, parcial: boolean): string {
  if (valor === null) return "sem custo";
  return parcial ? `${dinheiro(valor)} (parcial)` : dinheiro(valor);
}

function segundaLinha(e: EntradaResumo): string {
  const tipo = e.tipo === "sem_nota" ? "Sem nota" : "Com nota";
  return `${motivoTexto(e)} · ${tipo}`;
}

function tituloEntrada(e: EntradaResumo): string {
  return rotuloItens(e.itens_nomes ?? []) || motivoTexto(e);
}

function casaEntrada(consulta: string, e: EntradaResumo): boolean {
  return casaBusca(consulta, [...(e.itens_nomes ?? []), ...(e.ingredientes ?? []), ...(e.lotes ?? []), motivoTexto(e), e.fornecedor]);
}

function custoDaLinha(linha: EntradaLinhaDetalhe): string {
  const por = linha.custo_unidade_base != null ? custoTexto(linha.custo_unidade_base, linha.unidade_base) : "sem custo";
  if (linha.valor_total === null) return por;
  return `${dinheiro(linha.valor_total)} pagos · ${por}`;
}

function validadeTexto(linha: EntradaLinhaDetalhe): string {
  if (linha.validade_pendente) return "falta a validade";
  if (linha.sem_validade || !linha.validade) return "sem validade";
  return dataBr(linha.validade);
}

export function ComoChegou({ onFechar, onSemNota }: { onFechar: () => void; onSemNota: () => void }) {
  return (
    <SidePanel titulo="Como chegou?" subtitulo="Escolha como você vai lançar esta entrada." onFechar={onFechar}>
      <div className="como-chegou">
        <section className="como-bloco" aria-labelledby="como-com-nota">
          <h3 id="como-com-nota">Com nota</h3>
          <p>A nota fiscal preenche tudo sozinha. Chega numa próxima etapa.</p>
          <ul className="como-opcoes">
            {["Importar o XML", "Ler o QR Code", "Digitar a nota"].map((rotulo) => (
              <li key={rotulo}>
                <button type="button" className="como-opcao" disabled>
                  <span>{rotulo}</span>
                  <span className="soon">em breve</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
        <section className="como-bloco" aria-labelledby="como-sem-nota">
          <h3 id="como-sem-nota">Sem nota</h3>
          <p>Contagem de estoque, compra sem nota, bonificação. Você digita ou cola de uma planilha.</p>
          <Button variant="primary" className="como-sem-nota-botao" onClick={onSemNota}>
            Entrada sem nota
          </Button>
        </section>
      </div>
    </SidePanel>
  );
}

function DetalheDaEntrada({ id, onFechar, aoAtualizar }: { id: string; onFechar: () => void; aoAtualizar: () => void }) {
  const [dados, setDados] = useState<EntradaDetalhe | null>(null);
  const [falhou, setFalhou] = useState(false);
  const [editando, setEditando] = useState<string | null>(null);
  const [corrigindo, setCorrigindo] = useState<string | null>(null);
  const [data, setData] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const { pode } = useGestao();

  const carregar = useCallback(async () => {
    try {
      setDados(await detalheEntrada(id));
      setFalhou(false);
    } catch {
      setFalhou(true);
    }
  }, [id]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  async function salvar(loteId: string, corpo: { validade?: string; sem_validade?: boolean }) {
    setSalvando(true);
    setErro(null);
    try {
      await informarValidade(loteId, corpo);
      setEditando(null);
      setData("");
      await carregar();
      aoAtualizar();
    } catch (falha) {
      setErro(textoDoErro(falha));
    } finally {
      setSalvando(false);
    }
  }

  const titulo = dados ? `Entrada de ${dataBr(dados.data)}` : "Entrada";
  return (
    <SidePanel
      titulo={titulo}
      subtitulo={dados ? motivoTexto(dados) : undefined}
      onFechar={onFechar}
      rodape={
        dados ? (
          <p className="painel-total">
            <span>Total</span>
            <strong>{valorTexto(dados.valor, dados.valor_parcial)}</strong>
          </p>
        ) : undefined
      }
    >
      {falhou ? <p role="alert">Não foi possível abrir esta entrada agora.</p> : null}
      {!dados && !falhou ? <p>Carregando.</p> : null}
      {dados ? (
        <>
          <dl className="painel-fatos">
            <div>
              <dt>Tipo</dt>
              <dd>{dados.tipo === "sem_nota" ? "Sem nota" : "Com nota"}</dd>
            </div>
            <div>
              <dt>Local</dt>
              <dd>{dados.local ?? "-"}</dd>
            </div>
            <div>
              <dt>Lançada por</dt>
              <dd>{dados.lancada_por ?? "-"}</dd>
            </div>
            <div>
              <dt>Situação</dt>
              <dd>
                <StatusChip
                  stage={dados.situacao === "pendente" ? "warning" : "ok"}
                  label={dados.situacao === "pendente" ? "Pendente" : "Completa"}
                />
              </dd>
            </div>
          </dl>
          {erro ? (
            <p role="alert" className="form-erro">
              {erro}
            </p>
          ) : null}
          <ul className="painel-itens" aria-label="Itens desta entrada">
            {dados.linhas.map((linha) => (
              <li key={linha.posicao} className="painel-item">
                <div className="painel-item-topo">
                  <strong>{linha.item}</strong>
                  <span>{quantidadeBase(linha.quantidade_base, linha.unidade_base)}</span>
                </div>
                <p className="painel-item-sub">
                  {linha.marca ? `${linha.marca} · ` : ""}
                  {linha.ingrediente}
                </p>
                <p className="painel-item-sub">
                  Lote {linha.lote} ·{" "}
                  {linha.validade_pendente ? (
                    <span className="texto-atencao">falta a validade</span>
                  ) : linha.sem_validade ? (
                    "sem validade"
                  ) : (
                    `validade ${dataBr(linha.validade!)}`
                  )}
                  {" · "}
                  {linha.valor_total === null ? "sem custo" : `${dinheiro(linha.valor_total)} pagos`}
                  {linha.custo_unidade_base != null ? ` · ${custoTexto(linha.custo_unidade_base, linha.unidade_base)}` : ""}
                </p>
                {pode("ajustar") && linha.lote_id ? (
                  corrigindo === linha.lote_id ? (
                    <CorrigirCusto
                      loteId={linha.lote_id}
                      onCancelar={() => setCorrigindo(null)}
                      onFeito={() => {
                        setCorrigindo(null);
                        void carregar();
                        aoAtualizar();
                      }}
                    />
                  ) : (
                    <Button className="validade-abrir" onClick={() => setCorrigindo(linha.lote_id)}>
                      Corrigir custo
                    </Button>
                  )
                ) : null}
                {linha.validade_pendente && pode("lancar") ? (
                  editando === linha.lote_id ? (
                    <div className="validade-editor">
                      <label className="gestao-field">
                        <span>Validade do lote {linha.lote}</span>
                        <input type="date" value={data} onChange={(e) => setData(e.target.value)} />
                      </label>
                      <div className="validade-acoes">
                        <Button
                          variant="primary"
                          disabled={!data || salvando}
                          onClick={() => void salvar(linha.lote_id, { validade: data })}
                        >
                          Salvar validade
                        </Button>
                        <Button disabled={salvando} onClick={() => void salvar(linha.lote_id, { sem_validade: true })}>
                          Não tem validade
                        </Button>
                        <Button onClick={() => setEditando(null)}>Cancelar</Button>
                      </div>
                    </div>
                  ) : (
                    <Button className="validade-abrir" onClick={() => setEditando(linha.lote_id)}>
                      Informar validade
                    </Button>
                  )
                ) : null}
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </SidePanel>
  );
}

function TrocaNaLinha({
  linha,
  onCancelar,
  onFeito,
}: {
  linha: EntradaLinhaDetalhe;
  onCancelar: () => void;
  onFeito: () => void;
}) {
  const [novo, setNovo] = useState<IngredienteEscolhido | null>(null);
  const [motivo, setMotivo] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const outra = novo !== null && novo.unidade_base !== linha.unidade_base;
  const mesmo = novo !== null && novo.id === linha.ingrediente_id;
  const pronto = Boolean(linha.item_id) && novo !== null && !outra && !mesmo && motivo.trim().length >= 3;

  async function enviar(event: FormEvent) {
    event.preventDefault();
    if (!pronto || !novo || !linha.item_id) return;
    setEnviando(true);
    setErro(null);
    try {
      await trocarIngrediente(linha.item_id, { ingrediente_id: novo.id, motivo: motivo.trim() });
      onFeito();
    } catch (falha) {
      setErro(textoDoErro(falha));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form className="painel-form" aria-label={`Trocar o ingrediente de ${linha.item}`} onSubmit={(e) => void enviar(e)}>
      <h3>Trocar ingrediente</h3>
      <p className="sub">
        “{linha.item}” hoje está ligado a “{linha.ingrediente}”. Ao trocar, os lotes e o saldo do item vão junto. Fica no histórico, com o motivo.
      </p>
      <CampoIngrediente
        rotulo="Novo ingrediente do item"
        valor={novo ? { nome: novo.nome, categoria: novo.categoria } : null}
        item={linha.item}
        marca={linha.marca}
        placeholder="Buscar o ingrediente certo"
        onEscolher={(ing) => setNovo(ing)}
        onTrocar={() => setNovo(null)}
      />
      {outra ? (
        <p role="alert" className="form-erro">
          “{novo?.nome}” é medido em outra unidade. Escolha um ingrediente em {linha.unidade_base}.
        </p>
      ) : null}
      {mesmo ? <p className="sub">Este item já está ligado a “{linha.ingrediente}”.</p> : null}
      <label className="gestao-field">
        <span>Motivo (obrigatório)</span>
        <input type="text" value={motivo} maxLength={300} onChange={(e) => setMotivo(e.target.value)} />
      </label>
      {erro ? (
        <p role="alert" className="form-erro">
          {erro}
        </p>
      ) : null}
      <div className="painel-acoes">
        <Button type="submit" variant="primary" disabled={enviando || !pronto}>
          Trocar ingrediente
        </Button>
        <Button onClick={onCancelar}>Cancelar</Button>
      </div>
    </form>
  );
}

function ExpansaoEntrada({
  id,
  consulta,
  onAbrirPainel,
  aoMudar,
}: {
  id: string;
  consulta: string;
  onAbrirPainel: () => void;
  aoMudar: () => void;
}) {
  const { pode } = useGestao();
  const [dados, setDados] = useState<EntradaDetalhe | null>(null);
  const [falhou, setFalhou] = useState(false);
  const [corrigindo, setCorrigindo] = useState<string | null>(null);
  const [trocando, setTrocando] = useState<number | null>(null);
  const [editando, setEditando] = useState<string | null>(null);
  const [data, setData] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  const carregar = useCallback(async () => {
    try {
      setDados(await detalheEntrada(id));
      setFalhou(false);
    } catch {
      setFalhou(true);
    }
  }, [id]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  async function salvarValidade(loteId: string, corpo: { validade?: string; sem_validade?: boolean }) {
    setSalvando(true);
    setErro(null);
    try {
      await informarValidade(loteId, corpo);
      setEditando(null);
      setData("");
      await carregar();
      aoMudar();
    } catch (falha) {
      setErro(textoDoErro(falha));
    } finally {
      setSalvando(false);
    }
  }

  const linhaTrocada = dados?.linhas.find((l) => l.posicao === trocando) ?? null;

  return (
    <div className="linha-expandida" role="region" aria-label="Itens desta entrada">
      {falhou ? <p role="alert">Não foi possível abrir esta entrada agora.</p> : null}
      {!dados && !falhou ? <p>Carregando.</p> : null}
      {erro ? (
        <p role="alert" className="form-erro">
          {erro}
        </p>
      ) : null}
      {dados ? (
        <div className="linha-tabela-rola">
          <table className="linha-tabela">
            <thead>
              <tr>
                <th>Item</th>
                <th>Ingrediente</th>
                <th>Quantidade</th>
                <th>Lote</th>
                <th>Validade</th>
                <th>Custo</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {dados.linhas.map((linha) => {
                const destaque = casaLote(consulta, linha.lote);
                return (
                  <tr key={linha.posicao} className={destaque ? "lote-destaque" : undefined}>
                    <td data-rotulo="Item">{linha.item}</td>
                    <td data-rotulo="Ingrediente">{linha.ingrediente}</td>
                    <td data-rotulo="Quantidade">{quantidadeBase(linha.quantidade_base, linha.unidade_base)}</td>
                    <td data-rotulo="Lote">
                      <strong className="lote-codigo">{linha.lote}</strong>
                      {linha.custo_corrigido ? (
                        <SeloCusto antes={linha.custo_antes ?? null} depois={linha.custo_depois ?? null} base={linha.unidade_base} />
                      ) : null}
                    </td>
                    <td data-rotulo="Validade" className={linha.validade_pendente ? "texto-atencao" : undefined}>{validadeTexto(linha)}</td>
                    <td data-rotulo="Custo">{custoDaLinha(linha)}</td>
                    <td data-rotulo="Ações">
                      <span className="acoes-linha">
                        {pode("ajustar") && linha.lote_id ? (
                          <button type="button" className="link-acao" onClick={() => setCorrigindo(linha.lote_id)}>
                            Corrigir custo
                          </button>
                        ) : null}
                        {pode("juntar") && linha.item_id ? (
                          <button
                            type="button"
                            className="link-acao"
                            aria-label={`Trocar ingrediente de ${linha.item}`}
                            onClick={() => setTrocando(linha.posicao)}
                          >
                            Trocar ingrediente
                          </button>
                        ) : null}
                        {linha.validade_pendente && pode("lancar") ? (
                          <button type="button" className="link-acao" onClick={() => setEditando(linha.lote_id)}>
                            Informar validade
                          </button>
                        ) : null}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}
      {corrigindo ? (
        <CorrigirCusto
          loteId={corrigindo}
          onCancelar={() => setCorrigindo(null)}
          onFeito={() => {
            setCorrigindo(null);
            void carregar();
            aoMudar();
          }}
        />
      ) : null}
      {linhaTrocada ? (
        <TrocaNaLinha
          linha={linhaTrocada}
          onCancelar={() => setTrocando(null)}
          onFeito={() => {
            setTrocando(null);
            void carregar();
            aoMudar();
          }}
        />
      ) : null}
      {editando ? (
        <div className="validade-editor">
          <label className="gestao-field">
            <span>Validade do lote</span>
            <input type="date" value={data} onChange={(e) => setData(e.target.value)} />
          </label>
          <div className="validade-acoes">
            <Button variant="primary" disabled={!data || salvando} onClick={() => void salvarValidade(editando, { validade: data })}>
              Salvar validade
            </Button>
            <Button disabled={salvando} onClick={() => void salvarValidade(editando, { sem_validade: true })}>
              Não tem validade
            </Button>
            <Button onClick={() => setEditando(null)}>Cancelar</Button>
          </div>
        </div>
      ) : null}
      <Button onClick={onAbrirPainel}>Ver detalhes</Button>
    </div>
  );
}

type Painel = { tipo: "como" } | { tipo: "entrada"; id: string } | null;

export function Entradas() {
  const { search, navegar, pode, atualizarFluxo } = useGestao();
  const filtro = filtroDaUrl(search);
  const params = new URLSearchParams(search);
  const [lista, setLista] = useState<EntradaResumo[] | null>(null);
  const [falhou, setFalhou] = useState(false);
  const [busca, setBusca] = useState("");
  const [abertas, setAbertas] = useState<Set<string>>(new Set());
  const ancora = useRef<HTMLLIElement | null>(null);
  const [painel, setPainel] = useState<Painel>(() => {
    if (params.get("nova")) return { tipo: "como" };
    const abrir = params.get("abrir");
    return abrir ? { tipo: "entrada", id: abrir } : null;
  });

  const carregar = useCallback(async (f: FiltroEntradas) => {
    setFalhou(false);
    try {
      setLista(await listarEntradas(f));
    } catch (erro) {
      if (!(erro instanceof ApiError && erro.status === 401)) setFalhou(true);
    }
  }, []);

  useEffect(() => {
    void carregar(filtro);
  }, [carregar, filtro]);

  const consulta = busca.trim();
  const visiveis = (lista ?? []).filter((e) => casaEntrada(consulta, e));
  const primeira = visiveis[0]?.id ?? "";

  useEffect(() => {
    if (!consulta || !lista) return;
    setAbertas(new Set(lista.filter((e) => casaEntrada(consulta, e)).map((e) => e.id)));
  }, [consulta, lista]);

  useEffect(() => {
    if (consulta) ancora.current?.scrollIntoView?.({ block: "nearest" });
  }, [consulta, primeira]);

  function mudarFiltro(valor: FiltroEntradas) {
    navegar(valor === "todas" ? "/entradas" : `/entradas?filtro=${valor}`, true);
  }

  const acao = pode("lancar") ? (
    <Button variant="primary" onClick={() => setPainel({ tipo: "como" })}>
      Nova entrada
    </Button>
  ) : undefined;

  return (
    <main className="fluxo-pagina">
      <PageHeader title="Entradas" description="O que chegou?" actions={acao} />
      <label className="gestao-field busca-lista">
        <span>Buscar item, ingrediente ou lote</span>
        <input
          type="search"
          value={busca}
          placeholder="Parte do nome ou do lote, como -12"
          onChange={(e) => setBusca(e.target.value)}
        />
      </label>
      <Chips rotulo="Filtrar entradas" opcoes={FILTROS} valor={filtro} onChange={mudarFiltro} />

      {falhou ? (
        <Card className="fluxo-vazio">
          <p role="alert">Não foi possível carregar as entradas agora.</p>
          <Button onClick={() => void carregar(filtro)}>Tentar de novo</Button>
        </Card>
      ) : null}
      {!lista && !falhou ? <p className="fluxo-estado">Carregando as entradas.</p> : null}

      {lista && lista.length === 0 ? (
        <Card className="fluxo-vazio">
          <p>
            <strong>{filtro === "todas" ? "Nenhuma entrada ainda." : "Nenhuma entrada neste filtro."}</strong>
          </p>
          <p>
            {filtro === "todas"
              ? "Lance o que você tem em casa ou o que acabou de chegar. É daqui que sai o saldo dos ingredientes."
              : "Troque o filtro para ver as outras."}
          </p>
        </Card>
      ) : null}

      {lista && lista.length > 0 && visiveis.length === 0 ? (
        <Card className="fluxo-vazio">
          <p>
            <strong>Nenhuma entrada para “{consulta}”.</strong>
          </p>
          <p>Tente um pedaço do nome ou do lote, como -12.</p>
        </Card>
      ) : null}

      {visiveis.length > 0 ? (
        <Card className="fluxo-lista-card">
          <ul className="fluxo-linhas" aria-label="Entradas">
            {visiveis.map((e, indice) => {
              const aberta = abertas.has(e.id);
              const lotes = rotuloLotes(e.lotes ?? []);
              return (
                <li key={e.id} id={`entrada-${e.id}`} ref={indice === 0 ? ancora : undefined}>
                  <button
                    type="button"
                    className="fluxo-linha entrada-linha"
                    aria-expanded={aberta}
                    onClick={() =>
                      setAbertas((atual) => {
                        const proxima = new Set(atual);
                        if (proxima.has(e.id)) proxima.delete(e.id);
                        else proxima.add(e.id);
                        return proxima;
                      })
                    }
                  >
                    <span className="col-data">{dataBr(e.data)}</span>
                    <span className="col-nome">
                      <strong>{tituloEntrada(e)}</strong>
                      <span className="sub">{segundaLinha(e)}</span>
                    </span>
                    <span className="col-num col-lotes">{lotes}</span>
                    <span className="col-num col-valor">{valorTexto(e.valor, e.valor_parcial)}</span>
                    <span className="col-estado">
                      <StatusChip
                        stage={e.situacao === "pendente" ? "warning" : "ok"}
                        label={e.situacao === "pendente" ? "Pendente" : "Completa"}
                      />
                    </span>
                  </button>
                  {aberta ? (
                    <ExpansaoEntrada
                      id={e.id}
                      consulta={consulta}
                      onAbrirPainel={() => setPainel({ tipo: "entrada", id: e.id })}
                      aoMudar={() => {
                        void carregar(filtro);
                        atualizarFluxo();
                      }}
                    />
                  ) : null}
                </li>
              );
            })}
          </ul>
        </Card>
      ) : null}

      {painel?.tipo === "como" ? (
        <ComoChegou onFechar={() => setPainel(null)} onSemNota={() => navegar("/entradas/sem-nota")} />
      ) : null}
      {painel?.tipo === "entrada" ? (
        <DetalheDaEntrada
          id={painel.id}
          onFechar={() => setPainel(null)}
          aoAtualizar={() => {
            void carregar(filtro);
            atualizarFluxo();
          }}
        />
      ) : null}
    </main>
  );
}
