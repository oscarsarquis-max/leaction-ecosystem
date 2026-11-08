import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  ApiError,
  buscarIngredientes,
  criarIngrediente,
  sugerirIngrediente,
  textoDoErro,
  type CatalogoSugerido,
  type IngredienteBusca,
  type IngredienteDetalhe,
  type Juntado,
} from "../lib/api";
import { CATEGORIAS, UNIDADES_BASE } from "../lib/categorias";
import { quantidadeBase } from "../lib/format";
import { Button } from "./Button";
import { Modal } from "./Modal";
import { ReativarIngredienteDialog } from "./ReativarIngrediente";

/** O que o diálogo recebe para começar: o que a pessoa digitou ou a entrada do catálogo escolhida. */
export type PedidoCadastro = {
  nome: string;
  categoria: string;
  unidade_base: string;
  apelidos: string[];
  doCatalogo: boolean;
  /** O item da linha (para achar o candidato do catálogo quando o texto digitado é curto). */
  item?: string;
};

/** "fermento seco" -> "Fermento seco": nunca o texto cru em minúsculas. */
function capitalizar(texto: string): string {
  const t = texto.trim();
  return t ? t.charAt(0).toLocaleUpperCase("pt-BR") + t.slice(1) : t;
}

type Props = {
  pedido: PedidoCadastro;
  onFechar: () => void;
  /** "Usar" um dos que já existem (nada é criado). */
  onUsar: (ingrediente: IngredienteBusca) => void;
  onCriado: (ingrediente: IngredienteDetalhe) => void;
};

/**
 * "Cadastrar novo": primeiro mostra o que já existe e parece com o nome digitado; só depois vêm os
 * campos e o botão "Confirmo que não existe, cadastrar". Ninguém cadastra sem ter olhado.
 */
export function NovoIngredienteDialogo({ pedido, onFechar, onUsar, onCriado }: Props) {
  const [nome, setNome] = useState(pedido.nome);
  const [categoria, setCategoria] = useState(pedido.categoria);
  const [base, setBase] = useState(pedido.unidade_base);
  const [apelidos, setApelidos] = useState<string[]>(pedido.apelidos);
  const [existentes, setExistentes] = useState<IngredienteBusca[] | null>(null);
  const [juntados, setJuntados] = useState<Juntado[]>([]);
  const [reativar, setReativar] = useState<Juntado | null>(null);
  const [doCatalogo, setDoCatalogo] = useState<CatalogoSugerido[]>([]);
  // A pessoa mexeu no nome/categoria: o candidato do catálogo não sobrescreve mais.
  const editado = useRef(pedido.doCatalogo);
  const [igual, setIgual] = useState<IngredienteBusca | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  // Pré-preenche com o melhor candidato do catálogo (o do item; senão o do texto digitado), só com certeza.
  useEffect(() => {
    if (pedido.doCatalogo) return;
    let ativo = true;
    const consultas = [pedido.item?.trim() ?? "", pedido.nome.trim()].filter((c, i, todas) => c.length >= 2 && todas.indexOf(c) === i);
    void (async () => {
      for (const consulta of consultas) {
        const achadas = await sugerirIngrediente(consulta, "", true).catch(() => []);
        const certa = achadas.find((s) => s.destaque && s.catalogo);
        if (certa?.catalogo && ativo && !editado.current) {
          setNome(certa.catalogo.nome);
          setCategoria(certa.catalogo.categoria);
          setBase(certa.catalogo.unidade_base);
          setApelidos(certa.catalogo.apelidos);
          return;
        }
      }
      if (ativo && !editado.current) setNome((atual) => capitalizar(atual));
    })();
    return () => {
      ativo = false;
    };
    // só ao abrir
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Os que já existem e parecem com o nome: a padaria (os 3 mais próximos) e o catálogo (até 2, sem contradizer).
  useEffect(() => {
    const texto = nome.trim();
    if (texto.length < 2) {
      setExistentes(null);
      setDoCatalogo([]);
      setJuntados([]);
      return;
    }
    let ativo = true;
    const espera = setTimeout(() => {
      buscarIngredientes(texto)
        .then((r) => {
          if (!ativo) return;
          setExistentes(r.da_padaria.slice(0, 3));
          setJuntados(r.juntados ?? []);
        })
        .catch(() => ativo && setExistentes([]));
      sugerirIngrediente(texto, "", true)
        .then((s) => ativo && setDoCatalogo(s.flatMap((x) => (x.catalogo ? [x.catalogo] : [])).slice(0, 2)))
        .catch(() => ativo && setDoCatalogo([]));
    }, 250);
    return () => {
      ativo = false;
      clearTimeout(espera);
    };
  }, [nome]);

  async function cadastrar(event?: FormEvent) {
    event?.preventDefault();
    if (enviando || nome.trim().length === 0 || !categoria) return;
    setEnviando(true);
    setErro(null);
    setIgual(null);
    try {
      const criado = await criarIngrediente({
        nome: nome.trim(),
        unidade_base: base,
        categoria,
        apelidos,
      });
      onCriado(criado);
    } catch (falha) {
      if (falha instanceof ApiError && falha.codigo === "ingrediente_inativo") {
        const ficha = (falha.detalhe as { reativar?: Juntado } | null)?.reativar;
        if (ficha) setReativar(ficha);
      } else if (falha instanceof ApiError && falha.codigo === "ja_existe") {
        const existente = (falha.detalhe as { existente?: IngredienteBusca } | null)?.existente;
        if (existente) {
          setIgual({ ...existente, apelidos: existente.apelidos ?? [], saldo: existente.saldo ?? 0, itens: existente.itens ?? 0 });
        }
      }
      setErro(textoDoErro(falha));
      setEnviando(false);
    }
  }

  return (
    <Modal
      titulo="Cadastrar novo ingrediente"
      subtitulo={
        pedido.doCatalogo
          ? "Sugerido pelo catálogo. Confira antes de criar."
          : "Antes de criar, veja se ele já existe."
      }
      onFechar={onFechar}
      rodape={
        <div className="painel-acoes">
          <Button
            variant="primary"
            disabled={enviando || nome.trim().length === 0 || !categoria}
            onClick={() => void cadastrar()}
          >
            Confirmo que não existe, cadastrar
          </Button>
          <Button onClick={onFechar}>Cancelar</Button>
        </div>
      }
    >
      {juntados.map((j) => (
        <button key={j.id} type="button" className="ing-reativar" onClick={() => setReativar(j)}>
          <strong>{j.nome}</strong> foi juntado{j.destino_nome ? ` a ${j.destino_nome}` : ""}. Reativar
        </button>
      ))}
      <section className="novo-existentes" aria-labelledby="novo-existentes-titulo">
        <h3 id="novo-existentes-titulo">Estes já existem e parecem com o que você digitou</h3>
        {existentes === null ? (
          <p className="sub">Digite o nome abaixo para ver o que já existe.</p>
        ) : existentes.length === 0 && doCatalogo.length === 0 ? (
          <p className="sub">Nada parecido com “{nome.trim()}” na sua padaria nem no catálogo.</p>
        ) : (
          <ul className="novo-existentes-lista">
            {doCatalogo.map((c) => (
              <li key={`cat-${c.id}`}>
                <span className="novo-existente-nome">
                  <strong>{c.nome}</strong>
                  <span className="sub">
                    {c.categoria} · <span className="selo-catalogo">do catálogo</span>
                  </span>
                </span>
                <Button
                  aria-label={`Usar ${c.nome}, do catálogo`}
                  onClick={() => {
                    editado.current = true;
                    setNome(c.nome);
                    setCategoria(c.categoria);
                    setBase(c.unidade_base);
                    setApelidos(c.apelidos);
                    setIgual(null);
                    setErro(null);
                  }}
                >
                  Usar
                </Button>
              </li>
            ))}
            {existentes.map((e) => (
              <li key={e.id}>
                <span className="novo-existente-nome">
                  <strong>{e.nome}</strong>
                  <span className="sub">
                    {e.categoria} · {quantidadeBase(e.saldo, e.unidade_base)}
                  </span>
                </span>
                <Button aria-label={`Usar ${e.nome}`} onClick={() => onUsar(e)}>
                  Usar
                </Button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <form className="painel-form" onSubmit={(event) => void cadastrar(event)}>
        <label className="gestao-field">
          <span>Nome genérico</span>
          <input
            type="text"
            value={nome}
            maxLength={120}
            autoComplete="off"
            onChange={(e) => {
              editado.current = true;
              setNome(e.target.value);
              setIgual(null);
              setErro(null);
            }}
          />
        </label>
        <label className="gestao-field">
          <span>Categoria</span>
          <select
            value={categoria}
            onChange={(e) => {
              editado.current = true;
              setCategoria(e.target.value);
            }}
          >
            <option value="" disabled>
              Escolha a categoria
            </option>
            {CATEGORIAS.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        <label className="gestao-field">
          <span>Unidade base</span>
          <select value={base} onChange={(e) => setBase(e.target.value)}>
            {UNIDADES_BASE.map((u) => (
              <option key={u.valor} value={u.valor}>
                {u.rotulo}
              </option>
            ))}
          </select>
        </label>
        {apelidos.length > 0 ? (
          <p className="sub">Também chamado de: {apelidos.join(", ")}.</p>
        ) : null}
        {erro ? (
          <div role="alert" className="form-erro">
            <p>{erro}</p>
            {igual ? (
              <Button aria-label={`Usar ${igual.nome}`} onClick={() => onUsar(igual)}>
                Usar “{igual.nome}”
              </Button>
            ) : null}
          </div>
        ) : null}
      </form>
      {reativar ? (
        <ReativarIngredienteDialog
          juntado={reativar}
          onFechar={() => setReativar(null)}
          onReativado={() => {
            setReativar(null);
            setJuntados((lista) => lista.filter((j) => j.id !== reativar.id));
            onFechar();
          }}
        />
      ) : null}
    </Modal>
  );
}
