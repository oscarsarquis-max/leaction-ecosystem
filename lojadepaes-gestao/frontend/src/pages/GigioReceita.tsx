import { useEffect, useRef, useState } from "react";
import {
  aplicarSugestao,
  listarProdutos,
  sugerirGigio,
  textoDoErro,
  type LinhaSugestao,
  type ProdutoLinha,
  type ReceitaFicha,
  type SugestaoGigio,
  type UnidadeReceita,
} from "../lib/api";
import { useTabela } from "../lib/useNarrow";
import { Button } from "../shell/Button";
import { SidePanel } from "../shell/SidePanel";

export type LinhaConhecida = {
  ingredienteId: string | null;
  nome: string;
  quantidade: string;
  unidade: UnidadeReceita;
};

const CONFIANCA: Record<string, string> = { alta: "Alta", media: "Média", baixa: "Baixa" };

function faixa(linha: LinhaSugestao): string {
  if (linha.faixa_min == null || linha.faixa_max == null) return "—";
  const fmt = (n: number) => new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(n);
  return `${fmt(linha.faixa_min)}–${fmt(linha.faixa_max)} %`;
}

function percento(valor: number | null): string {
  if (valor == null) return "—";
  return `${new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(valor)} %`;
}

export function PainelGigio({
  produtoId,
  linhas,
  rendimento,
  unidade,
  onFechar,
  onAplicada,
}: {
  produtoId: string;
  linhas: LinhaConhecida[];
  rendimento: string;
  unidade: UnidadeReceita | "";
  onFechar: () => void;
  onAplicada: (ficha: ReceitaFicha) => void;
}) {
  const tabela = useTabela();
  const [passo, setPasso] = useState<1 | 2 | 3>(1);
  const [descricao, setDescricao] = useState("");
  const [massaId, setMassaId] = useState("");
  const [massas, setMassas] = useState<ProdutoLinha[]>([]);
  const [conhecidas, setConhecidas] = useState(linhas.filter((l) => l.nome && Number(l.quantidade.replace(",", ".")) > 0));
  const [sugestao, setSugestao] = useState<SugestaoGigio | null>(null);
  const [marcadas, setMarcadas] = useState<boolean[]>([]);
  const [modoAberto, setModoAberto] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const cancelado = useRef(false);

  useEffect(() => {
    listarProdutos("componentes").then((r) => setMassas(r.produtos)).catch(() => setMassas([]));
  }, []);

  async function pedir() {
    setErro(null);
    cancelado.current = false;
    setPasso(2);
    try {
      const qtd = rendimento.trim() ? Number(rendimento.replace(",", ".")) : null;
      const resposta = await sugerirGigio(produtoId, {
        descricao: descricao.trim(),
        massa_base_id: massaId || null,
        linhas_fixas: conhecidas.map((l) => ({
          ingrediente_id: l.ingredienteId,
          texto: l.ingredienteId ? null : l.nome,
          quantidade: Number(l.quantidade.replace(",", ".")),
          unidade: l.unidade,
        })),
        rendimento_quantidade: qtd != null && Number.isFinite(qtd) ? qtd : null,
        rendimento_unidade: unidade || null,
      });
      if (cancelado.current) return;
      setSugestao(resposta);
      setMarcadas(resposta.linhas.map(() => true));
      setPasso(3);
    } catch (falha) {
      if (!cancelado.current) {
        setErro(textoDoErro(falha));
        setPasso(1);
      }
    }
  }

  async function aplicar() {
    if (!sugestao) return;
    setErro(null);
    const escolhidas = sugestao.linhas.filter((_, i) => marcadas[i]);
    try {
      const ficha = await aplicarSugestao(produtoId, {
        linhas: escolhidas.map((l) => ({
          ingrediente_id: l.ingrediente_id,
          texto: l.texto,
          quantidade: l.quantidade,
          unidade: l.unidade,
          origem: l.origem,
          faixa_min: l.faixa_min,
          faixa_max: l.faixa_max,
          fixa: l.fixa,
        })),
        rendimento_g: sugestao.rendimento_g,
        perda_pct: sugestao.perda_pct,
        modo_de_fazer: sugestao.modo_de_fazer,
      });
      onAplicada(ficha);
    } catch (falha) {
      setErro(textoDoErro(falha));
    }
  }

  const topo = (
    <div className="gigio-topo">
      <img className="avatar-gigio grande" src="/avatar_gigio.png" alt="" width={48} height={48} />
      <p>{passo === 2 ? "O Gigio está montando a sugestão…" : "O Gigio sugere. Você decide."}</p>
    </div>
  );

  return (
    <SidePanel
      titulo={passo === 1 ? "Conte ao Gigio sobre este pão" : passo === 2 ? "Pensando" : "Sugestão do Gigio"}
      onFechar={onFechar}
      rodape={
        <div className="painel-acoes">
          {passo === 1 ? (
            <>
              <Button onClick={onFechar}>Cancelar</Button>
              <Button variant="primary" disabled={!descricao.trim()} onClick={() => void pedir()}>
                Pedir sugestão
              </Button>
            </>
          ) : null}
          {passo === 2 ? (
            <Button
              onClick={() => {
                cancelado.current = true;
                setPasso(1);
              }}
            >
              Cancelar
            </Button>
          ) : null}
          {passo === 3 ? (
            <>
              <Button onClick={onFechar}>Descartar</Button>
              <Button variant="primary" disabled={!marcadas.some(Boolean)} onClick={() => void aplicar()}>
                Aplicar ao rascunho
              </Button>
            </>
          ) : null}
        </div>
      }
    >
      {topo}
      {erro ? <p role="alert" className="form-erro">{erro}</p> : null}
      {passo === 1 ? (
        <>
          <label className="gestao-field">
            <span>Descrição</span>
            <textarea className="colar-texto" rows={6} value={descricao} onChange={(e) => setDescricao(e.target.value)} />
          </label>
          <label className="gestao-field">
            <span>Massa-base</span>
            <select value={massaId} onChange={(e) => setMassaId(e.target.value)}>
              <option value="">Nenhuma</option>
              {massas.map((m) => (
                <option key={m.id} value={m.id}>{m.nome}</option>
              ))}
            </select>
          </label>
          <p className="sub">O que você já sabe</p>
          <ul className="fluxo-linhas" aria-label="O que você já sabe">
            {conhecidas.map((linha, i) => (
              <li key={`${linha.nome}-${i}`} className="fluxo-linha">
                <span>{linha.nome}</span>
                <label>
                  <span className="so-leitor">Quantidade</span>
                  <input
                    type="text"
                    inputMode="decimal"
                    value={linha.quantidade}
                    onChange={(e) =>
                      setConhecidas((atuais) => atuais.map((l, n) => (n === i ? { ...l, quantidade: e.target.value } : l)))
                    }
                  />
                </label>
                <span>{linha.unidade}</span>
              </li>
            ))}
          </ul>
          {conhecidas.length === 0 ? <p className="sub">Nenhuma linha ainda. O Gigio parte da descrição.</p> : null}
        </>
      ) : null}
      {passo === 3 && sugestao ? (
        <>
          {tabela ? (
            <div className="entrada-tabela-rolagem">
              <table className="entrada-tabela tabela-receita" aria-label="Sugestão do Gigio">
                <thead>
                  <tr>
                    <th>Usar</th>
                    <th>Ingrediente</th>
                    <th>% do padeiro</th>
                    <th>Quantidade</th>
                    <th>Faixa</th>
                    <th>Confiança</th>
                  </tr>
                </thead>
                <tbody>
                  {sugestao.linhas.map((linha, i) => (
                    <tr key={`${linha.nome}-${i}`}>
                      <td>
                        <input
                          type="checkbox"
                          aria-label={`Usar ${linha.nome}`}
                          checked={marcadas[i]}
                          onChange={(e) => setMarcadas((atuais) => atuais.map((v, n) => (n === i ? e.target.checked : v)))}
                        />
                      </td>
                      <td>
                        {linha.nome}
                        {linha.a_decidir ? <small className="sub"> a decidir</small> : null}
                        <small className="sub"> {linha.motivo}</small>
                      </td>
                      <td>{percento(linha.percentual)}</td>
                      <td>{linha.quantidade} {linha.unidade}</td>
                      <td>{faixa(linha)}</td>
                      <td>{CONFIANCA[linha.confianca] ?? linha.confianca}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <ul className="entrada-grade" aria-label="Sugestão do Gigio">
              {sugestao.linhas.map((linha, i) => (
                <li key={`${linha.nome}-${i}`} className="grade-linha">
                  <label className="gigio-topo">
                    <input
                      type="checkbox"
                      aria-label={`Usar ${linha.nome}`}
                      checked={marcadas[i]}
                      onChange={(e) => setMarcadas((atuais) => atuais.map((v, n) => (n === i ? e.target.checked : v)))}
                    />
                    <span>
                      <strong>{linha.nome}</strong>
                      {linha.a_decidir ? <small className="sub"> a decidir</small> : null}
                      <small className="sub"> {percento(linha.percentual)} · {linha.quantidade} {linha.unidade} · {faixa(linha)} · {CONFIANCA[linha.confianca]}</small>
                      <small className="sub"> {linha.motivo}</small>
                    </span>
                  </label>
                </li>
              ))}
            </ul>
          )}
          {sugestao.modo_de_fazer.length ? (
            <details open={modoAberto} onToggle={(e) => setModoAberto((e.target as HTMLDetailsElement).open)}>
              <summary>Modo de fazer sugerido</summary>
              <ol>
                {sugestao.modo_de_fazer.map((passo) => (
                  <li key={passo}>{passo}</li>
                ))}
              </ol>
            </details>
          ) : null}
          {sugestao.observacoes ? <p className="sub">{sugestao.observacoes}</p> : null}
        </>
      ) : null}
    </SidePanel>
  );
}
