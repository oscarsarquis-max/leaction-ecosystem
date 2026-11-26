import { useCallback, useEffect, useState } from "react";
import {
  apagarCustoFixo,
  carregarCustos,
  criarCustoFixo,
  definirPrecoProduto,
  definirRegraFamilia,
  definirRegraProduto,
  editarCustoFixo,
  salvarParametrosCusto,
  textoDoErro,
  type CustoFixo,
  type CustosVisao,
  type ProdutoCusto,
  type RegraPreco,
} from "../lib/api";
import { dinheiro } from "../lib/format";
import { Button } from "../shell/Button";
import { Card } from "../shell/Card";
import { PageHeader } from "../shell/PageHeader";
import { SidePanel } from "../shell/SidePanel";
import { StatusChip } from "../shell/StatusChip";
import "./fluxo.css";
import "./pages.css";

function numero(texto: string): number | null {
  const limpo = texto.trim().replace(/\./g, "").replace(",", ".");
  if (!limpo) return null;
  const valor = Number(limpo);
  return Number.isFinite(valor) ? valor : null;
}

function decimal(valor: number | null | undefined, casas = 1): string {
  if (valor == null) return "";
  return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: casas }).format(valor);
}

export function textoRegra(regra: RegraPreco | null | undefined): string {
  if (!regra) return "—";
  return regra.tipo === "margem" ? `Margem ${decimal(regra.valor)} %` : `Markup ${decimal(regra.valor, 2)}×`;
}

const ORIGEM: Record<string, string> = { produto: "do produto", familia: "da família", geral: "geral" };

/** Escolhe margem (%) ou markup (×); "herdar" volta para o nível de cima. */
function EditorRegra({
  rotulo,
  regra,
  herdar,
  onSalvar,
}: {
  rotulo: string;
  regra: RegraPreco | null;
  herdar?: string;
  onSalvar: (regra: RegraPreco | null) => Promise<void>;
}) {
  const [tipo, setTipo] = useState<"herdar" | "margem" | "markup">(regra ? regra.tipo : herdar ? "herdar" : "margem");
  const [valor, setValor] = useState(regra ? decimal(regra.valor, 2) : "");
  const [salvando, setSalvando] = useState(false);
  const numeroValor = numero(valor);
  const valido = tipo === "herdar" || (numeroValor != null && numeroValor > 0 && (tipo === "markup" || numeroValor < 100));
  const mudou =
    tipo === "herdar" ? regra != null : !regra || regra.tipo !== tipo || regra.valor !== numeroValor;
  return (
    <div className="regra-editor" role="group" aria-label={rotulo}>
      <select aria-label={`Tipo, ${rotulo}`} value={tipo} onChange={(e) => setTipo(e.target.value as typeof tipo)}>
        {herdar ? <option value="herdar">{herdar}</option> : null}
        <option value="margem">Margem (%)</option>
        <option value="markup">Markup (×)</option>
      </select>
      {tipo !== "herdar" ? (
        <label className="regra-valor">
          <input
            type="text"
            inputMode="decimal"
            aria-label={`Valor, ${rotulo}`}
            value={valor}
            placeholder={tipo === "margem" ? "60" : "3"}
            onChange={(e) => setValor(e.target.value)}
          />
          <span aria-hidden="true">{tipo === "margem" ? "%" : "×"}</span>
        </label>
      ) : null}
      <Button
        disabled={!valido || !mudou || salvando}
        onClick={async () => {
          setSalvando(true);
          try {
            await onSalvar(tipo === "herdar" ? null : { tipo, valor: numeroValor as number });
          } finally {
            setSalvando(false);
          }
        }}
      >
        Salvar
      </Button>
    </div>
  );
}

function LinhaCustoFixo({ custo, onMudar }: { custo: CustoFixo; onMudar: (acao: () => Promise<CustosVisao>) => Promise<void> }) {
  const [nome, setNome] = useState(custo.nome);
  const [valor, setValor] = useState(decimal(custo.valor_mensal, 2));
  const salvar = () => {
    const v = numero(valor);
    if (!nome.trim() || v == null || v < 0) return;
    if (nome.trim() === custo.nome && v === custo.valor_mensal) return;
    void onMudar(() => editarCustoFixo(custo.id, { nome: nome.trim(), valor_mensal: v }));
  };
  return (
    <li className="custo-fixo-linha">
      <input type="text" aria-label={`Nome do custo, ${custo.nome}`} value={nome} onChange={(e) => setNome(e.target.value)} onBlur={salvar} />
      <label className="regra-valor dinheiro">
        <span aria-hidden="true">R$</span>
        <input type="text" inputMode="decimal" aria-label={`Valor por mês, ${custo.nome}`} value={valor} onChange={(e) => setValor(e.target.value)} onBlur={salvar} />
      </label>
      <button type="button" className="custo-remover" aria-label={`Remover ${custo.nome}`} onClick={() => void onMudar(() => apagarCustoFixo(custo.id))}>
        Remover
      </button>
    </li>
  );
}

function NovoCustoFixo({ onMudar }: { onMudar: (acao: () => Promise<CustosVisao>) => Promise<void> }) {
  const [nome, setNome] = useState("");
  const [valor, setValor] = useState("");
  const v = numero(valor);
  const pronto = nome.trim() !== "" && v != null && v >= 0;
  return (
    <form
      className="custo-fixo-linha novo"
      onSubmit={async (e) => {
        e.preventDefault();
        if (!pronto) return;
        await onMudar(() => criarCustoFixo({ nome: nome.trim(), valor_mensal: v as number }));
        setNome("");
        setValor("");
      }}
    >
      <input type="text" aria-label="Nome do novo custo" placeholder="Ex.: Energia" value={nome} onChange={(e) => setNome(e.target.value)} />
      <label className="regra-valor dinheiro">
        <span aria-hidden="true">R$</span>
        <input type="text" inputMode="decimal" aria-label="Valor por mês do novo custo" placeholder="0,00" value={valor} onChange={(e) => setValor(e.target.value)} />
      </label>
      <Button type="submit" disabled={!pronto}>
        Adicionar
      </Button>
    </form>
  );
}

function Resultado({ valor }: { valor: number | null }) {
  if (valor == null) return <span className="travessao">—</span>;
  return valor < 0 ? (
    <StatusChip stage="cancelled" label={`Prejuízo ${dinheiro(-valor)}`} />
  ) : (
    <StatusChip stage="ok" label={`Sobra ${dinheiro(valor)}`} />
  );
}

function PainelProduto({ produto, visao, onFechar, onMudar }: {
  produto: ProdutoCusto;
  visao: CustosVisao;
  onFechar: () => void;
  onMudar: (acao: () => Promise<CustosVisao>) => Promise<void>;
}) {
  const familia = visao.familias.find((f) => f.id === produto.familia_id);
  const herdada = familia?.regra ? `Usar a da família (${textoRegra(familia.regra)})` : `Usar a geral (${textoRegra(visao.parametros.regra)})`;
  return (
    <SidePanel titulo={produto.nome} subtitulo={produto.familia ?? "Sem família"} onFechar={onFechar}>
      <dl className="painel-fatos custos-fatos">
        <div>
          <dt>Massa por pão</dt>
          <dd>{produto.massa_g == null ? "—" : `${decimal(produto.massa_g, 0)} g`}</dd>
        </div>
        <div>
          <dt>Custo variável</dt>
          <dd>
            {produto.custo_variavel == null ? "—" : dinheiro(produto.custo_variavel)}
            {produto.custo_parcial ? <span className="custo-parcial"> parcial</span> : null}
          </dd>
        </div>
        <div>
          <dt>Parte do custo fixo</dt>
          <dd>{produto.rateio == null ? "—" : dinheiro(produto.rateio)}</dd>
        </div>
        <div>
          <dt>Custo total (preço mínimo)</dt>
          <dd>{produto.custo_total == null ? "—" : dinheiro(produto.custo_total)}</dd>
        </div>
      </dl>
      <h3 className="custos-sub">Regra de preço deste produto</h3>
      <EditorRegra
        key={`${produto.produto_id}-${JSON.stringify(produto.regra_propria)}`}
        rotulo={`Regra de ${produto.nome}`}
        regra={produto.regra_propria}
        herdar={herdada}
        onSalvar={(regra) => onMudar(() => definirRegraProduto(produto.produto_id, regra))}
      />
      <p className="sub custos-explica">
        Preço sugerido agora: <strong>{produto.preco_sugerido == null ? "—" : dinheiro(produto.preco_sugerido)}</strong>
        {produto.regra ? ` · ${textoRegra(produto.regra)} ${ORIGEM[produto.regra_origem ?? "geral"]}` : ""}
      </p>
      {produto.loja.length > 0 ? (
        <>
          <h3 className="custos-sub">Na Loja</h3>
          <ul className="custos-loja">
            {produto.loja.map((preco) => (
              <li key={preco.variante}>
                <span>
                  <strong>{preco.variante}</strong>
                  <span className="sub">
                    {` · ${dinheiro(preco.preco)}`}
                    {preco.unidades > 1 ? ` · ${preco.unidades} pães · ${dinheiro(preco.preco_por_unidade)} cada` : ""}
                  </span>
                </span>
                <span className="sub">
                  {preco.mc_pct == null ? "" : `margem ${decimal(preco.mc_pct)} %`}
                  {preco.markup == null ? "" : ` · markup ${decimal(preco.markup, 2)}×`}
                </span>
                <Resultado valor={preco.resultado} />
              </li>
            ))}
          </ul>
        </>
      ) : (
        <PrecoInformado produto={produto} onMudar={onMudar} />
      )}
    </SidePanel>
  );
}

/** Sem preço na Loja (cliente sem Loja integrada, ou produto fora dela), o preço de venda é informado aqui. */
function PrecoInformado({ produto, onMudar }: { produto: ProdutoCusto; onMudar: (acao: () => Promise<CustosVisao>) => Promise<void> }) {
  const [valor, setValor] = useState(produto.preco_manual == null ? "" : decimal(produto.preco_manual, 2));
  const numeroValor = numero(valor);
  const mudou = numeroValor !== produto.preco_manual;
  const valido = valor.trim() === "" || (numeroValor != null && numeroValor > 0);
  const proprio = produto.preco_proprio;
  return (
    <>
      <h3 className="custos-sub">Preço de venda</h3>
      <p className="sub custos-explica">Este produto não tem preço na Loja. Informe o preço por pão para ver o resultado.</p>
      <div className="regra-editor preco-informado">
        <label className="regra-valor dinheiro">
          <span aria-hidden="true">R$</span>
          <input type="text" inputMode="decimal" aria-label="Preço de venda por pão" placeholder="0,00" value={valor} onChange={(e) => setValor(e.target.value)} />
        </label>
        <Button
          disabled={!mudou || !valido}
          onClick={() => void onMudar(() => definirPrecoProduto(produto.produto_id, valor.trim() === "" ? null : (numeroValor as number)))}
        >
          Salvar
        </Button>
      </div>
      {proprio ? (
        <ul className="custos-loja">
          <li>
            <span className="sub">
              {proprio.mc_pct == null ? "" : `margem ${decimal(proprio.mc_pct)} %`}
              {proprio.markup == null ? "" : ` · markup ${decimal(proprio.markup, 2)}×`}
            </span>
            <Resultado valor={proprio.resultado} />
          </li>
        </ul>
      ) : null}
    </>
  );
}

export function Custos() {
  const [visao, setVisao] = useState<CustosVisao | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [falhou, setFalhou] = useState(false);
  const [aberto, setAberto] = useState<string | null>(null);
  const [massa, setMassa] = useState("");

  const aplicar = useCallback((nova: CustosVisao) => {
    setVisao(nova);
    setMassa(decimal(nova.parametros.massa_mensal_kg, 1));
  }, []);

  useEffect(() => {
    carregarCustos().then(aplicar).catch(() => setFalhou(true));
  }, [aplicar]);

  const mudar = useCallback(
    async (acao: () => Promise<CustosVisao>) => {
      setErro(null);
      try {
        aplicar(await acao());
      } catch (falha) {
        setErro(textoDoErro(falha));
      }
    },
    [aplicar],
  );

  const parametros = visao?.parametros;
  const produtoAberto = visao?.produtos.find((p) => p.produto_id === aberto) ?? null;

  return (
    <main className="custos">
      <PageHeader title="Custos" description="Quanto custa, quanto a Loja cobra e quanto sobra." />
      {falhou ? (
        <Card className="fluxo-vazio">
          <p role="alert">Não foi possível carregar os custos agora.</p>
        </Card>
      ) : null}
      {erro ? (
        <p role="alert" className="form-erro">
          {erro}
        </p>
      ) : null}
      {visao && parametros ? (
        <>
          <div className="custos-topo">
            <Card className="custos-cartao">
              <section aria-labelledby="custos-fixos-titulo">
                <h2 id="custos-fixos-titulo">Custos fixos do mês</h2>
                <p className="sub">Informe uma vez. O total é dividido pelos quilos de massa do mês.</p>
                <ul className="custos-fixos">
                  {visao.custos_fixos.map((custo) => (
                    <LinhaCustoFixo key={`${custo.id}-${custo.valor_mensal}-${custo.nome}`} custo={custo} onMudar={mudar} />
                  ))}
                </ul>
                <NovoCustoFixo onMudar={mudar} />
                <div className="custos-rateio">
                  <label className="gestao-field">
                    <span>Massa produzida por mês</span>
                    <span className="regra-valor">
                      <input
                        type="text"
                        inputMode="decimal"
                        aria-label="Massa produzida por mês"
                        value={massa}
                        placeholder="Ex.: 600"
                        onChange={(e) => setMassa(e.target.value)}
                        onBlur={() => {
                          const valor = numero(massa);
                          if (valor === parametros.massa_mensal_kg) return;
                          void mudar(() => salvarParametrosCusto({ massa_mensal_kg: valor, regra: parametros.regra }));
                        }}
                      />
                      <span aria-hidden="true">kg</span>
                    </span>
                  </label>
                  <dl className="painel-fatos">
                    <div>
                      <dt>Total no mês</dt>
                      <dd>{dinheiro(parametros.custo_fixo_total)}</dd>
                    </div>
                    <div>
                      <dt>Custo fixo por kg</dt>
                      <dd>{parametros.custo_fixo_por_kg == null ? "informe a massa do mês" : dinheiro(parametros.custo_fixo_por_kg)}</dd>
                    </div>
                  </dl>
                </div>
              </section>
            </Card>
            <Card className="custos-cartao">
              <section aria-labelledby="custos-regras-titulo">
                <h2 id="custos-regras-titulo">Regra de preço</h2>
                <p className="sub">Vale a do produto; se não houver, a da família; senão, a geral.</p>
                <h3 className="custos-sub">Geral</h3>
                <EditorRegra
                  key={`geral-${JSON.stringify(parametros.regra)}`}
                  rotulo="Regra geral"
                  regra={parametros.regra}
                  onSalvar={(regra) => mudar(() => salvarParametrosCusto({ massa_mensal_kg: parametros.massa_mensal_kg, regra }))}
                />
                {visao.familias.length > 0 ? <h3 className="custos-sub">Por família</h3> : null}
                <ul className="custos-familias">
                  {visao.familias.map((familia) => (
                    <li key={familia.id}>
                      <span className="custos-familia-nome">{familia.nome}</span>
                      <EditorRegra
                        key={`${familia.id}-${JSON.stringify(familia.regra)}`}
                        rotulo={`Regra da família ${familia.nome}`}
                        regra={familia.regra}
                        herdar="Usar a geral"
                        onSalvar={(regra) => mudar(() => definirRegraFamilia(familia.id, regra))}
                      />
                    </li>
                  ))}
                </ul>
              </section>
            </Card>
          </div>

          <Card className="fluxo-lista-card">
            <table className="hoje-tabela custos-tabela" aria-label="Produtos: custo e preço">
              <thead>
                <tr>
                  <th scope="col">Produto</th>
                  <th scope="col" className="num">Custo variável</th>
                  <th scope="col" className="num">Custo fixo</th>
                  <th scope="col" className="num">Preço</th>
                  <th scope="col">Resultado por pão</th>
                  <th scope="col" className="num">Preço sugerido</th>
                </tr>
              </thead>
              <tbody>
                {visao.produtos.map((produto) => {
                  const preco = produto.loja[0] ?? produto.preco_proprio ?? undefined;
                  return (
                    <tr key={produto.produto_id}>
                      <th scope="row" data-label="Produto">
                        <button type="button" className="custos-produto" onClick={() => setAberto(produto.produto_id)}>
                          <strong>{produto.nome}</strong>
                          <span className="sub">{produto.receita_publicada ? produto.familia ?? "Sem família" : "sem receita publicada"}</span>
                        </button>
                      </th>
                      <td data-label="Custo variável" className="num">
                        {produto.custo_variavel == null ? "—" : dinheiro(produto.custo_variavel)}
                        {produto.custo_parcial ? <span className="custo-parcial"> parcial</span> : null}
                      </td>
                      <td data-label="Custo fixo" className="num">
                        {produto.rateio == null ? "—" : dinheiro(produto.rateio)}
                      </td>
                      <td data-label="Preço" className="num">
                        {preco ? dinheiro(preco.preco_por_unidade) : <span className="sub">sem preço</span>}
                        {produto.loja.length > 1 ? <span className="sub"> +{produto.loja.length - 1}</span> : null}
                        {produto.loja.length === 0 && produto.preco_proprio ? <span className="custos-origem-preco sub">informado</span> : null}
                        {produto.loja.length > 0 ? <span className="custos-origem-preco sub">Loja</span> : null}
                      </td>
                      <td data-label="Resultado por pão">
                        <Resultado valor={preco ? preco.resultado : null} />
                      </td>
                      <td data-label="Preço sugerido" className="num">
                        <span className="custos-sugerido">
                          <strong>{produto.preco_sugerido == null ? "—" : dinheiro(produto.preco_sugerido)}</strong>
                          <span className="custos-regra sub">
                            {textoRegra(produto.regra)}
                            {produto.regra_origem ? ` · ${ORIGEM[produto.regra_origem]}` : ""}
                          </span>
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Card>
          <p className="hoje-rodape">
            Custo variável: ingredientes da receita publicada, por pão. Custo fixo: massa do pão × custo fixo por kg. Resultado: preço −
            custo variável − custo fixo. O preço vem da Loja (só lido; nada muda lá) ou é informado no produto.
          </p>
          {produtoAberto ? (
            <PainelProduto produto={produtoAberto} visao={visao} onFechar={() => setAberto(null)} onMudar={mudar} />
          ) : null}
        </>
      ) : null}
    </main>
  );
}
