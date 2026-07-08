import { useCallback, useEffect, useMemo, useState } from "react";
import { Plus, RotateCcw, Save, Search, Trash2, Variable } from "lucide-react";
import { fetchIndicadoresConfig, salvarIndicadorConfig } from "../../api/client";
import { obterVariaveisIndicador } from "../../config/gestaoTecnicaCatalog";
import { AlertaFeedback } from "./ConfiguracaoUi";

const MAX_FORMULA_CARACTERES = 255;

function indicadorChave(indicador) {
  return `${indicador.id}-${indicador.cod_indicador}-${indicador.nome_grupo}`;
}

function parametrosParaLinhas(parametros) {
  if (!parametros || typeof parametros !== "object") {
    return [];
  }

  return Object.entries(parametros).map(([chave, valor], index) => ({
    id: `${chave}-${index}`,
    chave,
    valor: valor === null || valor === undefined ? "" : String(valor),
  }));
}

function linhasParaParametros(linhas) {
  const resultado = {};

  linhas.forEach((linha) => {
    const chave = String(linha.chave || "").trim();
    if (!chave) {
      return;
    }

    const valorBruto = String(linha.valor ?? "").trim();
    if (valorBruto === "") {
      resultado[chave] = null;
      return;
    }

    if (valorBruto === "true") {
      resultado[chave] = true;
      return;
    }

    if (valorBruto === "false") {
      resultado[chave] = false;
      return;
    }

    const numerico = Number(valorBruto);
    resultado[chave] = Number.isNaN(numerico) ? valorBruto : numerico;
  });

  return resultado;
}

function linhasNumeradas(texto) {
  const linhas = String(texto || "").split("\n");
  if (linhas.length === 0) {
    return ["1"];
  }

  return linhas.map((_, index) => String(index + 1));
}

function EditorFormula({ codIndicador, valor, onChange }) {
  const linhas = linhasNumeradas(valor);
  const comprimento = valor.length;
  const proximoDoLimite = comprimento > MAX_FORMULA_CARACTERES * 0.85;
  const excedeuLimite = comprimento > MAX_FORMULA_CARACTERES;

  return (
    <div className="space-y-2">
      <span className="mb-2 flex items-center gap-2 text-sm font-semibold text-brand-cinza">
        <Variable className="h-4 w-4 text-brand-laranja" strokeWidth={2} />
        Fórmula Normalizada
      </span>

      <div className="formula-editor-shell">
        <div className="formula-editor-toolbar">
          <div className="flex items-center gap-2">
            <span className="rounded-md bg-brand-laranja/20 px-2 py-0.5 font-mono text-xs font-bold text-brand-laranja">
              {codIndicador}
            </span>
            <span className="text-xs text-emerald-100/70">mathjs · expressão avaliada em runtime</span>
          </div>
          <span className="rounded border border-brand-verde/30 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-emerald-100/50">
            engine
          </span>
        </div>

        <div className="formula-editor-body">
          <div className="formula-editor-gutter" aria-hidden="true">
            {linhas.map((numero) => (
              <div key={numero}>{numero}</div>
            ))}
          </div>
          <textarea
            value={valor}
            onChange={(event) => onChange(event.target.value)}
            rows={Math.max(6, linhas.length)}
            spellCheck={false}
            maxLength={MAX_FORMULA_CARACTERES}
            placeholder="ex: 1 - (ir / ie)"
            className="formula-editor-input"
            aria-label="Fórmula normalizada do indicador"
          />
        </div>

        <div className="formula-editor-status">
          <span>Identificadores devem existir no JSON ingerido ou nos parâmetros abaixo</span>
          <span className={excedeuLimite ? "font-semibold text-brand-laranja" : proximoDoLimite ? "text-brand-laranja/80" : ""}>
            {comprimento}/{MAX_FORMULA_CARACTERES}
          </span>
        </div>
      </div>
    </div>
  );
}

function EditorParametros({ linhas, onChange }) {
  const atualizarLinha = (id, campo, valor) => {
    onChange(
      linhas.map((linha) => (linha.id === id ? { ...linha, [campo]: valor } : linha))
    );
  };

  const adicionarLinha = () => {
    onChange([
      ...linhas,
      {
        id: `novo-${Date.now()}`,
        chave: "",
        valor: "",
      },
    ]);
  };

  const removerLinha = (id) => {
    onChange(linhas.filter((linha) => linha.id !== id));
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h4 className="text-sm font-semibold text-brand-cinza">Parâmetros Configuráveis</h4>
          <p className="text-xs text-brand-cinza/70">
            Pesos, limites e constantes mesclados com as variáveis do JSON ingerido.
          </p>
        </div>
        <button
          type="button"
          onClick={adicionarLinha}
          className="btn-outline px-3 py-1.5 text-xs"
        >
          <Plus className="h-3.5 w-3.5" strokeWidth={2} />
          Adicionar parâmetro
        </button>
      </div>

      {linhas.length === 0 ? (
        <div className="rounded-lg border border-dashed border-brand-verde/30 bg-brand-verde/5 px-4 py-6 text-center text-sm text-brand-cinza/70">
          Nenhum parâmetro definido. Use &quot;Adicionar parâmetro&quot; para incluir chaves como{" "}
          <code className="rounded bg-white px-1 font-mono text-xs text-brand-verde">peso_ir</code>.
        </div>
      ) : (
        <div className="space-y-2">
          <div className="hidden grid-cols-[1fr_1fr_auto] gap-2 px-1 text-xs font-semibold uppercase tracking-wide text-brand-cinza/60 sm:grid">
            <span>Chave</span>
            <span>Valor</span>
            <span className="w-9" />
          </div>

          {linhas.map((linha) => (
            <div
              key={linha.id}
              className="grid grid-cols-1 gap-2 rounded-lg border border-gray-100 bg-surface/60 p-3 sm:grid-cols-[1fr_1fr_auto] sm:items-center sm:p-2"
            >
              <input
                type="text"
                value={linha.chave}
                onChange={(event) => atualizarLinha(linha.id, "chave", event.target.value)}
                placeholder="ex: peso_ir"
                className="rounded-lg border border-gray-200 bg-white px-3 py-2 font-mono text-sm focus:border-brand-verde focus:outline-none focus:ring-2 focus:ring-brand-laranja/30"
              />
              <input
                type="text"
                value={linha.valor}
                onChange={(event) => atualizarLinha(linha.id, "valor", event.target.value)}
                placeholder="ex: 4"
                className="rounded-lg border border-gray-200 bg-white px-3 py-2 font-mono text-sm focus:border-brand-verde focus:outline-none focus:ring-2 focus:ring-brand-laranja/30"
              />
              <button
                type="button"
                onClick={() => removerLinha(linha.id)}
                className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-brand-vermelho/20 text-brand-vermelho transition hover:bg-brand-vermelho/10 focus:outline-none focus:ring-2 focus:ring-brand-laranja/30"
                aria-label="Remover parâmetro"
              >
                <Trash2 className="h-4 w-4" strokeWidth={2} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function FormularioIndicador({
  indicador,
  formula,
  linhasParametros,
  onFormulaChange,
  onParametrosChange,
}) {
  const variaveisEsperadas = obterVariaveisIndicador(indicador.cod_indicador);

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-brand-verde/15 bg-gradient-to-br from-brand-verde/5 to-white p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-brand-laranja">
              Indicador selecionado
            </p>
            <h3 className="mt-1 text-xl font-bold text-brand-verde">
              {indicador.cod_indicador} · {indicador.nome_indicador}
            </h3>
            <p className="mt-1 text-sm text-brand-cinza/80">
              {indicador.nome_grupo} · {indicador.dimensao} · {indicador.nivel_avaliacao}
            </p>
          </div>
          <div className="rounded-lg border border-brand-verde/20 bg-white px-3 py-2 text-xs text-brand-cinza">
            <span className="font-semibold text-brand-verde">ID</span> {indicador.id}
          </div>
        </div>

        {indicador.formula_original && (
          <p className="mt-4 rounded-lg border border-gray-100 bg-white/80 px-3 py-2 text-xs text-brand-cinza/80">
            <span className="font-semibold text-brand-cinza">Fórmula original:</span>{" "}
            {indicador.formula_original}
          </p>
        )}
      </div>

      <EditorFormula
        codIndicador={indicador.cod_indicador}
        valor={formula}
        onChange={onFormulaChange}
      />

      <p className="rounded-lg border border-brand-laranja/20 bg-brand-laranja/5 px-3 py-2 text-xs leading-relaxed text-brand-cinza">
        <strong className="text-brand-verde">Atenção:</strong> os identificadores usados na fórmula
        devem coincidir exatamente com as chaves presentes no JSON ingerido (payload da medição) ou
        com os parâmetros configuráveis abaixo.
        {variaveisEsperadas.length > 0 && (
          <>
            {" "}
            Variáveis de referência para{" "}
            <code className="font-mono text-brand-verde">{indicador.cod_indicador}</code>:{" "}
            {variaveisEsperadas.map((variavel) => (
              <code key={variavel} className="mr-1 font-mono text-brand-verde">
                {variavel}
              </code>
            ))}
          </>
        )}
      </p>

      <EditorParametros linhas={linhasParametros} onChange={onParametrosChange} />
    </div>
  );
}

function FormulasIndicadoresTab() {
  const [indicadores, setIndicadores] = useState([]);
  const [busca, setBusca] = useState("");
  const [selecionado, setSelecionado] = useState(null);
  const [formula, setFormula] = useState("");
  const [linhasParametros, setLinhasParametros] = useState([]);
  const [loading, setLoading] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState(null);
  const [sucesso, setSucesso] = useState(null);

  const carregarIndicadores = useCallback(async () => {
    try {
      setLoading(true);
      setErro(null);
      const data = await fetchIndicadoresConfig();
      const lista = data.indicadores || [];
      setIndicadores(lista);

      if (lista.length > 0) {
        setSelecionado((atual) => {
          if (!atual) {
            return lista[0];
          }

          return (
            lista.find((item) => indicadorChave(item) === indicadorChave(atual)) || lista[0]
          );
        });
      }
    } catch (err) {
      setErro(
        err.response?.data?.erro ||
          "Não foi possível carregar os indicadores configuráveis."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    carregarIndicadores();
  }, [carregarIndicadores]);

  useEffect(() => {
    if (!selecionado) {
      setFormula("");
      setLinhasParametros([]);
      return;
    }

    setFormula(selecionado.formula_normalizada || "");
    setLinhasParametros(parametrosParaLinhas(selecionado.parametros_configuraveis));
    setSucesso(null);
    setErro(null);
  }, [selecionado]);

  useEffect(() => {
    if (!sucesso) {
      return undefined;
    }

    const timer = window.setTimeout(() => setSucesso(null), 5000);
    return () => window.clearTimeout(timer);
  }, [sucesso]);

  const indicadoresFiltrados = useMemo(() => {
    const termo = busca.trim().toLowerCase();
    if (!termo) {
      return indicadores;
    }

    return indicadores.filter((item) => {
      const texto = [
        item.cod_indicador,
        item.nome_indicador,
        item.nome_grupo,
        item.dimensao,
        item.nivel_avaliacao,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return texto.includes(termo);
    });
  }, [busca, indicadores]);

  const temAlteracoesPendentes = useMemo(() => {
    if (!selecionado) {
      return false;
    }

    const formulaSalva = (selecionado.formula_normalizada || "").trim();
    const formulaAtual = formula.trim();
    const parametrosSalvos = JSON.stringify(selecionado.parametros_configuraveis || {});
    const parametrosAtuais = JSON.stringify(linhasParaParametros(linhasParametros));

    return formulaSalva !== formulaAtual || parametrosSalvos !== parametrosAtuais;
  }, [selecionado, formula, linhasParametros]);

  const handleSelecionar = (indicador) => {
    if (
      temAlteracoesPendentes &&
      !window.confirm("Existem alterações não guardadas neste indicador. Deseja continuar?")
    ) {
      return;
    }

    setSelecionado(indicador);
  };

  const handleDescartar = () => {
    if (!selecionado) {
      return;
    }

    setFormula(selecionado.formula_normalizada || "");
    setLinhasParametros(parametrosParaLinhas(selecionado.parametros_configuraveis));
    setErro(null);
    setSucesso(null);
  };

  const handleSalvar = async (event) => {
    event.preventDefault();
    if (!selecionado) {
      return;
    }

    setErro(null);
    setSucesso(null);

    const formulaLimpa = formula.trim();
    if (!formulaLimpa) {
      setErro("Informe a fórmula normalizada antes de salvar.");
      return;
    }

    if (formulaLimpa.length > MAX_FORMULA_CARACTERES) {
      setErro(`A fórmula não pode exceder ${MAX_FORMULA_CARACTERES} caracteres.`);
      return;
    }

    try {
      setSalvando(true);
      const payload = {
        formula_normalizada: formulaLimpa,
        parametros_configuraveis: linhasParaParametros(linhasParametros),
      };

      const resposta = await salvarIndicadorConfig(
        selecionado.cod_indicador,
        payload,
        selecionado.nome_grupo
      );

      const atualizado =
        resposta.indicadores?.find(
          (item) =>
            item.cod_indicador === selecionado.cod_indicador &&
            item.nome_grupo === selecionado.nome_grupo
        ) || null;

      if (atualizado) {
        setIndicadores((lista) =>
          lista.map((item) =>
            indicadorChave(item) === indicadorChave(atualizado) ? { ...item, ...atualizado } : item
          )
        );
        setSelecionado((atual) =>
          atual && indicadorChave(atual) === indicadorChave(atualizado)
            ? { ...atual, ...atualizado }
            : atual
        );
      } else {
        await carregarIndicadores();
      }

      setSucesso(resposta.mensagem || "Configuração do indicador atualizada com sucesso.");
    } catch (err) {
      const detalhes = err.response?.data?.detalhes;
      const mensagemBase =
        err.response?.data?.erro || "Não foi possível salvar a configuração do indicador.";

      setErro(
        Array.isArray(detalhes) && detalhes.length > 0
          ? `${mensagemBase} ${detalhes.join(" ")}`
          : mensagemBase
      );
    } finally {
      setSalvando(false);
    }
  };

  return (
    <div className="space-y-6">
      <section className="space-y-2">
        <h2 className="text-2xl font-bold text-brand-cinza">Fórmulas e Variáveis</h2>
        <p className="max-w-3xl text-sm text-brand-cinza/80">
          Configure o motor de regras de cada indicador: a expressão matemática avaliada em tempo
          real e os parâmetros internos mesclados com o payload das medições.
        </p>
      </section>

      <AlertaFeedback tipo="sucesso" mensagem={sucesso} onFechar={() => setSucesso(null)} />
      <AlertaFeedback tipo="erro" mensagem={erro} onFechar={() => setErro(null)} />

      {loading ? (
        <div className="card-panel flex items-center justify-center gap-3 py-16 text-brand-cinza">
          <span className="h-5 w-5 animate-spin rounded-full border-2 border-brand-verde border-t-transparent" />
          A carregar indicadores...
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(280px,320px)_1fr]">
          <aside className="card-panel flex flex-col gap-4 p-4">
            <label className="block">
              <span className="sr-only">Buscar indicador</span>
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-brand-cinza/50" />
                <input
                  type="search"
                  value={busca}
                  onChange={(event) => setBusca(event.target.value)}
                  placeholder="Buscar por código ou nome..."
                  className="w-full rounded-lg border border-gray-200 py-2 pl-9 pr-3 text-sm focus:border-brand-verde focus:outline-none focus:ring-2 focus:ring-brand-laranja/30"
                />
              </div>
            </label>

            <p className="text-xs font-medium uppercase tracking-wide text-brand-cinza/60">
              {indicadoresFiltrados.length} indicador(es)
            </p>

            <ul className="max-h-[min(70vh,640px)] space-y-1 overflow-y-auto pr-1">
              {indicadoresFiltrados.length === 0 ? (
                <li className="rounded-lg px-3 py-6 text-center text-sm text-brand-cinza/60">
                  Nenhum indicador encontrado.
                </li>
              ) : (
                indicadoresFiltrados.map((indicador) => {
                  const ativo =
                    selecionado && indicadorChave(indicador) === indicadorChave(selecionado);

                  return (
                    <li key={indicadorChave(indicador)}>
                      <button
                        type="button"
                        onClick={() => handleSelecionar(indicador)}
                        className={`w-full rounded-lg border px-3 py-3 text-left transition focus:outline-none focus:ring-2 focus:ring-brand-laranja/40 ${
                          ativo
                            ? "border-brand-verde bg-brand-verde/10 shadow-sm"
                            : "border-transparent bg-white hover:border-brand-verde/20 hover:bg-brand-verde/5"
                        }`}
                      >
                        <p
                          className={`font-mono text-sm font-bold ${
                            ativo ? "text-brand-verde" : "text-brand-cinza"
                          }`}
                        >
                          {indicador.cod_indicador}
                        </p>
                        <p className="mt-0.5 text-sm font-medium text-brand-cinza">
                          {indicador.nome_indicador}
                        </p>
                        <p className="mt-1 text-xs text-brand-cinza/60">
                          {indicador.nome_grupo}
                          {indicador.formula_normalizada ? " · com fórmula" : ""}
                        </p>
                      </button>
                    </li>
                  );
                })
              )}
            </ul>
          </aside>

          <section className="card-panel min-h-[480px]">
            {!selecionado ? (
              <div className="flex h-full min-h-[320px] items-center justify-center text-sm text-brand-cinza/60">
                Selecione um indicador na lista para editar a fórmula.
              </div>
            ) : (
              <form onSubmit={handleSalvar} className="space-y-6">
                <FormularioIndicador
                  indicador={selecionado}
                  formula={formula}
                  linhasParametros={linhasParametros}
                  onFormulaChange={setFormula}
                  onParametrosChange={setLinhasParametros}
                />

                <div className="sticky bottom-0 flex flex-wrap items-center gap-3 border-t border-gray-100 bg-white/95 pt-5 backdrop-blur-sm">
                  {temAlteracoesPendentes && (
                    <span className="rounded-full bg-brand-laranja/10 px-3 py-1 text-xs font-semibold text-brand-laranja">
                      Alterações por guardar
                    </span>
                  )}
                  <button
                    type="submit"
                    className="btn-primary"
                    disabled={salvando || !temAlteracoesPendentes}
                  >
                    <Save className="h-4 w-4" strokeWidth={2} />
                    {salvando ? "A guardar..." : "Salvar Configuração do Indicador"}
                  </button>
                  <button
                    type="button"
                    className="btn-outline"
                    onClick={handleDescartar}
                    disabled={salvando || !temAlteracoesPendentes}
                  >
                    <RotateCcw className="h-4 w-4" strokeWidth={2} />
                    Descartar
                  </button>
                  <button
                    type="button"
                    className="btn-outline"
                    onClick={carregarIndicadores}
                    disabled={salvando}
                  >
                    Recarregar lista
                  </button>
                </div>
              </form>
            )}
          </section>
        </div>
      )}
    </div>
  );
}

export default FormulasIndicadoresTab;
