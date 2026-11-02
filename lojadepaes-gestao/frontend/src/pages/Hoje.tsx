import { useCallback, useEffect, useState } from "react";
import { carregarHoje, type Fornada, type Hoje as HojeDados, type ItemDemanda } from "../lib/api";
import { dataLonga, inteiro, pluralPaes, quando } from "../lib/format";
import { Button } from "../shell/Button";
import { Card } from "../shell/Card";
import { PageHeader } from "../shell/PageHeader";
import { StatusChip } from "../shell/StatusChip";
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

  return (
    <main className="hoje">
      <PageHeader
        title="Hoje"
        description="O que a Loja já confirmou para as próximas fornadas. Só leitura, nada é gravado."
        actions={periodo}
      />

      {carregando && !dados ? <p className="hoje-estado">Carregando a demanda…</p> : null}

      {falhou ? (
        <Card className="hoje-vazio">
          <p role="alert">Não foi possível carregar a demanda agora.</p>
          <Button onClick={() => void carregar(dias)}>Tentar de novo</Button>
        </Card>
      ) : null}

      {dados && !dados.compatibilidade.ok ? (
        <Card className="hoje-vazio">
          <p role="alert">{dados.compatibilidade.mensagem}</p>
          <Button onClick={() => void carregar(dias)}>Tentar de novo</Button>
        </Card>
      ) : null}

      {dados && dados.compatibilidade.ok ? (
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
