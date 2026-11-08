import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useGestao } from "../contexto";
import {
  listarFornadas,
  listarProdutos,
  listarProgramacoes,
  salvarProgramacao,
  textoDoErro,
  type FornadaProducao,
  type ProdutoLinha,
  type Programacao,
} from "../lib/api";
import { Button } from "../shell/Button";
import { Card } from "../shell/Card";
import { PageHeader } from "../shell/PageHeader";
import { SidePanel } from "../shell/SidePanel";
import "./fluxo.css";

const DIAS = [
  { valor: 0, rotulo: "Seg" },
  { valor: 1, rotulo: "Ter" },
  { valor: 2, rotulo: "Qua" },
  { valor: 3, rotulo: "Qui" },
  { valor: 4, rotulo: "Sex" },
  { valor: 5, rotulo: "Sáb" },
  { valor: 6, rotulo: "Dom" },
];

const VAZIO: Programacao = {
  id: "",
  produto_id: "",
  produto: "",
  quantidade_por_fornada: 100,
  fornada_ids: [],
  dias_semana: [0, 1, 2, 3, 4, 5],
  inicio: null,
  fim: null,
  ativa: true,
};

export function Programacoes() {
  const { pode, atualizarFluxo } = useGestao();
  const [lista, setLista] = useState<Programacao[] | null>(null);
  const [falhou, setFalhou] = useState(false);
  const [aberto, setAberto] = useState<Programacao | null>(null);
  const [produtos, setProdutos] = useState<ProdutoLinha[]>([]);
  const [fornadas, setFornadas] = useState<FornadaProducao[]>([]);
  const [erro, setErro] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const podeEditar = pode("lancar");

  const carregar = useCallback(async () => {
    try {
      setLista((await listarProgramacoes()).programacoes);
      setFalhou(false);
    } catch {
      setFalhou(true);
    }
  }, []);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  async function abrir(item: Programacao | null) {
    setErro(null);
    if (!produtos.length) setProdutos((await listarProdutos("produzidos")).produtos);
    if (!fornadas.length) setFornadas((await listarFornadas()).fornadas);
    setAberto(item ?? { ...VAZIO });
  }

  async function gravar(event?: FormEvent) {
    event?.preventDefault();
    if (!aberto) return;
    setOcupado(true);
    setErro(null);
    try {
      await salvarProgramacao(aberto.id || null, {
        produto_id: aberto.produto_id,
        quantidade_por_fornada: Number(aberto.quantidade_por_fornada),
        fornada_ids: aberto.fornada_ids,
        dias_semana: aberto.dias_semana,
        inicio: aberto.inicio || null,
        fim: aberto.fim || null,
        ativa: aberto.ativa,
      });
      setAberto(null);
      await carregar();
      atualizarFluxo();
    } catch (falha) {
      setErro(textoDoErro(falha));
    } finally {
      setOcupado(false);
    }
  }

  function alternarDia(valor: number) {
    if (!aberto) return;
    const tem = aberto.dias_semana.includes(valor);
    setAberto({ ...aberto, dias_semana: tem ? aberto.dias_semana.filter((dia) => dia !== valor) : [...aberto.dias_semana, valor].sort() });
  }

  function alternarFornada(id: string) {
    if (!aberto) return;
    const tem = aberto.fornada_ids.includes(id);
    setAberto({ ...aberto, fornada_ids: tem ? aberto.fornada_ids.filter((item) => item !== id) : [...aberto.fornada_ids, id] });
  }

  return (
    <main className="fluxo-pagina">
      <PageHeader
        title="Programações"
        description="O que a padaria produz todo dia, sem esperar pedido."
        actions={podeEditar ? <Button variant="primary" onClick={() => void abrir(null)}>Nova programação</Button> : undefined}
      />
      {falhou ? (
        <Card className="fluxo-vazio">
          <p role="alert">Não foi possível carregar as programações agora.</p>
          <Button onClick={() => void carregar()}>Tentar de novo</Button>
        </Card>
      ) : null}
      {!lista && !falhou ? <p className="fluxo-estado">Carregando as programações.</p> : null}
      {lista ? (
        <Card className="fluxo-lista-card">
          <table className="lista-entradas lista-producao" aria-label="Programações">
            <thead>
              <tr>
                <th scope="col">Produto</th>
                <th scope="col">Por fornada</th>
                <th scope="col">Dias</th>
                <th scope="col">Vigência</th>
                <th scope="col">Situação</th>
              </tr>
            </thead>
            <tbody>
              {lista.length === 0 ? (
                <tr className="entrada-linha"><td colSpan={5}>Nenhuma programação ainda.</td></tr>
              ) : null}
              {lista.map((item) => (
                <tr key={item.id} className="entrada-linha">
                  <th scope="row" data-label="Produto">
                    <button type="button" className="ing-nome" disabled={!podeEditar} onClick={() => void abrir(item)}>
                      <strong>{item.produto}</strong>
                    </button>
                  </th>
                  <td data-label="Por fornada" className="num">{item.quantidade_por_fornada}</td>
                  <td data-label="Dias">{DIAS.filter((dia) => item.dias_semana.includes(dia.valor)).map((dia) => dia.rotulo).join(" ")}</td>
                  <td data-label="Vigência">{item.inicio || item.fim ? `${item.inicio ?? "…"} a ${item.fim ?? "…"}` : "Sempre"}</td>
                  <td data-label="Situação">{item.ativa ? "Ativa" : "Inativa"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ) : null}
      {aberto ? (
        <SidePanel
          titulo={aberto.id ? aberto.produto : "Nova programação"}
          subtitulo="Programação"
          onFechar={() => setAberto(null)}
          rodape={<div className="painel-acoes"><Button onClick={() => setAberto(null)}>Cancelar</Button><Button variant="primary" disabled={ocupado} onClick={() => void gravar()}>Salvar</Button></div>}
        >
          <form onSubmit={(e) => void gravar(e)}>
            {erro ? <p role="alert" className="form-erro">{erro}</p> : null}
            <label className="gestao-field">
              <span>Produto</span>
              <select value={aberto.produto_id} onChange={(e) => setAberto({ ...aberto, produto_id: e.target.value })}>
                <option value="">Escolha</option>
                {produtos.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}
              </select>
            </label>
            <label className="gestao-field">
              <span>Unidades por fornada</span>
              <input inputMode="numeric" value={String(aberto.quantidade_por_fornada)} onChange={(e) => setAberto({ ...aberto, quantidade_por_fornada: Number(e.target.value.replace(/\D/g, "")) || 0 })} />
            </label>
            <fieldset className="cal-opcoes">
              <legend>Fornadas</legend>
              {fornadas.filter((item) => item.ativa).map((item) => (
                <label key={item.id} className="gigio-topo">
                  <input type="checkbox" checked={aberto.fornada_ids.includes(item.id)} onChange={() => alternarFornada(item.id)} />
                  <span>{item.nome}</span>
                </label>
              ))}
            </fieldset>
            <div className="gestao-chips" role="group" aria-label="Dias da semana">
              {DIAS.map((dia) => (
                <button key={dia.valor} type="button" className={aberto.dias_semana.includes(dia.valor) ? "chip-filtro on" : "chip-filtro"} aria-pressed={aberto.dias_semana.includes(dia.valor)} onClick={() => alternarDia(dia.valor)}>
                  {dia.rotulo}
                </button>
              ))}
            </div>
            <label className="gestao-field">
              <span>Início</span>
              <input type="date" value={aberto.inicio ?? ""} onChange={(e) => setAberto({ ...aberto, inicio: e.target.value || null })} />
            </label>
            <label className="gestao-field">
              <span>Fim</span>
              <input type="date" value={aberto.fim ?? ""} onChange={(e) => setAberto({ ...aberto, fim: e.target.value || null })} />
            </label>
            <label className="gigio-topo">
              <input type="checkbox" checked={aberto.ativa} onChange={(e) => setAberto({ ...aberto, ativa: e.target.checked })} />
              <span>Ativa</span>
            </label>
          </form>
        </SidePanel>
      ) : null}
    </main>
  );
}
