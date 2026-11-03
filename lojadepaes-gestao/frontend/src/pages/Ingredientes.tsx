import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useGestao } from "../contexto";
import {
  ajustarSaldo,
  ApiError,
  criarIngrediente,
  detalheIngrediente,
  editarIngrediente,
  juntarIngredientes,
  listarIngredientes,
  marcarDistintos,
  textoDoErro,
  type FiltroIngredientes,
  type IngredienteDetalhe,
  type IngredienteLinha,
  type IngredientesLista,
  type ParecidoPar,
} from "../lib/api";
import { numero } from "../lib/entradaForm";
import { custoPorUnidade, dataBr, dataCurta, diasAte, quantidadeBase } from "../lib/format";
import { Button } from "../shell/Button";
import { Card } from "../shell/Card";
import { Chips } from "../shell/Chips";
import { PageHeader } from "../shell/PageHeader";
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

function estadoDe(i: IngredienteLinha): { stage: string; rotulo: string } {
  if (i.saldo <= 0) return { stage: "attention", rotulo: "Sem saldo" };
  if (i.vence_em_7_dias) return { stage: "warning", rotulo: "Vence em 7 dias" };
  return { stage: "ok", rotulo: "Em dia" };
}

/** Unidades em que a pessoa conta, e quanto cada uma vale na unidade base. */
function unidadesDeContagem(base: string): { valor: string; rotulo: string; fator: number }[] {
  if (base === "g") return [{ valor: "kg", rotulo: "kg", fator: 1000 }, { valor: "g", rotulo: "g", fator: 1 }];
  if (base === "ml") return [{ valor: "l", rotulo: "L", fator: 1000 }, { valor: "ml", rotulo: "ml", fator: 1 }];
  return [{ valor: "un", rotulo: "un", fator: 1 }];
}

const TIPO_MOVIMENTO: Record<string, string> = { entrada: "Entrada", ajuste: "Ajuste", juncao: "Junção" };

// ---------------------------------------------------------------- painel do ingrediente

type Modo = "ver" | "ajustar" | "editar" | "juntar";

function PainelIngrediente({
  id,
  outros,
  hoje,
  onFechar,
  aoMudar,
}: {
  id: string;
  outros: IngredienteLinha[];
  hoje: string;
  onFechar: () => void;
  aoMudar: () => void;
}) {
  const { pode } = useGestao();
  const [dados, setDados] = useState<IngredienteDetalhe | null>(null);
  const [falhou, setFalhou] = useState(false);
  const [modo, setModo] = useState<Modo>("ver");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

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
                      <span className="sub">
                        {" "}
                        · {l.item} · {l.local}
                      </span>
                      <span className="sub bloco">
                        {l.validade ? `${dataBr(l.validade)}, ${diasAte(hoje, l.validade)}` : l.sem_validade ? "sem validade" : "validade não informada"}
                      </span>
                    </span>
                    <span>{quantidadeBase(l.saldo, dados.unidade_base)}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section aria-labelledby="pi-hist" className="painel-secao">
            <h3 id="pi-hist">Histórico</h3>
            {dados.movimentos.length === 0 ? (
              <p className="sub">Nada movimentado.</p>
            ) : (
              <ul className="painel-lista historico">
                {dados.movimentos.map((m) => (
                  <li key={m.id}>
                    <span>
                      <strong>{TIPO_MOVIMENTO[m.tipo] ?? m.tipo}</strong>
                      <span className="sub bloco">
                        {dataCurta(m.quando.slice(0, 10))}
                        {m.lote ? ` · lote ${m.lote}` : ""}
                        {m.tipo === "juncao" && m.de && m.para ? ` · ${m.de} → ${m.para}` : ""}
                        {m.tipo === "ajuste" && m.motivo ? ` · ${m.motivo}` : ""}
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

function FormEditar({
  dados,
  enviando,
  onCancelar,
  onEnviar,
}: {
  dados: IngredienteDetalhe;
  enviando: boolean;
  onCancelar: () => void;
  onEnviar: (corpo: { nome?: string; unidade_base?: string }) => void;
}) {
  const [nome, setNome] = useState(dados.nome);
  const [base, setBase] = useState(dados.unidade_base);
  const movimentado = dados.movimentos.length > 0 || dados.itens_detalhe.length > 0;

  function enviar(event: FormEvent) {
    event.preventDefault();
    onEnviar({
      nome: nome.trim() !== dados.nome ? nome.trim() : undefined,
      unidade_base: base !== dados.unidade_base ? base : undefined,
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

function PainelNovo({ onFechar, onCriado }: { onFechar: () => void; onCriado: (id: string) => void }) {
  const [nome, setNome] = useState("");
  const [base, setBase] = useState("g");
  const [erro, setErro] = useState<string | null>(null);
  const [parecido, setParecido] = useState(false);
  const [enviando, setEnviando] = useState(false);

  async function criar(confirmar: boolean) {
    setEnviando(true);
    setErro(null);
    try {
      const criado = await criarIngrediente(nome.trim(), base, confirmar);
      onCriado(criado.id);
    } catch (falha) {
      setParecido(falha instanceof ApiError && falha.codigo === "ingrediente_parecido");
      setErro(textoDoErro(falha));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <SidePanel titulo="Novo ingrediente" subtitulo="Ele só ganha saldo quando chegar uma entrada." onFechar={onFechar}>
      <form
        className="painel-form"
        onSubmit={(event) => {
          event.preventDefault();
          void criar(false);
        }}
      >
        <label className="gestao-field">
          <span>Nome</span>
          <input type="text" value={nome} maxLength={120} onChange={(e) => setNome(e.target.value)} />
        </label>
        <label className="gestao-field">
          <span>Unidade base</span>
          <select value={base} onChange={(e) => setBase(e.target.value)}>
            {Object.entries(BASES).map(([valor, rotulo]) => (
              <option key={valor} value={valor}>
                {rotulo}
              </option>
            ))}
          </select>
        </label>
        {erro ? (
          <p role="alert" className="form-erro">
            {erro}
          </p>
        ) : null}
        <div className="painel-acoes">
          <Button type="submit" variant="primary" disabled={enviando || nome.trim().length === 0}>
            Criar ingrediente
          </Button>
          {parecido ? (
            <Button disabled={enviando} onClick={() => void criar(true)}>
              Criar mesmo assim
            </Button>
          ) : null}
          <Button onClick={onFechar}>Cancelar</Button>
        </div>
      </form>
    </SidePanel>
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

// ---------------------------------------------------------------- página

type Painel = { tipo: "ing"; id: string } | { tipo: "novo" } | { tipo: "pares" } | null;

export function Ingredientes() {
  const { search, navegar, pode, atualizarFluxo, sessao } = useGestao();
  const filtro = filtroDaUrl(search);
  const [dados, setDados] = useState<IngredientesLista | null>(null);
  const [todos, setTodos] = useState<IngredienteLinha[]>([]);
  const [falhou, setFalhou] = useState(false);
  const [painel, setPainel] = useState<Painel>(null);
  const hoje = hojeNoFuso(sessao.fuso);

  const carregar = useCallback(async (f: FiltroIngredientes) => {
    setFalhou(false);
    try {
      const resposta = await listarIngredientes(f);
      setDados(resposta);
      if (f === "todos") setTodos(resposta.ingredientes);
      else setTodos((await listarIngredientes("todos")).ingredientes);
    } catch (erro) {
      if (!(erro instanceof ApiError && erro.status === 401)) setFalhou(true);
    }
  }, []);

  useEffect(() => {
    void carregar(filtro);
  }, [carregar, filtro]);

  function mudou() {
    void carregar(filtro);
    atualizarFluxo();
  }

  const acoes = (
    <div className="acoes-cabecalho">
      {pode("lancar") ? (
        <Button variant="primary" onClick={() => navegar("/entradas?nova=1")}>
          Nova entrada
        </Button>
      ) : null}
      {pode("lancar") ? <Button onClick={() => setPainel({ tipo: "novo" })}>Novo ingrediente</Button> : null}
    </div>
  );

  const pares = dados?.pares_parecidos ?? [];

  return (
    <main className="fluxo-pagina">
      <PageHeader title="Ingredientes" description="O que eu tenho?" actions={acoes} />
      <Chips
        rotulo="Filtrar ingredientes"
        opcoes={FILTROS}
        valor={filtro}
        onChange={(v) => navegar(v === "todos" ? "/ingredientes" : `/ingredientes?filtro=${v}`, true)}
      />

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
          <Button onClick={() => void carregar(filtro)}>Tentar de novo</Button>
        </Card>
      ) : null}
      {!dados && !falhou ? <p className="fluxo-estado">Carregando os ingredientes.</p> : null}

      {dados && dados.ingredientes.length === 0 ? (
        <Card className="fluxo-vazio">
          <p>
            <strong>{filtro === "todos" ? "Nenhum ingrediente ainda." : "Nenhum ingrediente neste filtro."}</strong>
          </p>
          <p>
            {filtro === "todos"
              ? "Os ingredientes nascem das entradas. Lance a primeira para saber o que você tem."
              : "Troque o filtro para ver os outros."}
          </p>
        </Card>
      ) : null}

      {dados && dados.ingredientes.length > 0 ? (
        <Card className="fluxo-lista-card">
          <ul className="fluxo-linhas" aria-label="Ingredientes">
            {dados.ingredientes.map((i) => {
              const estado = estadoDe(i);
              return (
                <li key={i.id}>
                  <button type="button" className="fluxo-linha ingrediente-linha" onClick={() => setPainel({ tipo: "ing", id: i.id })}>
                    <span className="col-nome">
                      <strong>{i.nome}</strong>
                      <span className="sub">
                        {i.itens} {i.itens === 1 ? "item" : "itens"} · {i.lotes} {i.lotes === 1 ? "lote" : "lotes"}
                      </span>
                    </span>
                    <span className="col-num col-saldo">{quantidadeBase(i.saldo, i.unidade_base)}</span>
                    <span className="col-num col-vence">
                      {i.vence_primeiro && i.saldo > 0 ? (
                        <>
                          <span className="rotulo-mobile">Vence primeiro </span>
                          {dataCurta(i.vence_primeiro)}
                        </>
                      ) : (
                        <span className="sub">sem validade a vigiar</span>
                      )}
                    </span>
                    <span className="col-estado">
                      <StatusChip stage={estado.stage} label={estado.rotulo} />
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </Card>
      ) : null}

      {painel?.tipo === "ing" ? (
        <PainelIngrediente
          key={painel.id}
          id={painel.id}
          outros={todos}
          hoje={hoje}
          onFechar={() => setPainel(null)}
          aoMudar={mudou}
        />
      ) : null}
      {painel?.tipo === "novo" ? (
        <PainelNovo
          onFechar={() => setPainel(null)}
          onCriado={(id) => {
            mudou();
            setPainel({ tipo: "ing", id });
          }}
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
