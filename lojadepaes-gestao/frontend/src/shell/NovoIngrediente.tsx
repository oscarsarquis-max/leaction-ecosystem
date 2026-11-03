import { useEffect, useState, type FormEvent } from "react";
import {
  ApiError,
  buscarIngredientes,
  criarIngrediente,
  textoDoErro,
  type IngredienteBusca,
  type IngredienteDetalhe,
} from "../lib/api";
import { CATEGORIAS, UNIDADES_BASE } from "../lib/categorias";
import { quantidadeBase } from "../lib/format";
import { Button } from "./Button";
import { SidePanel } from "./SidePanel";

/** O que o diálogo recebe para começar: o que a pessoa digitou ou a entrada do catálogo escolhida. */
export type PedidoCadastro = {
  nome: string;
  categoria: string;
  unidade_base: string;
  apelidos: string[];
  doCatalogo: boolean;
};

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
  const [existentes, setExistentes] = useState<IngredienteBusca[] | null>(null);
  const [igual, setIgual] = useState<IngredienteBusca | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  // Os que já existem e parecem com o nome (a busca da padaria, os 3 mais próximos).
  useEffect(() => {
    const texto = nome.trim();
    if (texto.length < 2) {
      setExistentes(null);
      return;
    }
    let ativo = true;
    const espera = setTimeout(() => {
      buscarIngredientes(texto)
        .then((r) => ativo && setExistentes(r.da_padaria.slice(0, 3)))
        .catch(() => ativo && setExistentes([]));
    }, 250);
    return () => {
      ativo = false;
      clearTimeout(espera);
    };
  }, [nome]);

  async function cadastrar(event?: FormEvent) {
    event?.preventDefault();
    if (enviando || nome.trim().length === 0) return;
    setEnviando(true);
    setErro(null);
    setIgual(null);
    try {
      const criado = await criarIngrediente({
        nome: nome.trim(),
        unidade_base: base,
        categoria,
        apelidos: pedido.apelidos,
      });
      onCriado(criado);
    } catch (falha) {
      if (falha instanceof ApiError && falha.codigo === "ja_existe") {
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
    <SidePanel
      titulo="Cadastrar novo ingrediente"
      subtitulo={
        pedido.doCatalogo
          ? "Sugerido pelo catálogo. Confira antes de criar."
          : "Antes de criar, veja se ele já existe."
      }
      onFechar={onFechar}
      rodape={
        <div className="painel-acoes">
          <Button variant="primary" disabled={enviando || nome.trim().length === 0} onClick={() => void cadastrar()}>
            Confirmo que não existe, cadastrar
          </Button>
          <Button onClick={onFechar}>Cancelar</Button>
        </div>
      }
    >
      <section className="novo-existentes" aria-labelledby="novo-existentes-titulo">
        <h3 id="novo-existentes-titulo">Estes já existem e parecem com o que você digitou</h3>
        {existentes === null ? (
          <p className="sub">Digite o nome abaixo para ver o que já existe.</p>
        ) : existentes.length === 0 ? (
          <p className="sub">Nada parecido com “{nome.trim()}” na sua padaria.</p>
        ) : (
          <ul className="novo-existentes-lista">
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
              setNome(e.target.value);
              setIgual(null);
              setErro(null);
            }}
          />
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
          <span>Unidade base</span>
          <select value={base} onChange={(e) => setBase(e.target.value)}>
            {UNIDADES_BASE.map((u) => (
              <option key={u.valor} value={u.valor}>
                {u.rotulo}
              </option>
            ))}
          </select>
        </label>
        {pedido.apelidos.length > 0 ? (
          <p className="sub">Também chamado de: {pedido.apelidos.join(", ")}.</p>
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
    </SidePanel>
  );
}
