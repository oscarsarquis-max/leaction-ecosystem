import { useEffect, useState } from "react";
import { useGestao } from "../contexto";
import { carregarComanda, imprimirComanda, textoDoErro, type Comanda as Folha, type LinhaComanda } from "../lib/api";
import { dataLonga } from "../lib/format";
import { Button } from "../shell/Button";
import { Marca } from "../shell/Marca";
import "./fluxo.css";

const FUNCOES = ["inoculo", "massa", "recheio", "cobertura", "finalizacao"];

function grupos(linhas: LinhaComanda[]) {
  return FUNCOES.map((funcao) => ({
    funcao,
    rotulo: linhas.find((linha) => linha.funcao === funcao)?.funcao_rotulo ?? funcao,
    linhas: linhas.filter((linha) => linha.funcao === funcao),
  })).filter((grupo) => grupo.linhas.length > 0);
}

export function Comanda() {
  const { search, navegar, pode } = useGestao();
  const params = new URLSearchParams(search);
  const data = params.get("data") ?? "";
  const fornada = params.get("fornada") ?? "";
  const [folha, setFolha] = useState<Folha | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [formato, setFormato] = useState<"a4" | "t80">("a4");
  const [ocupado, setOcupado] = useState(false);

  useEffect(() => {
    if (!data || !fornada) return;
    carregarComanda(data, fornada)
      .then(setFolha)
      .catch((falha) => setErro(textoDoErro(falha)));
  }, [data, fornada]);

  async function imprimir() {
    setOcupado(true);
    setErro(null);
    try {
      const gravada = await imprimirComanda(data, fornada);
      setFolha(gravada);
      window.setTimeout(() => window.print(), 60);
    } catch (falha) {
      setErro(textoDoErro(falha));
    } finally {
      setOcupado(false);
    }
  }

  return (
    <div className="gestao-frame">
    <main className={`comanda ${formato}`}>
      <div className="comanda-barra no-print">
        <Button onClick={() => navegar(`/producao/dia?data=${data}`)}>Voltar ao dia</Button>
        <div className="gestao-chips" role="group" aria-label="Formato da comanda">
          <button type="button" className={formato === "a4" ? "chip-filtro on" : "chip-filtro"} aria-pressed={formato === "a4"} onClick={() => setFormato("a4")}>A4</button>
          <button type="button" className={formato === "t80" ? "chip-filtro on" : "chip-filtro"} aria-pressed={formato === "t80"} onClick={() => setFormato("t80")}>80 mm</button>
        </div>
        {pode("lancar") ? (
          <Button variant="primary" disabled={ocupado || !folha} onClick={() => void imprimir()}>
            {folha && folha.via >= 1 ? "Reimprimir" : "Imprimir"}
          </Button>
        ) : null}
      </div>
      {erro ? <p role="alert" className="form-erro no-print">{erro}</p> : null}
      {!folha && !erro ? <p className="fluxo-estado no-print">Carregando a comanda.</p> : null}
      {folha ? <FolhaImpressa folha={folha} /> : null}
    </main>
    </div>
  );
}

function FolhaImpressa({ folha }: { folha: Folha }) {
  const quando = folha.impressa_em && folha.impressa_por ? `impressa em ${folha.impressa_em} por ${folha.impressa_por}` : "ainda não impressa";
  return (
    <article className="comanda-folha">
      <header className="comanda-topo">
        <Marca altura={56} />
        <div>
          <p>{dataLonga(folha.data)}</p>
          <h1>{folha.fornada.nome.includes(folha.fornada.horario) ? folha.fornada.nome : `${folha.fornada.nome} · ${folha.fornada.horario}`}</h1>
          <p>Comanda {folha.numero ?? "—"}{folha.via_rotulo ? ` · ${folha.via_rotulo}` : ""}</p>
          <p>{quando}</p>
        </div>
      </header>
      {folha.produtos.map((produto) => (
        <section key={produto.ordem_id} className="comanda-produto">
          <h2>{produto.por_unidade === false ? `${produto.produto} · ${produto.massa ?? "—"}` : produto.produto}</h2>
          {produto.por_unidade === false ? null : (
          <p className="comanda-medidas">
            <strong>{produto.unidades} un</strong>
            {produto.origens ? <span>({produto.origens})</span> : null}
            {produto.pecas ? <span>{produto.pecas}</span> : null}
            {produto.massa ? <span>Massa {produto.massa}</span> : null}
          </p>
          )}
          {produto.loja && produto.loja.length ? (
            <p className="comanda-loja">
              Loja: {produto.loja.map((pedido) => `${pedido.referencia} (${pedido.unidades})`).join(", ")}
            </p>
          ) : null}
          {produto.aviso ? <p className="comanda-aviso">{produto.aviso}</p> : null}
          {grupos(produto.linhas).map((grupo) => (
            <div key={grupo.funcao}>
              <h3>{grupo.rotulo}</h3>
              <table className="comanda-tabela">
                <thead>
                  <tr><th scope="col">Ingrediente</th><th scope="col" className="comanda-qtd">Quantidade</th></tr>
                </thead>
                <tbody>
                  {grupo.linhas.map((linha) => (
                    <Linha key={`${linha.nome}-${linha.texto}`} linha={linha} />
                  ))}
                </tbody>
              </table>
            </div>
          ))}
          {produto.modo_fazer.length ? (
            <div className="comanda-modo">
              <h3>Modo de fazer</h3>
              <ol>{produto.modo_fazer.map((passo) => <li key={passo}>{passo}</li>)}</ol>
            </div>
          ) : null}
          <div className="comanda-rodape-produto">
            <p className="comanda-feito"><span className="comanda-caixa" aria-hidden="true" /> feito ✓</p>
            <p className="comanda-obs">Observações{produto.observacao ? `: ${produto.observacao}` : ""}</p>
          </div>
        </section>
      ))}
      <section className="comanda-pesagem">
        <h2>Pesagem total da fornada</h2>
        <table className="comanda-tabela">
          <thead>
            <tr><th scope="col">Ingrediente</th><th scope="col" className="comanda-qtd">Quantidade</th></tr>
          </thead>
          <tbody>
            {folha.pesagem.map((item) => (
              <tr key={item.nome}><th scope="row">{item.nome}</th><td>{item.texto}</td></tr>
            ))}
          </tbody>
        </table>
      </section>
    </article>
  );
}

function Linha({ linha }: { linha: LinhaComanda }) {
  return (
    <>
      <tr>
        <th scope="row">
          {linha.nome}
          {linha.observacao ? <small className="comanda-obs-linha">{linha.observacao}</small> : null}
        </th>
        <td>{linha.texto}</td>
      </tr>
      {linha.filhos.map((filho) => (
        <tr key={`${linha.nome}-${filho.nome}`} className="comanda-filho">
          <th scope="row">{filho.nome}</th>
          <td>{filho.texto}</td>
        </tr>
      ))}
    </>
  );
}
