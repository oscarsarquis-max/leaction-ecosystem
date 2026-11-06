import { useCallback, useEffect, useState, type ReactNode } from "react";
import { useGestao } from "../contexto";
import {
  ApiError,
  buscarIngredientes,
  detalheReceita,
  listarReceitas,
  publicarReceita,
  salvarReceita,
  situacaoGigio,
  textoDoErro,
  type GigioSituacao,
  type AbaReceita,
  type FiltroReceitas,
  type ReceitaFicha,
  type ReceitaListaItem,
  type UnidadeReceita,
} from "../lib/api";
import { casaBusca } from "../lib/buscaLista";
import { dinheiro, quantidadeBase } from "../lib/format";
import { useTabela } from "../lib/useNarrow";
import { CampoIngrediente, type IngredienteEscolhido } from "../shell/CampoIngrediente";
import { Button } from "../shell/Button";
import { Card } from "../shell/Card";
import { Chips } from "../shell/Chips";
import { PageHeader } from "../shell/PageHeader";
import { SidePanel } from "../shell/SidePanel";
import { StatusChip } from "../shell/StatusChip";
import { PainelGigio } from "./GigioReceita";
import "./fluxo.css";

const FILTROS: { valor: FiltroReceitas; rotulo: string }[] = [
  { valor: "todas", rotulo: "Todas" },
  { valor: "rascunhos", rotulo: "Rascunhos" },
  { valor: "publicadas", rotulo: "Publicadas" },
  { valor: "custo_parcial", rotulo: "Custo parcial" },
];

const ABAS: { valor: AbaReceita; rotulo: string }[] = [
  { valor: "ingredientes", rotulo: "Ingredientes" },
  { valor: "modo", rotulo: "Modo de fazer" },
  { valor: "rendimento", rotulo: "Rendimento" },
  { valor: "revisar", rotulo: "Revisar" },
];

const UNIDADES: { valor: UnidadeReceita; rotulo: string }[] = [
  { valor: "g", rotulo: "g" },
  { valor: "kg", rotulo: "kg" },
  { valor: "ml", rotulo: "ml" },
  { valor: "l", rotulo: "l" },
  { valor: "un", rotulo: "un" },
];

const SELOS: Record<string, string> = {
  rascunho: "Rascunho",
  custo_parcial: "Custo parcial",
  sem_linhas: "Sem linhas",
};

const UNIDADE_TEXTO: Record<string, UnidadeReceita> = {
  g: "g",
  gr: "g",
  grama: "g",
  gramas: "g",
  kg: "kg",
  quilo: "kg",
  quilos: "kg",
  ml: "ml",
  mililitro: "ml",
  mililitros: "ml",
  l: "l",
  litro: "l",
  litros: "l",
  un: "un",
  unidade: "un",
  unidades: "un",
};

type LinhaUi = {
  chave: string;
  ingrediente: IngredienteEscolhido | null;
  texto: string;
  quantidade: string;
  unidade: UnidadeReceita;
  observacao: string;
  percentual: number | null;
  custo: number | null;
  origem: "manual" | "estimado" | "conferido";
  faixaMin: number | null;
  faixaMax: number | null;
  erro: string | null;
  obsAberta: boolean;
};

function chave() {
  return Math.random().toString(36).slice(2);
}

function linhaVazia(): LinhaUi {
  return {
    chave: chave(),
    ingrediente: null,
    texto: "",
    quantidade: "",
    unidade: "g",
    observacao: "",
    percentual: null,
    custo: null,
    origem: "manual",
    faixaMin: null,
    faixaMax: null,
    erro: null,
    obsAberta: false,
  };
}

function normalizar(texto: string): string {
  return texto
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function linhasDaFicha(ficha: ReceitaFicha): LinhaUi[] {
  const linhas = ficha.linhas.map((linha) => ({
    chave: linha.id,
    ingrediente: linha.ingrediente_id
      ? {
          id: linha.ingrediente_id,
          nome: linha.nome,
          categoria: linha.categoria ?? "",
          unidade_base: linha.unidade_base ?? "g",
        }
      : null,
    texto: linha.a_decidir ? linha.nome || linha.texto || "" : "",
    quantidade: linha.quantidade == null ? "" : String(linha.quantidade),
    unidade: linha.unidade,
    observacao: linha.observacao ?? "",
    percentual: linha.percentual_padeiro,
    custo: linha.custo,
    origem: linha.origem ?? "manual",
    faixaMin: linha.faixa_min,
    faixaMax: linha.faixa_max,
    erro: null,
    obsAberta: Boolean(linha.observacao),
  }));
  return linhas.length ? linhas : [linhaVazia()];
}

function filtroDaUrl(search: string): FiltroReceitas {
  const valor = new URLSearchParams(search).get("filtro");
  return FILTROS.some((f) => f.valor === valor) ? (valor as FiltroReceitas) : "todas";
}

function percento(valor: number | null): string {
  if (valor == null) return "—";
  return `${new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(valor)} %`;
}

function MenuLinha({
  n,
  onRemover,
  onObservacao,
  onConferir,
}: {
  n: number;
  onRemover: () => void;
  onObservacao: () => void;
  onConferir?: () => void;
}) {
  const [aberto, setAberto] = useState(false);
  return (
    <div className="linha-menu">
      <button
        type="button"
        className="icone-remover linha-menu-botao"
        aria-label={`Mais ações da linha ${n}`}
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
        <div className="linha-menu-lista" role="menu">
          <button type="button" role="menuitem" onClick={() => { setAberto(false); onObservacao(); }}>
            Observação
          </button>
          {onConferir ? (
            <button type="button" role="menuitem" onClick={() => { setAberto(false); onConferir(); }}>
              Marcar como conferido
            </button>
          ) : null}
          <button type="button" role="menuitem" className="perigo" onClick={() => { setAberto(false); onRemover(); }}>
            Remover
          </button>
        </div>
      ) : null}
    </div>
  );
}

export function Receitas() {
  const { search, navegar } = useGestao();
  const filtro = filtroDaUrl(search);
  const [dados, setDados] = useState<ReceitaListaItem[] | null>(null);
  const [falhou, setFalhou] = useState(false);
  const [busca, setBusca] = useState("");

  const carregar = useCallback(async (qual: FiltroReceitas) => {
    try {
      setDados((await listarReceitas(qual)).receitas);
      setFalhou(false);
    } catch {
      setFalhou(true);
    }
  }, []);

  useEffect(() => {
    void carregar(filtro);
  }, [carregar, filtro]);

  const consulta = busca.trim();
  const visiveis = (dados ?? []).filter((r) => casaBusca(consulta, [r.nome, r.rendimento]));

  return (
    <main className="fluxo-pagina">
      <PageHeader title="Receitas" description="Como eu faço?" />
      <label className="gestao-field busca-lista">
        <span>Buscar receita</span>
        <input type="search" value={busca} placeholder="Buscar receita" onChange={(e) => setBusca(e.target.value)} />
      </label>
      <Chips rotulo="Filtrar receitas" opcoes={FILTROS} valor={filtro} onChange={(v) => navegar(v === "todas" ? "/receitas" : `/receitas?filtro=${v}`)} />
      {falhou ? (
        <Card className="fluxo-vazio">
          <p role="alert">Não foi possível carregar as receitas agora.</p>
          <Button onClick={() => void carregar(filtro)}>Tentar de novo</Button>
        </Card>
      ) : null}
      {!dados && !falhou ? <p className="fluxo-estado">Carregando as receitas.</p> : null}
      {dados && dados.length === 0 ? (
        <Card className="fluxo-vazio">
          <p>
            <strong>{filtro === "todas" ? "Nenhum produto produzido ainda." : "Nenhuma receita neste filtro."}</strong>
          </p>
          {filtro === "todas" ? <Button variant="primary" onClick={() => navegar("/produtos")}>Ver produtos</Button> : null}
        </Card>
      ) : null}
      {visiveis.length > 0 ? (
        <Card className="fluxo-lista-card">
          <table className="lista-ingredientes" aria-label="Receitas">
            <thead>
              <tr>
                <th>Receita</th>
                <th>Rendimento</th>
                <th>Custo por unidade</th>
                <th>Situação</th>
              </tr>
            </thead>
            <tbody>
              {visiveis.map((r) => (
                <tr className="ing-linha" key={r.id}>
                  <td className="col-ing">
                    <button type="button" className="ing-nome" onClick={() => navegar(`/receitas/${r.produto_id}`)}>
                      <strong>{r.nome}</strong>
                    </button>
                  </td>
                  <td className="col-saldo">{r.rendimento ?? <span className="travessao">—</span>}</td>
                  <td className="col-meio">
                    {r.custo_parcial ? (
                      <span className="custo-parcial">
                        {r.custo_por_unidade == null ? "—" : `${dinheiro(r.custo_por_unidade)} parcial`}
                      </span>
                    ) : r.custo_por_unidade == null ? (
                      <span className="travessao">—</span>
                    ) : (
                      dinheiro(r.custo_por_unidade)
                    )}
                  </td>
                  <td className="col-sit">
                    {r.selos.length === 0 ? (
                      <span className="travessao">—</span>
                    ) : (
                      <span className="sels">
                        {r.selos.map((selo) => (
                          <StatusChip key={selo} stage="attention" label={SELOS[selo] ?? selo} />
                        ))}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ) : null}
    </main>
  );
}

export function EditorReceita({ produtoId }: { produtoId: string }) {
  const { navegar, definirTitulo, pode, atualizarFluxo } = useGestao();
  const tabela = useTabela();
  const [ficha, setFicha] = useState<ReceitaFicha | null>(null);
  const [linhas, setLinhas] = useState<LinhaUi[]>([linhaVazia()]);
  const [passos, setPassos] = useState<string[]>([""]);
  const [rendimento, setRendimento] = useState("");
  const [unidadeRend, setUnidadeRend] = useState<UnidadeReceita | "">("");
  const [peso, setPeso] = useState("");
  const [perda, setPerda] = useState("0");
  const [aba, setAba] = useState<AbaReceita>("ingredientes");
  const [erro, setErro] = useState<string | null>(null);
  const [falhou, setFalhou] = useState(false);
  const [gravando, setGravando] = useState(false);
  const [colando, setColando] = useState(false);
  const [gigioAberto, setGigioAberto] = useState(false);
  const [gigio, setGigio] = useState<GigioSituacao | null>(null);

  const aplicar = useCallback((nova: ReceitaFicha) => {
    setFicha(nova);
    setLinhas(linhasDaFicha(nova));
    setPassos(nova.modo_fazer.length ? nova.modo_fazer : [""]);
    setRendimento(nova.rendimento_quantidade == null ? "" : String(nova.rendimento_quantidade));
    setUnidadeRend(nova.rendimento_unidade ?? "");
    setPeso(nova.peso_unidade_g == null ? "" : String(nova.peso_unidade_g));
    setPerda(nova.perda_percentual == null ? "0" : String(nova.perda_percentual));
  }, []);

  useEffect(() => {
    let ativo = true;
    detalheReceita(produtoId)
      .then((nova) => {
        if (ativo) aplicar(nova);
      })
      .catch(() => {
        if (ativo) setFalhou(true);
      });
    return () => {
      ativo = false;
    };
  }, [produtoId, aplicar]);

  useEffect(() => {
    situacaoGigio().then(setGigio).catch(() => setGigio({ disponivel: false, motivo: "O Gigio ainda não está configurado nesta padaria.", usadas: 0, limite: 30 }));
  }, []);

  useEffect(() => {
    definirTitulo?.(ficha?.produto ?? null);
    return () => definirTitulo?.(null);
  }, [ficha?.produto, definirTitulo]);

  function corpo() {
    const enviadas = linhas.flatMap((linha) => {
      const quantidade = Number(String(linha.quantidade).replace(",", "."));
      if (!linha.ingrediente && !linha.texto.trim()) return [];
      if (!Number.isFinite(quantidade) || quantidade <= 0) return [];
      return [
        {
          ingrediente_id: linha.ingrediente?.id ?? null,
          texto: linha.ingrediente ? null : linha.texto.trim(),
          quantidade,
          unidade: linha.unidade,
          observacao: linha.observacao.trim() || null,
          origem: linha.origem,
          faixa_min: linha.faixaMin,
          faixa_max: linha.faixaMax,
        },
      ];
    });
    const qtd = rendimento.trim() ? Number(rendimento.replace(",", ".")) : null;
    return {
      linhas: enviadas,
      rendimento_quantidade: qtd != null && Number.isFinite(qtd) ? qtd : null,
      rendimento_unidade: unidadeRend || null,
      peso_unidade_g: peso.trim() ? Number(peso.replace(",", ".")) : null,
      perda_percentual: Number(perda.replace(",", ".")) || 0,
      modo_fazer: passos.map((p) => p.trim()).filter(Boolean),
    };
  }

  async function gravar(): Promise<ReceitaFicha | null> {
    setGravando(true);
    setErro(null);
    try {
      const nova = await salvarReceita(produtoId, corpo());
      aplicar(nova);
      atualizarFluxo();
      return nova;
    } catch (falha) {
      setErro(textoDoErro(falha));
      if (falha instanceof ApiError && falha.detalhe && typeof falha.detalhe === "object") {
        const indice = (falha.detalhe as { linha?: number }).linha;
        if (indice) {
          setLinhas((atuais) => {
            let vista = 0;
            return atuais.map((linha) => {
              const conta = Boolean(linha.ingrediente || linha.texto.trim());
              if (!conta) return linha;
              vista += 1;
              return vista === indice ? { ...linha, erro: textoDoErro(falha) } : linha;
            });
          });
        }
      }
      return null;
    } finally {
      setGravando(false);
    }
  }

  async function publicar() {
    const gravada = await gravar();
    if (!gravada) return;
    if (gravada.linhas.some((l) => l.a_decidir)) {
      setErro("Há linha a decidir. Escolha o ingrediente antes de publicar.");
      setAba("ingredientes");
      return;
    }
    setGravando(true);
    try {
      const nova = await publicarReceita(produtoId);
      aplicar(nova);
      atualizarFluxo();
    } catch (falha) {
      setErro(textoDoErro(falha));
    } finally {
      setGravando(false);
    }
  }

  async function colar(texto: string) {
    const pedacos = texto.split(/\r?\n/).map((l) => l.split("\t")).filter((c) => c.some((p) => p.trim()));
    const novas: LinhaUi[] = [];
    for (const colunas of pedacos) {
      const nome = (colunas[0] ?? "").trim();
      const quantidade = (colunas[1] ?? "").trim();
      const unidade = UNIDADE_TEXTO[normalizar(colunas[2] ?? "")] ?? null;
      if (!nome) continue;
      let ingrediente: IngredienteEscolhido | null = null;
      try {
        const busca = await buscarIngredientes(nome);
        const alvo = normalizar(nome);
        const achado = busca.da_padaria.find((i) => normalizar(i.nome) === alvo);
        if (achado) {
          ingrediente = { id: achado.id, nome: achado.nome, categoria: achado.categoria, unidade_base: achado.unidade_base };
        }
      } catch {
        ingrediente = null;
      }
      novas.push({
        ...linhaVazia(),
        ingrediente,
        texto: ingrediente ? "" : nome,
        quantidade,
        unidade: unidade ?? "g",
        erro: unidade ? null : "A unidade não é g, kg, ml, l ou un.",
      });
    }
    if (novas.length) setLinhas((atuais) => [...atuais.filter((l) => l.ingrediente || l.texto || l.quantidade), ...novas]);
    setColando(false);
  }

  const bloqueada =
    linhas.some((l) => (l.texto.trim() && !l.ingrediente) || l.erro) || !rendimento.trim() || !unidadeRend;
  const custo = ficha?.custo_por_unidade;

  function campos(linha: LinhaUi, n: number) {
    const caixa = (classe: string, miolo: ReactNode) =>
      tabela ? <td className={`celula ${classe}`}>{miolo}</td> : <div className={`campo ${classe}`}>{miolo}</div>;
    return (
      <>
        {caixa(
          "campo-ingrediente",
          <>
          {!tabela ? <span>Ingrediente</span> : null}
          <CampoIngrediente
            rotulo={`Ingrediente, linha ${n}`}
            valor={linha.ingrediente ? { nome: linha.ingrediente.nome, categoria: linha.ingrediente.categoria } : null}
            textoInicial={linha.texto}
            placeholder={linha.texto ? linha.texto : "Buscar ingrediente"}
            onEscolher={(ing) =>
              setLinhas((atuais) => atuais.map((l) => (l.chave === linha.chave ? { ...l, ingrediente: ing, texto: "", erro: null } : l)))
            }
            onTrocar={() =>
              setLinhas((atuais) => atuais.map((l) => (l.chave === linha.chave ? { ...l, ingrediente: null, erro: null } : l)))
            }
          />
          {linha.texto && !linha.ingrediente ? <small className="sub">a decidir</small> : null}
          {linha.origem === "estimado" ? (
            <small
              className="etiqueta-estimado"
              title={linha.faixaMin != null && linha.faixaMax != null ? `Faixa ${linha.faixaMin}–${linha.faixaMax} %` : "Estimado pelo Gigio"}
            >
              estimado
            </small>
          ) : null}
          </>,
        )}
        {caixa(
          "campo-qtd",
          <label>
            {!tabela ? <span>Quantidade</span> : null}
            <input
              type="text"
              inputMode="decimal"
              aria-label={`Quantidade, linha ${n}`}
              value={linha.quantidade}
              onChange={(e) =>
                setLinhas((atuais) =>
                  atuais.map((l) =>
                    l.chave === linha.chave
                      ? { ...l, quantidade: e.target.value, origem: l.origem === "estimado" ? "conferido" : l.origem }
                      : l,
                  ),
                )
              }
            />
          </label>,
        )}
        {caixa(
          "campo-unidade",
          <label>
            {!tabela ? <span>Unidade</span> : null}
            <select
              aria-label={`Unidade, linha ${n}`}
              value={linha.unidade}
              onChange={(e) =>
                setLinhas((atuais) =>
                  atuais.map((l) =>
                    l.chave === linha.chave
                      ? { ...l, unidade: e.target.value as UnidadeReceita, erro: null, origem: l.origem === "estimado" ? "conferido" : l.origem }
                      : l,
                  ),
                )
              }
            >
              {UNIDADES.map((u) => (
                <option key={u.valor} value={u.valor}>
                  {u.rotulo}
                </option>
              ))}
            </select>
          </label>,
        )}
        {caixa("campo-conteudo", <>{!tabela ? <span>% do padeiro</span> : null}<span>{percento(linha.percentual)}</span></>)}
        {caixa("campo-custo", <>{!tabela ? <span>Custo</span> : null}<span>{linha.custo == null ? "—" : dinheiro(linha.custo)}</span></>)}
        {caixa(
          "campo-remover",
          <MenuLinha
            n={n}
            onRemover={() => setLinhas((atuais) => atuais.filter((l) => l.chave !== linha.chave))}
            onObservacao={() => setLinhas((atuais) => atuais.map((l) => (l.chave === linha.chave ? { ...l, obsAberta: true } : l)))}
            onConferir={
              linha.origem === "estimado"
                ? () => setLinhas((atuais) => atuais.map((l) => (l.chave === linha.chave ? { ...l, origem: "conferido" } : l)))
                : undefined
            }
          />,
        )}
      </>
    );
  }

  return (
    <main className={aba === "ingredientes" ? "entrada-pagina" : "fluxo-pagina"}>
      <PageHeader title={ficha?.produto ?? "Receita"} description="Como eu faço?" />
      {falhou ? (
        <Card className="fluxo-vazio">
          <p role="alert">Não foi possível abrir esta receita.</p>
          <Button onClick={() => navegar("/receitas")}>Voltar para Receitas</Button>
        </Card>
      ) : null}
      {ficha ? (
        <>
          <Chips
            rotulo="Partes da receita"
            opcoes={ABAS}
            valor={aba}
            onChange={(v) => {
              void gravar().then((gravada) => {
                if (gravada) setAba(v);
              });
            }}
          />
          {aba === "ingredientes" ? (
            <Card className="entrada-grade-card">
              <div className="painel-acoes">
                <Button onClick={() => setLinhas((atuais) => [...atuais, linhaVazia()])}>Adicionar linha</Button>
                <Button onClick={() => setColando(true)}>Colar da planilha</Button>
                {pode("lancar") ? (
                  <Button className="botao-gigio" disabled={!gigio?.disponivel} onClick={() => setGigioAberto(true)}>
                    <img className="avatar-gigio" src="/avatar_gigio.png" alt="" width={20} height={20} />
                    Sugerir com o Gigio
                  </Button>
                ) : null}
              </div>
              {pode("lancar") && gigio && !gigio.disponivel ? <p className="sub">{gigio.motivo}</p> : null}
              {tabela ? (
                <div className="entrada-tabela-rolagem">
                  <table className="entrada-tabela tabela-receita" aria-label="Ingredientes da receita">
                    <thead>
                      <tr>
                        <th className="campo-ingrediente">Ingrediente</th>
                        <th className="campo-qtd">Quantidade</th>
                        <th className="campo-unidade">Unidade</th>
                        <th className="campo-conteudo">% do padeiro</th>
                        <th className="campo-custo">Custo</th>
                        <th className="campo-remover"><span className="so-leitor">Ações</span></th>
                      </tr>
                    </thead>
                    <tbody>
                      {linhas.map((linha, i) => (
                        <tr key={linha.chave}>
                          {campos(linha, i + 1)}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <ul className="entrada-grade" aria-label="Ingredientes da receita">
                  {linhas.map((linha, i) => (
                    <li key={linha.chave} className={`grade-linha${linha.texto && !linha.ingrediente ? " decidir" : ""}`}>
                      <div className="grade-campos">{campos(linha, i + 1)}</div>
                      {linha.erro ? <p className="form-erro">{linha.erro}</p> : null}
                      {linha.obsAberta ? (
                        <label className="gestao-field">
                          <span>Observação</span>
                          <input
                            type="text"
                            value={linha.observacao}
                            onChange={(e) =>
                              setLinhas((atuais) => atuais.map((l) => (l.chave === linha.chave ? { ...l, observacao: e.target.value } : l)))
                            }
                          />
                        </label>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
              <p className="entrada-dica">
                Dica: cole de uma planilha as colunas, nesta ordem: ingrediente, quantidade, unidade. O que não bater exatamente fica “a decidir”.
              </p>
            </Card>
          ) : null}
          {aba === "modo" ? (
            <Card>
              <ol className="pares">
                {passos.map((passo, i) => (
                  <li key={i} className="item-com-menu">
                    <span>{i + 1}</span>
                    <label className="gestao-field">
                      <span className="so-leitor">Etapa {i + 1}</span>
                      <input
                        type="text"
                        value={passo}
                        onChange={(e) => setPassos((atuais) => atuais.map((p, n) => (n === i ? e.target.value : p)))}
                      />
                    </label>
                    <Button disabled={i === 0} onClick={() => setPassos((atuais) => {
                      const copia = [...atuais];
                      [copia[i - 1], copia[i]] = [copia[i], copia[i - 1]];
                      return copia;
                    })}>Subir</Button>
                    <Button disabled={i === passos.length - 1} onClick={() => setPassos((atuais) => {
                      const copia = [...atuais];
                      [copia[i + 1], copia[i]] = [copia[i], copia[i + 1]];
                      return copia;
                    })}>Descer</Button>
                    <Button onClick={() => setPassos((atuais) => atuais.filter((_, n) => n !== i))}>Remover</Button>
                  </li>
                ))}
              </ol>
              <Button onClick={() => setPassos((atuais) => [...atuais, ""])}>Adicionar etapa</Button>
            </Card>
          ) : null}
          {aba === "rendimento" ? (
            <Card>
              <div className="entrada-cab-grid">
                <label className="gestao-field">
                  <span>Quantidade</span>
                  <input type="text" inputMode="decimal" value={rendimento} onChange={(e) => setRendimento(e.target.value)} />
                </label>
                <label className="gestao-field">
                  <span>Unidade</span>
                  <select value={unidadeRend} onChange={(e) => setUnidadeRend(e.target.value as UnidadeReceita | "")}>
                    <option value="">Escolha</option>
                    {UNIDADES.map((u) => (
                      <option key={u.valor} value={u.valor}>{u.rotulo}</option>
                    ))}
                  </select>
                </label>
                <label className="gestao-field">
                  <span>Peso da unidade (g)</span>
                  <input type="text" inputMode="decimal" value={peso} onChange={(e) => setPeso(e.target.value)} />
                </label>
                <label className="gestao-field">
                  <span>Perda (%)</span>
                  <input type="text" inputMode="decimal" value={perda} onChange={(e) => setPerda(e.target.value)} />
                </label>
              </div>
              <p className="entrada-dica">
                {ficha.custo_parcial
                  ? `Custo parcial, falta o custo de ${ficha.linhas_sem_custo} ${ficha.linhas_sem_custo === 1 ? "linha" : "linhas"}.`
                  : custo == null
                    ? "O custo por unidade aparece quando o rendimento e o custo das linhas estão completos."
                    : `${dinheiro(custo)} por unidade`}
              </p>
            </Card>
          ) : null}
          {aba === "revisar" ? (
            <Card>
              <dl className="painel-fatos">
                <div>
                  <dt>Linhas</dt>
                  <dd>{ficha.linhas.length}</dd>
                </div>
                <div>
                  <dt>Rendimento</dt>
                  <dd>{ficha.rendimento ?? "—"}</dd>
                </div>
                <div>
                  <dt>Custo por unidade</dt>
                  <dd>
                    {ficha.custo_parcial ? (
                      <span className="custo-parcial">
                        {custo == null ? "—" : `${dinheiro(custo)} parcial`}
                        {` · ${ficha.linhas_sem_custo} ${ficha.linhas_sem_custo === 1 ? "linha" : "linhas"} sem custo`}
                      </span>
                    ) : custo == null ? (
                      "—"
                    ) : (
                      dinheiro(custo)
                    )}
                  </dd>
                </div>
              </dl>
              {ficha.linhas.some((l) => l.a_decidir) ? <p className="form-erro">Há linha a decidir.</p> : null}
              {linhas.some((l) => l.origem === "estimado") ? (
                <p className="sub">
                  {linhas.filter((l) => l.origem === "estimado").length} linhas estimadas, ainda não conferidas.
                </p>
              ) : null}
              {erro ? <p role="alert" className="form-erro">{erro}</p> : null}
              {pode("lancar") ? (
                <Button variant="primary" disabled={bloqueada || gravando} onClick={() => void publicar()}>
                  {gravando ? "Publicando." : `Publicar versão ${ficha.versao}`}
                </Button>
              ) : null}
            </Card>
          ) : null}
        </>
      ) : null}
      {aba === "ingredientes" && ficha ? (
        <div className="entrada-rodape" role="region" aria-label="Resumo da receita">
          <p className="rodape-numeros">
            <span><strong>{linhas.filter((l) => l.ingrediente || l.texto).length}</strong> linhas</span>
            {linhas.some((l) => l.origem === "estimado") ? (
              <span>{linhas.filter((l) => l.origem === "estimado").length} estimadas</span>
            ) : null}
            <span>Massa {ficha.total_massa_g == null ? "—" : quantidadeBase(ficha.total_massa_g, "g")}</span>
            <span className="rodape-total">
              {ficha.custo_parcial ? (
                <span className="custo-parcial">
                  Parcial: {ficha.custo_total == null ? "—" : dinheiro(ficha.custo_total)}
                  {` · ${ficha.linhas_sem_custo} ${ficha.linhas_sem_custo === 1 ? "linha" : "linhas"} sem custo`}
                </span>
              ) : ficha.custo_total == null ? null : (
                <strong>{dinheiro(ficha.custo_total)}</strong>
              )}
            </span>
          </p>
          {erro ? <p role="alert" className="form-erro">{erro}</p> : null}
        </div>
      ) : null}
      {colando ? (
        <PainelColar onFechar={() => setColando(false)} onAdicionar={(texto) => void colar(texto)} />
      ) : null}
      {gigioAberto ? (
        <PainelGigio
          produtoId={produtoId}
          linhas={linhas
            .filter((l) => (l.ingrediente || l.texto) && Number(String(l.quantidade).replace(",", ".")) > 0)
            .map((l) => ({
              ingredienteId: l.ingrediente?.id ?? null,
              nome: l.ingrediente?.nome || l.texto,
              quantidade: l.quantidade,
              unidade: l.unidade,
            }))}
          rendimento={rendimento}
          unidade={unidadeRend}
          onFechar={() => setGigioAberto(false)}
          onAplicada={(nova) => {
            aplicar(nova);
            setGigioAberto(false);
            atualizarFluxo();
          }}
        />
      ) : null}
    </main>
  );
}

function PainelColar({ onFechar, onAdicionar }: { onFechar: () => void; onAdicionar: (texto: string) => void }) {
  const [texto, setTexto] = useState("");
  const quantas = texto.split("\n").filter((l) => l.trim()).length;
  return (
    <SidePanel
      titulo="Colar da planilha"
      subtitulo="Copie as células no Excel ou no Google Planilhas e cole aqui."
      onFechar={onFechar}
      rodape={
        <div className="painel-acoes">
          <Button onClick={onFechar}>Cancelar</Button>
          <Button variant="primary" disabled={quantas === 0} onClick={() => onAdicionar(texto)}>
            {quantas <= 1 ? "Adicionar a linha" : `Adicionar ${quantas} linhas`}
          </Button>
        </div>
      }
    >
      <label className="gestao-field">
        <span>Linhas copiadas</span>
        <textarea className="colar-texto" rows={8} value={texto} spellCheck={false} onChange={(e) => setTexto(e.target.value)} />
      </label>
      <p className="sub">As colunas, nesta ordem: ingrediente, quantidade, unidade. O que não bater exatamente fica “a decidir”.</p>
    </SidePanel>
  );
}
