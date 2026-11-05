import { Fragment, useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { useGestao } from "../contexto";
import {
  ajustarSaldo,
  ApiError,
  detalheIngrediente,
  editarIngrediente,
  juntarIngredientes,
  listarIngredientes,
  marcarDistintos,
  textoDoErro,
  trocarIngrediente,
  type FiltroIngredientes,
  type IngredienteDetalhe,
  type IngredienteLinha,
  type IngredientesLista,
  type ParecidoPar,
} from "../lib/api";
import { casaBusca, casaLote } from "../lib/buscaLista";
import { CATEGORIAS } from "../lib/categorias";
import { numero } from "../lib/entradaForm";
import { custoPorUnidade, custoTexto, dataBr, dataCurta, dinheiro, diasAte, quantidadeBase } from "../lib/format";
import { Button } from "../shell/Button";
import { Card } from "../shell/Card";
import { CampoIngrediente, type IngredienteEscolhido } from "../shell/CampoIngrediente";
import { Chips } from "../shell/Chips";
import { CorrigirCusto } from "../shell/CorrigirCusto";
import { PageHeader } from "../shell/PageHeader";
import { SeloCusto } from "../shell/SeloCusto";
import { SidePanel } from "../shell/SidePanel";
import { StatusChip } from "../shell/StatusChip";
import { hojeNoFuso } from "../lib/useNarrow";
import "./fluxo.css";

const FILTROS: { valor: FiltroIngredientes; rotulo: string }[] = [
  { valor: "todos", rotulo: "Todos" },
  { valor: "com_saldo", rotulo: "Com saldo" },
  { valor: "sem_saldo", rotulo: "Sem saldo" },
  { valor: "vence7", rotulo: "Vence em 7 dias" },
];

const BASES: Record<string, string> = { g: "Massa (g)", ml: "Volume (ml)", un: "Unidade (un)" };

function filtroDaUrl(search: string): FiltroIngredientes {
  const valor = new URLSearchParams(search).get("filtro");
  return FILTROS.some((f) => f.valor === valor) ? (valor as FiltroIngredientes) : "todos";
}

function categoriaDaUrl(search: string): string {
  return new URLSearchParams(search).get("categoria") ?? "";
}

function urlDaLista(filtro: FiltroIngredientes, categoria: string): string {
  const partes: string[] = [];
  if (filtro !== "todos") partes.push(`filtro=${filtro}`);
  if (categoria) partes.push(`categoria=${encodeURIComponent(categoria)}`);
  return partes.length ? `/ingredientes?${partes.join("&")}` : "/ingredientes";
}

function contagemDe(i: IngredienteLinha): string {
  if (i.itens === 0) return "nenhum item";
  const itens = `${i.itens} ${i.itens === 1 ? "item" : "itens"}`;
  const lotes = i.lotes === 0 ? "nenhum lote" : `${i.lotes} ${i.lotes === 1 ? "lote" : "lotes"}`;
  return `${itens} · ${lotes}`;
}

/** Selo só na exceção. O dia comum fica com travessão. */
function selosDe(i: IngredienteLinha, parecido: boolean): { stage: string; rotulo: string }[] {
  const selos: { stage: string; rotulo: string }[] = [];
  if (i.saldo <= 0) selos.push({ stage: "attention", rotulo: "Sem saldo" });
  else if (i.vence_em_7_dias) selos.push({ stage: "warning", rotulo: "Vence em 7 dias" });
  if (parecido) selos.push({ stage: "attention", rotulo: "Parecidos" });
  return selos;
}

/** Unidades em que a pessoa conta, e quanto cada uma vale na unidade base. */
function unidadesDeContagem(base: string): { valor: string; rotulo: string; fator: number }[] {
  if (base === "g") return [{ valor: "kg", rotulo: "kg", fator: 1000 }, { valor: "g", rotulo: "g", fator: 1 }];
  if (base === "ml") return [{ valor: "l", rotulo: "L", fator: 1000 }, { valor: "ml", rotulo: "ml", fator: 1 }];
  return [{ valor: "un", rotulo: "un", fator: 1 }];
}

const TIPO_MOVIMENTO: Record<string, string> = { entrada: "Entrada", ajuste: "Ajuste", juncao: "Junção" };

/** O custo de hoje do lote, como a pessoa lê (R$ por kg, L ou un). */
function custoDoLoteTexto(custo: number | null, base: string): string {
  return custo === null ? "sem custo informado" : custoTexto(custo, base);
}

// ---------------------------------------------------------------- painel do ingrediente

type Modo = "ver" | "ajustar" | "editar" | "juntar" | "trocar" | "custo";

function PainelIngrediente({
  id,
  outros,
  hoje,
  onFechar,
  onAbrir,
  aoMudar,
}: {
  id: string;
  outros: IngredienteLinha[];
  hoje: string;
  onFechar: () => void;
  /** Abre outro ingrediente (depois de trocar o ingrediente de um item). */
  onAbrir: (id: string) => void;
  aoMudar: () => void;
}) {
  const { pode } = useGestao();
  const [dados, setDados] = useState<IngredienteDetalhe | null>(null);
  const [falhou, setFalhou] = useState(false);
  const [modo, setModo] = useState<Modo>("ver");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [itemEmTroca, setItemEmTroca] = useState<{ id: string; nome: string; marca: string } | null>(null);
  const [loteEmCusto, setLoteEmCusto] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    try {
      setDados(await detalheIngrediente(id));
      setFalhou(false);
    } catch {
      setFalhou(true);
    }
  }, [id]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  async function executar(acao: () => Promise<IngredienteDetalhe>, aoConcluir?: (novo: IngredienteDetalhe) => void) {
    setEnviando(true);
    setErro(null);
    try {
      const novo = await acao();
      setDados(novo);
      setModo("ver");
      aoMudar();
      aoConcluir?.(novo);
    } catch (falha) {
      setErro(textoDoErro(falha));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <SidePanel
      titulo={dados?.nome ?? "Ingrediente"}
      subtitulo={dados ? `Saldo ${quantidadeBase(dados.saldo, dados.unidade_base)}` : undefined}
      onFechar={onFechar}
      rodape={
        dados && modo === "ver" ? (
          <div className="painel-acoes">
            {pode("ajustar") ? (
              <Button variant="primary" onClick={() => setModo("ajustar")} disabled={dados.lotes_detalhe.length === 0}>
                Ajustar saldo
              </Button>
            ) : null}
            {pode("lancar") ? <Button onClick={() => setModo("editar")}>Editar</Button> : null}
            {pode("juntar") ? <Button onClick={() => setModo("juntar")}>Juntar com…</Button> : null}
          </div>
        ) : undefined
      }
    >
      {falhou ? <p role="alert">Não foi possível abrir este ingrediente agora.</p> : null}
      {!dados && !falhou ? <p>Carregando.</p> : null}
      {erro ? (
        <p role="alert" className="form-erro">
          {erro}
        </p>
      ) : null}

      {dados && modo === "ajustar" ? (
        <FormAjuste
          dados={dados}
          enviando={enviando}
          onCancelar={() => {
            setModo("ver");
            setErro(null);
          }}
          onEnviar={(corpo) => executar(() => ajustarSaldo(dados.id, corpo))}
        />
      ) : null}
      {dados && modo === "editar" ? (
        <FormEditar
          dados={dados}
          enviando={enviando}
          onCancelar={() => {
            setModo("ver");
            setErro(null);
          }}
          onEnviar={(corpo) => executar(() => editarIngrediente(dados.id, corpo))}
        />
      ) : null}
      {dados && modo === "trocar" && itemEmTroca ? (
        <FormTrocar
          dados={dados}
          item={itemEmTroca}
          enviando={enviando}
          onCancelar={() => {
            setModo("ver");
            setErro(null);
          }}
          onEnviar={(ingredienteId, motivo) =>
            executar(() => trocarIngrediente(itemEmTroca.id, { ingrediente_id: ingredienteId, motivo }), (novo) => {
              if (novo.id !== id) onAbrir(novo.id);
            })
          }
        />
      ) : null}
      {dados && modo === "custo" && loteEmCusto ? (
        <CorrigirCusto
          loteId={loteEmCusto}
          onCancelar={() => {
            setModo("ver");
            setLoteEmCusto(null);
          }}
          onFeito={() => {
            setModo("ver");
            setLoteEmCusto(null);
            void carregar();
            aoMudar();
          }}
        />
      ) : null}
      {dados && modo === "juntar" ? (
        <FormJuntar
          dados={dados}
          candidatos={outros.filter((o) => o.id !== dados.id && o.unidade_base === dados.unidade_base)}
          enviando={enviando}
          onCancelar={() => {
            setModo("ver");
            setErro(null);
          }}
          onEnviar={(mantem, remove) =>
            executar(() => juntarIngredientes(mantem, remove), (novo) => {
              if (novo.id !== id) onFechar();
            })
          }
        />
      ) : null}

      {dados && modo === "ver" ? (
        <>
          <dl className="painel-fatos">
            <div>
              <dt>Saldo</dt>
              <dd>{quantidadeBase(dados.saldo, dados.unidade_base)}</dd>
            </div>
            <div>
              <dt>Custo médio</dt>
              <dd>
                {dados.custo_medio_base === null
                  ? "sem custo informado"
                  : custoPorUnidade(dados.custo_medio_base, dados.unidade_base)}
                {dados.custo_medio_base !== null && dados.lotes_com_custo < dados.lotes_com_saldo ? (
                  <span className="sub"> parcial: {dados.lotes_com_custo} de {dados.lotes_com_saldo} lotes</span>
                ) : null}
              </dd>
            </div>
            <div>
              <dt>Unidade</dt>
              <dd>{BASES[dados.unidade_base] ?? dados.unidade_base}</dd>
            </div>
            <div>
              <dt>Categoria</dt>
              <dd>{dados.categoria}</dd>
            </div>
            {(dados.apelidos ?? []).length > 0 ? (
              <div>
                <dt>Também chamado de</dt>
                <dd>{dados.apelidos.join(", ")}</dd>
              </div>
            ) : null}
          </dl>

          <section aria-labelledby="pi-itens" className="painel-secao">
            <h3 id="pi-itens">Itens</h3>
            {dados.itens_detalhe.length === 0 ? (
              <p className="sub">Nenhum item comprado ainda.</p>
            ) : (
              <ul className="painel-lista">
                {dados.itens_detalhe.map((i) => (
                  <li key={i.id}>
                    <span>
                      <strong>{i.nome}</strong>
                      {i.marca ? <span className="sub"> · {i.marca}</span> : null}
                      {pode("juntar") ? (
                        <span className="sub bloco">
                          <button
                            type="button"
                            className="link-acao"
                            aria-label={`Trocar ingrediente de ${i.nome}`}
                            onClick={() => {
                              setItemEmTroca({ id: i.id, nome: i.nome, marca: i.marca ?? "" });
                              setModo("trocar");
                              setErro(null);
                            }}
                          >
                            Trocar ingrediente
                          </button>
                        </span>
                      ) : null}
                    </span>
                    <span>{quantidadeBase(i.saldo, dados.unidade_base)}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section aria-labelledby="pi-lotes" className="painel-secao">
            <h3 id="pi-lotes">Lotes, o que vence primeiro no topo</h3>
            {dados.lotes_detalhe.length === 0 ? (
              <p className="sub">Nenhum lote.</p>
            ) : (
              <ul className="painel-lista">
                {dados.lotes_detalhe.map((l) => (
                  <li key={l.id}>
                    <span>
                      <strong>{l.codigo}</strong>
                      {l.custo_corrigido ? (
                        <SeloCusto antes={l.custo_antes ?? null} depois={l.custo_depois ?? null} base={dados.unidade_base} />
                      ) : null}
                      <span className="sub">
                        {" "}
                        · {l.item} · {l.local}
                      </span>
                      <span className="sub bloco">
                        {l.validade ? `${dataBr(l.validade)}, ${diasAte(hoje, l.validade)}` : l.sem_validade ? "sem validade" : "validade não informada"}
                      </span>
                      <span className="sub bloco">
                        Custo: {custoDoLoteTexto(l.custo_unidade_base, dados.unidade_base)}
                        {pode("ajustar") ? (
                          <>
                            {" · "}
                            <button
                              type="button"
                              className="link-acao"
                              aria-label={`Corrigir custo do lote ${l.codigo}`}
                              onClick={() => {
                                setLoteEmCusto(l.id);
                                setModo("custo");
                                setErro(null);
                              }}
                            >
                              Corrigir custo
                            </button>
                          </>
                        ) : null}
                      </span>
                    </span>
                    <span>{quantidadeBase(l.saldo, dados.unidade_base)}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {(dados.correcoes_custo ?? []).length > 0 ? (
            <section aria-labelledby="pi-custos" className="painel-secao">
              <h3 id="pi-custos">Correções de custo</h3>
              <ul className="painel-lista historico">
                {(dados.correcoes_custo ?? []).map((c) => (
                  <li key={c.id}>
                    <span>
                      <strong>
                        {custoDoLoteTexto(c.custo_antes, dados.unidade_base)} → {custoDoLoteTexto(c.custo_depois, dados.unidade_base)}
                      </strong>
                      <span className="sub bloco">
                        {dataCurta(c.quando.slice(0, 10))}
                        {c.quem ? ` · ${c.quem}` : ""}
                        {c.lote ? ` · lote ${c.lote}` : ""}
                        {c.modo === "valor_pago" && c.valor_pago !== null ? ` · valor pago ${dinheiro(c.valor_pago)}` : ""}
                      </span>
                      <span className="sub bloco">{c.motivo}</span>
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <section aria-labelledby="pi-hist" className="painel-secao">
            <h3 id="pi-hist">Histórico</h3>
            {dados.movimentos.length === 0 ? (
              <p className="sub">Nada movimentado.</p>
            ) : (
              <ul className="painel-lista historico">
                {dados.movimentos.map((m) => (
                  <li key={m.id}>
                    <span>
                      <strong>{m.troca ? "Troca de ingrediente" : (TIPO_MOVIMENTO[m.tipo] ?? m.tipo)}</strong>
                      <span className="sub bloco">
                        {dataCurta(m.quando.slice(0, 10))}
                        {m.lote ? ` · lote ${m.lote}` : ""}
                        {m.tipo === "juncao" && m.de && m.para ? ` · ${m.de} → ${m.para}` : ""}
                        {(m.tipo === "ajuste" || m.troca) && m.motivo ? ` · ${m.troca ? m.motivo.replace(/^Troca de ingrediente de /, "item ") : m.motivo}` : ""}
                      </span>
                    </span>
                    <span className={m.quantidade_base < 0 ? "mov-saida" : "mov-entrada"}>
                      {m.tipo === "juncao"
                        ? "—"
                        : `${m.quantidade_base > 0 ? "+" : "−"}${quantidadeBase(Math.abs(m.quantidade_base), dados.unidade_base)}`}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      ) : null}
    </SidePanel>
  );
}

function FormAjuste({
  dados,
  enviando,
  onCancelar,
  onEnviar,
}: {
  dados: IngredienteDetalhe;
  enviando: boolean;
  onCancelar: () => void;
  onEnviar: (corpo: { lote_id: string; saldo_contado_base: number; motivo: string }) => void;
}) {
  const unidades = unidadesDeContagem(dados.unidade_base);
  const comSaldo = dados.lotes_detalhe.filter((l) => l.saldo > 0);
  const lotes = comSaldo.length > 0 ? comSaldo : dados.lotes_detalhe;
  const [loteId, setLoteId] = useState(lotes[0]?.id ?? "");
  const [contado, setContado] = useState("");
  const [unidade, setUnidade] = useState(unidades[0].valor);
  const [motivo, setMotivo] = useState("");
  const lote = dados.lotes_detalhe.find((l) => l.id === loteId);
  const fator = unidades.find((u) => u.valor === unidade)?.fator ?? 1;
  const valor = numero(contado);
  const base = valor === null ? null : valor * fator;
  const diferenca = base !== null && lote ? base - lote.saldo : null;

  function enviar(event: FormEvent) {
    event.preventDefault();
    if (base === null || !loteId) return;
    onEnviar({ lote_id: loteId, saldo_contado_base: base, motivo: motivo.trim() });
  }

  return (
    <form className="painel-form" onSubmit={enviar}>
      <h3>Ajustar saldo</h3>
      <p className="sub">O histórico não é apagado: o ajuste vira um novo movimento, com o motivo.</p>
      <label className="gestao-field">
        <span>Lote</span>
        <select value={loteId} onChange={(e) => setLoteId(e.target.value)}>
          {lotes.map((l) => (
            <option key={l.id} value={l.id}>
              {l.codigo} · {l.item} · saldo {quantidadeBase(l.saldo, dados.unidade_base)}
            </option>
          ))}
        </select>
      </label>
      <div className="campo-linha">
        <label className="gestao-field">
          <span>Saldo contado</span>
          <input type="text" inputMode="decimal" value={contado} onChange={(e) => setContado(e.target.value)} />
        </label>
        <label className="gestao-field">
          <span>Unidade</span>
          <select value={unidade} onChange={(e) => setUnidade(e.target.value)}>
            {unidades.map((u) => (
              <option key={u.valor} value={u.valor}>
                {u.rotulo}
              </option>
            ))}
          </select>
        </label>
      </div>
      {diferenca !== null && lote ? (
        <p className="sub" aria-live="polite">
          {diferenca === 0
            ? "Igual ao saldo atual: nada a ajustar."
            : `Diferença: ${diferenca > 0 ? "+" : "−"}${quantidadeBase(Math.abs(diferenca), dados.unidade_base)}`}
        </p>
      ) : null}
      <label className="gestao-field">
        <span>Motivo (obrigatório)</span>
        <input type="text" value={motivo} maxLength={300} onChange={(e) => setMotivo(e.target.value)} />
      </label>
      <div className="painel-acoes">
        <Button type="submit" variant="primary" disabled={enviando || base === null || diferenca === 0 || motivo.trim().length < 3}>
          Gravar ajuste
        </Button>
        <Button onClick={onCancelar}>Cancelar</Button>
      </div>
    </form>
  );
}

function listaDeApelidos(texto: string): string[] {
  return texto
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);
}

function FormEditar({
  dados,
  enviando,
  onCancelar,
  onEnviar,
}: {
  dados: IngredienteDetalhe;
  enviando: boolean;
  onCancelar: () => void;
  onEnviar: (corpo: { nome?: string; unidade_base?: string; categoria?: string; apelidos?: string[] }) => void;
}) {
  const [nome, setNome] = useState(dados.nome);
  const [base, setBase] = useState(dados.unidade_base);
  const [categoria, setCategoria] = useState(dados.categoria);
  const [apelidos, setApelidos] = useState((dados.apelidos ?? []).join(", "));
  const movimentado = dados.movimentos.length > 0 || dados.itens_detalhe.length > 0;

  function enviar(event: FormEvent) {
    event.preventDefault();
    onEnviar({
      nome: nome.trim() !== dados.nome ? nome.trim() : undefined,
      unidade_base: base !== dados.unidade_base ? base : undefined,
      categoria: categoria !== dados.categoria ? categoria : undefined,
      apelidos: apelidos !== (dados.apelidos ?? []).join(", ") ? listaDeApelidos(apelidos) : undefined,
    });
  }

  return (
    <form className="painel-form" onSubmit={enviar}>
      <h3>Editar ingrediente</h3>
      <label className="gestao-field">
        <span>Nome</span>
        <input type="text" value={nome} maxLength={120} onChange={(e) => setNome(e.target.value)} />
      </label>
      <label className="gestao-field">
        <span>Categoria</span>
        <select value={categoria} onChange={(e) => setCategoria(e.target.value)}>
          {CATEGORIAS.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </label>
      <label className="gestao-field">
        <span>Apelidos</span>
        <input
          type="text"
          value={apelidos}
          maxLength={400}
          placeholder="farinha 00, tipo 00"
          onChange={(e) => setApelidos(e.target.value)}
        />
      </label>
      <p className="sub">Outros nomes pelos quais você chama este ingrediente, separados por vírgula. A busca também acha por eles.</p>
      <label className="gestao-field">
        <span>Unidade base</span>
        <select value={base} disabled={movimentado} onChange={(e) => setBase(e.target.value)}>
          {Object.entries(BASES).map(([valor, rotulo]) => (
            <option key={valor} value={valor}>
              {rotulo}
            </option>
          ))}
        </select>
      </label>
      {movimentado ? <p className="sub">A unidade não muda depois que há itens ou movimentos.</p> : null}
      <div className="painel-acoes">
        <Button type="submit" variant="primary" disabled={enviando || nome.trim().length === 0}>
          Salvar
        </Button>
        <Button onClick={onCancelar}>Cancelar</Button>
      </div>
    </form>
  );
}

function FormTrocar({
  dados,
  item,
  enviando,
  onCancelar,
  onEnviar,
}: {
  dados: IngredienteDetalhe;
  item: { id: string; nome: string; marca: string };
  enviando: boolean;
  onCancelar: () => void;
  onEnviar: (ingredienteId: string, motivo: string) => void;
}) {
  const [novo, setNovo] = useState<IngredienteEscolhido | null>(null);
  const [motivo, setMotivo] = useState("");
  const outraUnidade = novo !== null && novo.unidade_base !== dados.unidade_base;
  const mesmo = novo !== null && novo.id === dados.id;
  const pronto = novo !== null && !outraUnidade && !mesmo && motivo.trim().length >= 3;

  return (
    <form
      className="painel-form"
      aria-label={`Trocar o ingrediente de ${item.nome}`}
      onSubmit={(event) => {
        event.preventDefault();
        if (pronto && novo) onEnviar(novo.id, motivo.trim());
      }}
    >
      <h3>Trocar ingrediente</h3>
      <p className="sub">
        “{item.nome}” hoje está ligado a “{dados.nome}”. Ao trocar, os lotes e o saldo do item vão junto: o saldo de “{dados.nome}”
        diminui e o do novo aumenta. Fica no histórico, com o motivo. Nada é apagado.
      </p>
      <div className="gestao-field">
        <span id="trocar-rotulo">Passa a ser o ingrediente</span>
        <CampoIngrediente
          rotulo="Novo ingrediente do item"
          valor={novo ? { nome: novo.nome, categoria: novo.categoria } : null}
          item={item.nome}
          marca={item.marca}
          placeholder="Buscar o ingrediente certo"
          onEscolher={(ing) => setNovo(ing)}
          onTrocar={() => setNovo(null)}
        />
      </div>
      {outraUnidade ? (
        <p role="alert" className="form-erro">
          “{novo?.nome}” é medido em outra unidade ({BASES[novo?.unidade_base ?? ""] ?? novo?.unidade_base}). Escolha um ingrediente em{" "}
          {BASES[dados.unidade_base]}.
        </p>
      ) : null}
      {mesmo ? <p className="sub">Este item já está ligado a “{dados.nome}”.</p> : null}
      <label className="gestao-field">
        <span>Motivo (obrigatório)</span>
        <input type="text" value={motivo} maxLength={300} onChange={(e) => setMotivo(e.target.value)} />
      </label>
      <div className="painel-acoes">
        <Button type="submit" variant="primary" disabled={enviando || !pronto}>
          Trocar ingrediente
        </Button>
        <Button onClick={onCancelar}>Cancelar</Button>
      </div>
    </form>
  );
}

function FormJuntar({
  dados,
  candidatos,
  enviando,
  onCancelar,
  onEnviar,
}: {
  dados: IngredienteDetalhe;
  candidatos: IngredienteLinha[];
  enviando: boolean;
  onCancelar: () => void;
  onEnviar: (mantemId: string, removeId: string) => void;
}) {
  const [outroId, setOutroId] = useState(candidatos[0]?.id ?? "");
  const [manter, setManter] = useState<"este" | "outro">("este");
  const outro = candidatos.find((c) => c.id === outroId);

  return (
    <form
      className="painel-form"
      onSubmit={(event) => {
        event.preventDefault();
        if (!outro) return;
        if (manter === "este") onEnviar(dados.id, outro.id);
        else onEnviar(outro.id, dados.id);
      }}
    >
      <h3>Juntar com…</h3>
      <p className="sub">
        Os itens e o saldo de um passam para o outro. Nada é apagado: o que sobra fica guardado, inativo, com o histórico.
      </p>
      {candidatos.length === 0 ? (
        <p className="sub">Não há outro ingrediente na mesma unidade ({BASES[dados.unidade_base]}) para juntar.</p>
      ) : (
        <>
          <label className="gestao-field">
            <span>Juntar “{dados.nome}” com</span>
            <select value={outroId} onChange={(e) => setOutroId(e.target.value)}>
              {candidatos.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nome} · {quantidadeBase(c.saldo, c.unidade_base)}
                </option>
              ))}
            </select>
          </label>
          <fieldset className="painel-opcoes">
            <legend>Qual nome fica?</legend>
            <label>
              <input type="radio" name="manter" checked={manter === "este"} onChange={() => setManter("este")} />
              <span>{dados.nome}</span>
            </label>
            <label>
              <input type="radio" name="manter" checked={manter === "outro"} onChange={() => setManter("outro")} />
              <span>{outro?.nome ?? "o outro"}</span>
            </label>
          </fieldset>
        </>
      )}
      <div className="painel-acoes">
        <Button type="submit" variant="primary" disabled={enviando || !outro}>
          Juntar
        </Button>
        <Button onClick={onCancelar}>Cancelar</Button>
      </div>
    </form>
  );
}

// ---------------------------------------------------------------- novo ingrediente

/** "Novo ingrediente" começa pela BUSCA: ninguém cadastra sem antes ter certeza de que ele não existe. */
function NovoIngredienteBusca({
  onFechar,
  onEscolhido,
}: {
  onFechar: () => void;
  onEscolhido: (ingrediente: IngredienteEscolhido, criado: boolean) => void;
}) {
  return (
    <Card className="novo-ingrediente-card">
      <section aria-label="Novo ingrediente">
        <h2 className="novo-ingrediente-titulo">Novo ingrediente</h2>
        <p className="sub">
          Busque pelo nome antes de cadastrar. Se ele já existe, é só abrir; se não, cadastre pelo fim da lista. Ele só
          ganha saldo quando chegar uma entrada.
        </p>
        <div className="novo-ingrediente-linha">
          <CampoIngrediente
            rotulo="Buscar ingrediente"
            valor={null}
            autoFoco
            placeholder="Digite o nome: farinha, fermento, ovo…"
            onEscolher={onEscolhido}
          />
          <Button onClick={onFechar}>Fechar</Button>
        </div>
      </section>
    </Card>
  );
}

// ---------------------------------------------------------------- pares parecidos

function PainelPares({
  pares,
  onFechar,
  aoMudar,
}: {
  pares: ParecidoPar[];
  onFechar: () => void;
  aoMudar: () => void;
}) {
  const [erro, setErro] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState<string | null>(null);
  const [mantem, setMantem] = useState<Record<string, "a" | "b">>({});

  async function agir(chave: string, acao: () => Promise<unknown>) {
    setOcupado(chave);
    setErro(null);
    try {
      await acao();
      aoMudar();
    } catch (falha) {
      setErro(textoDoErro(falha));
    } finally {
      setOcupado(null);
    }
  }

  return (
    <SidePanel
      titulo="Parecem o mesmo ingrediente"
      subtitulo="Junte os repetidos para o saldo não ficar dividido."
      onFechar={onFechar}
    >
      {erro ? (
        <p role="alert" className="form-erro">
          {erro}
        </p>
      ) : null}
      {pares.length === 0 ? <p>Nenhum par sobrando.</p> : null}
      <ul className="pares">
        {pares.map((par) => {
          const chave = `${par.a.id}-${par.b.id}`;
          const fica = mantem[chave] ?? "a";
          const quem = fica === "a" ? par.a : par.b;
          const sai = fica === "a" ? par.b : par.a;
          return (
            <li key={chave} className="par">
              <fieldset className="painel-opcoes">
                <legend>Qual nome fica?</legend>
                <label>
                  <input type="radio" name={chave} checked={fica === "a"} onChange={() => setMantem({ ...mantem, [chave]: "a" })} />
                  <span>{par.a.nome}</span>
                </label>
                <label>
                  <input type="radio" name={chave} checked={fica === "b"} onChange={() => setMantem({ ...mantem, [chave]: "b" })} />
                  <span>{par.b.nome}</span>
                </label>
              </fieldset>
              <div className="painel-acoes">
                <Button
                  variant="primary"
                  disabled={ocupado !== null}
                  onClick={() => void agir(chave, () => juntarIngredientes(quem.id, sai.id))}
                >
                  Juntar
                </Button>
                <Button disabled={ocupado !== null} onClick={() => void agir(chave, () => marcarDistintos(par.a.id, par.b.id))}>
                  São diferentes
                </Button>
              </div>
            </li>
          );
        })}
      </ul>
    </SidePanel>
  );
}

function casaIngrediente(consulta: string, i: IngredienteLinha): boolean {
  return casaBusca(consulta, [i.nome, ...(i.apelidos ?? []), ...(i.itens_nomes ?? []), ...(i.lotes_codigos ?? [])]);
}

function MenuDoLote({ item, acoes }: { item: string; acoes: { rotulo: string; onClick: () => void }[] }) {
  const [aberto, setAberto] = useState(false);
  const raiz = useRef<HTMLDivElement>(null);
  const botao = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!aberto) return;
    const fora = (event: MouseEvent) => {
      if (raiz.current && !raiz.current.contains(event.target as Node)) setAberto(false);
    };
    const tecla = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setAberto(false);
        botao.current?.focus();
      }
    };
    document.addEventListener("mousedown", fora);
    document.addEventListener("keydown", tecla);
    return () => {
      document.removeEventListener("mousedown", fora);
      document.removeEventListener("keydown", tecla);
    };
  }, [aberto]);

  if (acoes.length === 0) return <span className="travessao">—</span>;

  return (
    <div
      className="linha-menu"
      ref={raiz}
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setAberto(false);
      }}
    >
      <button
        ref={botao}
        type="button"
        className="menu-pontos"
        aria-label={`Ações de ${item}`}
        aria-haspopup="menu"
        aria-expanded={aberto}
        onClick={() => setAberto((v) => !v)}
      >
        <svg width="18" height="18" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
          <circle cx="4.5" cy="10" r="1.6" fill="currentColor" />
          <circle cx="10" cy="10" r="1.6" fill="currentColor" />
          <circle cx="15.5" cy="10" r="1.6" fill="currentColor" />
        </svg>
      </button>
      {aberto ? (
        <div className="linha-menu-lista" role="menu" aria-label={`Ações de ${item}`}>
          {acoes.map((acao) => (
            <button
              key={acao.rotulo}
              type="button"
              role="menuitem"
              onClick={() => {
                setAberto(false);
                acao.onClick();
              }}
            >
              {acao.rotulo}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function textoValidade(validade: string | null, semValidade: boolean): string {
  if (validade) return dataBr(validade);
  if (semValidade) return "sem validade";
  return "validade não informada";
}

/** Itens do ingrediente e, embaixo de cada um, os lotes. A tabela segue a da entrada. */
function LotesNoLugar({
  id,
  consulta,
  aoMudar,
}: {
  id: string;
  consulta: string;
  aoMudar: () => void;
}) {
  const { pode } = useGestao();
  const [dados, setDados] = useState<IngredienteDetalhe | null>(null);
  const [falhou, setFalhou] = useState(false);
  const [corrigindo, setCorrigindo] = useState<string | null>(null);
  const [trocando, setTrocando] = useState<{ id: string; nome: string; marca: string } | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    try {
      setDados(await detalheIngrediente(id));
      setFalhou(false);
    } catch {
      setFalhou(true);
    }
  }, [id]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  if (falhou) return <p role="alert">Não foi possível abrir os lotes agora.</p>;
  if (!dados) return <p>Carregando.</p>;

  const lotesDoItem = (itemId: string, nome: string) =>
    dados.lotes_detalhe.filter((l) => l.item_id === itemId || (!l.item_id && l.item === nome));

  return (
    <div className="linha-expandida" role="region" aria-label={`Lotes de ${dados.nome}`}>
      {dados.itens_detalhe.length === 0 ? <p className="sub">Nenhum item comprado ainda.</p> : null}
      {dados.itens_detalhe.length > 0 ? (
        <div className="linha-tabela-rola">
          <table className="linha-tabela lotes-ing">
            <colgroup>
              <col className="c-nome" />
              <col className="c-qtd" />
              <col className="c-val" />
              <col className="c-custo" />
              <col className="c-acoes" />
            </colgroup>
            <thead>
              <tr>
                <th>Item / Lote</th>
                <th className="num">Quantidade</th>
                <th>Validade</th>
                <th>Custo</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {dados.itens_detalhe.map((item) => {
                const lotes = lotesDoItem(item.id, item.nome);
                return (
                  <Fragment key={item.id}>
                    <tr className="lote-item">
                      <td colSpan={5}>
                        <strong>{item.nome}</strong>
                        {item.marca ? <span className="sub"> · {item.marca}</span> : null}
                      </td>
                    </tr>
                    {lotes.length === 0 ? (
                      <tr className="lote-linha">
                        <td colSpan={5} className="sub">
                          Nenhum lote.
                        </td>
                      </tr>
                    ) : null}
                    {lotes.map((l) => (
                      <tr key={l.id} className={casaLote(consulta, l.codigo) ? "lote-linha lote-destaque" : "lote-linha"}>
                        <td className="c-nome lote-codigo">
                          <strong>{l.codigo}</strong>
                        </td>
                        <td className="num c-qtd">{quantidadeBase(l.saldo, dados.unidade_base)}</td>
                        <td className="c-val">{textoValidade(l.validade, l.sem_validade)}</td>
                        <td className="c-custo">
                          <span>{custoDoLoteTexto(l.custo_unidade_base, dados.unidade_base)}</span>
                          {l.custo_corrigido ? (
                            <SeloCusto antes={l.custo_antes ?? null} depois={l.custo_depois ?? null} base={dados.unidade_base} />
                          ) : null}
                        </td>
                        <td className="c-acoes">
                          <MenuDoLote
                            item={l.codigo}
                            acoes={[
                              ...(pode("ajustar")
                                ? [{ rotulo: "Corrigir custo", onClick: () => { setCorrigindo(l.id); setTrocando(null); } }]
                                : []),
                              ...(pode("juntar")
                                ? [{
                                    rotulo: "Trocar ingrediente",
                                    onClick: () => {
                                      setTrocando({ id: item.id, nome: item.nome, marca: item.marca ?? "" });
                                      setCorrigindo(null);
                                    },
                                  }]
                                : []),
                            ]}
                          />
                        </td>
                      </tr>
                    ))}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}
      {erro ? (
        <p role="alert" className="form-erro">
          {erro}
        </p>
      ) : null}
      {corrigindo ? (
        <CorrigirCusto
          loteId={corrigindo}
          onCancelar={() => setCorrigindo(null)}
          onFeito={() => {
            setCorrigindo(null);
            void carregar();
            aoMudar();
          }}
        />
      ) : null}
      {trocando ? (
        <FormTrocar
          dados={dados}
          item={trocando}
          enviando={enviando}
          onCancelar={() => setTrocando(null)}
          onEnviar={(ingredienteId, motivo) => {
            setEnviando(true);
            setErro(null);
            void trocarIngrediente(trocando.id, { ingrediente_id: ingredienteId, motivo })
              .then(async () => {
                setTrocando(null);
                await carregar();
                aoMudar();
              })
              .catch((e: unknown) => setErro(textoDoErro(e)))
              .finally(() => setEnviando(false));
          }}
        />
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------- página

type Painel = { tipo: "ing"; id: string } | { tipo: "pares" } | null;

export function Ingredientes() {
  const { search, navegar, pode, atualizarFluxo, sessao } = useGestao();
  const filtro = filtroDaUrl(search);
  const categoria = categoriaDaUrl(search);
  const [novo, setNovo] = useState(false);
  const [dados, setDados] = useState<IngredientesLista | null>(null);
  const [todos, setTodos] = useState<IngredienteLinha[]>([]);
  const [falhou, setFalhou] = useState(false);
  const [painel, setPainel] = useState<Painel>(null);
  const [busca, setBusca] = useState("");
  const [abertas, setAbertas] = useState<Set<string>>(new Set());
  const ancora = useRef<HTMLTableRowElement | null>(null);
  const hoje = hojeNoFuso(sessao.fuso);

  const carregar = useCallback(async (f: FiltroIngredientes, cat = "") => {
    setFalhou(false);
    try {
      const resposta = await listarIngredientes(f, cat);
      setDados(resposta);
      if (f === "todos" && !cat) setTodos(resposta.ingredientes);
      else setTodos((await listarIngredientes("todos")).ingredientes);
    } catch (erro) {
      if (!(erro instanceof ApiError && erro.status === 401)) setFalhou(true);
    }
  }, []);

  useEffect(() => {
    void carregar(filtro, categoria);
  }, [carregar, filtro, categoria]);

  const consulta = busca.trim();
  const visiveis = (dados?.ingredientes ?? []).filter((i) => casaIngrediente(consulta, i));
  const primeira = visiveis[0]?.id ?? "";

  useEffect(() => {
    if (!consulta || !dados) return;
    setAbertas(new Set(dados.ingredientes.filter((i) => casaIngrediente(consulta, i)).map((i) => i.id)));
  }, [consulta, dados]);

  useEffect(() => {
    if (consulta) ancora.current?.scrollIntoView?.({ block: "nearest" });
  }, [consulta, primeira]);

  function mudou() {
    void carregar(filtro, categoria);
    atualizarFluxo();
  }

  const acoes = (
    <div className="acoes-cabecalho">
      {pode("lancar") ? (
        <Button variant="primary" onClick={() => navegar("/entradas?nova=1")}>
          Nova entrada
        </Button>
      ) : null}
      {pode("lancar") ? (
        <Button aria-expanded={novo} onClick={() => setNovo((v) => !v)}>
          Novo ingrediente
        </Button>
      ) : null}
    </div>
  );

  const pares = dados?.pares_parecidos ?? [];

  return (
    <main className="fluxo-pagina">
      <PageHeader title="Ingredientes" description="O que eu tenho?" actions={acoes} />
      <label className="gestao-field busca-lista">
        <span>Buscar item, ingrediente ou lote</span>
        <input
          type="search"
          value={busca}
          placeholder="Parte do nome ou do lote, como -12"
          onChange={(e) => setBusca(e.target.value)}
        />
      </label>
      <Chips
        rotulo="Filtrar ingredientes"
        opcoes={FILTROS}
        valor={filtro}
        onChange={(v) => navegar(urlDaLista(v, categoria), true)}
      />

      {dados && (dados.categorias ?? []).length > 0 ? (
        <label className="gestao-field filtro-categoria">
          <span>Categoria</span>
          <select value={categoria} onChange={(e) => navegar(urlDaLista(filtro, e.target.value), true)}>
            <option value="">Todas as categorias</option>
            {(dados.categorias ?? []).map((c) => (
              <option key={c.nome} value={c.nome}>
                {c.nome} ({c.total})
              </option>
            ))}
          </select>
        </label>
      ) : null}

      {novo && pode("lancar") ? (
        <NovoIngredienteBusca
          onFechar={() => setNovo(false)}
          onEscolhido={(ing, criado) => {
            setNovo(false);
            if (criado) mudou();
            setPainel({ tipo: "ing", id: ing.id });
          }}
        />
      ) : null}

      {pares.length > 0 ? (
        <div className="fluxo-aviso" role="status">
          <span>
            <strong>
              {pares.length} {pares.length === 1 ? "par parece" : "pares parecem"} o mesmo ingrediente.
            </strong>{" "}
            Com o saldo dividido, o sistema subestima o que você tem.
          </span>
          {pode("juntar") ? <Button onClick={() => setPainel({ tipo: "pares" })}>Juntar</Button> : null}
        </div>
      ) : null}

      {falhou ? (
        <Card className="fluxo-vazio">
          <p role="alert">Não foi possível carregar os ingredientes agora.</p>
          <Button onClick={() => void carregar(filtro, categoria)}>Tentar de novo</Button>
        </Card>
      ) : null}
      {!dados && !falhou ? <p className="fluxo-estado">Carregando os ingredientes.</p> : null}

      {dados && dados.ingredientes.length === 0 ? (
        <Card className="fluxo-vazio">
          <p>
            <strong>{filtro === "todos" && !categoria ? "Nenhum ingrediente ainda." : "Nenhum ingrediente neste filtro."}</strong>
          </p>
          <p>
            {filtro === "todos" && !categoria
              ? "Cadastre o primeiro em “Novo ingrediente”: a busca mostra antes o que já existe e sugere pelo catálogo."
              : "Troque o filtro para ver os outros."}
          </p>
        </Card>
      ) : null}

      {dados && dados.ingredientes.length > 0 && visiveis.length === 0 ? (
        <Card className="fluxo-vazio">
          <p>
            <strong>Nenhum ingrediente para “{consulta}”.</strong>
          </p>
          <p>Tente um pedaço do nome ou do lote, como -12.</p>
        </Card>
      ) : null}

      {visiveis.length > 0 ? (
        <Card className="fluxo-lista-card">
          <table className="lista-ingredientes" aria-label="Ingredientes">
            <colgroup>
              <col />
              <col className="c-saldo" />
              <col className="c-vence" />
              <col className="c-sit" />
            </colgroup>
            <thead>
              <tr>
                <th>Ingrediente</th>
                <th className="num">Saldo</th>
                <th>Vence primeiro</th>
                <th>Situação</th>
              </tr>
            </thead>
            <tbody>
              {visiveis.map((i, indice) => {
                const selos = selosDe(i, pares.some((p) => p.a.id === i.id || p.b.id === i.id));
                const aberta = abertas.has(i.id);
                return (
                  <Fragment key={i.id}>
                    <tr className="ing-linha" id={`ingrediente-${i.id}`} ref={indice === 0 ? ancora : undefined}>
                      <td className="col-ing">
                        <div className="nome-com-seta">
                          <button
                            type="button"
                            className="seta-nome"
                            aria-expanded={aberta}
                            aria-label={aberta ? `Recolher lotes de ${i.nome}` : `Mostrar lotes de ${i.nome}`}
                            onClick={() =>
                              setAbertas((atual) => {
                                const proxima = new Set(atual);
                                if (proxima.has(i.id)) proxima.delete(i.id);
                                else proxima.add(i.id);
                                return proxima;
                              })
                            }
                          >
                            <span aria-hidden="true">{aberta ? "▾" : "▸"}</span>
                          </button>
                          <button type="button" className="ing-nome" onClick={() => setPainel({ tipo: "ing", id: i.id })}>
                            <strong>{i.nome}</strong>
                            <span className="sub linha-secundaria">
                              {i.categoria}
                              <span className="contagem"> · {contagemDe(i)}</span>
                            </span>
                          </button>
                        </div>
                      </td>
                      <td className="num col-saldo">{quantidadeBase(i.saldo, i.unidade_base)}</td>
                      <td className="col-vence">
                        {i.vence_primeiro && i.saldo > 0 ? dataCurta(i.vence_primeiro) : <span className="sub">sem validade a vigiar</span>}
                      </td>
                      <td className="col-sit">
                        {selos.length === 0 ? (
                          <span className="travessao">—</span>
                        ) : (
                          selos.map((selo) => <StatusChip key={selo.rotulo} stage={selo.stage} label={selo.rotulo} />)
                        )}
                      </td>
                    </tr>
                    {aberta ? (
                      <tr className="ing-aberta">
                        <td colSpan={4}>
                          <LotesNoLugar id={i.id} consulta={consulta} aoMudar={mudou} />
                        </td>
                      </tr>
                    ) : null}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </Card>
      ) : null}

      {painel?.tipo === "ing" ? (
        <PainelIngrediente
          key={painel.id}
          id={painel.id}
          outros={todos}
          hoje={hoje}
          onFechar={() => setPainel(null)}
          onAbrir={(novoId) => setPainel({ tipo: "ing", id: novoId })}
          aoMudar={mudou}
        />
      ) : null}
      {painel?.tipo === "pares" ? (
        <PainelPares
          pares={pares}
          onFechar={() => setPainel(null)}
          aoMudar={() => {
            mudou();
          }}
        />
      ) : null}
    </main>
  );
}
