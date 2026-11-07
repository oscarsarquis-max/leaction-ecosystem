import { useCallback, useEffect, useState } from "react";
import { useGestao } from "../contexto";
import { carregarHoje, type Fornada, type Hoje as HojeDados, type ItemDemanda } from "../lib/api";
import { dataCurta, dataLonga, inteiro, pluralPaes, quantidadeBase, quando } from "../lib/format";
import { Button } from "../shell/Button";
import { Card } from "../shell/Card";
import { PageHeader } from "../shell/PageHeader";
import { StatusChip } from "../shell/StatusChip";
import "./fluxo.css";
import "./pages.css";

const PERIODOS = [7, 14, 30];

function nomeDoItem(item: ItemDemanda): string {
  return item.produto_ou_massa ?? "Item sem nome";
}

function FornadaCard({ fornada, hoje }: { fornada: Fornada; hoje: string }) {
  const titulo = `fornada-${fornada.data}`;
  return (
    <Card className="hoje-fornada">
      <section aria-labelledby={titulo}>
        <header className="hoje-fornada-head">
          <div>
            <h2 id={titulo}>{dataLonga(fornada.data)}</h2>
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
        <table className="hoje-tabela">
          <caption className="sr-only">Demanda confirmada em {dataLonga(fornada.data)}</caption>
          <thead>
            <tr>
              <th scope="col">Produto</th>
              <th scope="col">Variante ou forma</th>
              <th scope="col">Receita-base</th>
              <th scope="col" className="num">
                Quantidade
              </th>
              <th scope="col" className="num">
                Pães
              </th>
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
                <td data-label="Receita-base">{item.receita_base ?? "—"}</td>
                <td data-label="Quantidade" className="num">
                  {inteiro(item.quantidade)}
                </td>
                <td data-label="Pães" className="num">
                  <span>
                    {inteiro(item.paes_fisicos)}
                    {item.linhas_unidades_pendentes > 0 ? <span className="hoje-pendente"> + a confirmar</span> : null}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </Card>
  );
}

function ProximoPassoCard({ dados }: { dados: HojeDados }) {
  const { navegar } = useGestao();
  const passo = dados.fluxo.proximo_passo;
  if (!passo) {
    return (
      <Card className="hoje-proximo em-dia">
        <div>
          <p className="hoje-proximo-rotulo">Próximo passo</p>
          <h2>Tudo em dia</h2>
          <p>Entradas e ingredientes não pedem nada agora.</p>
        </div>
      </Card>
    );
  }
  return (
    <Card className={`hoje-proximo ${passo.estado}`}>
      <div>
        <p className="hoje-proximo-rotulo">Próximo passo</p>
        <h2>{passo.titulo}</h2>
        <p>{passo.texto}</p>
      </div>
      <Button variant="primary" onClick={() => navegar(passo.href)}>
        {passo.acao}
      </Button>
    </Card>
  );
}

function ProducaoDeHoje({ dados }: { dados: HojeDados }) {
  const { navegar } = useGestao();
  const blocos = dados.producao_hoje ?? [];
  const temOrdem = blocos.some((item) => item.ordens > 0);
  return (
    <section className="hoje-producao" aria-label="Produção de hoje">
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

function AlertasDoEstoque({ dados }: { dados: HojeDados }) {
  const { navegar } = useGestao();
  if (dados.vence_em_7_dias.length === 0 && dados.sem_saldo.length === 0) return null;
  return (
    <section className="hoje-alertas" aria-label="Estoque que pede atenção">
      {dados.vence_em_7_dias.length > 0 ? (
        <Card className="hoje-alerta">
          <h2>Vence em 7 dias</h2>
          <ul>
            {dados.vence_em_7_dias.map((v) => (
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
        </Card>
      ) : null}
      {dados.sem_saldo.length > 0 ? (
        <Card className="hoje-alerta">
          <h2>Sem saldo</h2>
          <ul>
            {dados.sem_saldo.map((s) => (
              <li key={s.id}>
                <button type="button" onClick={() => navegar("/ingredientes?filtro=sem_saldo")}>
                  <strong>{s.nome}</strong>
                  <span className="sub">acabou</span>
                </button>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}
    </section>
  );
}
export function Hoje() {
  const [dias, setDias] = useState(14);
  const [dados, setDados] = useState<HojeDados | null>(null);
  const [falhou, setFalhou] = useState(false);
  const [carregando, setCarregando] = useState(true);

  const carregar = useCallback(async (periodo: number) => {
    setCarregando(true);
    setFalhou(false);
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
      <span>Período</span>
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

  return (
    <main className="hoje">
      <PageHeader
        title="Hoje"
        description={
          mostraDemanda
            ? "O que pede atenção hoje e o que a Loja já confirmou para as próximas fornadas."
            : "O que pede atenção hoje na sua padaria."
        }
        actions={mostraDemanda ? periodo : undefined}
      />

      {carregando && !dados ? <p className="hoje-estado">Carregando o dia.</p> : null}

      {falhou ? (
        <Card className="hoje-vazio">
          <p role="alert">Não foi possível carregar o dia agora.</p>
          <Button onClick={() => void carregar(dias)}>Tentar de novo</Button>
        </Card>
      ) : null}

      {dados ? <ProximoPassoCard dados={dados} /> : null}
      {dados ? <ProducaoDeHoje dados={dados} /> : null}
      {dados ? <AlertasDoEstoque dados={dados} /> : null}

      {dados && dados.fonte_loja && !dados.compatibilidade.ok ? (
        <Card className="hoje-vazio">
          <p role="alert">{dados.compatibilidade.mensagem}</p>
          <Button onClick={() => void carregar(dias)}>Tentar de novo</Button>
        </Card>
      ) : null}

      {dados && dados.fonte_loja && dados.compatibilidade.ok ? (
        <>
          {dados.compatibilidade.mensagem ? (
            <p className="hoje-aviso hoje-aviso-solto">
              <StatusChip stage="warning" label="Atenção" />
              <span>{dados.compatibilidade.mensagem}</span>
            </p>
          ) : null}

          <section className="hoje-resumo" aria-label="Resumo do período">
            <Card className="hoje-numero">
              <span className="rotulo">Pães confirmados</span>
              <strong>{inteiro(dados.total_paes_fisicos)}</strong>
              <span className="detalhe">nos próximos {dados.dias} dias</span>
            </Card>
            <Card className="hoje-numero">
              <span className="rotulo">Fornadas com pedidos</span>
              <strong>{inteiro(dados.fornadas.length)}</strong>
              <span className="detalhe">
                {dados.fornadas.length === 0 ? "nenhuma por enquanto" : `a primeira: ${quando(dados.hoje, dados.fornadas[0].data).toLowerCase()}`}
              </span>
            </Card>
          </section>

          {dados.fornadas.length === 0 ? (
            <Card className="hoje-vazio">
              <p>
                <strong>Nenhuma demanda confirmada nos próximos {dados.dias} dias.</strong>
              </p>
              <p>Aparecem aqui os pedidos aceitos, em produção ou prontos, com data de fornada.</p>
            </Card>
          ) : (
            <div className="hoje-lista">
              {dados.fornadas.map((fornada) => (
                <FornadaCard key={fornada.data} fornada={fornada} hoje={dados.hoje} />
              ))}
            </div>
          )}
          <p className="hoje-rodape">
            {pluralPaes(dados.total_paes_fisicos)} em {dados.fornadas.length}{" "}
            {dados.fornadas.length === 1 ? "fornada" : "fornadas"}. Pedidos de teste e duplicados não entram.
          </p>
        </>
      ) : null}
    </main>
  );
}