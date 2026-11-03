import {
  Fragment,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type ClipboardEvent,
  type KeyboardEvent,
  type ReactNode,
} from "react";
import { useGestao } from "../contexto";
import {
  ApiError,
  carregarCatalogo,
  lancarEntrada,
  textoDoErro,
  verificarEntrada,
  type AnaliseLinha,
  type Catalogo,
  type EntradaEnvio,
} from "../lib/api";
import {
  CUSTO_POR,
  UNIDADES,
  controleDaUnidade,
  escolherIngrediente,
  linhaVazia,
  linhasDaColagem,
  novaChave,
  novaLinha,
  paraEnvio,
  reconhecer,
  rotuloItem,
  soltarItem,
  trocarIngrediente,
  usarItem,
  type LinhaForm,
} from "../lib/entradaForm";
import { dinheiro, MOTIVOS } from "../lib/format";
import { hojeNoFuso, useNarrow, useTabela } from "../lib/useNarrow";
import { Button } from "../shell/Button";
import { Card } from "../shell/Card";
import { CampoIngrediente, type IngredienteEscolhido } from "../shell/CampoIngrediente";
import { Chips } from "../shell/Chips";
import { PageHeader } from "../shell/PageHeader";
import { SidePanel } from "../shell/SidePanel";
import "./fluxo.css";

type Motivo = "contagem" | "compra_sem_nota" | "bonificacao" | "outro";
const OPCOES_MOTIVO: { valor: Motivo; rotulo: string }[] = (
  ["contagem", "compra_sem_nota", "bonificacao", "outro"] as Motivo[]
).map((valor) => ({ valor, rotulo: MOTIVOS[valor] }));

// Pendências que a própria linha já mostra (o aviso do item, o campo Ingrediente): não repetem em texto.
const CODIGOS_TRATADOS = new Set(["item_parecido", "item_ja_existe", "sem_ingrediente"]);

/** As colunas, na ordem da tela e da colagem da planilha. */
type Coluna = "item" | "ingrediente" | "marca" | "qtd" | "unidade" | "conteudo" | "lote" | "validade" | "custo";

type Situacao = "decidir" | "incompleto" | "validade";

function chaveDeEnvio(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
}

function semValidadeEmAberto(a: AnaliseLinha | undefined): boolean {
  return Boolean(a?.pendencias.some((p) => p.codigo === "validade_nao_informada"));
}

/** Em que coluna a pessoa precisa mexer para resolver a situação da linha. */
function colunaDaSituacao(situacao: Situacao, a: AnaliseLinha): Coluna {
  if (situacao === "validade") return "validade";
  const codigos = a.pendencias.filter((p) => p.bloqueia).map((p) => p.codigo);
  if (situacao === "decidir") return codigos.includes("item_parecido") ? "item" : "ingrediente";
  const primeiro = codigos.find((c) => !["item_parecido", "sem_ingrediente"].includes(c)) ?? "";
  if (primeiro.startsWith("ingrediente")) return "ingrediente";
  if (primeiro === "sem_controle" || primeiro.startsWith("unidade")) return "unidade";
  if (primeiro === "embalagem_sem_conteudo") return "conteudo";
  if (primeiro === "quantidade_invalida") return "qtd";
  if (primeiro === "custo_invalido") return "custo";
  if (primeiro === "validade_conflito") return "validade";
  if (primeiro === "lote_conflito") return "lote";
  return "item";
}

function resumo(l: LinhaForm, a: AnaliseLinha | undefined): { texto: string; tom: "ok" | "decidir" | "incompleto" | "vazio" } {
  if (linhaVazia(l)) return { texto: "linha vazia", tom: "vazio" };
  if (!a) return { texto: "conferindo", tom: "vazio" };
  if (a.a_decidir) return { texto: "a decidir", tom: "decidir" };
  if (a.incompleta) return { texto: "incompleto", tom: "incompleto" };
  if (semValidadeEmAberto(a)) return { texto: "sem validade", tom: "ok" };
  return { texto: "ok", tom: "ok" };
}

// ---------------------------------------------------------------- menu da linha (⋯)

function MenuDaLinha({ n, onDuplicar, onRemover, podeRemover }: { n: number; onDuplicar: () => void; onRemover: () => void; podeRemover: boolean }) {
  const [aberto, setAberto] = useState(false);
  const raiz = useRef<HTMLDivElement>(null);
  const botao = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!aberto) return;
    const fora = (event: MouseEvent) => {
      if (raiz.current && !raiz.current.contains(event.target as Node)) setAberto(false);
    };
    const tecla = (event: globalThis.KeyboardEvent) => {
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
        className="icone-remover linha-menu-botao"
        aria-label={`Mais ações da linha ${n}`}
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
        <div className="linha-menu-lista" role="menu" aria-label={`Ações da linha ${n}`}>
          <button
            type="button"
            role="menuitem"
            aria-label={`Duplicar a linha ${n}`}
            onClick={() => {
              setAberto(false);
              onDuplicar();
            }}
          >
            Duplicar
          </button>
          <button
            type="button"
            role="menuitem"
            className="perigo"
            aria-label={`Remover a linha ${n}`}
            disabled={!podeRemover}
            onClick={() => {
              setAberto(false);
              onRemover();
            }}
          >
            Remover
          </button>
        </div>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------- uma linha

type LinhaProps = {
  linha: LinhaForm;
  indice: number;
  analise: AnaliseLinha | undefined;
  catalogo: Catalogo | null;
  narrow: boolean;
  tabela: boolean;
  aberta: boolean;
  podeRemover: boolean;
  onAbrir: () => void;
  onMudar: (mudar: (l: LinhaForm) => LinhaForm) => void;
  onRemover: () => void;
  onDuplicar: () => void;
  onProxima: () => void;
  /** Um ingrediente acabou de ser cadastrado pelo campo: a lista da tela passa a conhecê-lo. */
  onIngredienteCriado: (ingrediente: IngredienteEscolhido) => void;
};

function LinhaDaEntrada({
  linha,
  indice,
  analise,
  catalogo,
  narrow,
  tabela,
  aberta,
  podeRemover,
  onAbrir,
  onMudar,
  onRemover,
  onDuplicar,
  onProxima,
  onIngredienteCriado,
}: LinhaProps) {
  const n = indice + 1;
  const item = linha.itemId ? catalogo?.itens.find((i) => i.id === linha.itemId) : undefined;
  const travada = Boolean(item);
  const controle = item ? item.unidade_controle : controleDaUnidade(linha.unidade);
  const emb = controle === "embalagem";
  const unidades = item ? UNIDADES.filter((u) => u.controle === item.unidade_controle) : UNIDADES;
  const estado = resumo(linha, analise);

  const mudar = (patch: Partial<LinhaForm>) => onMudar((l) => ({ ...l, ...patch }));
  const celula = (coluna: Coluna) => ({ "data-celula": `${linha.chave}:${coluna}` });

  // Quem está digitando não pode ser interrompido: o nome só é reconhecido ao escolher da lista ou ao sair do campo.
  const digitando = (e: ChangeEvent<HTMLInputElement>) =>
    /^(insertText|insertFromPaste|insertFromDrop|delete|history)/.test((e.nativeEvent as InputEvent).inputType ?? "");
  const aoDigitarItem = (e: ChangeEvent<HTMLInputElement>) => {
    const texto = e.target.value;
    const soTexto = digitando(e);
    onMudar((l) => {
      const base = { ...(l.itemId ? soltarItem(l) : l), itemTexto: texto, decisaoItem: null };
      return soTexto ? base : reconhecer(base, catalogo);
    });
  };
  const reconhecerAoSair = () => onMudar((l) => reconhecer(l, catalogo));

  // Enter na última coluna segue para a linha de baixo, como numa planilha.
  const aoTeclarCusto = (e: KeyboardEvent<HTMLInputElement>) => {
    if (!tabela || e.key !== "Enter" || e.nativeEvent.isComposing) return;
    e.preventDefault();
    onProxima();
  };

  const rotuloCampo = (texto: string) => <span className="campo-rotulo">{texto}</span>;

  /** No celular e no tablet cada campo leva o rótulo; na tabela o rótulo é o cabeçalho fixo. */
  const campo = (cls: string, rotulo: string, filhos: ReactNode, comoDiv = false) => {
    if (tabela) {
      return (
        <td key={cls} className={`celula ${cls}`}>
          {filhos}
        </td>
      );
    }
    const dentro = (
      <>
        {rotuloCampo(rotulo)}
        {filhos}
      </>
    );
    return comoDiv ? (
      <div key={cls} className={`campo ${cls}`}>
        {dentro}
      </div>
    ) : (
      <label key={cls} className={`campo ${cls}`}>
        {dentro}
      </label>
    );
  };

  const placeholderCusto = controle ? CUSTO_POR[controle] : "R$";
  const custoCurto = controle === "massa" ? "R$/kg" : controle === "volume" ? "R$/L" : controle === "embalagem" ? "R$/emb." : "R$";

  const campos = [
    campo(
      "campo-item",
      "Item como comprado",
      <input
        type="text"
        list="entrada-itens"
        value={linha.itemTexto}
        autoComplete="off"
        aria-label={`Item como comprado, linha ${n}`}
        placeholder="Ex.: Farinha de trigo 25 kg"
        {...celula("item")}
        onChange={aoDigitarItem}
        onBlur={reconhecerAoSair}
      />,
    ),
    campo(
      "campo-ingrediente",
      "Ingrediente",
      <CampoIngrediente
        rotulo={`Ingrediente, linha ${n}`}
        valor={linha.ingredienteId ? { nome: linha.ingredienteTexto, categoria: linha.ingredienteCategoria } : null}
        travado={travada}
        textoInicial={linha.ingredienteId ? "" : linha.ingredienteTexto}
        item={linha.itemId ? "" : linha.itemTexto}
        marca={linha.marca}
        celula={celula("ingrediente")}
        onEscolher={(ing, criado) => {
          onMudar((l) => escolherIngrediente(l, ing));
          if (criado) onIngredienteCriado(ing);
        }}
        onTrocar={() => onMudar((l) => trocarIngrediente(l))}
      />,
      true,
    ),
    campo(
      "campo-marca",
      "Marca",
      <input
        type="text"
        value={linha.marca}
        autoComplete="off"
        readOnly={travada}
        aria-label={`Marca, linha ${n}`}
        {...celula("marca")}
        onChange={(e) => onMudar((l) => ({ ...l, marca: e.target.value }))}
        onBlur={reconhecerAoSair}
      />,
    ),
    campo(
      "campo-qtd",
      "Quantidade",
      <input
        type="text"
        inputMode="decimal"
        value={linha.quantidade}
        aria-label={`Quantidade, linha ${n}`}
        {...celula("qtd")}
        onChange={(e) => mudar({ quantidade: e.target.value })}
      />,
    ),
    campo(
      "campo-unidade",
      "Unidade",
      <select
        value={linha.unidade}
        aria-label={`Unidade, linha ${n}`}
        {...celula("unidade")}
        onChange={(e) => mudar({ unidade: e.target.value })}
      >
        <option value="">escolha</option>
        {unidades.map((u) => (
          <option key={u.valor} value={u.valor}>
            {tabela && u.valor === "emb" ? "emb." : u.rotulo}
          </option>
        ))}
      </select>,
    ),
    campo(
      "campo-conteudo",
      "Conteúdo da embalagem",
      <div className="campo-duplo">
        <input
          type="text"
          inputMode="decimal"
          value={emb ? linha.conteudo : ""}
          disabled={!emb}
          readOnly={travada}
          aria-label={`Conteúdo da embalagem, linha ${n}`}
          placeholder={emb ? "quanto vem" : "—"}
          {...celula("conteudo")}
          onChange={(e) => mudar({ conteudo: e.target.value })}
        />
        {emb ? (
          <select
            value={linha.ingredienteBase}
            disabled
            aria-label={`Unidade do conteúdo, linha ${n}`}
            title="A unidade vem do ingrediente"
          >
            <option value="">un.</option>
            <option value="g">g</option>
            <option value="ml">ml</option>
            <option value="un">un</option>
          </select>
        ) : null}
      </div>,
      true,
    ),
    campo(
      "campo-lote",
      "Lote",
      <input
        type="text"
        value={linha.lote}
        autoComplete="off"
        placeholder={tabela ? "auto" : "automático"}
        aria-label={`Lote, linha ${n}`}
        {...celula("lote")}
        onChange={(e) => mudar({ lote: e.target.value })}
      />,
    ),
    campo(
      "campo-validade",
      "Validade",
      <div className={tabela ? "validade-dupla" : "validade-grade"}>
        {tabela && linha.semValidade ? (
          <input type="text" disabled value="sem validade" aria-label={`Validade, linha ${n}`} readOnly {...celula("validade")} />
        ) : (
          <input
            type="date"
            value={linha.semValidade ? "" : linha.validade}
            disabled={linha.semValidade}
            aria-label={`Validade, linha ${n}`}
            {...celula("validade")}
            onChange={(e) => mudar({ validade: e.target.value })}
          />
        )}
        <label className="campo-check" title="Sem validade">
          <input
            type="checkbox"
            checked={linha.semValidade}
            aria-label={tabela ? `Sem validade, linha ${n}` : undefined}
            onChange={(e) => mudar({ semValidade: e.target.checked, validade: e.target.checked ? "" : linha.validade })}
          />
          {tabela ? null : <span>sem validade</span>}
        </label>
      </div>,
      true,
    ),
    campo(
      "campo-custo",
      controle ? CUSTO_POR[controle] : "Custo",
      <input
        type="text"
        inputMode="decimal"
        value={linha.custo}
        placeholder={tabela ? custoCurto : placeholderCusto}
        aria-label={`Custo ${controle ? CUSTO_POR[controle] : "em reais"}, linha ${n}`}
        {...celula("custo")}
        onChange={(e) => mudar({ custo: e.target.value })}
        onKeyDown={aoTeclarCusto}
      />,
    ),
  ];

  const remover = tabela ? (
    <td key="campo-remover" className="celula campo-remover">
      <MenuDaLinha n={n} onDuplicar={onDuplicar} onRemover={onRemover} podeRemover={podeRemover} />
    </td>
  ) : (
    <div key="campo-remover" className="campo campo-remover">
      <button type="button" className="icone-remover" aria-label={`Remover a linha ${n}`} onClick={onRemover}>
        <svg width="18" height="18" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
          <path d="M5 5l10 10M15 5 5 15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
      </button>
    </div>
  );

  const avisos: ReactNode[] = [];
  if (analise) {
    const itemParecido = analise.item_parecidos[0];
    if (itemParecido && linha.decisaoItem !== "novo" && !linha.itemId) {
      avisos.push(
        <div key="ip" className="aviso-linha decidir" role="group" aria-label={`Item parecido, linha ${n}`}>
          <span>
            <strong>Parecido com</strong> “{rotuloItem(itemParecido.nome, itemParecido.marca)}”.
          </span>
          <span className="aviso-acoes">
            <Button onClick={() => onMudar((l) => usarItem(l, itemParecido.id, catalogo))}>Usar este</Button>
            <Button onClick={() => mudar({ decisaoItem: "novo" })}>Criar novo</Button>
          </span>
        </div>,
      );
    }
    if (analise.item_parecidos.length > 0 && linha.decisaoItem === "novo") {
      avisos.push(
        <div key="ipn" className="aviso-linha decidido">
          <span>Vai criar um item novo, mesmo parecido com “{analise.item_parecidos[0].nome}”.</span>
          <Button onClick={() => mudar({ decisaoItem: null })}>Desfazer</Button>
        </div>,
      );
    }
    if (analise.item_igual) {
      const igual = analise.item_igual;
      avisos.push(
        <div key="ii" className="aviso-linha decidir">
          <span>
            Já existe o item “{rotuloItem(igual.nome, igual.marca)}”.
          </span>
          <Button onClick={() => onMudar((l) => usarItem(l, igual.id, catalogo))}>Usar este</Button>
        </div>,
      );
    }
    analise.pendencias
      .filter((p) => !CODIGOS_TRATADOS.has(p.codigo))
      .forEach((p) =>
        avisos.push(
          <p key={p.codigo} className={p.bloqueia ? "aviso-linha pendencia" : "aviso-linha atencao"} role={p.bloqueia ? "alert" : undefined}>
            {p.mensagem}
          </p>,
        ),
      );
  }

  if (tabela) {
    return (
      <tbody className={`grade-tabela-linha ${estado.tom}`} data-linha={linha.chave} aria-label={`Item ${n}`}>
        <tr className="linha-dados">
          {campos}
          {remover}
        </tr>
        {avisos.length > 0 ? (
          <tr className="linha-avisos">
            <td colSpan={10}>
              <div className="grade-avisos">{avisos}</div>
            </td>
          </tr>
        ) : null}
      </tbody>
    );
  }

  if (narrow) {
    return (
      <li className={`grade-linha compacta ${estado.tom}`} role="group" aria-label={`Item ${n}`} data-linha={linha.chave}>
        <button type="button" className="compacta-resumo" aria-expanded={aberta} onClick={onAbrir}>
          <span className="compacta-n">{n}</span>
          <span className="compacta-txt">
            <strong>{linha.itemTexto.trim() || "Item sem nome"}</strong>
            <span>
              {linha.quantidade || "?"} {UNIDADES.find((u) => u.valor === linha.unidade)?.rotulo ?? ""}
            </span>
          </span>
          <span className={`compacta-estado ${estado.tom}`}>{estado.texto}</span>
        </button>
        {aberta ? (
          <div className="compacta-campos">
            {campos}
            {remover}
          </div>
        ) : null}
        {avisos.length > 0 ? <div className="grade-avisos">{avisos}</div> : null}
      </li>
    );
  }

  return (
    <li className={`grade-linha ${estado.tom}`} role="group" aria-label={`Item ${n}`} data-linha={linha.chave}>
      <div className="grade-campos">
        {campos}
        {remover}
      </div>
      {avisos.length > 0 ? <div className="grade-avisos">{avisos}</div> : null}
    </li>
  );
}

// ---------------------------------------------------------------- colar da planilha

function PainelColar({ onFechar, onAdicionar }: { onFechar: () => void; onAdicionar: (texto: string) => boolean }) {
  const [texto, setTexto] = useState("");
  const [vazio, setVazio] = useState(false);
  const quantas = texto.split("\n").filter((l) => l.trim()).length;

  return (
    <SidePanel
      titulo="Colar da planilha"
      subtitulo="Copie as células no Excel ou no Google Planilhas e cole aqui."
      onFechar={onFechar}
      rodape={
        <div className="painel-acoes">
          <Button onClick={onFechar}>Cancelar</Button>
          <Button
            variant="primary"
            disabled={quantas === 0}
            onClick={() => {
              if (onAdicionar(texto)) onFechar();
              else setVazio(true);
            }}
          >
            {quantas <= 1 ? "Adicionar a linha" : `Adicionar ${quantas} linhas`}
          </Button>
        </div>
      }
    >
      <label className="gestao-field">
        <span>Linhas copiadas</span>
        <textarea
          className="colar-texto"
          rows={10}
          value={texto}
          spellCheck={false}
          placeholder="Cole aqui. Uma linha da planilha vira um item."
          onChange={(e) => {
            setTexto(e.target.value);
            setVazio(false);
          }}
        />
      </label>
      <p className="sub">
        As colunas, nesta ordem: item, ingrediente, marca, quantidade, unidade, conteúdo, lote, validade, custo. Nada é
        gravado ainda: as linhas entram na tela para você conferir.
      </p>
      <p className="sub">
        O ingrediente só liga sozinho quando o nome (ou um apelido) é igual a um que você já tem. Senão a linha fica “a
        decidir”, com as sugestões abertas. Colar nunca cria ingrediente.
      </p>
      {vazio ? (
        <p role="alert" className="form-erro">
          Não encontrei linhas para adicionar.
        </p>
      ) : null}
    </SidePanel>
  );
}

// ---------------------------------------------------------------- contador do rodapé

function Contador({ n, rotulo, tom, onIr }: { n: number; rotulo: string; tom?: string; onIr?: () => void }) {
  const dentro = (
    <>
      <strong>{n}</strong> {rotulo}
    </>
  );
  if (n > 0 && onIr) {
    return (
      <button type="button" className={`contador ${tom ?? ""}`} title="Ir para a primeira linha" onClick={onIr}>
        {dentro}
      </button>
    );
  }
  return <span>{dentro}</span>;
}

// ---------------------------------------------------------------- a tela

export function EntradaSemNota() {
  const { sessao, navegar, atualizarFluxo, pode } = useGestao();
  const narrow = useNarrow();
  const larga = useTabela();
  const tabela = larga && !narrow;
  const [catalogo, setCatalogo] = useState<Catalogo | null>(null);
  const [falhouCatalogo, setFalhouCatalogo] = useState(false);
  const [motivo, setMotivo] = useState<Motivo | "">("");
  const [detalhe, setDetalhe] = useState("");
  const [fornecedor, setFornecedor] = useState("");
  const [data, setData] = useState(() => hojeNoFuso(sessao.fuso));
  const [localId, setLocalId] = useState("");
  const [linhas, setLinhas] = useState<LinhaForm[]>(() => [novaLinha(), novaLinha(), novaLinha()]);
  const [analises, setAnalises] = useState<Record<string, AnaliseLinha>>({});
  const [conferindo, setConferindo] = useState(false);
  const [abertaNoCelular, setAbertaNoCelular] = useState<string | null>(() => linhas[0]?.chave ?? null);
  const [erro, setErro] = useState<string | null>(null);
  const [gravando, setGravando] = useState(false);
  const [colando, setColando] = useState(false);
  const [foco, setFoco] = useState<{ chave: string; coluna: Coluna; centro: boolean; vez: number } | null>(null);
  const chaveIdem = useRef(chaveDeEnvio());
  const pedido = useRef(0);

  useEffect(() => {
    let ativo = true;
    carregarCatalogo()
      .then((c) => {
        if (!ativo) return;
        setCatalogo(c);
        setLocalId((atual) => atual || (c.locais.find((l) => l.padrao) ?? c.locais[0])?.id || "");
      })
      .catch(() => ativo && setFalhouCatalogo(true));
    return () => {
      ativo = false;
    };
  }, []);

  // Leva o foco (e a rolagem) até uma célula depois que a tela já mudou.
  useEffect(() => {
    if (!foco) return;
    const alvo = document.querySelector<HTMLElement>(`[data-celula="${foco.chave}:${foco.coluna}"]`);
    if (!alvo) return;
    alvo.focus();
    alvo.scrollIntoView?.({ block: foco.centro ? "center" : "nearest" });
  }, [foco]);

  const pedirFoco = useCallback((chave: string, coluna: Coluna, centro = false) => {
    setAbertaNoCelular(chave);
    setFoco((atual) => ({ chave, coluna, centro, vez: (atual?.vez ?? 0) + 1 }));
  }, []);

  // Sempre sobra uma linha vazia no fim, como numa planilha.
  const atualizarLinhas = useCallback((fn: (atual: LinhaForm[]) => LinhaForm[]) => {
    setLinhas((atual) => {
      const novo = fn(atual);
      const ultima = novo[novo.length - 1];
      return !ultima || !linhaVazia(ultima) ? [...novo, novaLinha()] : novo;
    });
  }, []);

  const mudarLinha = (chave: string, fn: (l: LinhaForm) => LinhaForm) =>
    atualizarLinhas((atual) => atual.map((l) => (l.chave === chave ? fn(l) : l)));

  const preenchidas = useMemo(() => linhas.filter((l) => !linhaVazia(l)), [linhas]);

  // Confere no servidor (a mesma análise da gravação): parecidos, pendências, totais.
  useEffect(() => {
    if (!catalogo) return;
    if (preenchidas.length === 0) {
      setAnalises({});
      setConferindo(false);
      return;
    }
    setConferindo(true);
    const meu = ++pedido.current;
    const espera = setTimeout(() => {
      verificarEntrada(preenchidas.map((l) => paraEnvio(l, catalogo)))
        .then((resultado) => {
          if (meu !== pedido.current) return;
          const mapa: Record<string, AnaliseLinha> = {};
          preenchidas.forEach((l, i) => {
            mapa[l.chave] = resultado[i];
          });
          setAnalises(mapa);
          setConferindo(false);
          setErro(null);
        })
        .catch((falha) => {
          if (meu !== pedido.current) return;
          setConferindo(false);
          if (!(falha instanceof ApiError && falha.status === 401)) {
            setErro(textoDoErro(falha, "Não consegui conferir as linhas agora."));
          }
        });
    }, 350);
    return () => clearTimeout(espera);
  }, [preenchidas, catalogo]);

  function ingredienteCriado(i: IngredienteEscolhido) {
    setCatalogo((c) =>
      c && !c.ingredientes.some((x) => x.id === i.id)
        ? { ...c, ingredientes: [...c.ingredientes, { id: i.id, nome: i.nome, unidade_base: i.unidade_base, categoria: i.categoria, apelidos: [] }] }
        : c,
    );
  }

  function adicionarTexto(texto: string): boolean {
    const novas = linhasDaColagem(texto, catalogo);
    if (novas.length === 0) return false;
    atualizarLinhas((atual) => [...atual.filter((l) => !linhaVazia(l)), ...novas]);
    return true;
  }

  function colar(event: ClipboardEvent<HTMLElement>) {
    const texto = event.clipboardData.getData("text");
    if (!texto.includes("\t") && !texto.trim().includes("\n")) return;
    event.preventDefault();
    adicionarTexto(texto);
  }

  function irParaProxima(chave: string) {
    const i = linhas.findIndex((l) => l.chave === chave);
    const proxima = linhas[i + 1];
    if (proxima) {
      pedirFoco(proxima.chave, "item");
      return;
    }
    const nova = novaLinha();
    setLinhas((atual) => [...atual, nova]);
    pedirFoco(nova.chave, "item");
  }

  function duplicar(chave: string) {
    const nova = novaChave();
    atualizarLinhas((atual) => {
      const i = atual.findIndex((l) => l.chave === chave);
      if (i < 0) return atual;
      // O lote não se repete: a cópia serve para o próximo lote do mesmo item.
      const copia: LinhaForm = { ...atual[i], chave: nova, lote: "" };
      return [...atual.slice(0, i + 1), copia, ...atual.slice(i + 1)];
    });
    pedirFoco(nova, "item");
  }

  function remover(chave: string) {
    const i = linhas.findIndex((l) => l.chave === chave);
    const vizinha = linhas[i + 1] ?? linhas[i - 1];
    atualizarLinhas((atual) => (atual.length > 1 ? atual.filter((l) => l.chave !== chave) : atual));
    if (vizinha) pedirFoco(vizinha.chave, "item");
  }

  const itens = preenchidas.length;
  const analisadas = preenchidas.map((l) => analises[l.chave]).filter(Boolean);
  const aDecidir = analisadas.filter((a) => a.a_decidir).length;
  const incompletos = analisadas.filter((a) => a.incompleta).length;
  const semValidade = analisadas.filter(semValidadeEmAberto).length;
  const comValor = analisadas.filter((a) => a.valor_total !== null);
  const semCusto = analisadas.length - comValor.length;
  const total = comValor.reduce((soma, a) => soma + (a.valor_total ?? 0), 0);
  const motivoOk = motivo !== "" && (motivo !== "outro" || detalhe.trim().length > 0);
  const analiseCompleta = analisadas.length === itens;
  const podeGravar =
    pode("lancar") && !gravando && !conferindo && analiseCompleta && itens > 0 && aDecidir === 0 && incompletos === 0 && motivoOk && Boolean(localId) && Boolean(data);

  // O contador leva à primeira linha naquela situação.
  function irPara(situacao: Situacao) {
    const alvo = preenchidas.find((l) => {
      const a = analises[l.chave];
      if (!a) return false;
      return situacao === "decidir" ? a.a_decidir : situacao === "incompleto" ? a.incompleta : semValidadeEmAberto(a);
    });
    if (!alvo) return;
    pedirFoco(alvo.chave, colunaDaSituacao(situacao, analises[alvo.chave]), true);
  }

  // A frase ao lado do botão: o que impede de gravar, ou o que vai ficar pendente.
  const impedimentos: string[] = [];
  if (aDecidir > 0) impedimentos.push(`decida ${aDecidir} ${aDecidir === 1 ? "linha" : "linhas"} (ingrediente ou parecido)`);
  if (incompletos > 0) impedimentos.push(`complete ${incompletos} ${incompletos === 1 ? "linha incompleta" : "linhas incompletas"}`);

  const frase = !pode("lancar")
    ? "Seu papel não permite lançar entradas."
    : itens === 0
      ? "Preencha ao menos um item."
      : !motivoOk
        ? motivo === "outro"
          ? "Em “Outro”, diga o motivo."
          : "Escolha o motivo da entrada."
        : conferindo || !analiseCompleta
          ? "Conferindo as linhas."
          : impedimentos.length > 0
            ? `Para gravar: ${impedimentos.join(" e ")}.`
            : semValidade > 0
              ? `Pode gravar. A entrada fica pendente: ${semValidade} ${semValidade === 1 ? "item sem validade" : "itens sem validade"}.`
              : "";

  async function gravar() {
    if (!podeGravar) return;
    setGravando(true);
    setErro(null);
    const corpo: EntradaEnvio = {
      chave: chaveIdem.current,
      data,
      local_id: localId,
      tipo: "sem_nota",
      motivo,
      motivo_detalhe: motivo === "outro" ? detalhe.trim() : "",
      fornecedor: motivo === "contagem" || motivo === "outro" ? "" : fornecedor.trim(),
      observacao: "",
      linhas: preenchidas.map((l) => paraEnvio(l, catalogo)),
    };
    try {
      const gravada = await lancarEntrada(corpo);
      atualizarFluxo();
      navegar(`/entradas?abrir=${gravada.id}`);
    } catch (falha) {
      setErro(textoDoErro(falha, "Não foi possível gravar a entrada. Nada foi gravado."));
      setGravando(false);
      pedido.current += 1;
      setLinhas((atual) => [...atual]);
    }
  }

  const linhasDaGrade = linhas.map((linha, indice) => (
    <LinhaDaEntrada
      key={linha.chave}
      linha={linha}
      indice={indice}
      analise={analises[linha.chave]}
      catalogo={catalogo}
      narrow={narrow}
      tabela={tabela}
      aberta={abertaNoCelular === linha.chave}
      podeRemover={linhas.length > 1}
      onAbrir={() => setAbertaNoCelular((atual) => (atual === linha.chave ? null : linha.chave))}
      onMudar={(fn) => mudarLinha(linha.chave, fn)}
      onRemover={() => remover(linha.chave)}
      onDuplicar={() => duplicar(linha.chave)}
      onProxima={() => irParaProxima(linha.chave)}
      onIngredienteCriado={ingredienteCriado}
    />
  ));

  return (
    <Fragment>
      <main className="fluxo-pagina entrada-pagina" onPaste={colar}>
        <PageHeader
          title="Entrada sem nota"
          description="O que chegou? Digite item por item ou cole de uma planilha."
          actions={
            <div className="acoes-cabecalho">
              <Button onClick={() => setColando(true)}>Colar da planilha</Button>
              <Button onClick={() => navegar("/entradas")}>Voltar para Entradas</Button>
            </div>
          }
        />

        <Card className="entrada-cabecalho">
          <div className="entrada-cab-grid">
            <div className="entrada-motivo">
              <p className="campo-rotulo-fixo" id="rotulo-motivo">
                Motivo
              </p>
              <Chips rotulo="Motivo da entrada" opcoes={OPCOES_MOTIVO} valor={motivo as Motivo} onChange={setMotivo} />
            </div>
            {motivo === "outro" ? (
              <label className="gestao-field">
                <span>Qual o motivo?</span>
                <input type="text" value={detalhe} maxLength={200} onChange={(e) => setDetalhe(e.target.value)} />
              </label>
            ) : null}
            {motivo === "compra_sem_nota" || motivo === "bonificacao" ? (
              <label className="gestao-field">
                <span>{motivo === "bonificacao" ? "Quem deu (opcional)" : "Fornecedor (opcional)"}</span>
                <input type="text" value={fornecedor} maxLength={160} onChange={(e) => setFornecedor(e.target.value)} />
              </label>
            ) : null}
            <label className="gestao-field">
              <span>Local</span>
              <select value={localId} onChange={(e) => setLocalId(e.target.value)}>
                {(catalogo?.locais ?? []).map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.nome}
                  </option>
                ))}
              </select>
            </label>
            <label className="gestao-field">
              <span>Data</span>
              <input type="date" value={data} max={hojeNoFuso(sessao.fuso)} onChange={(e) => setData(e.target.value)} />
            </label>
          </div>
        </Card>

        {falhouCatalogo ? (
          <Card className="fluxo-vazio">
            <p role="alert">Não foi possível carregar os itens e ingredientes agora.</p>
            <Button onClick={() => window.location.reload()}>Recarregar</Button>
          </Card>
        ) : null}

        <datalist id="entrada-itens">
          {(catalogo?.itens ?? []).map((i) => (
            <option key={i.id} value={rotuloItem(i.nome, i.marca)} />
          ))}
        </datalist>

        <Card className="entrada-grade-card">
          {tabela ? (
            <div className="entrada-tabela-rolagem">
              <table className="entrada-tabela" aria-label="Itens da entrada">
                <thead>
                  <tr>
                    <th scope="col" className="campo-item" title="Item como comprado">Item</th>
                    <th scope="col" className="campo-ingrediente">Ingrediente</th>
                    <th scope="col" className="campo-marca">Marca</th>
                    <th scope="col" className="campo-qtd">
                      <abbr title="Quantidade">Qtd.</abbr>
                    </th>
                    <th scope="col" className="campo-unidade">Unidade</th>
                    <th scope="col" className="campo-conteudo">Conteúdo</th>
                    <th scope="col" className="campo-lote">Lote</th>
                    <th scope="col" className="campo-validade">
                      Validade <small>/ sem</small>
                    </th>
                    <th scope="col" className="campo-custo">Custo</th>
                    <th scope="col" className="campo-remover">
                      <span className="so-leitor">Ações</span>
                    </th>
                  </tr>
                </thead>
                {linhasDaGrade}
              </table>
            </div>
          ) : (
            <>
              {!narrow ? (
                <div className="grade-cab" aria-hidden="true">
                  <span className="campo-item">Item como comprado</span>
                  <span className="campo-ingrediente">Ingrediente</span>
                  <span className="campo-marca">Marca</span>
                  <span className="campo-qtd">Quantidade</span>
                  <span className="campo-unidade">Unidade</span>
                  <span className="campo-conteudo">Conteúdo da embalagem</span>
                  <span className="campo-lote">Lote</span>
                  <span className="campo-validade">Validade</span>
                  <span className="campo-custo">Custo</span>
                  <span className="campo-remover" />
                </div>
              ) : null}
              <ul className="entrada-grade" aria-label="Itens da entrada">
                {linhasDaGrade}
              </ul>
            </>
          )}
          <p className="entrada-dica">
            Dica: cole de uma planilha as colunas, nesta ordem: item, ingrediente, marca, quantidade, unidade, conteúdo, lote,
            validade, custo. O ingrediente que não bater exatamente fica “a decidir”.
          </p>
        </Card>

        <div className="entrada-rodape" role="region" aria-label="Resumo da entrada">
          <p className="rodape-numeros">
            <span>
              <strong>{itens}</strong> {itens === 1 ? "item" : "itens"}
            </span>
            <Contador n={aDecidir} rotulo="a decidir" tom="num-decidir" onIr={() => irPara("decidir")} />
            <Contador
              n={incompletos}
              rotulo={incompletos === 1 ? "incompleto" : "incompletos"}
              tom="num-incompleto"
              onIr={() => irPara("incompleto")}
            />
            <Contador n={semValidade} rotulo="sem validade" tom="num-validade" onIr={() => irPara("validade")} />
            <span className="rodape-total">
              Total <strong>{dinheiro(total)}</strong>
              {semCusto > 0 && itens > 0 ? <em> sem custo não soma</em> : null}
            </span>
          </p>
          <div className="rodape-acao">
            {erro ? (
              <p role="alert" className="form-erro">
                {erro}
              </p>
            ) : frase ? (
              <p className="rodape-motivo">{frase}</p>
            ) : null}
            <Button variant="primary" disabled={!podeGravar} onClick={() => void gravar()}>
              {gravando ? "Gravando." : "Gravar entrada"}
            </Button>
          </div>
        </div>
      </main>

      {colando ? <PainelColar onFechar={() => setColando(false)} onAdicionar={adicionarTexto} /> : null}
    </Fragment>
  );
}
