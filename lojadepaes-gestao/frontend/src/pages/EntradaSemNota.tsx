import { useCallback, useEffect, useMemo, useRef, useState, type ChangeEvent, type ClipboardEvent, type ReactNode } from "react";
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
  linhaVazia,
  linhasDaColagem,
  novaLinha,
  paraEnvio,
  reconhecer,
  rotuloItem,
  soltarItem,
  usarItem,
  type LinhaForm,
} from "../lib/entradaForm";
import { dinheiro, MOTIVOS } from "../lib/format";
import { hojeNoFuso, useNarrow } from "../lib/useNarrow";
import { Button } from "../shell/Button";
import { Card } from "../shell/Card";
import { Chips } from "../shell/Chips";
import { PageHeader } from "../shell/PageHeader";
import "./fluxo.css";

type Motivo = "contagem" | "compra_sem_nota" | "bonificacao" | "outro";
const OPCOES_MOTIVO: { valor: Motivo; rotulo: string }[] = (
  ["contagem", "compra_sem_nota", "bonificacao", "outro"] as Motivo[]
).map((valor) => ({ valor, rotulo: MOTIVOS[valor] }));

const CODIGOS_TRATADOS = new Set([
  "item_parecido",
  "item_ja_existe",
  "ingrediente_parecido",
  "ingrediente_ja_existe",
]);

function chaveDeEnvio(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
}

type LinhaProps = {
  linha: LinhaForm;
  indice: number;
  analise: AnaliseLinha | undefined;
  catalogo: Catalogo | null;
  narrow: boolean;
  aberta: boolean;
  onAbrir: () => void;
  onMudar: (mudar: (l: LinhaForm) => LinhaForm) => void;
  onRemover: () => void;
};

function resumo(l: LinhaForm, a: AnaliseLinha | undefined): { texto: string; tom: "ok" | "decidir" | "incompleto" | "vazio" } {
  if (linhaVazia(l)) return { texto: "linha vazia", tom: "vazio" };
  if (!a) return { texto: "conferindo", tom: "vazio" };
  if (a.a_decidir) return { texto: "a decidir", tom: "decidir" };
  if (a.incompleta) return { texto: "incompleto", tom: "incompleto" };
  if (a.pendencias.some((p) => p.codigo === "validade_nao_informada")) return { texto: "sem validade", tom: "ok" };
  return { texto: "ok", tom: "ok" };
}

function LinhaDaEntrada({ linha, indice, analise, catalogo, narrow, aberta, onAbrir, onMudar, onRemover }: LinhaProps) {
  const n = indice + 1;
  const item = linha.itemId ? catalogo?.itens.find((i) => i.id === linha.itemId) : undefined;
  const travada = Boolean(item);
  const controle = item ? item.unidade_controle : controleDaUnidade(linha.unidade);
  const emb = controle === "embalagem";
  const unidades = item ? UNIDADES.filter((u) => u.controle === item.unidade_controle) : UNIDADES;
  const baseTravada = travada || Boolean(linha.ingredienteId);
  const estado = resumo(linha, analise);

  const mudar = (patch: Partial<LinhaForm>) => onMudar((l) => ({ ...l, ...patch }));

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
  const aoDigitarIngrediente = (e: ChangeEvent<HTMLInputElement>) => {
    const texto = e.target.value;
    const soTexto = digitando(e);
    onMudar((l) => {
      const base = { ...l, ingredienteId: null, ingredienteBase: "" as const, ingredienteTexto: texto, decisaoIngrediente: null };
      return soTexto ? base : reconhecer(base, catalogo);
    });
  };
  const reconhecerAoSair = () => onMudar((l) => reconhecer(l, catalogo));

  const rotuloCampo = (texto: string) => <span className="campo-rotulo">{texto}</span>;

  const campos = (
    <>
      <label className="campo campo-item">
        {rotuloCampo("Item como comprado")}
        <input
          type="text"
          list="entrada-itens"
          value={linha.itemTexto}
          autoComplete="off"
          aria-label={`Item como comprado, linha ${n}`}
          placeholder="Ex.: Farinha de trigo 25 kg"
          onChange={aoDigitarItem}
          onBlur={reconhecerAoSair}
        />
      </label>
      <label className="campo campo-ingrediente">
        {rotuloCampo("Ingrediente")}
        <input
          type="text"
          list="entrada-ingredientes"
          value={linha.ingredienteTexto}
          autoComplete="off"
          readOnly={travada}
          aria-label={`Ingrediente, linha ${n}`}
          placeholder="Ex.: Farinha de trigo"
          onChange={aoDigitarIngrediente}
          onBlur={reconhecerAoSair}
        />
      </label>
      <label className="campo campo-marca">
        {rotuloCampo("Marca")}
        <input
          type="text"
          value={linha.marca}
          autoComplete="off"
          readOnly={travada}
          aria-label={`Marca, linha ${n}`}
          onChange={(e) => onMudar((l) => ({ ...l, marca: e.target.value }))}
          onBlur={reconhecerAoSair}
        />
      </label>
      <label className="campo campo-qtd">
        {rotuloCampo("Quantidade")}
        <input
          type="text"
          inputMode="decimal"
          value={linha.quantidade}
          aria-label={`Quantidade, linha ${n}`}
          onChange={(e) => mudar({ quantidade: e.target.value })}
        />
      </label>
      <label className="campo campo-unidade">
        {rotuloCampo("Unidade")}
        <select value={linha.unidade} aria-label={`Unidade, linha ${n}`} onChange={(e) => mudar({ unidade: e.target.value })}>
          <option value="">escolha</option>
          {unidades.map((u) => (
            <option key={u.valor} value={u.valor}>
              {u.rotulo}
            </option>
          ))}
        </select>
      </label>
      <div className="campo campo-conteudo">
        {rotuloCampo("Conteúdo da embalagem")}
        <div className="campo-duplo">
          <input
            type="text"
            inputMode="decimal"
            value={emb ? linha.conteudo : ""}
            disabled={!emb}
            readOnly={travada}
            aria-label={`Conteúdo da embalagem, linha ${n}`}
            placeholder={emb ? "quanto vem" : "—"}
            onChange={(e) => mudar({ conteudo: e.target.value })}
          />
          {emb ? (
            <select
              value={linha.ingredienteBase}
              disabled={baseTravada}
              aria-label={`Unidade do conteúdo, linha ${n}`}
              onChange={(e) => mudar({ ingredienteBase: e.target.value as LinhaForm["ingredienteBase"] })}
            >
              <option value="">un.</option>
              <option value="g">g</option>
              <option value="ml">ml</option>
              <option value="un">un</option>
            </select>
          ) : null}
        </div>
      </div>
      <label className="campo campo-lote">
        {rotuloCampo("Lote")}
        <input
          type="text"
          value={linha.lote}
          autoComplete="off"
          placeholder="automático"
          aria-label={`Lote, linha ${n}`}
          onChange={(e) => mudar({ lote: e.target.value })}
        />
      </label>
      <div className="campo campo-validade">
        {rotuloCampo("Validade")}
        <input
          type="date"
          value={linha.semValidade ? "" : linha.validade}
          disabled={linha.semValidade}
          aria-label={`Validade, linha ${n}`}
          onChange={(e) => mudar({ validade: e.target.value })}
        />
        <label className="campo-check">
          <input
            type="checkbox"
            checked={linha.semValidade}
            onChange={(e) => mudar({ semValidade: e.target.checked, validade: e.target.checked ? "" : linha.validade })}
          />
          <span>sem validade</span>
        </label>
      </div>
      <label className="campo campo-custo">
        {rotuloCampo(controle ? CUSTO_POR[controle] : "Custo")}
        <input
          type="text"
          inputMode="decimal"
          value={linha.custo}
          placeholder={controle ? CUSTO_POR[controle] : "R$"}
          aria-label={`Custo ${controle ? CUSTO_POR[controle] : "em reais"}, linha ${n}`}
          onChange={(e) => mudar({ custo: e.target.value })}
        />
      </label>
      <div className="campo campo-remover">
        <button type="button" className="icone-remover" aria-label={`Remover a linha ${n}`} onClick={onRemover}>
          <svg width="18" height="18" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
            <path d="M5 5l10 10M15 5 5 15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </button>
      </div>
    </>
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
    const ingParecido = analise.ingrediente_parecidos[0];
    if (ingParecido && linha.decisaoIngrediente !== "novo" && !linha.itemId && !linha.ingredienteId) {
      avisos.push(
        <div key="gp" className="aviso-linha decidir" role="group" aria-label={`Ingrediente parecido, linha ${n}`}>
          <span>
            <strong>Ingrediente parecido com</strong> “{ingParecido.nome}”.
          </span>
          <span className="aviso-acoes">
            <Button
              onClick={() =>
                mudar({
                  ingredienteId: ingParecido.id,
                  ingredienteTexto: ingParecido.nome,
                  ingredienteBase: ingParecido.unidade_base as LinhaForm["ingredienteBase"],
                  decisaoIngrediente: null,
                })
              }
            >
              Usar este
            </Button>
            <Button onClick={() => mudar({ decisaoIngrediente: "novo" })}>Criar novo</Button>
          </span>
        </div>,
      );
    }
    if (analise.ingrediente_parecidos.length > 0 && linha.decisaoIngrediente === "novo") {
      avisos.push(
        <div key="gpn" className="aviso-linha decidido">
          <span>Vai criar um ingrediente novo, mesmo parecido com “{analise.ingrediente_parecidos[0].nome}”.</span>
          <Button onClick={() => mudar({ decisaoIngrediente: null })}>Desfazer</Button>
        </div>,
      );
    }
    if (analise.ingrediente_igual) {
      const igual = analise.ingrediente_igual;
      avisos.push(
        <div key="gi" className="aviso-linha decidir">
          <span>Já existe o ingrediente “{igual.nome}”.</span>
          <Button
            onClick={() =>
              mudar({
                ingredienteId: igual.id,
                ingredienteTexto: igual.nome,
                ingredienteBase: igual.unidade_base as LinhaForm["ingredienteBase"],
              })
            }
          >
            Usar este
          </Button>
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

  if (narrow) {
    return (
      <li className={`grade-linha compacta ${estado.tom}`} role="group" aria-label={`Item ${n}`}>
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
        {aberta ? <div className="compacta-campos">{campos}</div> : null}
        {avisos.length > 0 ? <div className="grade-avisos">{avisos}</div> : null}
      </li>
    );
  }

  return (
    <li className={`grade-linha ${estado.tom}`} role="group" aria-label={`Item ${n}`}>
      <div className="grade-campos">{campos}</div>
      {avisos.length > 0 ? <div className="grade-avisos">{avisos}</div> : null}
    </li>
  );
}

export function EntradaSemNota() {
  const { sessao, navegar, atualizarFluxo, pode } = useGestao();
  const narrow = useNarrow();
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

  function colar(event: ClipboardEvent<HTMLElement>) {
    const texto = event.clipboardData.getData("text");
    if (!texto.includes("\t") && !texto.trim().includes("\n")) return;
    event.preventDefault();
    const novas = linhasDaColagem(texto, catalogo);
    if (novas.length === 0) return;
    atualizarLinhas((atual) => [...atual.filter((l) => !linhaVazia(l)), ...novas]);
  }

  const itens = preenchidas.length;
  const analisadas = preenchidas.map((l) => analises[l.chave]).filter(Boolean);
  const aDecidir = analisadas.filter((a) => a.a_decidir).length;
  const incompletos = analisadas.filter((a) => a.incompleta).length;
  const comValor = analisadas.filter((a) => a.valor_total !== null);
  const semCusto = analisadas.length - comValor.length;
  const total = comValor.reduce((soma, a) => soma + (a.valor_total ?? 0), 0);
  const motivoOk = motivo !== "" && (motivo !== "outro" || detalhe.trim().length > 0);
  const analiseCompleta = analisadas.length === itens;
  const podeGravar =
    pode("lancar") && !gravando && !conferindo && analiseCompleta && itens > 0 && aDecidir === 0 && incompletos === 0 && motivoOk && Boolean(localId) && Boolean(data);

  const bloqueio = !pode("lancar")
    ? "Seu papel não permite lançar entradas."
    : itens === 0
      ? "Preencha ao menos um item."
      : !motivoOk
        ? motivo === "outro"
          ? "Em “Outro”, diga o motivo."
          : "Escolha o motivo da entrada."
        : conferindo || !analiseCompleta
          ? "Conferindo as linhas."
          : aDecidir > 0
            ? "Decida os itens parecidos."
            : incompletos > 0
              ? "Complete as linhas marcadas."
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

  return (
    <main className="fluxo-pagina entrada-pagina" onPaste={colar}>
      <PageHeader
        title="Entrada sem nota"
        description="O que chegou? Digite item por item ou cole de uma planilha."
        actions={<Button onClick={() => navegar("/entradas")}>Voltar para Entradas</Button>}
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
      <datalist id="entrada-ingredientes">
        {(catalogo?.ingredientes ?? []).map((i) => (
          <option key={i.id} value={i.nome} />
        ))}
      </datalist>

      <Card className="entrada-grade-card">
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
          {linhas.map((linha, indice) => (
            <LinhaDaEntrada
              key={linha.chave}
              linha={linha}
              indice={indice}
              analise={analises[linha.chave]}
              catalogo={catalogo}
              narrow={narrow}
              aberta={abertaNoCelular === linha.chave}
              onAbrir={() => setAbertaNoCelular((atual) => (atual === linha.chave ? null : linha.chave))}
              onMudar={(fn) => mudarLinha(linha.chave, fn)}
              onRemover={() =>
                atualizarLinhas((atual) => (atual.length > 1 ? atual.filter((l) => l.chave !== linha.chave) : atual))
              }
            />
          ))}
        </ul>
        <p className="entrada-dica">
          Dica: cole de uma planilha as colunas, nesta ordem: item, ingrediente, marca, quantidade, unidade, conteúdo, lote,
          validade, custo.
        </p>
      </Card>

      <div className="entrada-rodape" role="region" aria-label="Resumo da entrada">
        <p className="rodape-numeros">
          <span>
            <strong>{itens}</strong> {itens === 1 ? "item" : "itens"}
          </span>
          <span className={aDecidir > 0 ? "num-decidir" : undefined}>
            <strong>{aDecidir}</strong> a decidir
          </span>
          <span className={incompletos > 0 ? "num-incompleto" : undefined}>
            <strong>{incompletos}</strong> {incompletos === 1 ? "incompleto" : "incompletos"}
          </span>
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
          ) : bloqueio ? (
            <p className="rodape-motivo">{bloqueio}</p>
          ) : null}
          <Button variant="primary" disabled={!podeGravar} onClick={() => void gravar()}>
            {gravando ? "Gravando." : "Gravar entrada"}
          </Button>
        </div>
      </div>
    </main>
  );
}
