import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useGestao } from "../contexto";
import { listarPadroes, salvarPadrao, textoDoErro, type PadraoPadaria } from "../lib/api";
import { Button } from "../shell/Button";
import { Card } from "../shell/Card";
import { PageHeader } from "../shell/PageHeader";
import { SidePanel } from "../shell/SidePanel";
import "./fluxo.css";

export function Padroes() {
  const { pode } = useGestao();
  const [lista, setLista] = useState<PadraoPadaria[] | null>(null);
  const [falhou, setFalhou] = useState(false);
  const [aberto, setAberto] = useState<PadraoPadaria | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

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

  async function gravar(event?: FormEvent) {
    event?.preventDefault();
    if (!aberto) return;
    setOcupado(true);
    setErro(null);
    try {
      await salvarPadrao(aberto.id, {
        nome: aberto.nome.trim(),
        termo: aberto.termo.trim(),
        ingrediente_id: aberto.ingrediente_id,
        percentual: aberto.percentual,
        observacao: aberto.observacao,
        ativo: aberto.ativo,
      });
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
      <PageHeader title="Padrões" description="O que a casa já sabe, em % do padeiro." />
      {falhou ? (
        <Card className="fluxo-vazio">
          <p role="alert">Não foi possível carregar os padrões agora.</p>
          <Button onClick={() => void carregar()}>Tentar de novo</Button>
        </Card>
      ) : null}
      {!lista && !falhou ? <p className="fluxo-estado">Carregando os padrões.</p> : null}
      {lista ? (
        <Card className="fluxo-lista-card">
          <ul className="fluxo-linhas" aria-label="Padrões da padaria">
            {lista.map((p) => (
              <li key={p.id} className="fluxo-linha">
                <button type="button" className="ing-nome" onClick={() => podeEditar && setAberto(p)} disabled={!podeEditar}>
                  <span className="ing-textos">
                    <strong>{p.nome}</strong>
                    <small className="linha-secundaria">{p.ingrediente || p.termo}</small>
                  </span>
                </button>
                <span>{new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(p.percentual)} %</span>
                {p.ativo ? null : <span className="sub">Inativo</span>}
              </li>
            ))}
          </ul>
        </Card>
      ) : null}
      {aberto ? (
        <SidePanel
          titulo={aberto.nome}
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
              <span>Termo</span>
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
