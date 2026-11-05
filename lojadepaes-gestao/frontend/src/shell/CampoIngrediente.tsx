import { createPortal } from "react-dom";
import { useEffect, useId, useLayoutEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import {
  buscarIngredientes,
  sugerirIngrediente,
  type BuscaIngredientes,
  type CatalogoSugerido,
  type IngredienteBusca,
  type IngredienteDetalhe,
  type Juntado,
  type Sugestao,
} from "../lib/api";
import { quantidadeBase } from "../lib/format";
import { NovoIngredienteDialogo, type PedidoCadastro } from "./NovoIngrediente";
import { ReativarIngredienteDialog } from "./ReativarIngrediente";

export type IngredienteEscolhido = { id: string; nome: string; categoria: string; unidade_base: string };

type Opcao =
  | { tipo: "sugestao"; sugestao: Sugestao }
  | { tipo: "padaria"; ingrediente: IngredienteBusca }
  | { tipo: "catalogo"; catalogo: CatalogoSugerido }
  | { tipo: "novo" };

type Props = {
  /** Texto do aria-label do campo, ex.: "Ingrediente, linha 1". */
  rotulo: string;
  /** Ingrediente já escolhido: o campo vira um chip (nome + categoria) com × para trocar. */
  valor: { nome: string; categoria: string } | null;
  /** O ingrediente vem do item que já existe: o chip não tem ×. */
  travado?: boolean;
  /** Texto que já veio para a busca (a coluna Ingrediente da planilha). */
  textoInicial?: string;
  /** O item da linha: dele sai a sugestão (até 3, cada uma com o motivo). */
  item?: string;
  marca?: string;
  /** Escolheu (ou cadastrou) um ingrediente. `criado` diz que acabou de nascer. */
  onEscolher: (ingrediente: IngredienteEscolhido, criado: boolean) => void;
  onTrocar?: () => void;
  celula?: Record<string, string>;
  placeholder?: string;
  /** Abre sozinho e leva o foco (a tela Ingredientes). */
  autoFoco?: boolean;
};

const MAX_SUGESTOES = 3;

function doCatalogo(c: CatalogoSugerido): PedidoCadastro {
  return { nome: c.nome, categoria: c.categoria, unidade_base: c.unidade_base, apelidos: c.apelidos, doCatalogo: true, item: "" };
}

function escolhido(i: IngredienteBusca): IngredienteEscolhido {
  return { id: i.id, nome: i.nome, categoria: i.categoria, unidade_base: i.unidade_base };
}

/**
 * O campo Ingrediente é uma BUSCA: primeiro o que a padaria já tem (e o que o sistema sugere pelo item),
 * depois o catálogo, e só no fim "Não encontrei, cadastrar novo". Nunca cria nada sozinho.
 */
export function CampoIngrediente({
  rotulo,
  valor,
  travado = false,
  textoInicial = "",
  item = "",
  marca = "",
  onEscolher,
  onTrocar,
  celula,
  placeholder = "Buscar ingrediente",
  autoFoco = false,
}: Props) {
  const uid = useId();
  const entrada = useRef<HTMLInputElement>(null);
  const raiz = useRef<HTMLDivElement>(null);
  const [texto, setTexto] = useState(textoInicial);
  const [aberto, setAberto] = useState(autoFoco);
  const [busca, setBusca] = useState<BuscaIngredientes | null>(null);
  const [sugestoes, setSugestoes] = useState<Sugestao[]>([]);
  const [ativo, setAtivo] = useState(0);
  const [cadastro, setCadastro] = useState<PedidoCadastro | null>(null);
  const [reativar, setReativar] = useState<Juntado | null>(null);
  const [juntadosDoItem, setJuntadosDoItem] = useState<Juntado[]>([]);
  const [lugar, setLugar] = useState<{ left: number; top: number; width: number; maxHeight: number; acima: boolean } | null>(null);
  const [voltarFoco, setVoltarFoco] = useState(false);

  // A sugestão vem do nome do item, sem ninguém pedir; fica PENDENTE até a pessoa confirmar.
  const itemLimpo = item.trim();
  useEffect(() => {
    if (valor || !itemLimpo || itemLimpo.length < 2) {
      setSugestoes([]);
      return;
    }
    let vivo = true;
    const espera = setTimeout(() => {
      sugerirIngrediente(itemLimpo, marca.trim())
        .then((s) => vivo && setSugestoes(s.slice(0, MAX_SUGESTOES)))
        .catch(() => vivo && setSugestoes([]));
    }, 300);
    return () => {
      vivo = false;
      clearTimeout(espera);
    };
  }, [valor, itemLimpo, marca]);

  // O nome do item pode bater com um ingrediente já juntado: a oferta de reativar aparece sem abrir a lista.
  useEffect(() => {
    if (valor || itemLimpo.length < 2) {
      setJuntadosDoItem([]);
      return;
    }
    let vivo = true;
    buscarIngredientes(itemLimpo)
      .then((r) => vivo && setJuntadosDoItem(r.juntados ?? []))
      .catch(() => vivo && setJuntadosDoItem([]));
    return () => {
      vivo = false;
    };
  }, [valor, itemLimpo]);

  // A busca da padaria e do catálogo, enquanto a lista está aberta.
  useEffect(() => {
    if (!aberto || valor) return;
    let vivo = true;
    const espera = setTimeout(
      () => {
        buscarIngredientes(texto.trim())
          .then((r) => vivo && setBusca(r))
          .catch(() => vivo && setBusca({ q: texto.trim(), da_padaria: [], do_catalogo: [] }));
      },
      busca === null ? 0 : 180,
    );
    return () => {
      vivo = false;
      clearTimeout(espera);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [aberto, texto, valor]);

  // As opções, na ordem em que aparecem (e em que o teclado anda).
  const digitado = texto.trim().length > 0;
  const juntados = useMemo(() => {
    const mapa = new Map<string, Juntado>();
    for (const j of [...juntadosDoItem, ...(busca?.juntados ?? [])]) mapa.set(j.id, j);
    return [...mapa.values()];
  }, [juntadosDoItem, busca]);
  const grupos = useMemo(() => {
    const sugeridas: Opcao[] = sugestoes.map((sugestao) => ({ tipo: "sugestao", sugestao }));
    const porCategoria = new Map<string, Opcao[]>();
    for (const ingrediente of busca?.da_padaria ?? []) {
      const lista = porCategoria.get(ingrediente.categoria) ?? [];
      lista.push({ tipo: "padaria", ingrediente });
      porCategoria.set(ingrediente.categoria, lista);
    }
    const catalogo: Opcao[] = (busca?.do_catalogo ?? []).map((c) => ({ tipo: "catalogo", catalogo: c }));
    return { sugeridas, porCategoria: [...porCategoria.entries()], catalogo };
  }, [sugestoes, busca]);

  const opcoes: Opcao[] = useMemo(
    () => [
      ...grupos.sugeridas,
      ...grupos.porCategoria.flatMap(([, lista]) => lista),
      ...grupos.catalogo,
      { tipo: "novo" } as Opcao,
    ],
    [grupos],
  );

  // Quem já digitou algo quer o resultado da busca. Quem só abriu: o Enter só leva a 1ª sugestão se ela
  // está em DESTAQUE (certeza); sem certeza nada fica ativo e o Enter não escolhe por ninguém.
  useEffect(() => {
    if (!aberto) return;
    const primeiroDaBusca = opcoes.findIndex((o) => o.tipo !== "sugestao");
    const comDestaque = sugestoes.length > 0 && sugestoes[0].destaque;
    setAtivo(digitado && primeiroDaBusca >= 0 ? primeiroDaBusca : comDestaque ? 0 : -1);
  }, [aberto, digitado, opcoes, sugestoes]);

  // A lista fica fora da tabela (que rola) para não ser cortada: posição calculada pelo campo.
  useLayoutEffect(() => {
    if (!aberto || !raiz.current) return;
    const calcular = () => {
      const r = raiz.current?.getBoundingClientRect();
      if (!r) return;
      const abaixo = window.innerHeight - r.bottom - 12;
      const acima = r.top - 12;
      const emCima = abaixo < 220 && acima > abaixo;
      const espaco = emCima ? acima : abaixo;
      setLugar({
        left: Math.max(8, Math.min(r.left, window.innerWidth - Math.max(r.width, 300) - 8)),
        top: emCima ? r.top - 4 : r.bottom + 4,
        width: Math.max(r.width, 300),
        maxHeight: Math.max(160, Math.min(420, espaco)),
        acima: emCima,
      });
    };
    calcular();
    window.addEventListener("resize", calcular);
    window.addEventListener("scroll", calcular, true);
    return () => {
      window.removeEventListener("resize", calcular);
      window.removeEventListener("scroll", calcular, true);
    };
  }, [aberto]);

  // Depois do × do chip o foco vai para a busca.
  useEffect(() => {
    if (voltarFoco && !valor) {
      entrada.current?.focus();
      setVoltarFoco(false);
    }
  }, [voltarFoco, valor]);

  useEffect(() => {
    if (autoFoco) entrada.current?.focus();
  }, [autoFoco]);

  function fechar() {
    setAberto(false);
  }

  function escolher(opcao: Opcao) {
    if (opcao.tipo === "sugestao") {
      if (opcao.sugestao.ingrediente) onEscolher(escolhido(opcao.sugestao.ingrediente), false);
      else if (opcao.sugestao.catalogo) setCadastro(doCatalogo(opcao.sugestao.catalogo));
    } else if (opcao.tipo === "padaria") {
      onEscolher(escolhido(opcao.ingrediente), false);
    } else if (opcao.tipo === "catalogo") {
      setCadastro(doCatalogo(opcao.catalogo));
    } else {
      setCadastro({ nome: texto.trim(), categoria: "", unidade_base: "g", apelidos: [], doCatalogo: false, item: itemLimpo });
    }
    fechar();
  }

  // Só há sugestão PENDENTE (pré-preenchida) quando o servidor tem certeza (`destaque`). Sem certeza o campo
  // pede "Escolha o ingrediente" e as sugestões ficam à mão, sem nada marcado.
  const pendente = !valor && !digitado && sugestoes.length > 0 && sugestoes[0].destaque ? sugestoes[0] : null;
  const semCerteza = !valor && !digitado && sugestoes.length > 0 && !pendente;
  const nomePendente = pendente ? (pendente.ingrediente?.nome ?? pendente.catalogo?.nome ?? "") : "";

  function aoTeclar(event: KeyboardEvent<HTMLInputElement>) {
    if (event.nativeEvent.isComposing) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      if (!aberto) setAberto(true);
      else setAtivo((a) => Math.min(opcoes.length - 1, a + 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      if (aberto) setAtivo((a) => Math.max(0, a - 1));
    } else if (event.key === "Enter") {
      if (aberto && opcoes[ativo]) {
        event.preventDefault();
        escolher(opcoes[ativo]);
      } else if (pendente) {
        event.preventDefault();
        escolher({ tipo: "sugestao", sugestao: pendente });
      }
    } else if (event.key === "Escape" && aberto) {
      event.preventDefault();
      event.stopPropagation();
      fechar();
    } else if (event.key === "Tab") {
      fechar();
    }
  }

  const idLista = `${uid}-lista`;
  const idOpcao = (i: number) => `${uid}-opcao-${i}`;

  // ------------------------------------------------------------ chip
  if (valor) {
    return (
      <div className={`ing-chip${travado ? " travado" : ""}`} role="group" aria-label={rotulo} {...celula} tabIndex={-1}>
        <span className="ing-chip-texto">
          <strong>{valor.nome}</strong>
          {valor.categoria ? <small>{valor.categoria}</small> : null}
        </span>
        {travado ? (
          <small className="ing-chip-trava">vem do item</small>
        ) : (
          <button
            type="button"
            className="ing-chip-x"
            aria-label={`Trocar o ingrediente ${valor.nome}`}
            onClick={() => {
              setTexto("");
              setBusca(null);
              setVoltarFoco(true);
              onTrocar?.();
            }}
          >
            <svg width="14" height="14" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
              <path d="M5 5l10 10M15 5 5 15" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
            </svg>
          </button>
        )}
      </div>
    );
  }

  // ------------------------------------------------------------ busca
  let indice = -1;
  const linha = (opcao: Opcao, conteudo: React.ReactNode, extra = "") => {
    indice += 1;
    const i = indice;
    return (
      // Padrão combobox: o teclado fica no campo (setas, Enter, Esc); a opção só responde ao clique.
      // eslint-disable-next-line jsx-a11y/click-events-have-key-events
      <li
        key={`${opcao.tipo}-${i}`}
        id={idOpcao(i)}
        role="option"
        aria-selected={i === ativo}
        className={`ing-opcao${i === ativo ? " ativa" : ""}${extra ? ` ${extra}` : ""}`}
        onMouseEnter={() => setAtivo(i)}
        onClick={() => escolher(opcao)}
      >
        {conteudo}
      </li>
    );
  };

  const lista =
    aberto && lugar
      ? createPortal(
          // A lista sai do quadro da tabela (portal); o .gestao-portal leva junto as variáveis e a fonte do tema.
          <div className="gestao-frame gestao-portal">
            {/* O mousedown não tira o foco do campo: clicar numa opção não fecha a lista antes do clique. */}
            {/* eslint-disable-next-line jsx-a11y/no-static-element-interactions */}
            <div
              className={`ing-lista${lugar.acima ? " acima" : ""}`}
              style={{ left: lugar.left, top: lugar.top, width: lugar.width, maxHeight: lugar.maxHeight }}
              onMouseDown={(e) => e.preventDefault()}
            >
            <ul id={idLista} role="listbox" aria-label={`Ingredientes, ${rotulo}`}>
              {grupos.sugeridas.length > 0 ? (
                <li role="presentation" className="ing-grupo">
                  <p className="ing-grupo-titulo">Sugeridos para “{itemLimpo}”</p>
                  <ul role="group" aria-label="Sugeridos">
                    {grupos.sugeridas.map((o) => {
                      if (o.tipo !== "sugestao") return null;
                      const s = o.sugestao;
                      return linha(
                        o,
                        <>
                          <span className="ing-opcao-nome">
                            <strong>{s.ingrediente?.nome ?? s.catalogo?.nome}</strong>
                            <small>{s.ingrediente?.categoria ?? s.catalogo?.categoria}</small>
                          </span>
                          <span className="ing-opcao-motivo">{s.motivo}</span>
                        </>,
                      );
                    })}
                  </ul>
                </li>
              ) : null}

              <li role="presentation" className="ing-grupo">
                <p className="ing-grupo-titulo">Na sua padaria</p>
                {grupos.porCategoria.length === 0 ? (
                  <p className="ing-vazio">
                    {busca === null ? "Buscando." : digitado ? `Nada na sua padaria com “${texto.trim()}”.` : "Você ainda não tem ingredientes."}
                  </p>
                ) : (
                  grupos.porCategoria.map(([categoria, lista]) => (
                    <ul role="group" aria-label={categoria} key={categoria} className="ing-categoria">
                      <li role="presentation" className="ing-categoria-nome">
                        {categoria}
                      </li>
                      {lista.map((o) => {
                        if (o.tipo !== "padaria") return null;
                        const i = o.ingrediente;
                        return linha(
                          o,
                          <>
                            <span className="ing-opcao-nome">
                              <strong>{i.nome}</strong>
                              {i.achado_por ? <small>também chamado de “{i.achado_por}”</small> : null}
                            </span>
                            <span className="ing-opcao-saldo">{i.saldo > 0 ? quantidadeBase(i.saldo, i.unidade_base) : "sem saldo"}</span>
                          </>,
                        );
                      })}
                    </ul>
                  ))
                )}
              </li>

              {grupos.catalogo.length > 0 ? (
                <li role="presentation" className="ing-grupo">
                  <p className="ing-grupo-titulo">Do catálogo</p>
                  <ul role="group" aria-label="Do catálogo">
                    {grupos.catalogo.map((o) => {
                      if (o.tipo !== "catalogo") return null;
                      return linha(
                        o,
                        <>
                          <span className="ing-opcao-nome">
                            <strong>{o.catalogo.nome}</strong>
                            <small>{o.catalogo.categoria}</small>
                          </span>
                          <span className="ing-opcao-selo">do catálogo</span>
                        </>,
                      );
                    })}
                  </ul>
                </li>
              ) : null}

              {linha({ tipo: "novo" }, <strong>Não encontrei, cadastrar novo</strong>, "ing-novo")}
            </ul>
            </div>
          </div>,
          document.body,
        )
      : null;

  const idPendente = `${uid}-pendente`;
  return (
    <div className={`ing-campo${pendente ? " com-pendente" : ""}${semCerteza ? " sem-certeza" : ""}`} ref={raiz}>
      <input
        ref={entrada}
        type="text"
        role="combobox"
        aria-expanded={aberto}
        aria-controls={aberto ? idLista : undefined}
        aria-autocomplete="list"
        aria-activedescendant={aberto && opcoes[ativo] ? idOpcao(ativo) : undefined}
        aria-describedby={pendente ? idPendente : undefined}
        aria-label={rotulo}
        autoComplete="off"
        value={texto}
        placeholder={pendente ? nomePendente : semCerteza ? "Escolha o ingrediente" : placeholder}
        className={pendente ? "pendente" : undefined}
        {...celula}
        onFocus={() => setAberto(true)}
        onClick={() => setAberto(true)}
        onChange={(e) => {
          setTexto(e.target.value);
          setAberto(true);
        }}
        onKeyDown={aoTeclar}
        onBlur={fechar}
      />
      {pendente ? (
        <>
          <span id={idPendente} className="so-leitor">
            Sugestão pendente: {nomePendente}. {pendente.motivo}. Tecle Enter ou use o botão para confirmar.
          </span>
          <button
            type="button"
            className="ing-confirmar"
            tabIndex={-1}
            title={`${nomePendente} — ${pendente.motivo}`}
            aria-label={`Confirmar a sugestão ${nomePendente}, ${rotulo}`}
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => escolher({ tipo: "sugestao", sugestao: pendente })}
          >
            Usar
          </button>
        </>
      ) : null}
      {semCerteza ? (
        <button
          type="button"
          className="ing-ver"
          tabIndex={-1}
          title={`Ver as ${sugestoes.length} sugestões`}
          aria-label={`Ver as ${sugestoes.length} sugestões, ${rotulo}`}
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => {
            setAberto(true);
            entrada.current?.focus();
          }}
        >
          <svg width="14" height="14" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
            <path d="M5 8l5 5 5-5" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      ) : null}
      {lista}
      {juntados.map((j) => (
        <button key={j.id} type="button" className="ing-reativar" onClick={() => setReativar(j)}>
          <strong>{j.nome}</strong> foi juntado{j.destino_nome ? ` a ${j.destino_nome}` : ""}. Reativar
        </button>
      ))}
      {cadastro
        ? createPortal(
            <div className="gestao-frame gestao-portal">
              <NovoIngredienteDialogo
                pedido={cadastro}
                onFechar={() => setCadastro(null)}
                onUsar={(existente) => {
                  setCadastro(null);
                  onEscolher(escolhido(existente), false);
                }}
                onCriado={(criado: IngredienteDetalhe) => {
                  setCadastro(null);
                  onEscolher(
                    { id: criado.id, nome: criado.nome, categoria: criado.categoria, unidade_base: criado.unidade_base },
                    true,
                  );
                }}
              />
            </div>,
            document.body,
          )
        : null}
      {reativar ? (
        <ReativarIngredienteDialog
          juntado={reativar}
          onFechar={() => setReativar(null)}
          onReativado={() => {
            setReativar(null);
            setJuntadosDoItem((lista) => lista.filter((j) => j.id !== reativar.id));
            if (texto.trim()) {
              void buscarIngredientes(texto.trim()).then(setBusca).catch(() => setBusca(null));
            }
          }}
        />
      ) : null}
    </div>
  );
}
