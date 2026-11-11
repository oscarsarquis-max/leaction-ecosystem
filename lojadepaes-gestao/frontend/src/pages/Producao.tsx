import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import { useGestao } from "../contexto";
import {
  alterarOrdem,
  cancelarOrdem,
  carregarProducao,
  criarOrdem,
  listarProdutos,
  textoDoErro,
  trazerLoja,
  type CalendarioProducao,
  type OrdemProducao,
  type ProdutoLinha,
  type SemVinculo,
} from "../lib/api";
import { dataCurta, dataLonga, diaDaSemana } from "../lib/format";
import { Button } from "../shell/Button";
import { Card } from "../shell/Card";
import { PageHeader } from "../shell/PageHeader";
import { SidePanel } from "../shell/SidePanel";
import { StatusChip } from "../shell/StatusChip";
import "./fluxo.css";

function deslocar(iso: string, dias: number): string {
  const [ano, mes, dia] = iso.split("-").map(Number);
  const data = new Date(Date.UTC(ano, mes - 1, dia));
  data.setUTCDate(data.getUTCDate() + dias);
  const m = String(data.getUTCMonth() + 1).padStart(2, "0");
  const d = String(data.getUTCDate()).padStart(2, "0");
  return `${data.getUTCFullYear()}-${m}-${d}`;
}

function periodo(de: string, ate: string): string[] {
  const dias: string[] = [];
  let cursor = de;
  while (cursor <= ate && dias.length < 7) {
    dias.push(cursor);
    cursor = deslocar(cursor, 1);
  }
  return dias;
}

function rotuloFornada(nome: string, horario: string) {
  return nome.includes(horario) ? nome : `${nome} · ${horario}`;
}

function Selos({ ordem }: { ordem: OrdemProducao }) {
  return (
    <>
      {ordem.sem_receita ? <StatusChip stage="warning" label="Sem receita" /> : null}
      {ordem.diferenca_texto ? <StatusChip stage="warning" label={`Pedido mudou ${ordem.diferenca_texto}`} /> : null}
    </>
  );
}

const ORIGENS = ["programada", "loja", "avulsa"] as const;

function parteOrigem(origem: string, n: number): string {
  if (origem === "programada") return n === 1 ? "1 programada" : `${n} programadas`;
  if (origem === "loja") return `${n} da Loja`;
  if (origem === "avulsa") return n === 1 ? "1 avulsa" : `${n} avulsas`;
  return `${n} ${origem}`;
}

function textoOrigens(ordens: OrdemProducao[]): string {
  const totais = new Map<string, number>();
  for (const ordem of ordens) totais.set(ordem.origem, (totais.get(ordem.origem) ?? 0) + ordem.unidades);
  const partes: string[] = [];
  for (const origem of ORIGENS) {
    const n = totais.get(origem);
    if (n) partes.push(parteOrigem(origem, n));
  }
  for (const [origem, n] of totais) {
    if (!(ORIGENS as readonly string[]).includes(origem)) partes.push(parteOrigem(origem, n));
  }
  return partes.join(" · ");
}

function agrupar(ordens: OrdemProducao[]): OrdemProducao[][] {
  const mapa = new Map<string, OrdemProducao[]>();
  for (const ordem of ordens) {
    const lista = mapa.get(ordem.produto_id) ?? [];
    lista.push(ordem);
    mapa.set(ordem.produto_id, lista);
  }
  return [...mapa.values()];
}

function textoQuantidade(gramas: number): string {
  if (gramas >= 1000) {
    const kg = Math.round((gramas / 1000) * 100) / 100;
    return `${kg.toFixed(2).replace(".", ",")} kg`;
  }
  if (gramas < 20) {
    const valor = Math.round(gramas * 10) / 10;
    return `${valor.toFixed(1).replace(".", ",")} g`;
  }
  return `${Math.round(gramas).toLocaleString("pt-BR")} g`;
}

function massaDoGrupo(grupo: OrdemProducao[]): string | null {
  if (!grupo.some((ordem) => ordem.massa_necessaria_g)) return grupo.find((ordem) => ordem.massa)?.massa ?? null;
  return textoQuantidade(grupo.reduce((soma, ordem) => soma + (ordem.massa_necessaria_g ?? 0), 0));
}

function BotaoPontos({ rotulo, aberto, onClick }: { rotulo: string; aberto: boolean; onClick: () => void }) {
  return (
    <button type="button" className="icone-remover linha-menu-botao" aria-label={rotulo} aria-haspopup="menu" aria-expanded={aberto} onClick={onClick}>
      <svg width="18" height="18" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
        <circle cx="4.5" cy="10" r="1.6" fill="currentColor" />
        <circle cx="10" cy="10" r="1.6" fill="currentColor" />
        <circle cx="15.5" cy="10" r="1.6" fill="currentColor" />
      </svg>
    </button>
  );
}

export function Producao({ dia = false }: { dia?: boolean }) {
  const { search, navegar, pode, sessao, atualizarFluxo } = useGestao();
  const dataUrl = new URLSearchParams(search).get("data");
  const [cursor, setCursor] = useState(dataUrl);
  const [dados, setDados] = useState<CalendarioProducao | null>(null);
  const [falhou, setFalhou] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [semVinculo, setSemVinculo] = useState<SemVinculo[] | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [nova, setNova] = useState(false);
  const [produtos, setProdutos] = useState<ProdutoLinha[]>([]);
  const [edicao, setEdicao] = useState<OrdemProducao | null>(null);
  const [menu, setMenu] = useState<string | null>(null);
  const [diaMovel, setDiaMovel] = useState<string | null>(dataUrl);

  const carregar = useCallback(async () => {
    try {
      const consulta = dia && (dataUrl || cursor) ? { de: (dataUrl || cursor) as string, ate: (dataUrl || cursor) as string } : { data: cursor ?? undefined };
      const resposta = await carregarProducao(consulta);
      setDados(resposta);
      setFalhou(false);
      setDiaMovel((atual) => {
        if (atual && resposta.de <= atual && atual <= resposta.ate) return atual;
        if (resposta.de <= resposta.hoje && resposta.hoje <= resposta.ate) return resposta.hoje;
        return resposta.de;
      });
    } catch {
      setFalhou(true);
    }
  }, [cursor, dataUrl, dia]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  const dias = useMemo(() => (dados ? periodo(dados.de, dados.ate) : []), [dados]);
  const foco = dia ? dataUrl || dados?.hoje || dias[0] : diaMovel || dados?.hoje;
  const fornadas = useMemo(() => {
    if (!dados) return [];
    const comOrdem = new Set(dados.ordens.map((ordem) => ordem.fornada_id));
    return dados.fornadas.filter((item) => item.ativa || comOrdem.has(item.id));
  }, [dados]);

  async function trazer() {
    if (!dados || !foco) return;
    setOcupado(true);
    setErro(null);
    try {
      const intervalo = dia ? { de: foco, ate: foco } : { de: dados.de, ate: dados.ate };
      const resposta = await trazerLoja(intervalo.de, intervalo.ate);
      setSemVinculo(resposta.sem_vinculo);
      await carregar();
      atualizarFluxo();
    } catch (falha) {
      setErro(textoDoErro(falha));
    } finally {
      setOcupado(false);
    }
  }

  async function abrirNova() {
    setErro(null);
    if (!produtos.length) {
      const lista = await listarProdutos("produzidos");
      setProdutos(lista.produtos);
    }
    setNova(true);
  }

  const podeLancar = pode("lancar");
  const acoes = (
    <div className="cal-acoes">
      {podeLancar ? <Button variant="primary" onClick={() => void abrirNova()}>Nova ordem</Button> : null}
      <Button onClick={() => navegar("/producao/programacoes")}>Programações</Button>
      {sessao.organizacao?.fonte_loja ? (
        <Button disabled={ocupado} onClick={() => void trazer()}>Trazer pedidos da Loja</Button>
      ) : null}
    </div>
  );

  return (
    <main className="fluxo-pagina">
      <PageHeader
        title={dia ? "Dia" : "Produção"}
        description={dia ? "O que sai nesta data, fornada por fornada." : "O que faço hoje?"}
        actions={acoes}
      />
      {erro ? <p role="alert" className="form-erro">{erro}</p> : null}
      {falhou ? (
        <Card className="fluxo-vazio">
          <p role="alert">Não foi possível carregar a produção agora.</p>
          <Button onClick={() => void carregar()}>Tentar de novo</Button>
        </Card>
      ) : null}
      {!dados && !falhou ? <p className="fluxo-estado">Carregando a produção.</p> : null}
      {dados && !dia ? (
        <div className="cal-nav">
          <Button onClick={() => setCursor(deslocar(dados.de, -7))}>Semana anterior</Button>
          <Button onClick={() => setCursor(dados.hoje)}>Hoje</Button>
          <Button onClick={() => setCursor(deslocar(dados.de, 7))}>Próxima</Button>
        </div>
      ) : null}
      {dados && !dia ? <Grade dados={dados} dias={dias} fornadas={fornadas} diaMovel={foco ?? dados.hoje} onDia={setDiaMovel} onAbrir={(data) => navegar(`/producao/dia?data=${data}`)} /> : null}
      {dados && dia && foco ? (
        <DiaLista
          dados={dados}
          data={foco}
          fornadas={fornadas}
          podeLancar={podeLancar}
          menu={menu}
          setMenu={setMenu}
          onEditar={setEdicao}
          onMudou={async () => {
            await carregar();
            atualizarFluxo();
          }}
          onImprimir={(fornadaId) => navegar(`/producao/comanda?data=${foco}&fornada=${fornadaId}`)}
        />
      ) : null}
      {semVinculo ? (
        <section className="cal-sem-vinculo" aria-label="Pedidos sem produto na Gestão">
          <h2>Pedidos sem produto na Gestão</h2>
          {semVinculo.length === 0 ? <p>Todos os pedidos do período têm produto na Gestão.</p> : null}
          <ul>
            {semVinculo.map((item) => (
              <li key={`${item.data}-${item.nome}`}>
                {dataCurta(item.data)} · {item.nome} · {item.unidades} {item.unidades === 1 ? "unidade" : "unidades"}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {nova && dados ? (
        <NovaOrdem
          data={foco || dados.hoje}
          fornadas={fornadas.filter((item) => item.ativa)}
          produtos={produtos}
          onFechar={() => setNova(false)}
          onSalvou={async () => {
            setNova(false);
            await carregar();
            atualizarFluxo();
          }}
        />
      ) : null}
      {edicao && dados ? (
        <EditarOrdem
          ordem={edicao}
          fornadas={fornadas.filter((item) => item.ativa)}
          onFechar={() => setEdicao(null)}
          onSalvou={async () => {
            setEdicao(null);
            await carregar();
            atualizarFluxo();
          }}
        />
      ) : null}
    </main>
  );
}

function Grade({
  dados,
  dias,
  fornadas,
  diaMovel,
  onDia,
  onAbrir,
}: {
  dados: CalendarioProducao;
  dias: string[];
  fornadas: CalendarioProducao["fornadas"];
  diaMovel: string;
  onDia: (dia: string) => void;
  onAbrir: (dia: string) => void;
}) {
  return (
    <>
      <div className="cal-grade" role="table" aria-label="Semana de produção">
        <div />
        {dias.map((dia) => (
          <button key={dia} type="button" className={dia === dados.hoje ? "cal-dia hoje" : "cal-dia"} onClick={() => onAbrir(dia)}>
            <span>{diaDaSemana(dia).slice(0, 3)}</span>
            <strong>{dataCurta(dia)}</strong>
          </button>
        ))}
        {fornadas.map((fornada) => (
          <div key={fornada.id} className="cal-linha">
            <div className="cal-fornada">
              <strong>{rotuloFornada(fornada.nome, fornada.horario)}</strong>
            </div>
            {dias.map((dia) => {
              const grupos = agrupar(dados.ordens.filter((ordem) => ordem.data === dia && ordem.fornada_id === fornada.id));
              return (
                <div key={dia} className={dia === dados.hoje ? "cal-celula hoje" : "cal-celula"}>
                  {grupos.map((grupo) => (
                    <button key={grupo[0].produto_id} type="button" className="cal-ordem" onClick={() => onAbrir(dia)}>
                      <strong>{grupo[0].produto}</strong>
                      <span>{grupo.reduce((soma, ordem) => soma + ordem.unidades, 0)} un</span>
                      <span className="cal-origens">{textoOrigens(grupo)}</span>
                      {grupo.map((ordem) => <Selos key={ordem.id} ordem={ordem} />)}
                    </button>
                  ))}
                </div>
              );
            })}
          </div>
        ))}
      </div>
      <div className="cal-movel">
        <label className="gestao-field">
          <span>Dia</span>
          <select value={diaMovel} onChange={(event) => onDia(event.target.value)}>
            {dias.map((dia) => (
              <option key={dia} value={dia}>
                {dataLonga(dia)}
              </option>
            ))}
          </select>
        </label>
        {fornadas.map((fornada) => {
          const grupos = agrupar(dados.ordens.filter((ordem) => ordem.data === diaMovel && ordem.fornada_id === fornada.id));
          return (
            <section key={fornada.id} className={diaMovel === dados.hoje ? "cal-celula hoje" : "cal-celula"}>
              <h2>{rotuloFornada(fornada.nome, fornada.horario)}</h2>
              {grupos.length === 0 ? <p>Nada nesta fornada.</p> : null}
              {grupos.map((grupo) => (
                <button key={grupo[0].produto_id} type="button" className="cal-ordem" onClick={() => onAbrir(diaMovel)}>
                  <strong>{grupo[0].produto}</strong>
                  <span>{grupo.reduce((soma, ordem) => soma + ordem.unidades, 0)} un</span>
                  <span className="cal-origens">{textoOrigens(grupo)}</span>
                  {grupo.map((ordem) => <Selos key={ordem.id} ordem={ordem} />)}
                </button>
              ))}
            </section>
          );
        })}
      </div>
    </>
  );
}

function DiaLista({
  dados,
  data,
  fornadas,
  podeLancar,
  menu,
  setMenu,
  onEditar,
  onMudou,
  onImprimir,
}: {
  dados: CalendarioProducao;
  data: string;
  fornadas: CalendarioProducao["fornadas"];
  podeLancar: boolean;
  menu: string | null;
  setMenu: (id: string | null) => void;
  onEditar: (ordem: OrdemProducao) => void;
  onMudou: () => Promise<void>;
  onImprimir: (fornadaId: string) => void;
}) {
  return (
    <div className="cal-dia-lista">
      <p className="cal-data-titulo">{dataLonga(data)}</p>
      {fornadas.map((fornada) => {
        const ordens = dados.ordens.filter((ordem) => ordem.fornada_id === fornada.id);
        return (
          <section key={fornada.id}>
            <header className="cal-fornada-head">
              <h2>{rotuloFornada(fornada.nome, fornada.horario)}</h2>
              {podeLancar && ordens.length ? (
                <Button variant="primary" onClick={() => onImprimir(fornada.id)}>Imprimir comanda da fornada</Button>
              ) : null}
            </header>
            {ordens.length === 0 ? <p className="fluxo-estado">Nada nesta fornada.</p> : null}
            {ordens.length ? (
              <Card className="fluxo-lista-card">
                <table className="lista-entradas lista-producao">
                  <thead>
                    <tr>
                      <th scope="col">Produto</th>
                      <th scope="col">Unidades</th>
                      <th scope="col">Peças</th>
                      <th scope="col">Massa</th>
                      <th scope="col">Origem</th>
                      <th scope="col">Situação</th>
                      <th scope="col"><span className="sr-only">Ações</span></th>
                    </tr>
                  </thead>
                  <tbody>
                    {agrupar(ordens).map((grupo) => {
                      const unidades = grupo.reduce((soma, ordem) => soma + ordem.unidades, 0);
                      const pecas = grupo.find((ordem) => ordem.pecas)?.pecas ?? "—";
                      const situacao = [...new Set(grupo.map((ordem) => ordem.situacao_rotulo))].join(" · ");
                      return (
                      <tr key={grupo[0].produto_id} className="entrada-linha">
                        <td className="col-entrada" data-label="Produto">
                          <strong>{grupo[0].produto}</strong>
                          {grupo.map((ordem) => <Selos key={ordem.id} ordem={ordem} />)}
                        </td>
                        <td data-label="Unidades" className="num">{unidades}</td>
                        <td data-label="Peças" className="sem-quebra">{pecas}</td>
                        <td data-label="Massa" className="sem-quebra">{massaDoGrupo(grupo) ?? "—"}</td>
                        <td data-label="Origem" className="sem-quebra">{textoOrigens(grupo)}</td>
                        <td data-label="Situação">{situacao}</td>
                        <td data-label="Ações">
                          {podeLancar ? (
                            <div className="linha-menu">
                              <BotaoPontos rotulo={`Ações de ${grupo[0].produto}`} aberto={menu === grupo[0].produto_id} onClick={() => setMenu(menu === grupo[0].produto_id ? null : grupo[0].produto_id)} />
                              {menu === grupo[0].produto_id ? (
                                <div className="linha-menu-lista" role="menu">
                                  {grupo.map((ordem) => {
                                    const sufixo = grupo.length > 1 ? ` · ${parteOrigem(ordem.origem, ordem.unidades)}` : "";
                                    return (
                                      <Fragment key={ordem.id}>
                                        <button type="button" disabled={ordem.situacao !== "planejada"} onClick={() => { setMenu(null); onEditar(ordem); }}>Editar unidades{sufixo}</button>
                                        <button type="button" disabled={ordem.situacao !== "planejada"} onClick={() => { setMenu(null); onEditar({ ...ordem, observacao: "fornada" }); }}>Mudar fornada{sufixo}</button>
                                        <button type="button" className="perigo" onClick={() => { setMenu(null); void cancelarOrdem(ordem.id).then(onMudou); }}>Cancelar{sufixo}</button>
                                      </Fragment>
                                    );
                                  })}
                                </div>
                              ) : null}
                            </div>
                          ) : null}
                        </td>
                      </tr>
                      );
                    })}
                  </tbody>
                </table>
              </Card>
            ) : null}
          </section>
        );
      })}
    </div>
  );
}

function NovaOrdem({
  data,
  fornadas,
  produtos,
  onFechar,
  onSalvou,
}: {
  data: string;
  fornadas: CalendarioProducao["fornadas"];
  produtos: ProdutoLinha[];
  onFechar: () => void;
  onSalvou: () => Promise<void>;
}) {
  const [produtoId, setProdutoId] = useState(produtos[0]?.id ?? "");
  const [fornadaId, setFornadaId] = useState(fornadas[0]?.id ?? "");
  const [unidades, setUnidades] = useState("10");
  const [observacao, setObservacao] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  async function gravar() {
    setOcupado(true);
    setErro(null);
    try {
      await criarOrdem({
        data,
        fornada_id: fornadaId,
        produto_id: produtoId,
        unidades: Number(unidades),
        observacao,
      });
      await onSalvou();
    } catch (falha) {
      setErro(textoDoErro(falha));
    } finally {
      setOcupado(false);
    }
  }

  return (
    <SidePanel titulo="Nova ordem" subtitulo="Avulsa" onFechar={onFechar} rodape={<div className="painel-acoes"><Button onClick={onFechar}>Cancelar</Button><Button variant="primary" disabled={ocupado || !produtoId} onClick={() => void gravar()}>Salvar</Button></div>}>
      {erro ? <p role="alert" className="form-erro">{erro}</p> : null}
      <label className="gestao-field"><span>Produto</span>
        <select value={produtoId} onChange={(e) => setProdutoId(e.target.value)}>
          {produtos.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}
        </select>
      </label>
      <label className="gestao-field"><span>Fornada</span>
        <select value={fornadaId} onChange={(e) => setFornadaId(e.target.value)}>
          {fornadas.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}
        </select>
      </label>
      <label className="gestao-field"><span>Unidades</span>
        <input inputMode="numeric" value={unidades} onChange={(e) => setUnidades(e.target.value.replace(/\D/g, ""))} />
      </label>
      <label className="gestao-field"><span>Observação</span>
        <input value={observacao} onChange={(e) => setObservacao(e.target.value)} />
      </label>
    </SidePanel>
  );
}

function EditarOrdem({
  ordem,
  fornadas,
  onFechar,
  onSalvou,
}: {
  ordem: OrdemProducao;
  fornadas: CalendarioProducao["fornadas"];
  onFechar: () => void;
  onSalvou: () => Promise<void>;
}) {
  const trocarFornada = ordem.observacao === "fornada";
  const [unidades, setUnidades] = useState(String(ordem.unidades));
  const [fornadaId, setFornadaId] = useState(ordem.fornada_id);
  const [erro, setErro] = useState<string | null>(null);

  async function gravar() {
    setErro(null);
    try {
      await alterarOrdem(ordem.id, trocarFornada ? { fornada_id: fornadaId } : { unidades: Number(unidades) });
      await onSalvou();
    } catch (falha) {
      setErro(textoDoErro(falha));
    }
  }

  return (
    <SidePanel titulo={ordem.produto} subtitulo={trocarFornada ? "Mudar fornada" : "Editar unidades"} onFechar={onFechar} rodape={<div className="painel-acoes"><Button onClick={onFechar}>Cancelar</Button><Button variant="primary" onClick={() => void gravar()}>Salvar</Button></div>}>
      {erro ? <p role="alert" className="form-erro">{erro}</p> : null}
      {trocarFornada ? (
        <label className="gestao-field"><span>Fornada</span>
          <select value={fornadaId} onChange={(e) => setFornadaId(e.target.value)}>
            {fornadas.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}
          </select>
        </label>
      ) : (
        <label className="gestao-field"><span>Unidades</span>
          <input inputMode="numeric" value={unidades} onChange={(e) => setUnidades(e.target.value.replace(/\D/g, ""))} />
        </label>
      )}
    </SidePanel>
  );
}
