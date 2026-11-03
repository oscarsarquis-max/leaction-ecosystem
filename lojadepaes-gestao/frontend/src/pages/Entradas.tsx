import { useCallback, useEffect, useState } from "react";
import { useGestao } from "../contexto";
import {
  ApiError,
  detalheEntrada,
  informarValidade,
  listarEntradas,
  textoDoErro,
  type EntradaDetalhe,
  type EntradaResumo,
  type FiltroEntradas,
} from "../lib/api";
import { custoTexto, dataBr, dinheiro, MOTIVOS, quantidadeBase } from "../lib/format";
import { Button } from "../shell/Button";
import { Card } from "../shell/Card";
import { CorrigirCusto } from "../shell/CorrigirCusto";
import { Chips } from "../shell/Chips";
import { PageHeader } from "../shell/PageHeader";
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

type Painel = { tipo: "como" } | { tipo: "entrada"; id: string } | null;

export function Entradas() {
  const { search, navegar, pode, atualizarFluxo } = useGestao();
  const filtro = filtroDaUrl(search);
  const params = new URLSearchParams(search);
  const [lista, setLista] = useState<EntradaResumo[] | null>(null);
  const [falhou, setFalhou] = useState(false);
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

      {lista && lista.length > 0 ? (
        <Card className="fluxo-lista-card">
          <ul className="fluxo-linhas" aria-label="Entradas">
            {lista.map((e) => (
              <li key={e.id}>
                <button type="button" className="fluxo-linha entrada-linha" onClick={() => setPainel({ tipo: "entrada", id: e.id })}>
                  <span className="col-data">{dataBr(e.data)}</span>
                  <span className="col-nome">
                    <strong>{motivoTexto(e)}</strong>
                    <span className="sub">{e.tipo === "sem_nota" ? "Sem nota" : "Com nota"}</span>
                  </span>
                  <span className="col-num">
                    {e.itens} {e.itens === 1 ? "item" : "itens"}
                  </span>
                  <span className="col-num">{valorTexto(e.valor, e.valor_parcial)}</span>
                  <span className="col-estado">
                    <StatusChip
                      stage={e.situacao === "pendente" ? "warning" : "ok"}
                      label={e.situacao === "pendente" ? "Pendente" : "Completa"}
                    />
                  </span>
                </button>
              </li>
            ))}
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
