import {
  IndicadorNomeComDefinicao,
  resolverDefinicaoIndicador,
} from "./IndicadorNomeComDefinicao";

function ehNulo(valor) {
  return valor === null || valor === undefined || Number.isNaN(Number(valor));
}

/** Scores da memória vêm em % (0–100); o card IAPS do colaborador usa escala 0–1. */
function paraEscalaUnitaria(valor) {
  if (ehNulo(valor)) {
    return null;
  }

  const numero = Number(valor);
  return numero > 1 ? numero / 100 : numero;
}

function formatarNumero(valor, casas = 2) {
  if (ehNulo(valor)) {
    return null;
  }

  return Number(valor).toLocaleString("pt-BR", {
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
  });
}

function TagSemDados() {
  return (
    <span className="inline-flex items-center rounded-md bg-gray-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-gray-500 ring-1 ring-inset ring-gray-200">
      Sem Dados
    </span>
  );
}

function CelulaScore({ valor }) {
  const formatado = formatarNumero(valor);
  if (formatado === null) {
    return <TagSemDados />;
  }

  return (
    <span className="font-semibold tabular-nums text-brand-verde">{formatado}</span>
  );
}

function rotuloIndicador(indicador) {
  if (!indicador) {
    return { titulo: null, codigo: null };
  }

  return {
    titulo: indicador.nome_indicador || indicador.cod_indicador || null,
    codigo: indicador.cod_indicador || null,
  };
}

function CelulaIndicador({ indicador, definicoesIndicadores }) {
  if (!indicador) {
    return <TagSemDados />;
  }

  const { titulo, codigo } = rotuloIndicador(indicador);
  const { explicacao, importancia } = resolverDefinicaoIndicador(
    indicador,
    definicoesIndicadores
  );

  if (!titulo) {
    return <TagSemDados />;
  }

  return (
    <div className="min-w-[140px]">
      <IndicadorNomeComDefinicao
        nome={titulo}
        explicacao={explicacao}
        importancia={importancia}
        className="block text-[11px] leading-snug sm:text-xs"
      />
      {codigo && (
        <p className="mt-0.5 font-mono text-[10px] text-brand-cinza/55">{codigo}</p>
      )}
    </div>
  );
}

/**
 * Tabela APD — memória de cálculo do IAPS a partir de memoria_calculo (mathjs).
 * Visível apenas no contexto de um colaborador específico.
 */
function DemonstrativoCalculo({
  memoriaCalculo,
  iapsCalculado,
  definicoesIndicadores = {},
}) {
  if (!memoriaCalculo?.length || !iapsCalculado?.id_colaborador) {
    return null;
  }

  const totalIaps = paraEscalaUnitaria(iapsCalculado.valor);
  const somaContribuicoes = memoriaCalculo.reduce(
    (acc, linha) => acc + (paraEscalaUnitaria(linha.contribuicao_iaps) ?? 0),
    0
  );
  const totalExibido = totalIaps ?? somaContribuicoes;

  const proporcao = memoriaCalculo[0]?.proporcao_ind_eq || "40/60";

  return (
    <section
      id="demonstrativo-calculo"
      className="card-panel min-w-0 overflow-hidden p-0 shadow-sm"
      aria-label="Demonstrativo de cálculo do IAPS"
    >
      <div className="border-b border-gray-100 bg-gradient-to-r from-brand-verde/[0.06] to-transparent px-4 py-4 sm:px-5">
        <h4 className="section-title">Demonstrativo de Cálculo do IAPS</h4>
        <p className="section-subtitle">
          Transparência matemática · planilha APD · scores calculados em tempo real (mathjs)
        </p>

        <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-xs text-brand-cinza">
          <p>
            <span className="font-medium text-brand-cinza/70">Colaborador:</span>{" "}
            {iapsCalculado.nome_colaborador || "—"}
            {iapsCalculado.matricula ? ` (${iapsCalculado.matricula})` : ""}
          </p>
          <p>
            <span className="font-medium text-brand-cinza/70">Papel / Subpapel:</span>{" "}
            {[iapsCalculado.papel, iapsCalculado.subpapel].filter(Boolean).join(" · ") ||
              "—"}
          </p>
          <p>
            <span className="font-medium text-brand-cinza/70">Proporção Ind./Eq.:</span>{" "}
            {proporcao}
          </p>
        </div>
      </div>

      <div className="relative min-w-0">
        <div className="overflow-x-auto [-webkit-overflow-scrolling:touch]">
          <table className="w-full min-w-[720px] border-collapse text-sm text-brand-cinza">
            <thead>
              <tr className="bg-brand-verde text-left text-[10px] font-semibold uppercase tracking-wide text-white sm:text-xs">
                <th className="sticky left-0 z-10 bg-brand-verde px-3 py-3 sm:px-4">
                  Dimensão
                </th>
                <th className="px-3 py-3 text-right sm:px-4">Peso da Dimensão</th>
                <th className="px-3 py-3 sm:px-4">Indicador Individual</th>
                <th className="px-3 py-3 text-right sm:px-4">Score Ind.</th>
                <th className="px-3 py-3 sm:px-4">Indicador de Equipe</th>
                <th className="px-3 py-3 text-right sm:px-4">Score Eq.</th>
                <th className="px-3 py-3 text-right sm:px-4">
                  Score Final (Dimensão)
                </th>
              </tr>
            </thead>

            <tbody>
              {memoriaCalculo.map((linha) => {
                const scoreInd = paraEscalaUnitaria(linha.score_individual);
                const scoreEq = paraEscalaUnitaria(linha.score_equipe);
                const scoreFinal = paraEscalaUnitaria(linha.score_final);
                const temIndicadorInd = Boolean(linha.indicador_individual);
                const temIndicadorEq = Boolean(linha.indicador_equipe);

                return (
                  <tr
                    key={linha.dimensao}
                    className="group border-b border-gray-100 align-middle transition hover:bg-brand-verde/[0.03]"
                  >
                    <td className="sticky left-0 z-10 bg-white px-3 py-3 font-semibold text-brand-cinza group-hover:bg-[#f7faf8] sm:px-4">
                      <span className="block">{linha.dimensao}</span>
                      {linha.simbolo && (
                        <span className="mt-0.5 block font-mono text-[10px] font-normal text-brand-cinza/50">
                          {linha.simbolo}
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-3 text-right tabular-nums sm:px-4">
                      {formatarNumero(linha.peso_dimensao) ?? <TagSemDados />}
                    </td>
                    <td className="px-3 py-3 sm:px-4">
                      {temIndicadorInd ? (
                        <CelulaIndicador
                          indicador={linha.indicador_individual}
                          definicoesIndicadores={definicoesIndicadores}
                        />
                      ) : (
                        <TagSemDados />
                      )}
                    </td>
                    <td className="px-3 py-3 text-right sm:px-4">
                      <CelulaScore valor={temIndicadorInd ? scoreInd : null} />
                    </td>
                    <td className="px-3 py-3 sm:px-4">
                      {temIndicadorEq ? (
                        <CelulaIndicador
                          indicador={linha.indicador_equipe}
                          definicoesIndicadores={definicoesIndicadores}
                        />
                      ) : (
                        <TagSemDados />
                      )}
                    </td>
                    <td className="px-3 py-3 text-right sm:px-4">
                      <CelulaScore valor={temIndicadorEq ? scoreEq : null} />
                    </td>
                    <td className="px-3 py-3 text-right sm:px-4">
                      <span className="text-base font-bold tabular-nums text-brand-cinza">
                        {formatarNumero(scoreFinal) ?? <TagSemDados />}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>

            <tfoot>
              <tr className="bg-brand-verde/10 text-brand-cinza">
                <td
                  colSpan={6}
                  className="sticky left-0 z-10 bg-brand-verde/10 px-3 py-4 text-sm font-bold uppercase tracking-wide sm:px-4"
                >
                  IAPS Total
                  <span className="mt-1 block text-[10px] font-normal normal-case tracking-normal text-brand-cinza/65">
                    Soma ponderada das dimensões (contribuições SPACE) · bate com o
                    índice do resumo
                  </span>
                </td>
                <td className="px-3 py-4 text-right sm:px-4">
                  <span className="text-2xl font-bold tabular-nums text-brand-verde sm:text-3xl">
                    {formatarNumero(totalExibido) ?? "—"}
                  </span>
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </section>
  );
}

export default DemonstrativoCalculo;
