import { useCallback, useEffect, useState } from "react";

import { Link } from "react-router-dom";

import {

  fetchFiltrosOpcoes,

  fetchMetricas,

  FILTROS_INICIAIS,

  isModoColaborador,

} from "../api/client";

import { getOrganizacaoNome } from "../config/organizacao";

import Header from "./Header";

import FilterBar from "./FilterBar";

import ResumoExecutivo from "./ResumoExecutivo";

import VisaoOrganizacao from "./VisaoOrganizacao";

import AnaliseCruzada from "./AnaliseCruzada";

import PainelIndicador from "./PainelIndicador";

import { extractPainelIndicadores } from "../utils/metricas";

import { filtrosColaboradorResolvidos } from "../utils/colaboradorFiltro";



const OPCOES_INICIAIS = {

  niveis: [

    { valor: "colaborador", label: "Colaborador", baseline: "Média do subpapel" },

    { valor: "papel", label: "Papel", baseline: "Média do setor" },

    { valor: "subpapel", label: "Subpapel", baseline: "Média do papel" },

    { valor: "setor", label: "Setor", baseline: "Média total" },

  ],

  colaboradores: [],

  papeis: [],

  subpapeis: [],

  setores: [],

};



function normalizarFiltrosColaborador(filtros, colaboradores, termoBusca = "") {

  return filtrosColaboradorResolvidos(colaboradores, filtros, termoBusca);

}



function Dashboard() {

  const [metricas, setMetricas] = useState([]);

  const [iapsCalculado, setIapsCalculado] = useState(null);

  const [scoresDimensoes, setScoresDimensoes] = useState(null);

  const [memoriaCalculo, setMemoriaCalculo] = useState(null);

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState(null);

  const [filtros, setFiltros] = useState(FILTROS_INICIAIS);

  const [filtrosAplicados, setFiltrosAplicados] = useState(FILTROS_INICIAIS);

  const [filtrosAbertos, setFiltrosAbertos] = useState(false);

  const [opcoes, setOpcoes] = useState(OPCOES_INICIAIS);

  const [avisoFiltro, setAvisoFiltro] = useState(null);



  const modoColaborador = isModoColaborador(filtrosAplicados);



  const loadMetricas = useCallback(async (filtrosAtivos = filtrosAplicados) => {

    try {

      setLoading(true);

      setError(null);

      const metricasData = await fetchMetricas(filtrosAtivos);

      setMetricas(metricasData.metricas || []);

      setIapsCalculado(metricasData.iaps_calculado ?? null);

      setScoresDimensoes(metricasData.scores_dimensoes ?? null);

      setMemoriaCalculo(metricasData.memoria_calculo ?? null);

    } catch (err) {

      setError(

        err.response?.data?.erro || "Não foi possível carregar as métricas do dashboard."

      );

    } finally {

      setLoading(false);

    }

  }, [filtrosAplicados]);



  useEffect(() => {

    let active = true;



    async function loadOpcoes() {

      try {

        const data = await fetchFiltrosOpcoes();

        if (active) {

          setOpcoes({

            niveis: data.niveis || OPCOES_INICIAIS.niveis,

            colaboradores: data.colaboradores || [],

            papeis: data.papeis || [],

            subpapeis: data.subpapeis || [],

            setores: data.setores || [],

          });

        }

      } catch {

        if (active) {

          setOpcoes(OPCOES_INICIAIS);

        }

      }

    }



    loadOpcoes();

    return () => {

      active = false;

    };

  }, []);



  useEffect(() => {

    loadMetricas(filtrosAplicados);

  }, [filtrosAplicados, loadMetricas]);



  const handleApplyFiltros = (termoAutocomplete = "") => {

    const filtrosResolvidos = normalizarFiltrosColaborador(

      filtros,

      opcoes.colaboradores,

      termoAutocomplete

    );



    if (

      filtrosResolvidos.nivel === "colaborador" &&

      !filtrosResolvidos.id_colaborador

    ) {

      setAvisoFiltro(

        "Selecione um colaborador na lista ou nos atalhos APD para ver a análise individual."

      );

      setFiltros(filtrosResolvidos);

      return;

    }



    setAvisoFiltro(null);

    setFiltros(filtrosResolvidos);

    setFiltrosAplicados(filtrosResolvidos);

  };



  const handleClearFiltros = () => {

    setFiltros(FILTROS_INICIAIS);

    setFiltrosAplicados(FILTROS_INICIAIS);

    setAvisoFiltro(null);

  };



  const handleSelectColaborador = (colaborador) => {

    const novosFiltros = normalizarFiltrosColaborador(

      {

        nivel: "colaborador",

        busca: colaborador.matricula,

        id_colaborador: colaborador.id_colaborador ?? null,

      },

      opcoes.colaboradores

    );

    setAvisoFiltro(null);

    setFiltros(novosFiltros);

    setFiltrosAplicados(novosFiltros);

    setFiltrosAbertos(true);

  };



  const handleInvalidateColaborador = () => {

    setFiltros((atual) => ({

      ...atual,

      id_colaborador: null,

    }));

  };



  const handleClearColaborador = () => {

    setFiltros(FILTROS_INICIAIS);

    setFiltrosAplicados(FILTROS_INICIAIS);

    setAvisoFiltro(null);

  };



  const handleSelectColaboradorTeste = (matricula) => {

    const colaborador = opcoes.colaboradores?.find((item) => item.matricula === matricula);

    if (colaborador) {

      handleSelectColaborador(colaborador);

      return;

    }



    const novosFiltros = normalizarFiltrosColaborador(

      {

        nivel: "colaborador",

        busca: matricula,

        id_colaborador: null,

      },

      opcoes.colaboradores,

      matricula

    );



    if (!novosFiltros.id_colaborador) {

      setAvisoFiltro("Colaborador não encontrado. Execute o seed APD ou selecione na lista.");

      return;

    }



    setAvisoFiltro(null);

    setFiltros(novosFiltros);

    setFiltrosAplicados(novosFiltros);

    setFiltrosAbertos(true);

  };



  const paineisIndicador = extractPainelIndicadores(

    metricas,

    filtrosAplicados,

    iapsCalculado

  );



  return (

    <div className="min-h-screen bg-surface">

      <Header metricCount={metricas.length} loading={loading} />



      <main id="dashboard" className="mx-auto max-w-7xl space-y-8 px-4 py-8 sm:px-6 lg:px-8">

        <section className="space-y-2">

          <h2 className="text-2xl font-bold text-brand-cinza">

            {modoColaborador ? "Análise do Colaborador" : "Dashboard da Organização"}

          </h2>

          <p className="max-w-3xl text-sm text-brand-cinza/80">

            {modoColaborador

              ? `Visão individual de ${iapsCalculado?.nome_colaborador || "colaborador"} — IAPS, indicadores, análise cruzada e insights IA.`

              : "Visão consolidada de toda a organização. Selecione um colaborador para aprofundar a análise."}

          </p>

        </section>



        <FilterBar

          filtros={filtros}

          opcoes={opcoes}

          filtrosAbertos={filtrosAbertos}

          onToggleFiltros={() => setFiltrosAbertos((open) => !open)}

          onFiltrosChange={setFiltros}

          onApply={handleApplyFiltros}

          onClear={handleClearFiltros}

          onRefresh={() => loadMetricas(filtrosAplicados)}

          onSelectColaboradorTeste={handleSelectColaboradorTeste}

          onSelectColaborador={handleSelectColaborador}

          onClearColaborador={handleClearColaborador}

          onInvalidateColaborador={handleInvalidateColaborador}

          loading={loading}

          modoColaborador={modoColaborador}

        />



        {avisoFiltro && (

          <div className="rounded-xl border border-brand-laranja/30 bg-brand-laranja/10 px-4 py-3 text-sm text-brand-cinza">

            {avisoFiltro}

          </div>

        )}



        {error && (

          <div className="rounded-xl border border-brand-vermelho/30 bg-brand-vermelho/10 px-4 py-3 text-sm font-medium text-brand-vermelho">

            {error}

          </div>

        )}



        {loading ? (

          <div className="card-panel flex items-center justify-center gap-3 py-16 text-brand-cinza">

            <span className="h-5 w-5 animate-spin rounded-full border-2 border-brand-verde border-t-transparent" />

            A carregar dados da API...

          </div>

        ) : (

          <>

            <section id="resumo-executivo" className="space-y-4">

              <div>

                <h3 className="section-title">Resumo Executivo</h3>

                <p className="section-subtitle">

                  {modoColaborador

                    ? "Índice IAPS e dimensões SPACE do colaborador selecionado."

                    : "Índice IAPS consolidado de toda a organização (últimos 12 meses)."}

                </p>

              </div>

              <ResumoExecutivo

                metricas={metricas}

                filtros={filtrosAplicados}

                iapsCalculado={iapsCalculado}

                scoresDimensoes={scoresDimensoes}

                memoriaCalculo={memoriaCalculo}

                modoColaborador={modoColaborador}

              />

            </section>



            {!modoColaborador && (

              <VisaoOrganizacao metricas={metricas} opcoes={opcoes} />

            )}



            {modoColaborador && iapsCalculado?.id_colaborador && (

              <AnaliseCruzada

                idColaborador={iapsCalculado.id_colaborador}

                colaboradorNome={iapsCalculado.nome_colaborador}

                scoresDimensoes={scoresDimensoes}

                memoriaCalculo={memoriaCalculo}

              />

            )}



            {modoColaborador && (

              <section id="metricas" className="relative space-y-6 overflow-visible">

                <div>

                  <h3 className="section-title">Painéis de Indicadores</h3>

                  <p className="section-subtitle">

                    {`${paineisIndicador.length} indicador(es) que compõem o IAPS do colaborador · alvo, referencial e evolução histórica.`}

                  </p>

                </div>



                {paineisIndicador.length === 0 ? (

                  <div className="card-panel border-dashed text-center text-sm text-brand-cinza">

                    Nenhum indicador com score disponível no período selecionado.

                  </div>

                ) : (

                  <div className="space-y-8">

                    {paineisIndicador.map((painel) => (

                      <PainelIndicador key={painel.cod_indicador} dados={painel} />

                    ))}

                  </div>

                )}

              </section>

            )}

          </>

        )}

      </main>



      <footer className="border-t border-gray-200 bg-white py-6 text-center text-xs text-brand-cinza">

        <p>Prodinx · Plataforma de Indicadores · {getOrganizacaoNome()}</p>

        <div className="mt-2 flex flex-wrap justify-center gap-4">

          <Link to="/detalhes" className="text-brand-verde underline-offset-2 hover:underline">

            Consultar registros detalhados

          </Link>

          <Link to="/importacoes" className="text-brand-verde underline-offset-2 hover:underline">

            Consultar histórico de importações

          </Link>

          <Link to="/parametros" className="text-brand-verde underline-offset-2 hover:underline">

            Configuração de parâmetros IAPS

          </Link>

        </div>

      </footer>

    </div>

  );

}



export default Dashboard;


