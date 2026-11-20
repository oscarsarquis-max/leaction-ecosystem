import { useCallback, useEffect, useState } from "react";
import { useGestao } from "../contexto";
import { carregarCustos, carregarHoje, type CustosVisao, type Fornada, type Hoje as HojeDados, type ItemDemanda } from "../lib/api";
import { dataCurta, dataLonga, dinheiro, inteiro, pluralPaes, quantidadeBase, quando } from "../lib/format";
import { Ponto } from "../shell/Ponto";
import { Button } from "../shell/Button";
import { Card } from "../shell/Card";
import { PageHeader } from "../shell/PageHeader";
import { StatusChip } from "../shell/StatusChip";
import "./fluxo.css";
import "./pages.css";

const PERIODOS = [7, 14, 30];

function maiuscula(texto: string): string {
  return texto ? texto[0].toUpperCase() + texto.slice(1) : texto;
}

function nomeDoItem(item: ItemDemanda): string {
  return item.produto_ou_massa ?? "Item sem nome";
}

/** Como o item da Loja está no Gestão: ligado a um produto e com receita publicada, ou não. */
function SeloDoVinculo({ item }: { item: ItemDemanda }) {
  if (item.vinculo === undefined) return <span className="travessao">—</span>;
  if (item.vinculo === null) return <StatusChip stage="cancelled" label="Sem vínculo" />;
  if (item.vinculo.receita === "publicada") return <StatusChip stage="ok" label="Receita publicada" />;
  if (item.vinculo.receita === "rascunho") return <StatusChip stage="warning" label="Receita em rascunho" />;
  return <StatusChip stage="cancelled" label="Sem receita" />;
}

function FornadaCard({ fornada, hoje }: { fornada: Fornada; hoje: string }) {
  const titulo = `fornada-${fornada.data}`;
  return (
    <Card className="hoje-fornada">
      <section aria-labelledby={titulo}>
        <header className="hoje-fornada-head">
          <div>
            <h3 id={titulo}>{dataLonga(fornada.data)}</h3>
            <p className="hoje-quando">{quando(hoje, fornada.data)}</p>
          </div>
          <div className="hoje-fornada-total">
            <strong>{inteiro(fornada.paes_fisicos)}</strong>
            <span>{fornada.paes_fisicos === 1 ? "pão" : "pães"}</span>
          </div>
        </header>
        {fornada.unidades_pendentes > 0 ? (
          <p className="hoje-aviso">
            <StatusChip stage="warning" label="Unidades a confirmar" />
            <span>
              {fornada.unidades_pendentes === 1
                ? "1 linha não informa quantos pães tem. O total acima pode estar menor."
                : `${fornada.unidades_pendentes} linhas não informam quantos pães têm. O total acima pode estar menor.`}
            </span>
          </p>
        ) : null}
        <table className="hoje-tabela hoje-tabela-demanda">
          <caption className="sr-only">Demanda confirmada em {dataLonga(fornada.data)}</caption>
          <thead>
            <tr>
              <th scope="col">Produto</th>
              <th scope="col">Variante ou forma</th>
              <th scope="col" className="num">
                Pães
              </th>
              <th scope="col">No Gestão</th>
            </tr>
          </thead>
          <tbody>
            {fornada.itens.map((item, indice) => (
              <tr key={`${item.origem}-${nomeDoItem(item)}-${item.variante_ou_forma}-${indice}`}>
                <th scope="row" data-label="Produto">
                  {nomeDoItem(item)}
                  {item.origem === "criador" ? <span className="hoje-origem">Criador de pães</span> : null}
                </th>
                <td data-label="Variante ou forma">{item.variante_ou_forma ?? "—"}</td>
                <td data-label="Pães" className="num">
                  <span>
                    {inteiro(item.paes_fisicos)}
                    {item.linhas_unidades_pendentes > 0 ? <span className="hoje-pendente"> + a confirmar</span> : null}
                  </span>
                </td>
                <td data-label="No Gestão">
                  <SeloDoVinculo item={item} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </Card>
  );
}

function Necessidade({ dados }: { dados: HojeDados }) {
  const necessidade = dados.necessidade;
  if (!necessidade || dados.fornadas.length === 0) return null;
  const itens = [...necessidade.itens].sort((a, b) => Number(b.falta > 0) - Number(a.falta > 0) || a.ingrediente.localeCompare(b.ingrediente));
  const faltam = itens.filter((item) => item.falta > 0).length;
  return (
    <Card className="hoje-necessidade">
      <section aria-labelledby="hoje-necessidade-titulo">
        <header className="hoje-bloco-head">
          <h3 id="hoje-necessidade-titulo">Ingredientes para essas fornadas</h3>
          <p className="sub">
            {itens.length === 0
              ? "Nenhuma receita publicada entre os pães confirmados."
              : faltam === 0
                ? "O estoque cobre tudo."
                : faltam === 1
                  ? "1 ingrediente vai faltar."
                  : `${faltam} ingredientes vão faltar.`}
          </p>
        </header>
        {itens.length > 0 ? (
          <table className="hoje-tabela hoje-tabela-necessidade">
            <caption className="sr-only">Ingredientes que as fornadas confirmadas consomem</caption>
            <thead>
              <tr>
                <th scope="col">Ingrediente</th>
                <th scope="col" className="num">
                  Precisa
                </th>
                <th scope="col" className="num">
                  Em estoque
                </th>
                <th scope="col">Situação</th>
              </tr>
            </thead>
            <tbody>
              {itens.map((item) => (
                <tr key={item.ingrediente_id}>
                  <th scope="row" data-label="Ingrediente">
                    {item.ingrediente}
                  </th>
                  <td data-label="Precisa" className="num">
                    {quantidadeBase(item.precisa, item.unidade_base)}
                  </td>
                  <td data-label="Em estoque" className="num">
                    {quantidadeBase(item.tem, item.unidade_base)}
                  </td>
                  <td data-label="Situação">
                    {item.falta > 0 ? (
                      <StatusChip stage="cancelled" label={`Falta ${quantidadeBase(item.falta, item.unidade_base)}`} />
                    ) : (
                      <StatusChip stage="ok" label="Tem" />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
        {necessidade.fora_da_conta > 0 ? (
          <p className="hoje-nota">
            {necessidade.fora_da_conta === 1
              ? "1 pão ficou fora da conta: sem vínculo ou sem receita publicada."
              : `${necessidade.fora_da_conta} pães ficaram fora da conta: sem vínculo ou sem receita publicada.`}
          </p>
        ) : null}
      </section>
    </Card>
  );
}

function ProximasFornadas({ dados, recarregar }: { dados: HojeDados; recarregar: () => void }) {
  const { sessao } = useGestao();
  return (
    <section className="hoje-bloco hoje-ordem-fornadas" aria-labelledby="hoje-fornadas-titulo">
      <header className="hoje-bloco-head">
        <h2 id="hoje-fornadas-titulo">Próximas fornadas da Loja</h2>
        {dados.compatibilidade.ok && dados.fornadas.length > 0 ? (
          <p className="sub">
            {`${pluralPaes(dados.total_paes_fisicos)} em ${dados.fornadas.length} ${dados.fornadas.length === 1 ? "fornada" : "fornadas"} · pedidos aceitos, em produção ou prontos; teste e duplicados não entram`}
          </p>
        ) : null}
      </header>
      {!dados.compatibilidade.ok ? (
        <Card className="hoje-vazio">
          <p role="alert">{dados.compatibilidade.mensagem}</p>
          <Button onClick={recarregar}>Tentar de novo</Button>
        </Card>
      ) : (
        <>
          {/* Aviso técnico (versão da Loja): só para quem administra a plataforma. */}
          {dados.compatibilidade.mensagem && sessao?.admin_plataforma ? (
            <p className="hoje-aviso hoje-aviso-solto">
              <StatusChip stage="warning" label="Técnico" />
              <span>{dados.compatibilidade.mensagem}</span>
            </p>
          ) : null}
          {dados.fornadas.length === 0 ? (
            <Card className="hoje-vazio">
              <p>
                <strong>Nenhuma demanda confirmada nos próximos {dados.dias} dias.</strong>
              </p>
              <p>Os pedidos aceitos na Loja aparecem aqui, por data de fornada.</p>
            </Card>
          ) : (
            <div className="hoje-lista">
              {dados.fornadas.map((fornada) => (
                <FornadaCard key={fornada.data} fornada={fornada} hoje={dados.hoje} />
              ))}
              <Necessidade dados={dados} />
            </div>
          )}
        </>
      )}
    </section>
  );
}

function ProducaoDeHoje({ dados }: { dados: HojeDados }) {
  const { navegar } = useGestao();
  const blocos = dados.producao_hoje ?? [];
  const temOrdem = blocos.some((item) => item.ordens > 0);
  return (
    <section className="hoje-bloco hoje-producao hoje-ordem-producao" aria-label="Produção de hoje">
      <header className="hoje-producao-head">
        <h2>Produção de hoje</h2>
        <Button onClick={() => navegar(`/producao/dia?data=${dados.hoje}`)}>Abrir o dia</Button>
      </header>
      {!temOrdem ? (
        <Card className="hoje-vazio">
          <p>Nada planejado hoje.</p>
        </Card>
      ) : (
        <div className="hoje-producao-lista">
          {blocos
            .filter((item) => item.ordens > 0)
            .map((item) => (
              <Card key={item.fornada_id} className="hoje-producao-card">
                <button type="button" className="hoje-producao-link" onClick={() => navegar(`/producao/dia?data=${dados.hoje}`)}>
                  <strong>{item.fornada.includes(item.horario) ? item.fornada : `${item.fornada} · ${item.horario}`}</strong>
                  <span>{item.unidades === 1 ? "1 unidade" : `${item.unidades} unidades`}</span>
                  {item.pedido_mudou ? <StatusChip stage="warning" label="Pedido mudou" /> : null}
                </button>
              </Card>
            ))}
        </div>
      )}
    </section>
  );
}

function Pendencias({ dados }: { dados: HojeDados }) {
  const { navegar } = useGestao();
  const itens = dados.pendencias ?? [];
  return (
    <Card className="hoje-lateral-card hoje-ordem-pendencias">
      <section aria-labelledby="hoje-pendencias-titulo">
        <h2 id="hoje-pendencias-titulo">Pendências</h2>
        {itens.length === 0 ? (
          <p className="sub hoje-lateral-vazio">Nada pendente no cadastro.</p>
        ) : (
          <ul className="hoje-pendencias">
            {itens.map((item) => (
              <li key={item.codigo} className={item.estado}>
                <span className="dot" aria-hidden="true" />
                <span className="hoje-pendencia-texto">{item.texto}</span>
                <button type="button" className="hoje-pendencia-acao" onClick={() => navegar(item.href)}>
                  {item.acao}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </Card>
  );
}

function Estoque({ dados }: { dados: HojeDados }) {
  const { navegar } = useGestao();
  const acabaram = dados.acabaram ?? [];
  const vencem = dados.vence_em_7_dias;
  return (
    <Card className="hoje-lateral-card hoje-ordem-estoque">
      <section aria-labelledby="hoje-estoque-titulo">
        <h2 id="hoje-estoque-titulo">Estoque</h2>
        {vencem.length === 0 && acabaram.length === 0 ? <p className="sub hoje-lateral-vazio">Nada vencendo e nada acabou.</p> : null}
        {vencem.length > 0 ? (
          <div className="hoje-estoque-grupo" aria-label="Vence em 7 dias" role="group">
            <h3>Vence em 7 dias</h3>
            <ul>
              {vencem.map((v) => (
                <li key={v.lote_id}>
                  <button type="button" onClick={() => navegar("/ingredientes?filtro=vence7")}>
                    <span>
                      <strong>{v.ingrediente}</strong>
                      <span className="sub">
                        {" "}
                        · lote {v.codigo} · {v.dias === 0 ? "hoje" : v.dias === 1 ? "amanhã" : `${dataCurta(v.validade)}`}
                      </span>
                    </span>
                    <span>{quantidadeBase(v.saldo, v.unidade_base)}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {acabaram.length > 0 ? (
          <div className="hoje-estoque-grupo" aria-label="Acabou" role="group">
            <h3>Acabou</h3>
            <ul>
              {acabaram.map((s) => (
                <li key={s.id}>
                  <button type="button" onClick={() => navegar("/ingredientes?filtro=sem_saldo")}>
                    <strong>{s.nome}</strong>
                    <span className="sub">saldo zero</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </section>
    </Card>
  );
}

/* ------------------------------------------------------------------ painel (GESTAO-020) */

const DIAS_SEMANA = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"];

function somarDias(iso: string, dias: number): string {
  const [y, m, d] = iso.split("-").map(Number);
  const data = new Date(Date.UTC(y, m - 1, d + dias));
  return data.toISOString().slice(0, 10);
}

function diaCurto(iso: string): { semana: string; dia: string } {
  const [y, m, d] = iso.split("-").map(Number);
  const data = new Date(Date.UTC(y, m - 1, d));
  return { semana: DIAS_SEMANA[data.getUTCDay()], dia: String(d) };
}

type Indicador = { id: string; rotulo: string; valor: string; detalhe: string; href: string; tom?: "alerta" | "ok"; medidor?: number };

function Indicadores({ itens }: { itens: Indicador[] }) {
  const { navegar } = useGestao();
  return (
    <section className="painel-indicadores" aria-label="Números do dia">
      {itens.map((item) => (
        <button key={item.id} type="button" className={`painel-indicador${item.tom ? ` ${item.tom}` : ""}`} onClick={() => navegar(item.href)}>
          <span className="rotulo">{item.rotulo}</span>
          <strong>{item.valor}</strong>
          {item.medidor != null ? (
            <span className="painel-medidor" aria-hidden="true">
              <span style={{ width: `${Math.max(0, Math.min(1, item.medidor)) * 100}%` }} />
            </span>
          ) : null}
          <span className="detalhe">{item.detalhe}</span>
        </button>
      ))}
    </section>
  );
}

/** Barras por dia: uma série (pães confirmados), um tom; o dia com pedido leva ao dia da Produção. */
function GraficoDemanda({ dados }: { dados: HojeDados }) {
  const { navegar } = useGestao();
  const porDia = new Map(dados.fornadas.map((f) => [f.data, f.paes_fisicos]));
  const dias = Array.from({ length: dados.dias }, (_, i) => somarDias(dados.hoje, i));
  const maximo = Math.max(1, ...dias.map((d) => porDia.get(d) ?? 0));
  return (
    <Card className="painel-grafico">
      <section aria-labelledby="painel-demanda-titulo">
        <header className="painel-grafico-head">
          <div>
            <h2 id="painel-demanda-titulo">Pães confirmados pela Loja, por dia</h2>
            <p className="sub">{`${pluralPaes(dados.total_paes_fisicos)} nos próximos ${dados.dias} dias`}</p>
          </div>
          <Button onClick={() => navegar("/producao")}>Abrir a produção</Button>
        </header>
        <div className="grafico-barras" role="list" aria-label="Pães por dia">
          {dias.map((dia) => {
            const valor = porDia.get(dia) ?? 0;
            const { semana, dia: numeroDia } = diaCurto(dia);
            const texto = `${dataCurta(dia)}: ${valor === 0 ? "nenhum pão" : pluralPaes(valor)}`;
            const conteudo = (
              <>
                <span className="grafico-valor">{valor > 0 ? inteiro(valor) : ""}</span>
                <span className="grafico-trilho">
                  <span className="grafico-barra" style={{ height: valor > 0 ? `${Math.max(6, (valor / maximo) * 100)}%` : "0" }} />
                </span>
                <span className={`grafico-rotulo${dia === dados.hoje ? " e-hoje" : ""}`}>
                  <span>{semana}</span>
                  <strong>{numeroDia}</strong>
                </span>
              </>
            );
            return (
              <div role="listitem" key={dia} className="grafico-coluna">
                {valor > 0 ? (
                  <button type="button" className="grafico-alvo" aria-label={texto} data-dica={texto} onClick={() => navegar(`/producao/dia?data=${dia}`)}>
                    {conteudo}
                  </button>
                ) : (
                  <span className="grafico-alvo vazio" aria-label={texto}>
                    {conteudo}
                  </span>
                )}
              </div>
            );
          })}
        </div>
        {dados.fornadas.length === 0 ? <p className="sub painel-grafico-vazio">Nenhum pedido confirmado no período.</p> : null}
      </section>
    </Card>
  );
}

/** Divergente em torno do zero: sobra à direita, prejuízo à esquerda; o valor sempre escrito. */
function GraficoResultado({ custos }: { custos: CustosVisao | null }) {
  const { navegar } = useGestao();
  const linhas = (custos?.produtos ?? [])
    .map((p) => ({ produto: p, preco: p.loja[0] ?? p.preco_proprio ?? null }))
    .filter((l) => l.preco?.resultado != null)
    .sort((a, b) => (a.preco!.resultado as number) - (b.preco!.resultado as number));
  const maximo = Math.max(1, ...linhas.map((l) => Math.abs(l.preco!.resultado as number)));
  const negativos = linhas.some((l) => (l.preco!.resultado as number) < 0);
  return (
    <Card className="painel-grafico">
      <section aria-labelledby="painel-resultado-titulo">
        <header className="painel-grafico-head">
          <div>
            <h2 id="painel-resultado-titulo">Resultado por pão</h2>
            <p className="sub">Preço − ingredientes − parte do custo fixo</p>
          </div>
          <Button onClick={() => navegar("/gestao/custos")}>Abrir custos</Button>
        </header>
        {linhas.length === 0 ? (
          <p className="sub painel-grafico-vazio">
            {custos == null ? "Os custos ainda não foram calculados." : "Nenhum produto com receita publicada e preço."}
          </p>
        ) : (
          <ul className={`grafico-divergente${negativos ? "" : " so-positivo"}`} aria-label="Resultado por pão de cada produto">
            {linhas.map(({ produto, preco }) => {
              const valor = preco!.resultado as number;
              const largura = `${(Math.abs(valor) / maximo) * (negativos ? 50 : 100)}%`;
              return (
                <li key={produto.produto_id}>
                  <button type="button" className="grafico-divergente-linha" onClick={() => navegar("/gestao/custos")}>
                    <span className="grafico-divergente-nome">{produto.nome}</span>
                    <span className="grafico-divergente-trilho" aria-hidden="true">
                      <span className={`grafico-divergente-barra ${valor < 0 ? "negativo" : "positivo"}`} style={{ width: largura }} />
                    </span>
                    <span className={`grafico-divergente-valor ${valor < 0 ? "negativo" : "positivo"}`}>
                      {valor < 0 ? `− ${dinheiro(-valor)}` : dinheiro(valor)}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </Card>
  );
}

/** O fluxo da padaria e a gestão: todas as áreas, com a situação de cada uma. */
function Atalhos({ dados }: { dados: HojeDados }) {
  const { navegar } = useGestao();
  const etapas = dados.fluxo.etapas ?? [];
  return (
    <Card className="hoje-lateral-card hoje-ordem-atalhos">
      <section aria-labelledby="painel-atalhos-titulo">
        <h2 id="painel-atalhos-titulo">Áreas</h2>
        <ul className="painel-atalhos">
          {etapas.map((etapa, indice) => (
            <li key={etapa.id}>
              <button type="button" disabled={!etapa.href} onClick={() => etapa.href && navegar(etapa.href)}>
                <span className="painel-atalho-num">{indice + 1}</span>
                <span className="painel-atalho-texto">
                  <strong>{etapa.nome}</strong>
                  <span className="sub">{etapa.frase || etapa.pergunta}</span>
                </span>
                <Ponto estado={etapa.estado} />
              </button>
            </li>
          ))}
          {[
            { id: "custos", nome: "Custos", frase: "custos fixos, margem e preço", href: "/gestao/custos" },
            { id: "padroes", nome: "Padrões", frase: "padrões da casa e fornadas", href: "/gestao/padroes" },
          ].map((item) => (
            <li key={item.id} className="gestao">
              <button type="button" onClick={() => navegar(item.href)}>
                <span className="painel-atalho-num" aria-hidden="true">·</span>
                <span className="painel-atalho-texto">
                  <strong>{item.nome}</strong>
                  <span className="sub">{item.frase}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      </section>
    </Card>
  );
}

export function Hoje() {
  const [dias, setDias] = useState(14);
  const [dados, setDados] = useState<HojeDados | null>(null);
  const [custos, setCustos] = useState<CustosVisao | null>(null);
  const [falhou, setFalhou] = useState(false);
  const [carregando, setCarregando] = useState(true);

  const carregar = useCallback(async (periodo: number) => {
    setCarregando(true);
    setFalhou(false);
    // Os custos enriquecem o painel, mas não seguram o dia: se falharem, o resto aparece.
    void carregarCustos()
      .then(setCustos)
      .catch(() => setCustos(null));
    try {
      setDados(await carregarHoje(periodo));
    } catch {
      setFalhou(true);
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    void carregar(dias);
  }, [carregar, dias]);

  const periodo = (
    <label className="gestao-field hoje-periodo">
      <span>Período da Loja</span>
      <select value={dias} onChange={(event) => setDias(Number(event.target.value))}>
        {PERIODOS.map((valor) => (
          <option key={valor} value={valor}>
            Próximos {valor} dias
          </option>
        ))}
      </select>
    </label>
  );

  const mostraDemanda = !dados || dados.fonte_loja;

  const indicadores: Indicador[] = [];
  if (dados) {
    const producao = (dados.producao_hoje ?? []).filter((p) => p.ordens > 0);
    const unidades = producao.reduce((soma, p) => soma + p.unidades, 0);
    indicadores.push({
      id: "producao",
      rotulo: "Produção de hoje",
      valor: inteiro(unidades),
      detalhe: producao.length === 0 ? "nada planejado" : `${unidades === 1 ? "unidade" : "unidades"} em ${producao.length} ${producao.length === 1 ? "fornada" : "fornadas"}`,
      href: `/producao/dia?data=${dados.hoje}`,
    });
    if (dados.fonte_loja && dados.compatibilidade.ok) {
      indicadores.push({
        id: "loja",
        rotulo: "Confirmados na Loja",
        valor: inteiro(dados.total_paes_fisicos),
        detalhe: `pães nos próximos ${dados.dias} dias`,
        href: "/producao",
      });
    }
    if (dados.indicadores) {
      const { receitas_publicadas: feitas, produtos_produzidos: total } = dados.indicadores;
      indicadores.push({
        id: "receitas",
        rotulo: "Receitas publicadas",
        valor: `${inteiro(feitas)} de ${inteiro(total)}`,
        detalhe: total - feitas === 0 ? "todas valendo" : `${total - feitas} a publicar`,
        href: "/receitas",
        medidor: total > 0 ? feitas / total : 0,
        tom: total - feitas > 0 ? "alerta" : "ok",
      });
    }
    if (dados.necessidade) {
      const faltam = dados.necessidade.itens.filter((i) => i.falta > 0).length;
      indicadores.push({
        id: "falta",
        rotulo: "Ingredientes em falta",
        valor: inteiro(faltam),
        detalhe: "para as fornadas confirmadas",
        href: "/ingredientes",
        tom: faltam > 0 ? "alerta" : "ok",
      });
    }
    if (custos) {
      const comPreco = custos.produtos.filter((p) => (p.loja[0] ?? p.preco_proprio)?.resultado != null);
      const prejuizo = comPreco.filter((p) => ((p.loja[0] ?? p.preco_proprio)?.resultado as number) < 0).length;
      indicadores.push({
        id: "prejuizo",
        rotulo: "Produtos com prejuízo",
        valor: inteiro(prejuizo),
        detalhe: comPreco.length === 0 ? "nenhum com custo e preço" : `de ${comPreco.length} com custo e preço`,
        href: "/gestao/custos",
        tom: prejuizo > 0 ? "alerta" : "ok",
      });
    }
    if (dados.indicadores) {
      indicadores.push({
        id: "entradas",
        rotulo: "Entradas no mês",
        valor: dinheiro(dados.indicadores.entradas_mes_valor),
        detalhe: `${dados.indicadores.entradas_mes_qtd} ${dados.indicadores.entradas_mes_qtd === 1 ? "entrada" : "entradas"}`,
        href: "/entradas",
      });
    }
  }

  return (
    <main className="hoje">
      <PageHeader
        title="Hoje"
        description={dados ? maiuscula(dataLonga(dados.hoje)) : "O que fazer hoje na padaria."}
        actions={mostraDemanda ? periodo : undefined}
      />

      {carregando && !dados ? <p className="hoje-estado">Carregando o dia.</p> : null}

      {falhou ? (
        <Card className="hoje-vazio">
          <p role="alert">Não foi possível carregar o dia agora.</p>
          <Button onClick={() => void carregar(dias)}>Tentar de novo</Button>
        </Card>
      ) : null}

      {dados ? (
        <>
          <Indicadores itens={indicadores} />
          <div className="hoje-grade">
            <div className="hoje-principal">
              <ProducaoDeHoje dados={dados} />
              {dados.fonte_loja && dados.compatibilidade.ok ? (
                <div className="hoje-ordem-graficos painel-graficos">
                  <GraficoDemanda dados={dados} />
                </div>
              ) : null}
              <div className="hoje-ordem-graficos painel-graficos">
                <GraficoResultado custos={custos} />
              </div>
              {dados.fonte_loja ? <ProximasFornadas dados={dados} recarregar={() => void carregar(dias)} /> : null}
            </div>
            <aside className="hoje-lateral" aria-label="Pendências, estoque e áreas">
              <Pendencias dados={dados} />
              <Estoque dados={dados} />
              <Atalhos dados={dados} />
            </aside>
          </div>
        </>
      ) : null}
    </main>
  );
}
