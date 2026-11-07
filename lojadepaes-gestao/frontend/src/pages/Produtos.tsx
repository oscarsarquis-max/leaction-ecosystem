import { useCallback, useEffect, useRef, useState } from "react";
import { useGestao } from "../contexto";
import {
  ApiError,
  apagarFamilia,
  buscarItensEstoque,
  criarFamilia,
  criarProduto,
  detalheProduto,
  dispensarSugestoesFamilia,
  editarProduto,
  enviarFoto,
  inativarProduto,
  removerFoto,
  listarFamilias,
  listarProdutos,
  textoDoErro,
  type FamiliasLista,
  type FiltroProdutos,
  type ItemDeProduto,
  type ProdutoDetalhe,
  type ProdutoEnvio,
  type ProdutoLinha,
  type ProdutosLista,
} from "../lib/api";
import { casaBusca } from "../lib/buscaLista";
import { custoPorUnidade, dataCurta, dinheiro, quantidadeBase } from "../lib/format";
import { Button } from "../shell/Button";
import { Card } from "../shell/Card";
import { Chips } from "../shell/Chips";
import { Modal } from "../shell/Modal";
import { PageHeader } from "../shell/PageHeader";
import { SidePanel } from "../shell/SidePanel";
import { StatusChip } from "../shell/StatusChip";
import "./fluxo.css";

const FILTROS: { valor: FiltroProdutos; rotulo: string }[] = [
  { valor: "todos", rotulo: "Todos" },
  { valor: "produzidos", rotulo: "Produzidos" },
  { valor: "comprados", rotulo: "Comprados" },
  { valor: "componentes", rotulo: "Componentes" },
  { valor: "pendentes", rotulo: "Pendentes" },
];

const SELOS: Record<string, string> = { sem_receita: "Sem receita", sem_item: "Sem item" };

function filtroDaUrl(search: string): FiltroProdutos {
  const valor = new URLSearchParams(search).get("filtro");
  return FILTROS.some((f) => f.valor === valor) ? (valor as FiltroProdutos) : "todos";
}

function familiaDaUrl(search: string): string {
  return new URLSearchParams(search).get("familia") ?? "";
}

function urlDaLista(filtro: FiltroProdutos, familia: string): string {
  const partes: string[] = [];
  if (filtro !== "todos") partes.push(`filtro=${filtro}`);
  if (familia) partes.push(`familia=${encodeURIComponent(familia)}`);
  return partes.length ? `/produtos?${partes.join("&")}` : "/produtos";
}

function unidadeVenda(unidade: string): string {
  return unidade === "kg" ? "kg" : "unidade";
}

function modalidadeTexto(modalidade: string): string {
  return modalidade === "comprado" ? "Comprado" : "Produzido";
}

function usoTexto(venda: boolean, componente: boolean): string {
  if (venda && componente) return "Venda e componente";
  if (componente) return "Componente";
  return "Venda";
}

function X() {
  return (
    <svg width="14" height="14" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <path d="M5 5l10 10M15 5 5 15" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
    </svg>
  );
}

function BuscaItem({
  valor,
  onEscolher,
}: {
  valor: ItemDeProduto | null;
  onEscolher: (item: ItemDeProduto | null) => void;
}) {
  const [texto, setTexto] = useState("");
  const [itens, setItens] = useState<ItemDeProduto[]>([]);

  useEffect(() => {
    if (valor) return;
    let vivo = true;
    const espera = setTimeout(() => {
      buscarItensEstoque(texto.trim())
        .then((lista) => vivo && setItens(lista))
        .catch(() => vivo && setItens([]));
    }, 200);
    return () => {
      vivo = false;
      clearTimeout(espera);
    };
  }, [texto, valor]);

  if (valor) {
    return (
      <div className="ing-chip" role="group" aria-label="Item de estoque">
        <span className="ing-chip-texto">
          <strong>{valor.nome}</strong>
          {valor.ingrediente ? <small>{valor.ingrediente}</small> : null}
        </span>
        <button type="button" className="ing-chip-x" aria-label={`Trocar o item ${valor.nome}`} onClick={() => onEscolher(null)}>
          <X />
        </button>
      </div>
    );
  }

  return (
    <>
      <label className="gestao-field">
        <span>Item de estoque</span>
        <input
          type="search"
          value={texto}
          placeholder="Buscar item de estoque"
          onChange={(e) => setTexto(e.target.value)}
        />
      </label>
      {itens.length > 0 ? (
        <ul className="pares" aria-label="Itens de estoque">
          {itens.map((item) => (
            <li key={item.id}>
              <button type="button" className="gestao-btn" onClick={() => onEscolher(item)}>
                {item.nome}
                {item.marca ? ` · ${item.marca}` : ""} · {quantidadeBase(item.saldo, item.unidade_base)}
              </button>
            </li>
          ))}
        </ul>
      ) : texto.trim() ? (
        <p className="sub">Nenhum item com esse nome.</p>
      ) : null}
    </>
  );
}

function FormProduto({
  titulo,
  modalidadeFixa,
  inicial,
  familias,
  enviando,
  erro,
  parecidos,
  itemInicial = null,
  onCancelar,
  onEnviar,
}: {
  titulo: string;
  modalidadeFixa: "produzido" | "comprado" | null;
  inicial: ProdutoEnvio;
  familias: { id: string; nome: string }[];
  enviando: boolean;
  erro: string | null;
  parecidos: string[];
  itemInicial?: ItemDeProduto | null;
  onCancelar: () => void;
  onEnviar: (corpo: ProdutoEnvio, confirmado: boolean, foto: File | null) => void;
}) {
  const [nome, setNome] = useState(inicial.nome);
  const [modalidade, setModalidade] = useState<"produzido" | "comprado">(inicial.modalidade ?? "produzido");
  const [venda, setVenda] = useState(inicial.uso_venda);
  const [componente, setComponente] = useState(inicial.uso_componente);
  const [familiaId, setFamiliaId] = useState(inicial.familia_id ?? "");
  const [unidade, setUnidade] = useState<"un" | "kg">(inicial.unidade_venda);
  const [base, setBase] = useState<"g" | "ml" | "un">(inicial.unidade_base ?? "g");
  const [item, setItem] = useState<ItemDeProduto | null>(itemInicial);
  const [foto, setFoto] = useState<File | null>(null);
  const [previaFoto, setPreviaFoto] = useState<string | null>(null);
  const [fotoAberta, setFotoAberta] = useState(false);
  const modo = modalidadeFixa ?? modalidade;
  const pronto = nome.trim().length > 0 && (venda || componente);

  function enviar(event: { preventDefault(): void }, confirmado = false) {
    event.preventDefault();
    if (!pronto) return;
    onEnviar(
      {
        nome: nome.trim(),
        modalidade: modo,
        uso_venda: venda,
        uso_componente: componente,
        familia_id: familiaId || null,
        unidade_venda: unidade,
        unidade_base: componente ? base : undefined,
        item_estoque_id: modo === "comprado" ? item?.id ?? null : null,
      },
      confirmado,
      modalidadeFixa ? null : foto,
    );
  }

  return (
    <form className="painel-form" onSubmit={(event) => enviar(event)} aria-label={titulo}>
      {modalidadeFixa ? <h3>{titulo}</h3> : null}
      <label className="gestao-field">
        <span>Nome</span>
        <input type="text" value={nome} maxLength={120} onChange={(e) => setNome(e.target.value)} />
      </label>
      {modalidadeFixa ? (
        <p className="sub">Modalidade: {modalidadeTexto(modalidadeFixa)}.</p>
      ) : (
        <fieldset className="painel-opcoes">
          <legend>Modalidade</legend>
          <label>
            <input type="radio" name="modalidade" checked={modalidade === "produzido"} onChange={() => setModalidade("produzido")} />
            <span>Produzido</span>
          </label>
          <label>
            <input type="radio" name="modalidade" checked={modalidade === "comprado"} onChange={() => setModalidade("comprado")} />
            <span>Comprado</span>
          </label>
        </fieldset>
      )}
      <fieldset className="painel-opcoes">
        <legend>Uso</legend>
        <label>
          <input type="checkbox" checked={venda} onChange={(e) => setVenda(e.target.checked)} />
          <span>Venda</span>
        </label>
        <label>
          <input type="checkbox" checked={componente} onChange={(e) => setComponente(e.target.checked)} />
          <span>Componente</span>
        </label>
      </fieldset>
      {componente ? (
        <label className="gestao-field">
          <span>Unidade base do preparo</span>
          <select value={base} onChange={(e) => setBase(e.target.value === "ml" ? "ml" : e.target.value === "un" ? "un" : "g")}>
            <option value="g">g</option>
            <option value="ml">ml</option>
            <option value="un">un</option>
          </select>
        </label>
      ) : null}
      {!venda && !componente ? <p className="form-erro">Escolha Venda, Componente ou os dois.</p> : null}
      <label className="gestao-field">
        <span>Família</span>
        <select value={familiaId} onChange={(e) => setFamiliaId(e.target.value)}>
          <option value="">Sem família</option>
          {familias.map((f) => (
            <option key={f.id} value={f.id}>
              {f.nome}
            </option>
          ))}
        </select>
      </label>
      {!modalidadeFixa ? (
        <div className="gestao-field">
          <span>Foto</span>
          {previaFoto ? (
            <div className="foto-quadro">
              <img src={previaFoto} alt="Prévia da foto" />
            </div>
          ) : (
            <p className="sub">Opcional.</p>
          )}
          <Button type="button" onClick={() => setFotoAberta(true)}>
            {foto ? "Trocar foto" : "Adicionar foto"}
          </Button>
        </div>
      ) : null}
      <label className="gestao-field">
        <span>Unidade de venda</span>
        <select value={unidade} onChange={(e) => setUnidade(e.target.value === "kg" ? "kg" : "un")}>
          <option value="un">unidade</option>
          <option value="kg">kg</option>
        </select>
      </label>
      {modo === "comprado" ? <BuscaItem valor={item} onEscolher={setItem} /> : null}
      {erro ? (
        <div role="alert" className="form-erro">
          <p>{erro}</p>
          {parecidos.length > 0 ? <p className="sub">Parecido com {parecidos.join(", ")}.</p> : null}
        </div>
      ) : null}
      <div className="painel-acoes">
        {parecidos.length > 0 ? (
          <Button type="button" variant="primary" disabled={enviando || !pronto} onClick={(event) => enviar(event, true)}>
            Confirmo que não existe, cadastrar
          </Button>
        ) : (
          <Button type="submit" variant="primary" disabled={enviando || !pronto}>
            {modalidadeFixa ? "Salvar" : "Cadastrar"}
          </Button>
        )}
        <Button onClick={onCancelar}>Cancelar</Button>
      </div>
      {fotoAberta ? (
        <DialogoFoto
          onFechar={() => setFotoAberta(false)}
          onConfirmar={async (arquivo, imagem) => {
            setFoto(arquivo);
            setPreviaFoto(imagem);
          }}
        />
      ) : null}
    </form>
  );
}

function inicialDe(nome: string): string {
  const letra = nome.trim().charAt(0);
  return letra ? letra.toLocaleUpperCase("pt-BR") : "?";
}

function Miniatura({ nome, url }: { nome: string; url: string | null }) {
  const [falhou, setFalhou] = useState(false);
  if (!url || falhou) {
    return <span className="foto-inicial" aria-hidden="true">{inicialDe(nome)}</span>;
  }
  return <img className="foto-mini" src={url} alt="" onError={() => setFalhou(true)} />;
}

const LIMITE_FOTO = 10 * 1024 * 1024;

function urlDaFoto(id: string, temFoto: boolean, fotoUrl: string | null, enviadaEm: string | null, mini: boolean): string | null {
  if (!temFoto) return fotoUrl;
  const caminho = mini ? `/api/v1/produtos/${id}/foto/mini` : `/api/v1/produtos/${id}/foto`;
  return `${caminho}?v=${encodeURIComponent(enviadaEm ?? "")}`;
}

function erroDoArquivo(arquivo: File): string | null {
  if (arquivo.size > LIMITE_FOTO) return "Arquivo maior que 10 MB";
  const nome = arquivo.name.toLowerCase();
  const tipo = arquivo.type.toLowerCase();
  const tipos = ["image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"];
  const extensoes = [".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"];
  if (!tipos.includes(tipo) && !extensoes.some((ext) => nome.endsWith(ext))) return "Formato não aceito";
  return null;
}

function previa43(arquivo: File): Promise<string | null> {
  return createImageBitmap(arquivo)
    .then((bitmap) => {
      const quadro = document.createElement("canvas");
      quadro.width = 640;
      quadro.height = 480;
      const ctx = quadro.getContext("2d");
      if (!ctx) return null;
      const escala = Math.max(quadro.width / bitmap.width, quadro.height / bitmap.height);
      const largura = bitmap.width * escala;
      const altura = bitmap.height * escala;
      ctx.drawImage(bitmap, (quadro.width - largura) / 2, (quadro.height - altura) / 2, largura, altura);
      bitmap.close();
      return quadro.toDataURL("image/jpeg", 0.85);
    })
    .catch(() => null);
}

function DialogoFoto({
  onFechar,
  onConfirmar,
}: {
  onFechar: () => void;
  onConfirmar: (arquivo: File, previa: string | null, aoProgresso: (pct: number) => void) => Promise<void>;
}) {
  const arquivoRef = useRef<HTMLInputElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [previa, setPrevia] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [pct, setPct] = useState(0);

  async function escolher(escolhido: File | null) {
    if (!escolhido) return;
    const recado = erroDoArquivo(escolhido);
    setArquivo(recado ? null : escolhido);
    setPrevia(recado ? null : await previa43(escolhido));
    setErro(recado);
  }

  async function lerEscolha(input: HTMLInputElement) {
    const escolhido = input.files?.[0];
    if (!escolhido) return;
    const copia = new File([await escolhido.arrayBuffer()], escolhido.name, { type: escolhido.type || "image/jpeg" });
    input.value = "";
    await escolher(copia);
  }

  return (
    <Modal titulo="Foto do produto" onFechar={enviando ? () => undefined : onFechar}>
      <div className="painel-form">
        <input
          ref={arquivoRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,image/heic,image/heif,.jpg,.jpeg,.png,.webp,.heic,.heif"
          hidden
          onChange={(e) => void lerEscolha(e.target)}
        />
        <input
          ref={cameraRef}
          type="file"
          accept="image/*"
          capture="environment"
          hidden
          onChange={(e) => void lerEscolha(e.target)}
        />
        <div className="painel-acoes">
          <Button type="button" onClick={() => arquivoRef.current?.click()}>Escolher arquivo</Button>
          <Button type="button" onClick={() => cameraRef.current?.click()}>Tirar foto</Button>
        </div>
        {previa ? (
          <div className="foto-quadro">
            <img src={previa} alt="Prévia da foto" />
          </div>
        ) : arquivo ? (
          <p className="sub">A prévia não abre neste navegador. A foto será gravada ao salvar.</p>
        ) : (
          <div className="foto-quadro">
            <span className="foto-vazio">
              <span className="foto-inicial" aria-hidden="true">?</span>
            </span>
          </div>
        )}
        {enviando ? (
          <div className="foto-progresso" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
            <span style={{ width: `${pct}%` }} />
          </div>
        ) : null}
        {erro ? <p role="alert" className="form-erro">{erro}</p> : null}
        <div className="painel-acoes">
          <Button
            type="button"
            variant="primary"
            disabled={!arquivo || enviando}
            onClick={() => {
              if (!arquivo) return;
              setEnviando(true);
              setPct(0);
              setErro(null);
              void onConfirmar(arquivo, previa, setPct)
                .then(onFechar)
                .catch((falha: unknown) => setErro(textoDoErro(falha)))
                .finally(() => setEnviando(false));
            }}
          >
            Salvar
          </Button>
          <Button type="button" onClick={onFechar} disabled={enviando}>Cancelar</Button>
        </div>
      </div>
    </Modal>
  );
}

function FotoDoProduto({
  dados,
  podeEnviar,
  onAdicionar,
  onTrocar,
  onRemover,
}: {
  dados: ProdutoDetalhe;
  podeEnviar: boolean;
  onAdicionar: () => void;
  onTrocar: () => void;
  onRemover: () => void;
}) {
  const [menu, setMenu] = useState(false);
  const [falhou, setFalhou] = useState(false);
  const url = falhou ? null : urlDaFoto(dados.id, dados.tem_foto, dados.foto_url, dados.foto_enviada_em, false);
  const origem = dados.tem_foto && dados.foto_enviada_em
    ? `Foto enviada em ${dataCurta(dados.foto_enviada_em.slice(0, 10))}`
    : dados.importado_em
      ? `Importado da Loja em ${dataCurta(dados.importado_em)}`
      : null;
  return (
    <div className="foto-bloco">
      <div className="foto-quadro">
        {url ? (
          <img src={url} alt={dados.nome} onError={() => setFalhou(true)} />
        ) : (
          <span className="foto-vazio">
            <span className="foto-inicial" aria-hidden="true">{inicialDe(dados.nome)}</span>
            {podeEnviar ? <Button type="button" onClick={onAdicionar}>Adicionar foto</Button> : null}
          </span>
        )}
      </div>
      {url && podeEnviar ? (
        <div className="foto-menu linha-menu">
          <button type="button" className="linha-menu-botao" aria-label="Ações da foto" aria-expanded={menu} onClick={() => setMenu((aberto) => !aberto)}>
            ⋯
          </button>
          {menu ? (
            <div className="linha-menu-lista" role="menu">
              <button type="button" role="menuitem" onClick={() => { setMenu(false); onTrocar(); }}>Trocar foto</button>
              {dados.tem_foto ? (
                <button type="button" role="menuitem" className="perigo" onClick={() => { setMenu(false); onRemover(); }}>
                  Remover foto enviada
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}
      {origem ? <p className="foto-origem">{origem}</p> : null}
    </div>
  );
}

function textoCusto(dados: ProdutoDetalhe): string {
  const receita = dados.receita;
  if (!receita) return "";
  if (receita.custo_parcial) {
    const valor = receita.custo_por_unidade == null ? "—" : `${dinheiro(receita.custo_por_unidade)} parcial`;
    const linhas = receita.linhas_sem_custo === 1 ? "linha" : "linhas";
    return ` · ${valor} · falta o custo de ${receita.linhas_sem_custo} ${linhas}`;
  }
  return receita.custo_por_unidade != null ? ` · ${dinheiro(receita.custo_por_unidade)} por unidade` : "";
}

function Estrutura({ dados, onMontar }: { dados: ProdutoDetalhe; onMontar: (id: string) => void }) {
  const linhas = dados.receita?.linhas ?? [];
  return (
    <section className="painel-secao" aria-label="Estrutura">
      <h3>Estrutura</h3>
      <ol className="estrutura">
        <li className="estrutura-no">
          <strong>{dados.nome}</strong>
          <span className="sub">Produto</span>
        </li>
        {dados.modalidade === "produzido" ? (
          <>
            <li className="estrutura-liga" aria-hidden="true" />
            <li className="estrutura-no">
              <strong>Receita técnica</strong>
              <span className="sub">
                {dados.receita?.publicada ? `Versão ${dados.receita.versao}` : "Rascunho"}
                {dados.receita?.custo_parcial ? (
                  <span className="custo-parcial">{textoCusto(dados)}</span>
                ) : (
                  textoCusto(dados)
                )}
              </span>
            </li>
            <li className="estrutura-liga" aria-hidden="true" />
            {linhas.length === 0 ? (
              <li className="estrutura-vazio">Receita ainda vazia</li>
            ) : (
              linhas.map((linha) => (
                <li key={linha.id} className={linha.componente ? "estrutura-no componente" : "estrutura-no"}>
                  <strong>{linha.nome}</strong>
                  <span className="sub">
                    {linha.quantidade ?? "—"} {linha.unidade}
                    {linha.componente ? " · Componente" : ""}
                  </span>
                </li>
              ))
            )}
            <li className="estrutura-liga" aria-hidden="true" />
            <li>
              <Button variant="primary" onClick={() => onMontar(dados.id)}>
                Montar receita
              </Button>
            </li>
          </>
        ) : (
          <>
            <li className="estrutura-liga" aria-hidden="true" />
            {dados.item ? (
              <li className="estrutura-no">
                <strong>{dados.item.nome}</strong>
                <span className="sub">Item de estoque</span>
              </li>
            ) : (
              <li className="estrutura-vazio">Sem item de estoque</li>
            )}
          </>
        )}
      </ol>
    </section>
  );
}

function PainelProduto({
  id,
  onFechar,
  aoMudar,
  onAbrirIngrediente,
  onMontar,
}: {
  id: string;
  onFechar: () => void;
  aoMudar: () => void;
  onAbrirIngrediente: (id: string) => void;
  onMontar: (id: string) => void;
}) {
  const { pode } = useGestao();
  const [dados, setDados] = useState<ProdutoDetalhe | null>(null);
  const [familias, setFamilias] = useState<FamiliasLista | null>(null);
  const [falhou, setFalhou] = useState(false);
  const [modo, setModo] = useState<"ver" | "editar">("ver");
  const [inativar, setInativar] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [parecidos, setParecidos] = useState<string[]>([]);
  const [enviando, setEnviando] = useState(false);
  const [fotoAberta, setFotoAberta] = useState(false);

  const carregar = useCallback(async () => {
    try {
      setDados(await detalheProduto(id));
      setFalhou(false);
    } catch {
      setFalhou(true);
    }
  }, [id]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  useEffect(() => {
    if (modo !== "editar") return;
    void listarFamilias().then(setFamilias).catch(() => setFamilias({ familias: [], sugestoes: [] }));
  }, [modo]);

  async function salvar(corpo: ProdutoEnvio, confirmado: boolean) {
    if (!dados) return;
    setEnviando(true);
    setErro(null);
    try {
      const novo = await editarProduto(dados.id, {
        nome: corpo.nome,
        uso_venda: corpo.uso_venda,
        uso_componente: corpo.uso_componente,
        familia_id: corpo.familia_id,
        unidade_venda: corpo.unidade_venda,
        unidade_base: corpo.unidade_base,
        item_estoque_id: corpo.item_estoque_id,
        confirmado_inexistente: confirmado,
      });
      setDados(novo);
      setModo("ver");
      setParecidos([]);
      aoMudar();
    } catch (falha) {
      setErro(textoDoErro(falha));
      const lista =
        falha instanceof ApiError ? (falha.detalhe as { parecidos?: { nome: string }[] } | null)?.parecidos : undefined;
      setParecidos(falha instanceof ApiError && falha.codigo === "produto_parecido" ? (lista ?? []).map((p) => p.nome) : []);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <SidePanel
      titulo={dados?.nome ?? "Produto"}
      subtitulo={dados ? `${modalidadeTexto(dados.modalidade)} · ${usoTexto(dados.uso_venda, dados.uso_componente)}` : undefined}
      onFechar={onFechar}
      rodape={
        dados && modo === "ver" && pode("lancar") ? (
          <div className="painel-acoes">
            <Button variant="primary" onClick={() => setModo("editar")}>
              Editar
            </Button>
            <Button onClick={() => setInativar(true)}>Inativar</Button>
          </div>
        ) : undefined
      }
    >
      {falhou ? <p role="alert">Não foi possível abrir este produto agora.</p> : null}
      {!dados && !falhou ? <p>Carregando.</p> : null}
      {dados && modo === "editar" ? (
        <FormProduto
          titulo="Editar produto"
          modalidadeFixa={dados.modalidade}
          inicial={{
            nome: dados.nome,
            modalidade: dados.modalidade,
            uso_venda: dados.uso_venda,
            uso_componente: dados.uso_componente,
            familia_id: dados.familia_id,
            unidade_venda: dados.unidade_venda,
            unidade_base: dados.unidade_base,
            item_estoque_id: dados.item?.id ?? null,
          }}
          familias={familias?.familias ?? []}
          enviando={enviando}
          erro={erro}
          parecidos={parecidos}
          itemInicial={dados.item}
          onCancelar={() => {
            setModo("ver");
            setErro(null);
            setParecidos([]);
          }}
          onEnviar={(corpo, confirmado) => void salvar(corpo, confirmado)}
        />
      ) : null}
      {dados && modo === "ver" ? (
        <>
          <FotoDoProduto
            key={`${dados.id}-${dados.foto_enviada_em ?? ""}-${dados.foto_url ?? ""}`}
            dados={dados}
            podeEnviar={pode("lancar")}
            onAdicionar={() => setFotoAberta(true)}
            onTrocar={() => setFotoAberta(true)}
            onRemover={() => {
              void removerFoto(dados.id)
                .then((novo) => {
                  setDados(novo);
                  aoMudar();
                })
                .catch((falha: unknown) => setErro(textoDoErro(falha)));
            }}
          />
          {erro ? <p role="alert" className="form-erro">{erro}</p> : null}
          <Estrutura dados={dados} onMontar={onMontar} />
          <section className="painel-secao" aria-label="Usado em">
            <h3>Usado em</h3>
            {dados.usado_em.length === 0 ? (
              <p className="sub">Nenhum produto usa este ainda.</p>
            ) : (
              <ul className="pares">
                {dados.usado_em.map((p) => (
                  <li key={p.id}>{p.nome}</li>
                ))}
              </ul>
            )}
          </section>
          {dados.modalidade === "comprado" && dados.item ? (
            <section className="painel-secao" aria-label="Item de estoque">
              <h3>Item de estoque</h3>
              <dl className="painel-fatos">
                <div>
                  <dt>Item</dt>
                  <dd>{dados.item.nome}{dados.item.marca ? ` · ${dados.item.marca}` : ""}</dd>
                </div>
                <div>
                  <dt>Saldo</dt>
                  <dd>{quantidadeBase(dados.item.saldo, dados.item.unidade_base)}</dd>
                </div>
                <div>
                  <dt>Custo médio</dt>
                  <dd>
                    {dados.item.custo_medio_base == null
                      ? "sem custo informado"
                      : custoPorUnidade(dados.item.custo_medio_base, dados.item.unidade_base)}
                  </dd>
                </div>
              </dl>
              <Button onClick={() => onAbrirIngrediente(dados.item!.ingrediente_id)}>Abrir ingrediente</Button>
            </section>
          ) : null}
          {dados.ingrediente_id ? (
            <p className="sub">
              Entra na busca de ingredientes como Preparos da casa.{" "}
              <button type="button" className="gestao-btn" onClick={() => onAbrirIngrediente(dados.ingrediente_id!)}>
                Ver em Ingredientes
              </button>
            </p>
          ) : null}
        </>
      ) : null}
      {inativar && dados ? (
        <Modal titulo="Inativar produto" onFechar={() => setInativar(false)}>
          <form
            className="painel-form"
            onSubmit={(event) => {
              event.preventDefault();
              setEnviando(true);
              void inativarProduto(dados.id)
                .then(() => {
                  setInativar(false);
                  aoMudar();
                  onFechar();
                })
                .catch((falha: unknown) => setErro(textoDoErro(falha)))
                .finally(() => setEnviando(false));
            }}
          >
            <p>“{dados.nome}” sai da lista. O ingrediente do componente, se existir, não é apagado.</p>
            {erro ? <p role="alert" className="form-erro">{erro}</p> : null}
            <div className="painel-acoes">
              <Button type="submit" variant="danger" disabled={enviando}>
                Inativar
              </Button>
              <Button onClick={() => setInativar(false)}>Cancelar</Button>
            </div>
          </form>
        </Modal>
      ) : null}
      {fotoAberta && dados ? (
        <DialogoFoto
          onFechar={() => setFotoAberta(false)}
          onConfirmar={async (arquivo, _previa, progresso) => {
            const novo = await enviarFoto(dados.id, arquivo, progresso);
            setDados(novo);
            aoMudar();
          }}
        />
      ) : null}
    </SidePanel>
  );
}

function DialogoFamilias({ onFechar, aoMudar }: { onFechar: () => void; aoMudar: () => void }) {
  const [dados, setDados] = useState<FamiliasLista | null>(null);
  const [nome, setNome] = useState("");
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    try {
      setDados(await listarFamilias());
      setErro(null);
    } catch (falha) {
      setErro(textoDoErro(falha));
    }
  }, []);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  async function aceitar(sugerida: string) {
    try {
      await criarFamilia(sugerida);
      await carregar();
      aoMudar();
    } catch (falha) {
      setErro(textoDoErro(falha));
    }
  }

  return (
    <Modal titulo="Famílias" onFechar={onFechar}>
      <form
        className="painel-form"
        aria-label="Famílias"
        onSubmit={(event) => {
          event.preventDefault();
          if (!nome.trim()) return;
          void aceitar(nome.trim()).then(() => setNome(""));
        }}
      >
        {erro ? <p role="alert" className="form-erro">{erro}</p> : null}
        {dados && dados.sugestoes.length > 0 ? (
          <fieldset className="painel-opcoes">
            <legend>Sugestões</legend>
            {dados.sugestoes.map((s) => (
              <Button key={s} onClick={() => void aceitar(s)}>
                {s}
              </Button>
            ))}
            <Button
              onClick={() => {
                void dispensarSugestoesFamilia()
                  .then(() => carregar())
                  .catch((falha: unknown) => setErro(textoDoErro(falha)));
              }}
            >
              Não quero estas sugestões
            </Button>
          </fieldset>
        ) : null}
        <ul className="pares" aria-label="Famílias da padaria">
          {(dados?.familias ?? []).map((f) => (
            <li key={f.id} className="item-com-menu">
              <span>{f.nome}</span>
              <Button
                onClick={() => {
                  void apagarFamilia(f.id)
                    .then(() => {
                      void carregar();
                      aoMudar();
                    })
                    .catch((falha: unknown) => setErro(textoDoErro(falha)));
                }}
              >
                Apagar
              </Button>
            </li>
          ))}
        </ul>
        {(dados?.familias ?? []).length === 0 ? <p className="sub">Nenhuma família ainda.</p> : null}
        <label className="gestao-field">
          <span>Nova família</span>
          <input type="text" value={nome} maxLength={80} onChange={(e) => setNome(e.target.value)} />
        </label>
        <div className="painel-acoes">
          <Button type="submit" variant="primary" disabled={!nome.trim()}>
            Criar
          </Button>
          <Button onClick={onFechar}>Fechar</Button>
        </div>
      </form>
    </Modal>
  );
}

export function Produtos() {
  const { search, navegar, pode, atualizarFluxo } = useGestao();
  const filtro = filtroDaUrl(search);
  const familia = familiaDaUrl(search);
  const [novo, setNovo] = useState(() => new URLSearchParams(search).get("novo") === "1");
  const [familiasAberto, setFamiliasAberto] = useState(false);
  const [dados, setDados] = useState<ProdutosLista | null>(null);
  const [catalogoFamilias, setCatalogoFamilias] = useState<FamiliasLista | null>(null);
  const [falhou, setFalhou] = useState(false);
  const [painel, setPainel] = useState<string | null>(null);
  const [busca, setBusca] = useState("");
  const [erroNovo, setErroNovo] = useState<string | null>(null);
  const [parecidos, setParecidos] = useState<string[]>([]);
  const [enviando, setEnviando] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

  const carregar = useCallback(async (f: FiltroProdutos, fam: string) => {
    setFalhou(false);
    try {
      setDados(await listarProdutos(f, fam));
    } catch (erro) {
      if (!(erro instanceof ApiError && erro.status === 401)) setFalhou(true);
    }
  }, []);

  useEffect(() => {
    void carregar(filtro, familia);
  }, [carregar, filtro, familia]);

  useEffect(() => {
    if (new URLSearchParams(search).get("novo") === "1") setNovo(true);
  }, [search]);

  function mudou() {
    void carregar(filtro, familia);
    atualizarFluxo();
  }

  function fecharNovo() {
    setNovo(false);
    setErroNovo(null);
    setParecidos([]);
    if (new URLSearchParams(search).get("novo") === "1") navegar(urlDaLista(filtro, familia), true);
  }

  async function cadastrar(corpo: ProdutoEnvio, confirmado: boolean, foto: File | null) {
    setEnviando(true);
    setErroNovo(null);
    setAviso(null);
    try {
      const criado = await criarProduto({ ...corpo, confirmado_inexistente: confirmado });
      if (foto) {
        try {
          await enviarFoto(criado.id, foto, () => undefined);
        } catch (falha) {
          setParecidos([]);
          fecharNovo();
          mudou();
          setPainel(criado.id);
          setAviso(`O produto entrou, mas a foto não: ${textoDoErro(falha)}`);
          return;
        }
      }
      setParecidos([]);
      fecharNovo();
      mudou();
      setPainel(criado.id);
    } catch (falha) {
      setErroNovo(textoDoErro(falha));
      const lista =
        falha instanceof ApiError ? (falha.detalhe as { parecidos?: { nome: string }[] } | null)?.parecidos : undefined;
      setParecidos(falha instanceof ApiError && falha.codigo === "produto_parecido" ? (lista ?? []).map((p) => p.nome) : []);
    } finally {
      setEnviando(false);
    }
  }

  const consulta = busca.trim();
  const visiveis = (dados?.produtos ?? []).filter((p) => casaBusca(consulta, [p.nome, p.familia, p.codigo]));
  const vazioDeVerdade = filtro === "todos" && !familia && !consulta;

  const acoes = pode("lancar") ? (
    <div className="acoes-cabecalho">
      <Button variant="primary" onClick={() => setNovo(true)}>
        Novo produto
      </Button>
      <Button onClick={() => setFamiliasAberto(true)}>Famílias</Button>
    </div>
  ) : null;

  return (
    <main className="fluxo-pagina">
      <PageHeader title="Produtos" description="O que eu vendo?" actions={acoes} />
      {aviso ? <p role="alert" className="form-erro">{aviso}</p> : null}
      <label className="gestao-field busca-lista">
        <span>Buscar produto</span>
        <input type="search" value={busca} placeholder="Buscar produto" onChange={(e) => setBusca(e.target.value)} />
      </label>
      <Chips rotulo="Filtrar produtos" opcoes={FILTROS} valor={filtro} onChange={(v) => navegar(urlDaLista(v, familia), true)} />
      {dados && dados.familias.length > 0 ? (
        <label className="gestao-field filtro-categoria">
          <span>Família</span>
          <select value={familia} onChange={(e) => navegar(urlDaLista(filtro, e.target.value), true)}>
            <option value="">Todas as famílias</option>
            {dados.familias.map((f) => (
              <option key={f.id} value={f.id}>
                {f.nome} ({f.total})
              </option>
            ))}
          </select>
        </label>
      ) : null}

      {falhou ? (
        <Card className="fluxo-vazio">
          <p role="alert">Não foi possível carregar os produtos agora.</p>
          <Button onClick={() => void carregar(filtro, familia)}>Tentar de novo</Button>
        </Card>
      ) : null}
      {!dados && !falhou ? <p className="fluxo-estado">Carregando os produtos.</p> : null}

      {dados && dados.produtos.length === 0 ? (
        <Card className="fluxo-vazio">
          <p>
            <strong>{vazioDeVerdade ? "Nenhum produto ainda." : "Nenhum produto neste filtro."}</strong>
          </p>
          <p>{vazioDeVerdade ? "Cadastre o primeiro em “Novo produto”." : "Troque o filtro para ver os outros."}</p>
        </Card>
      ) : null}
      {dados && dados.produtos.length > 0 && visiveis.length === 0 ? (
        <Card className="fluxo-vazio">
          <p>
            <strong>Nenhum produto para “{consulta}”.</strong>
          </p>
        </Card>
      ) : null}

      {visiveis.length > 0 ? (
        <Card className="fluxo-lista-card">
          <table className="lista-ingredientes" aria-label="Produtos">
            <colgroup>
              <col />
              <col className="c-saldo" />
              <col className="c-meio" />
              <col className="c-meio" />
              <col className="c-sit" />
            </colgroup>
            <thead>
              <tr>
                <th>Produto</th>
                <th>Modalidade</th>
                <th>Uso</th>
                <th>Família</th>
                <th>Situação</th>
              </tr>
            </thead>
            <tbody>
              {visiveis.map((p: ProdutoLinha) => (
                <tr className="ing-linha" key={p.id}>
                  <td className="col-ing">
                    <button type="button" className="ing-nome com-foto" onClick={() => setPainel(p.id)}>
                      <Miniatura nome={p.nome} url={urlDaFoto(p.id, p.tem_foto, p.foto_url, p.foto_enviada_em, true)} />
                      <span className="ing-textos">
                        <strong>{p.nome}</strong>
                        <span className="sub linha-secundaria">{unidadeVenda(p.unidade_venda)}</span>
                      </span>
                    </button>
                  </td>
                  <td className="col-saldo">{modalidadeTexto(p.modalidade)}</td>
                  <td className="col-meio">{usoTexto(p.uso_venda, p.uso_componente)}</td>
                  <td className="col-meio">{p.familia ?? <span className="travessao">—</span>}</td>
                  <td className="col-sit">
                    {p.selos.length === 0 ? (
                      <span className="travessao">—</span>
                    ) : (
                      <span className="sels">
                        {p.selos.map((selo) => (
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

      {painel ? (
        <PainelProduto
          key={painel}
          id={painel}
          onFechar={() => setPainel(null)}
          aoMudar={mudou}
          onAbrirIngrediente={(ingredienteId) => navegar(`/ingredientes?abrir=${ingredienteId}`)}
          onMontar={(produtoId) => navegar(`/receitas/${produtoId}`)}
        />
      ) : null}

      {novo && pode("lancar") ? (
        <Modal titulo="Novo produto" onFechar={fecharNovo}>
          <FormProduto
            titulo="Novo produto"
            modalidadeFixa={null}
            inicial={{
              nome: "",
              modalidade: "produzido",
              uso_venda: true,
              uso_componente: false,
              familia_id: null,
              unidade_venda: "un",
            }}
            familias={catalogoFamilias?.familias ?? dados?.familias ?? []}
            enviando={enviando}
            erro={erroNovo}
            parecidos={parecidos}
            onCancelar={fecharNovo}
            onEnviar={(corpo, confirmado, foto) => void cadastrar(corpo, confirmado, foto)}
          />
        </Modal>
      ) : null}
      {familiasAberto ? (
        <DialogoFamilias
          onFechar={() => setFamiliasAberto(false)}
          aoMudar={() => {
            mudou();
            void listarFamilias().then(setCatalogoFamilias).catch(() => undefined);
          }}
        />
      ) : null}
    </main>
  );
}
