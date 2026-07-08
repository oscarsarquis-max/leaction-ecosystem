import { useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchConfiguracaoPesos,
  fetchConfiguracaoPesosOpcoes,
  salvarConfiguracaoPesos,
} from "../../api/client";
import { BRAND_COLORS } from "../../theme/brand";
import { AlertaFeedback, IndicadorSoma } from "./ConfiguracaoUi";

const PESOS_PADRAO = {
  peso_ind: 40,
  peso_eq: 60,
  peso_satisfacao: 25,
  peso_performance: 25,
  peso_atividade: 20,
  peso_comunicacao: 20,
  peso_eficiencia: 10,
};

const DIMENSOES = [
  { chave: "peso_satisfacao", label: "Satisfação", cor: BRAND_COLORS.laranja },
  { chave: "peso_performance", label: "Performance", cor: BRAND_COLORS.verde },
  { chave: "peso_atividade", label: "Atividade", cor: BRAND_COLORS.cinza },
  { chave: "peso_comunicacao", label: "Comunicação", cor: BRAND_COLORS.vermelho },
  { chave: "peso_eficiencia", label: "Eficiência", cor: "#1B6B47" },
];

const TOLERANCIA_SOMA = 0.5;

function decimalParaPercentual(valor) {
  if (valor === null || valor === undefined || Number.isNaN(Number(valor))) {
    return "";
  }

  return Number((Number(valor) * 100).toFixed(2));
}

function percentualParaDecimal(valor) {
  if (valor === "" || valor === null || valor === undefined) {
    return null;
  }

  const numerico = Number(valor);
  if (Number.isNaN(numerico)) {
    return null;
  }

  return Number((numerico / 100).toFixed(4));
}

function mapConfiguracaoParaFormulario(configuracao) {
  if (!configuracao) {
    return { ...PESOS_PADRAO };
  }

  return {
    peso_ind: decimalParaPercentual(configuracao.peso_ind),
    peso_eq: decimalParaPercentual(configuracao.peso_eq),
    peso_satisfacao: decimalParaPercentual(configuracao.peso_satisfacao),
    peso_performance: decimalParaPercentual(configuracao.peso_performance),
    peso_atividade: decimalParaPercentual(configuracao.peso_atividade),
    peso_comunicacao: decimalParaPercentual(configuracao.peso_comunicacao),
    peso_eficiencia: decimalParaPercentual(configuracao.peso_eficiencia),
  };
}

function somaPercentuais(valores) {
  return valores.reduce((total, valor) => total + (Number(valor) || 0), 0);
}

function PesosIapsTab() {
  const [opcoes, setOpcoes] = useState({ papeis: [], subpapeis_por_papel: {} });
  const [papel, setPapel] = useState("");
  const [subpapel, setSubpapel] = useState("");
  const [formulario, setFormulario] = useState(PESOS_PADRAO);
  const [configuracaoId, setConfiguracaoId] = useState(null);
  const [loadingOpcoes, setLoadingOpcoes] = useState(true);
  const [loadingConfig, setLoadingConfig] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState(null);
  const [sucesso, setSucesso] = useState(null);

  const subpapeisDisponiveis = useMemo(
    () => (papel ? opcoes.subpapeis_por_papel[papel] || [] : []),
    [opcoes.subpapeis_por_papel, papel]
  );

  const somaProporcao = useMemo(
    () => somaPercentuais([formulario.peso_ind, formulario.peso_eq]),
    [formulario.peso_ind, formulario.peso_eq]
  );

  const somaDimensoes = useMemo(
    () =>
      somaPercentuais(DIMENSOES.map((dimensao) => formulario[dimensao.chave])),
    [formulario]
  );

  const formularioValido =
    papel &&
    subpapel &&
    Math.abs(somaProporcao - 100) <= TOLERANCIA_SOMA &&
    Math.abs(somaDimensoes - 100) <= TOLERANCIA_SOMA;

  const carregarOpcoes = useCallback(async () => {
    try {
      setLoadingOpcoes(true);
      setErro(null);
      const data = await fetchConfiguracaoPesosOpcoes();
      setOpcoes(data);

      const primeiroPapel = data.papeis?.[0] || "";
      const primeiroSubpapel = data.subpapeis_por_papel?.[primeiroPapel]?.[0] || "";
      setPapel(primeiroPapel);
      setSubpapel(primeiroSubpapel);
    } catch (err) {
      setErro(
        err.response?.data?.erro ||
          "Não foi possível carregar as opções de papel e subpapel."
      );
    } finally {
      setLoadingOpcoes(false);
    }
  }, []);

  const carregarConfiguracao = useCallback(async () => {
    if (!papel || !subpapel) {
      return;
    }

    try {
      setLoadingConfig(true);
      setErro(null);
      const data = await fetchConfiguracaoPesos(papel, subpapel);
      setConfiguracaoId(data.configuracao?.id ?? null);
      setFormulario(mapConfiguracaoParaFormulario(data.configuracao));
    } catch (err) {
      setErro(
        err.response?.data?.erro ||
          "Não foi possível carregar a configuração selecionada."
      );
    } finally {
      setLoadingConfig(false);
    }
  }, [papel, subpapel]);

  useEffect(() => {
    carregarOpcoes();
  }, [carregarOpcoes]);

  useEffect(() => {
    if (!papel) {
      return;
    }

    const subpapeis = opcoes.subpapeis_por_papel[papel] || [];
    if (!subpapeis.includes(subpapel)) {
      setSubpapel(subpapeis[0] || "");
    }
  }, [papel, subpapel, opcoes.subpapeis_por_papel]);

  useEffect(() => {
    carregarConfiguracao();
  }, [carregarConfiguracao]);

  useEffect(() => {
    if (!sucesso) {
      return undefined;
    }

    const timer = window.setTimeout(() => setSucesso(null), 5000);
    return () => window.clearTimeout(timer);
  }, [sucesso]);

  const atualizarCampo = (campo, valor) => {
    setFormulario((estadoAtual) => ({
      ...estadoAtual,
      [campo]: valor,
    }));
    setSucesso(null);
  };

  const handleSalvar = async (event) => {
    event.preventDefault();
    setErro(null);
    setSucesso(null);

    if (!formularioValido) {
      setErro("Revise os pesos: as somas de proporção e dimensões devem totalizar 100%.");
      return;
    }

    try {
      setSalvando(true);
      const payload = {
        papel,
        subpapel,
        peso_ind: percentualParaDecimal(formulario.peso_ind),
        peso_eq: percentualParaDecimal(formulario.peso_eq),
        peso_satisfacao: percentualParaDecimal(formulario.peso_satisfacao),
        peso_performance: percentualParaDecimal(formulario.peso_performance),
        peso_atividade: percentualParaDecimal(formulario.peso_atividade),
        peso_comunicacao: percentualParaDecimal(formulario.peso_comunicacao),
        peso_eficiencia: percentualParaDecimal(formulario.peso_eficiencia),
      };

      const resposta = await salvarConfiguracaoPesos(payload);
      setConfiguracaoId(resposta.configuracao?.id ?? null);
      setFormulario(mapConfiguracaoParaFormulario(resposta.configuracao));
      setSucesso(resposta.mensagem || "Configurações salvas com sucesso.");
    } catch (err) {
      setErro(
        err.response?.data?.erro ||
          "Não foi possível salvar as configurações. Tente novamente."
      );
    } finally {
      setSalvando(false);
    }
  };

  return (
    <div className="space-y-6">
      <section className="space-y-2">
        <h2 className="text-2xl font-bold text-brand-cinza">Pesos por Papel e Subpapel</h2>
        <p className="max-w-3xl text-sm text-brand-cinza/80">
          Defina a proporção Individual/Equipe e os pesos das dimensões SPACE que alimentam o
          motor de cálculo do IAPS na base de dados.
        </p>
      </section>

      <AlertaFeedback tipo="sucesso" mensagem={sucesso} onFechar={() => setSucesso(null)} />
      <AlertaFeedback tipo="erro" mensagem={erro} onFechar={() => setErro(null)} />

      <section className="card-panel space-y-4">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <label className="block text-sm text-brand-cinza">
            <span className="mb-1 block font-medium">Selecione o Papel</span>
            <select
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-brand-verde focus:outline-none focus:ring-2 focus:ring-brand-laranja/30"
              value={papel}
              onChange={(event) => setPapel(event.target.value)}
              disabled={loadingOpcoes}
            >
              {opcoes.papeis.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>

          <label className="block text-sm text-brand-cinza">
            <span className="mb-1 block font-medium">Selecione o Subpapel</span>
            <select
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-brand-verde focus:outline-none focus:ring-2 focus:ring-brand-laranja/30"
              value={subpapel}
              onChange={(event) => setSubpapel(event.target.value)}
              disabled={loadingOpcoes || subpapeisDisponiveis.length === 0}
            >
              {subpapeisDisponiveis.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
        </div>

        {configuracaoId && (
          <p className="text-xs text-brand-cinza/70">
            Configuração ativa no banco · ID {configuracaoId}
          </p>
        )}
      </section>

      {loadingConfig ? (
        <div className="card-panel flex items-center justify-center gap-3 py-16 text-brand-cinza">
          <span className="h-5 w-5 animate-spin rounded-full border-2 border-brand-verde border-t-transparent" />
          A carregar parâmetros...
        </div>
      ) : (
        <form onSubmit={handleSalvar} className="space-y-6">
          <section className="card-panel space-y-5">
            <div>
              <h3 className="section-title">Proporção de Avaliação</h3>
              <p className="section-subtitle">
                Distribuição entre medições individuais e de equipe no cálculo por dimensão.
              </p>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <label className="block rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
                <span className="text-xs font-semibold uppercase tracking-wide text-brand-cinza">
                  Peso Individual (%)
                </span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  value={formulario.peso_ind}
                  onChange={(event) => atualizarCampo("peso_ind", event.target.value)}
                  className="mt-2 w-full rounded-lg border border-gray-200 px-3 py-2 text-lg font-semibold text-brand-verde focus:border-brand-verde focus:outline-none focus:ring-2 focus:ring-brand-laranja/30"
                />
              </label>

              <label className="block rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
                <span className="text-xs font-semibold uppercase tracking-wide text-brand-cinza">
                  Peso Equipe (%)
                </span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  value={formulario.peso_eq}
                  onChange={(event) => atualizarCampo("peso_eq", event.target.value)}
                  className="mt-2 w-full rounded-lg border border-gray-200 px-3 py-2 text-lg font-semibold text-brand-verde focus:border-brand-verde focus:outline-none focus:ring-2 focus:ring-brand-laranja/30"
                />
              </label>
            </div>

            <IndicadorSoma valor={somaProporcao} rotulo="Soma da proporção" />
          </section>

          <section className="card-panel space-y-5">
            <div>
              <h3 className="section-title">Pesos das Dimensões (SPACE)</h3>
              <p className="section-subtitle">
                Contribuição de cada dimensão no índice final do colaborador.
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm text-brand-cinza">
                <thead>
                  <tr className="border-b border-gray-100 text-xs uppercase tracking-wide text-brand-cinza/70">
                    <th className="px-3 py-3 font-semibold">Dimensão</th>
                    <th className="px-3 py-3 font-semibold">Peso (%)</th>
                  </tr>
                </thead>
                <tbody>
                  {DIMENSOES.map((dimensao) => (
                    <tr key={dimensao.chave} className="border-b border-gray-50">
                      <td className="px-3 py-3">
                        <div className="flex items-center gap-2">
                          <span
                            className="h-2.5 w-2.5 rounded-full"
                            style={{ backgroundColor: dimensao.cor }}
                          />
                          <span className="font-medium">{dimensao.label}</span>
                        </div>
                      </td>
                      <td className="px-3 py-3">
                        <input
                          type="number"
                          min="0"
                          max="100"
                          step="0.1"
                          value={formulario[dimensao.chave]}
                          onChange={(event) =>
                            atualizarCampo(dimensao.chave, event.target.value)
                          }
                          className="w-full max-w-[160px] rounded-lg border border-gray-200 px-3 py-2 font-semibold focus:border-brand-verde focus:outline-none focus:ring-2 focus:ring-brand-laranja/30"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <IndicadorSoma valor={somaDimensoes} rotulo="Soma das dimensões" />
          </section>

          <div className="flex flex-wrap items-center gap-3">
            <button type="submit" className="btn-primary" disabled={salvando || !formularioValido}>
              {salvando ? "A guardar..." : "Salvar Configurações"}
            </button>
            <button
              type="button"
              className="btn-outline"
              onClick={carregarConfiguracao}
              disabled={salvando || loadingConfig}
            >
              Recarregar
            </button>
            {!formularioValido && (
              <p className="text-xs text-brand-vermelho">
                Ajuste os valores até que ambas as somas totalizem 100%.
              </p>
            )}
          </div>
        </form>
      )}
    </div>
  );
}

export default PesosIapsTab;
