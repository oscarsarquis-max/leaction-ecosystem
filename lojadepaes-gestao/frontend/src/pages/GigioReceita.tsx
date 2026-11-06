import { Fragment, useEffect, useRef, useState } from "react";
import { useGestao } from "../contexto";
import {
  aplicarSugestao,
  detalheReceita,
  listarProdutos,
  sugerirGigio,
  textoDoErro,
  type LinhaSugestao,
  type ProdutoLinha,
  type ReceitaFicha,
  type SugestaoGigio,
  type UnidadeReceita,
} from "../lib/api";
import { useNarrow } from "../lib/useNarrow";
import { Button } from "../shell/Button";
import { CampoIngrediente } from "../shell/CampoIngrediente";
import { SidePanel } from "../shell/SidePanel";

export type LinhaConhecida = {
  ingredienteId: string | null;
  nome: string;
  categoria: string;
  quantidade: string;
  unidade: UnidadeReceita;
};

const UNIDADES: UnidadeReceita[] = ["g", "kg", "ml", "l", "un"];
const CONFIANCA: Record<string, string> = { alta: "Alta", media: "Média", baixa: "Baixa" };

function faixa(linha: LinhaSugestao): string | null {
  if (linha.faixa_min == null || linha.faixa_max == null) return null;
  if (linha.faixa_min === linha.faixa_max) return null;
  const fmt = (n: number) => new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(n);
  return `${fmt(linha.faixa_min)}–${fmt(linha.faixa_max)} %`;
}

function percento(valor: number | null): string {
  if (valor == null) return "—";
  return `${new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(valor)} %`;
}

function linhaVazia(): LinhaConhecida {
  return { ingredienteId: null, nome: "", categoria: "", quantidade: "", unidade: "g" };
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
  const estreito = useNarrow();
  const { navegar } = useGestao();
  const [passo, setPasso] = useState<1 | 2 | 3>(1);
  const [descricao, setDescricao] = useState("");
  const [massaId, setMassaId] = useState("");
  const [peso, setPeso] = useState("");
  const [massas, setMassas] = useState<ProdutoLinha[]>([]);
  const [base, setBase] = useState<ReceitaFicha | null>(null);
  const [conhecidas, setConhecidas] = useState<LinhaConhecida[]>(
    linhas.filter((l) => l.nome && Number(l.quantidade.replace(",", ".")) > 0),
  );
  const [sugestao, setSugestao] = useState<SugestaoGigio | null>(null);
  const [marcadas, setMarcadas] = useState<boolean[]>([]);
  const [trocas, setTrocas] = useState<boolean[]>([]);
  const [confirmoSemFermento, setConfirmoSemFermento] = useState(false);
  const [modoAberto, setModoAberto] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const cancelado = useRef(false);
  const publicada = !massaId || base?.situacao === "publicada";
  const pesoOk = !massaId || Number(peso.replace(",", ".")) > 0;

  useEffect(() => {
    listarProdutos("componentes").then((r) => setMassas(r.produtos)).catch(() => setMassas([]));
  }, []);

  useEffect(() => {
    if (!massaId) {
      setBase(null);
      return;
    }
    let vivo = true;
    detalheReceita(massaId)
      .then((ficha) => {
        if (vivo) setBase(ficha);
      })
      .catch(() => {
        if (vivo) setBase(null);
      });
    return () => {
      vivo = false;
    };
  }, [massaId]);

  function mudar(i: number, parcial: Partial<LinhaConhecida>) {
    setConhecidas((atuais) => atuais.map((l, n) => (n === i ? { ...l, ...parcial } : l)));
  }

  async function pedir() {
    setErro(null);
    cancelado.current = false;
    setPasso(2);
    try {
      const qtd = rendimento.trim() ? Number(rendimento.replace(",", ".")) : null;
      const pesoMassa = Number(peso.replace(",", "."));
      const resposta = await sugerirGigio(produtoId, {
        descricao: descricao.trim(),
        massa_base_id: massaId || null,
        massa_base_quantidade: massaId && Number.isFinite(pesoMassa) ? pesoMassa : null,
        linhas_fixas: conhecidas
          .filter((l) => (l.ingredienteId || l.nome) && Number(l.quantidade.replace(",", ".")) > 0)
          .map((l) => ({
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
      setTrocas((resposta.substituicoes ?? []).map(() => true));
      setConfirmoSemFermento(false);
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
    const faltou = sugestao.verificacoes?.pendencias.some((p) => p.codigo === "sem_fermento");
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
        substituicoes: (sugestao.substituicoes ?? []).filter((_, i) => trocas[i]),
        confirmar_sem_fermento: Boolean(faltou && confirmoSemFermento),
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
  const nomeBase = massas.find((m) => m.id === massaId)?.nome ?? "massa-base";
  const faltaFermento = Boolean(sugestao?.verificacoes?.pendencias.some((item) => item.codigo === "sem_fermento"));

  return (
    <SidePanel
      largo
      titulo={passo === 1 ? "Conte ao Gigio sobre este pão" : passo === 2 ? "Pensando" : "Sugestão do Gigio"}
      onFechar={onFechar}
      rodape={
        <div className="painel-acoes">
          {passo === 1 ? (
            <>
              <Button onClick={onFechar}>Cancelar</Button>
              <Button variant="primary" disabled={!descricao.trim() || !publicada || !pesoOk} onClick={() => void pedir()}>
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
              <Button variant="primary" disabled={!marcadas.some(Boolean) || (faltaFermento && !confirmoSemFermento)} onClick={() => void aplicar()}>
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
          {massaId ? (
            <label className="gestao-field">
              <span>Peso da massa</span>
              <input
                type="text"
                inputMode="decimal"
                aria-label="Peso da massa"
                value={peso}
                onChange={(e) => setPeso(e.target.value)}
              />
            </label>
          ) : null}
          {massaId && base && base.situacao !== "publicada" ? (
            <p role="alert" className="form-erro">
              Monte primeiro a receita da {nomeBase}.{" "}
              <button type="button" className="link-acao" onClick={() => navegar(`/receitas/${massaId}`)}>
                Abrir essa receita
              </button>
            </p>
          ) : null}
          <p className="sub">O que você já sabe</p>
          <div aria-label="O que você já sabe">
            {conhecidas.map((linha, i) => (
              <div key={i} className="gigio-conhecida">
                <CampoIngrediente
                  rotulo={`Ingrediente que você já sabe, linha ${i + 1}`}
                  valor={linha.nome ? { nome: linha.nome, categoria: linha.categoria } : null}
                  textoInicial={linha.ingredienteId ? "" : linha.nome}
                  onEscolher={(ing) => mudar(i, { ingredienteId: ing.id, nome: ing.nome, categoria: ing.categoria })}
                  onTrocar={() => mudar(i, { ingredienteId: null, nome: "", categoria: "" })}
                />
                <input
                  type="text"
                  inputMode="decimal"
                  aria-label={`Quantidade, linha ${i + 1}`}
                  value={linha.quantidade}
                  onChange={(e) => mudar(i, { quantidade: e.target.value })}
                />
                <select
                  aria-label={`Unidade, linha ${i + 1}`}
                  value={linha.unidade}
                  onChange={(e) => mudar(i, { unidade: e.target.value as UnidadeReceita })}
                >
                  {UNIDADES.map((u) => (
                    <option key={u} value={u}>{u}</option>
                  ))}
                </select>
                <button type="button" className="ing-chip-x" aria-label={`Remover linha ${i + 1}`} onClick={() => setConhecidas((atuais) => atuais.filter((_, n) => n !== i))}>
                  ×
                </button>
              </div>
            ))}
          </div>
          <Button onClick={() => setConhecidas((atuais) => [...atuais, linhaVazia()])}>+ linha</Button>
        </>
      ) : null}
      {passo === 3 && sugestao ? (
        <>
          {sugestao.avisos?.length ? (
            <ul>
              {sugestao.avisos.map((aviso) => (
                <li key={aviso}>{aviso}</li>
              ))}
            </ul>
          ) : null}
          {sugestao.substituicoes?.length ? (
            <section className="gigio-altera" aria-label="Altera a massa-base">
              <h3>Altera a massa-base</h3>
              {sugestao.substituicoes.map((troca, i) => (
                <label key={`${troca.nome}-${i}`} className="gigio-topo">
                  <input
                    type="checkbox"
                    aria-label={`Substituir por ${troca.nome}`}
                    checked={trocas[i] ?? false}
                    onChange={(e) => setTrocas((atuais) => atuais.map((v, n) => (n === i ? e.target.checked : v)))}
                  />
                  <span>
                    <strong>{percento(troca.percentual)} da farinha da base por {troca.nome}</strong>
                    <small className="sub"> {troca.quantidade_g} g. {troca.motivo}</small>
                  </span>
                </label>
              ))}
            </section>
          ) : null}
          {faltaFermento ? (
            <label className="gigio-topo">
              <input type="checkbox" checked={confirmoSemFermento} onChange={(e) => setConfirmoSemFermento(e.target.checked)} />
              <span>Falta o fermento. Aplicar mesmo assim?</span>
            </label>
          ) : null}
          {estreito ? (
            <ul className="entrada-grade" aria-label="Sugestão do Gigio">
              {sugestao.linhas.map((linha, i) => (
                <li key={`${linha.nome}-${i}`} className="gigio-cartao">
                  <label className="gigio-topo">
                    <input
                      type="checkbox"
                      aria-label={`Usar ${linha.nome}`}
                      checked={marcadas[i]}
                      onChange={(e) => setMarcadas((atuais) => atuais.map((v, n) => (n === i ? e.target.checked : v)))}
                    />
                    <strong>{linha.nome}</strong>
                    {linha.a_decidir ? (
                      <small className="sub">{linha.fora_estoque ? " a decidir · não está no seu estoque" : " a decidir"}</small>
                    ) : null}
                  </label>
                  <span>{percento(linha.percentual)} · {linha.quantidade} {linha.unidade} · {faixa(linha) ?? "—"} · {CONFIANCA[linha.confianca] ?? linha.confianca}</span>
                  {linha.motivo ? <p>{linha.motivo}</p> : null}
                </li>
              ))}
            </ul>
          ) : (
            <table className="tabela-gigio" aria-label="Sugestão do Gigio">
              <thead>
                <tr>
                  <th>Usar</th>
                  <th>Ingrediente</th>
                  <th>%</th>
                  <th>Quantidade</th>
                  <th>Faixa</th>
                  <th>Confiança</th>
                </tr>
              </thead>
              <tbody>
                {sugestao.linhas.map((linha, i) => (
                  <Fragment key={`${linha.nome}-${i}`}>
                    <tr>
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
                        {linha.a_decidir ? (
                      <small className="sub">{linha.fora_estoque ? " a decidir · não está no seu estoque" : " a decidir"}</small>
                    ) : null}
                      </td>
                      <td>{percento(linha.percentual)}</td>
                      <td>{linha.quantidade} {linha.unidade}</td>
                      <td>{faixa(linha) ?? "—"}</td>
                      <td>{CONFIANCA[linha.confianca] ?? linha.confianca}</td>
                    </tr>
                    {linha.motivo ? (
                      <tr className="gigio-motivo">
                        <td />
                        <td colSpan={5}>{linha.motivo}</td>
                      </tr>
                    ) : null}
                  </Fragment>
                ))}
              </tbody>
            </table>
          )}
          {sugestao.modo_de_fazer.length ? (
            <details open={modoAberto} onToggle={(e) => setModoAberto((e.target as HTMLDetailsElement).open)}>
              <summary>Modo de fazer sugerido</summary>
              <ol>
                {sugestao.modo_de_fazer.map((passoModo) => (
                  <li key={passoModo}>{passoModo}</li>
                ))}
              </ol>
            </details>
          ) : null}
          {sugestao.observacoes && !sugestao.observacoes.startsWith("Produto:") ? <p className="sub">{sugestao.observacoes}</p> : null}
        </>
      ) : null}
    </SidePanel>
  );
}
