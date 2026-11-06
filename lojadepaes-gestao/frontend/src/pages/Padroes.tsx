import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useGestao } from "../contexto";
import { criarPadrao, listarPadroes, listarPerdas, salvarPadrao, textoDoErro, type PadraoPadaria, type PadraoPerda, type ReferenciaPerda } from "../lib/api";
import { Button } from "../shell/Button";
import { Card } from "../shell/Card";
import { Chips } from "../shell/Chips";
import { PageHeader } from "../shell/PageHeader";
import { SidePanel } from "../shell/SidePanel";
import "./fluxo.css";

const VAZIO: PadraoPadaria = {
  id: "",
  nome: "",
  termo: "",
  ingrediente_id: null,
  ingrediente: null,
  percentual: 0,
  observacao: "",
  ativo: true,
};

function percento(valor: number): string {
  return `${new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(valor)} %`;
}

function fonteCurta(titulo: string): string {
  const achado = titulo.match(/\(([^)]+)\)\s*$/);
  return achado ? achado[1] : titulo;
}

export function Padroes() {
  const { pode } = useGestao();
  const [lista, setLista] = useState<PadraoPadaria[] | null>(null);
  const [falhou, setFalhou] = useState(false);
  const [aberto, setAberto] = useState<PadraoPadaria | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [aba, setAba] = useState<"casa" | "perdas">("casa");
  const [perdasCasa, setPerdasCasa] = useState<PadraoPerda[] | null>(null);
  const [referencias, setReferencias] = useState<ReferenciaPerda[] | null>(null);

  const carregar = useCallback(async () => {
    try {
      setLista(await listarPadroes());
      setFalhou(false);
    } catch {
      setFalhou(true);
    }
  }, []);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  useEffect(() => {
    if (aba !== "perdas") return;
    listarPerdas()
      .then((resposta) => {
        setPerdasCasa(resposta.padroes);
        setReferencias(resposta.referencias);
      })
      .catch(() => setFalhou(true));
  }, [aba]);

  async function gravar(event?: FormEvent) {
    event?.preventDefault();
    if (!aberto) return;
    setOcupado(true);
    setErro(null);
    const corpo = {
      nome: aberto.nome.trim(),
      termo: aberto.termo.trim(),
      ingrediente_id: aberto.ingrediente_id,
      percentual: aberto.percentual,
      observacao: aberto.observacao,
      ativo: aberto.ativo,
    };
    try {
      if (aberto.id) await salvarPadrao(aberto.id, corpo);
      else await criarPadrao(corpo);
      setAberto(null);
      await carregar();
    } catch (falha) {
      setErro(textoDoErro(falha));
    } finally {
      setOcupado(false);
    }
  }

  const podeEditar = pode("lancar");
  return (
    <main className="fluxo-pagina">
      <PageHeader
        title="Padrões"
        description="O que a casa já sabe, em % do padeiro."
        actions={podeEditar && aba === "casa" ? <Button variant="primary" onClick={() => setAberto({ ...VAZIO })}>Novo padrão</Button> : undefined}
      />
      <Chips
        rotulo="Tipos de padrão"
        opcoes={[
          { valor: "casa", rotulo: "Casa" },
          { valor: "perdas", rotulo: "Perdas" },
        ]}
        valor={aba}
        onChange={setAba}
      />
      {falhou ? (
        <Card className="fluxo-vazio">
          <p role="alert">Não foi possível carregar os padrões agora.</p>
          <Button onClick={() => void carregar()}>Tentar de novo</Button>
        </Card>
      ) : null}
      {aba === "casa" && !lista && !falhou ? <p className="fluxo-estado">Carregando os padrões.</p> : null}
      {aba === "perdas" && perdasCasa && referencias ? (
        <>
          <section className="perdas-bloco">
            <h2>Padrão da casa</h2>
            <Card className="fluxo-lista-card">
              <table className="lista-padroes lista-perdas" aria-label="Padrões de perda da casa">
                <thead>
                  <tr>
                    <th>Tipo</th>
                    <th>Formato</th>
                    <th>Faixa</th>
                    <th className="num">%</th>
                    <th>Observação</th>
                  </tr>
                </thead>
                <tbody>
                  {perdasCasa.map((p) => (
                    <tr key={p.id}>
                      <td>{p.tipo_rotulo}</td>
                      <td>{p.formato ? p.formato_rotulo : "Qualquer formato"}</td>
                      <td>{p.faixa}</td>
                      <td className="num">{p.rotulo}</td>
                      <td className="obs">{p.observacao || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          </section>
          <section className="perdas-bloco">
            <h2>Referência</h2>
            <Card className="fluxo-lista-card">
              <table className="lista-padroes lista-perdas" aria-label="Referência de perdas">
                <thead>
                  <tr>
                    <th>Tipo</th>
                    <th>Formato</th>
                    <th>Faixa</th>
                    <th className="num">%</th>
                    <th>Fonte</th>
                  </tr>
                </thead>
                <tbody>
                  {referencias.map((r) => (
                    <tr key={r.id}>
                      <td>{r.tipo_rotulo}</td>
                      <td>{r.formato_rotulo}</td>
                      <td>{r.faixa}</td>
                      <td className="num">{r.sugerido}</td>
                      <td className="obs">
                        {r.fonte_url ? (
                          <a href={r.fonte_url} title={r.fonte}>{fonteCurta(r.fonte)}</a>
                        ) : (
                          r.fonte
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          </section>
        </>
      ) : null}
      {aba === "casa" && lista ? (
        <Card className="fluxo-lista-card">
          <table className="lista-padroes" aria-label="Padrões da padaria">
            <thead>
              <tr>
                <th>Padrão</th>
                <th>Ingrediente</th>
                <th className="num">%</th>
                <th>Observação</th>
              </tr>
            </thead>
            <tbody>
              {lista.map((p) => (
                <tr key={p.id}>
                  <td>
                    <button type="button" className="ing-nome" onClick={() => podeEditar && setAberto(p)} disabled={!podeEditar}>
                      <strong>{p.nome}</strong>
                    </button>
                    {p.ativo ? null : <small className="sub"> Inativo</small>}
                  </td>
                  <td>{p.ingrediente || p.termo}</td>
                  <td className="num">{percento(p.percentual)}</td>
                  <td className="obs">{p.observacao || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ) : null}
      {aberto ? (
        <SidePanel
          titulo={aberto.id ? aberto.nome : "Novo padrão"}
          subtitulo="Padrão da casa"
          onFechar={() => setAberto(null)}
          rodape={
            <div className="painel-acoes">
              <Button onClick={() => setAberto(null)}>Cancelar</Button>
              <Button variant="primary" disabled={ocupado} onClick={() => void gravar()}>
                Salvar
              </Button>
            </div>
          }
        >
          <form onSubmit={(e) => void gravar(e)}>
            {erro ? <p role="alert" className="form-erro">{erro}</p> : null}
            <label className="gestao-field">
              <span>Nome</span>
              <input value={aberto.nome} onChange={(e) => setAberto({ ...aberto, nome: e.target.value })} />
            </label>
            <label className="gestao-field">
              <span>Ingrediente ou termo</span>
              <input value={aberto.termo} onChange={(e) => setAberto({ ...aberto, termo: e.target.value })} />
            </label>
            <label className="gestao-field">
              <span>% do padeiro</span>
              <input
                type="text"
                inputMode="decimal"
                value={String(aberto.percentual)}
                onChange={(e) => setAberto({ ...aberto, percentual: Number(e.target.value.replace(",", ".")) || 0 })}
              />
            </label>
            <label className="gestao-field">
              <span>Observação</span>
              <input value={aberto.observacao ?? ""} onChange={(e) => setAberto({ ...aberto, observacao: e.target.value })} />
            </label>
            <label className="gigio-topo">
              <input type="checkbox" checked={aberto.ativo} onChange={(e) => setAberto({ ...aberto, ativo: e.target.checked })} />
              <span>Ativo</span>
            </label>
          </form>
        </SidePanel>
      ) : null}
    </main>
  );
}
