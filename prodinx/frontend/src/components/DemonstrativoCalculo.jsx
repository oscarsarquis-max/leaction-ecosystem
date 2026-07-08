import {
  IndicadorNomeComDefinicao,
  resolverDefinicaoIndicador,
} from "./IndicadorNomeComDefinicao";

function formatarNumero(valor, casas = 2) {
  if (valor === null || valor === undefined || Number.isNaN(Number(valor))) {
    return "—";
  }

  return Number(valor).toLocaleString("pt-BR", {
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
  });
}

function formatarPeso(valor, casas = 2) {
  if (valor === null || valor === undefined || Number.isNaN(Number(valor))) {
    return "—";
  }

  return formatarNumero(Number(valor), casas);
}

function paraEscalaUnitaria(valor) {
  if (valor === null || valor === undefined || Number.isNaN(Number(valor))) {
    return null;
  }

  const numero = Number(valor);
  return numero > 1 ? numero / 100 : numero;
}

function rotuloIndicador(indicador) {
  if (!indicador) {
    return { titulo: "—", codigo: null };
  }

  return {
    titulo: indicador.nome_indicador || indicador.cod_indicador || "—",
    codigo: indicador.cod_indicador || null,
  };
}

function CelulaIndicador({ indicador, definicoesIndicadores }) {
  const { titulo, codigo } = rotuloIndicador(indicador);
  const { explicacao, importancia } = resolverDefinicaoIndicador(indicador, definicoesIndicadores);

  if (!indicador) {
    return <span className="text-[11px] sm:text-xs">—</span>;
  }

  return (
    <>
      <IndicadorNomeComDefinicao
        nome={titulo}
        explicacao={explicacao}
        importancia={importancia}
        className="block max-w-[140px] text-[11px] leading-snug sm:max-w-none sm:text-xs"
      />
      {codigo && (
        <p className="mt-0.5 font-mono text-[10px] text-brand-cinza/60">{codigo}</p>
      )}
    </>
  );
}

function montarExpressaoDimensao(linha) {
  const scoreInd = linha.score_individual_unidade ?? paraEscalaUnitaria(linha.score_individual);
  const scoreEq = linha.score_equipe_unidade ?? paraEscalaUnitaria(linha.score_equipe);
  const pesoInd = linha.peso_individual;
  const pesoEq = linha.peso_equipe;
  const scoreFinal = linha.score_final_unidade ?? paraEscalaUnitaria(linha.score_final);

  if (scoreInd === null && scoreEq === null) {
    return "—";
  }

  const partes = [];

  if (scoreInd !== null) {
    partes.push(`(${formatarNumero(scoreInd)} × ${formatarPeso(pesoInd)})`);
  }

  if (scoreEq !== null) {
    partes.push(`(${formatarNumero(scoreEq)} × ${formatarPeso(pesoEq)})`);
  }

  let expressao = partes.join(" + ");

  if (scoreFinal !== null) {
    expressao += ` = ${formatarNumero(scoreFinal)}`;
  }

  return expressao;
}

function montarExpressaoContribuicao(linha) {
  const scoreFinal = linha.score_final_unidade ?? paraEscalaUnitaria(linha.score_final);
  const contribuicao =
    linha.contribuicao_iaps_unidade ?? paraEscalaUnitaria(linha.contribuicao_iaps);

  if (scoreFinal === null || contribuicao === null || linha.simbolo === null) {
    return "—";
  }

  return `${linha.simbolo} × ${formatarPeso(linha.peso_dimensao)} = ${formatarNumero(contribuicao)}`;
}

function montarExpressaoIaps(memoriaCalculo, totalIapsUnidade) {
  const termos = memoriaCalculo
    .filter((linha) => linha.simbolo && linha.peso_dimensao !== null)
    .map((linha) => `${linha.simbolo} × ${formatarPeso(linha.peso_dimensao)}`);

  if (!termos.length) {
    return "—";
  }

  const soma =
    totalIapsUnidade !== null && totalIapsUnidade !== undefined
      ? ` = ${formatarNumero(totalIapsUnidade)}`
      : "";

  return `IAPS = ${termos.join(" + ")}${soma}`;
}

function DemonstrativoCalculo({ memoriaCalculo, iapsCalculado, definicoesIndicadores = {} }) {
  if (!memoriaCalculo?.length || !iapsCalculado?.id_colaborador) {
    return null;
  }

  const totalIapsUnidade =
    paraEscalaUnitaria(iapsCalculado.valor) ??
    memoriaCalculo.reduce(
      (acumulado, linha) =>
        acumulado + (linha.contribuicao_iaps_unidade ?? paraEscalaUnitaria(linha.contribuicao_iaps) ?? 0),
      0
    );

  const proporcao = memoriaCalculo[0]?.proporcao_ind_eq || "40/60";
  const [pesoInd, pesoEq] = proporcao.split("/");

  return (
    <section className="card-panel min-w-0 overflow-hidden p-0">
      <div className="border-b border-gray-100 px-4 py-4 sm:px-5">
        <h4 className="section-title">Demonstrativo de Cálculo do IAPS</h4>
        <p className="section-subtitle">
          Memória de cálculo para auditoria · espelha a planilha APD
        </p>

        <div className="mt-3 grid gap-2 text-xs text-brand-cinza sm:grid-cols-2 lg:grid-cols-4">
          <p>
            <span className="font-medium text-brand-cinza/70">Colaborador:</span>{" "}
            {iapsCalculado.nome_colaborador || "—"}
            {iapsCalculado.matricula ? ` (${iapsCalculado.matricula})` : ""}
          </p>
          <p>
            <span className="font-medium text-brand-cinza/70">Papel / Subpapel:</span>{" "}
            {[iapsCalculado.papel, iapsCalculado.subpapel].filter(Boolean).join(" · ") || "—"}
          </p>
          <p>
            <span className="font-medium text-brand-cinza/70">Peso Individual:</span>{" "}
            {formatarPeso(pesoInd ? Number(pesoInd) / 100 : memoriaCalculo[0]?.peso_individual)}
          </p>
          <p>
            <span className="font-medium text-brand-cinza/70">Peso Equipe:</span>{" "}
            {formatarPeso(pesoEq ? Number(pesoEq) / 100 : memoriaCalculo[0]?.peso_equipe)}
          </p>
        </div>
      </div>

      <div className="relative min-w-0">
        <div className="overflow-x-auto pb-1 [-webkit-overflow-scrolling:touch]">
          <table className="w-max min-w-full border-collapse text-sm text-brand-cinza">
            <thead>
              <tr className="bg-brand-verde text-left text-[10px] font-semibold uppercase tracking-wide text-white sm:text-xs">
                <th className="sticky left-0 z-10 border-b border-brand-verde/20 bg-brand-verde px-2 py-2 sm:px-3 sm:py-3">
                  Dimensão
                </th>
                <th className="border-b border-brand-verde/20 px-2 py-2 sm:px-3 sm:py-3">Subpapel</th>
                <th className="border-b border-brand-verde/20 px-2 py-2 text-right sm:px-3 sm:py-3">
                  Peso
                </th>
                <th className="border-b border-brand-verde/20 px-2 py-2 sm:px-3 sm:py-3 min-w-[120px]">
                  Ind. Individual
                </th>
                <th className="border-b border-brand-verde/20 px-2 py-2 text-right sm:px-3 sm:py-3">
                  Sc. Ind.
                </th>
                <th className="border-b border-brand-verde/20 px-2 py-2 sm:px-3 sm:py-3 min-w-[120px]">
                  Ind. Equipe
                </th>
                <th className="border-b border-brand-verde/20 px-2 py-2 text-right sm:px-3 sm:py-3">
                  Sc. Eq.
                </th>
                <th className="border-b border-brand-verde/20 px-2 py-2 text-right sm:px-3 sm:py-3">
                  Sc. Dim.
                </th>
                <th className="border-b border-brand-verde/20 px-2 py-2 text-center sm:px-3 sm:py-3">
                  Var.
                </th>
                <th className="border-b border-brand-verde/20 px-2 py-2 sm:px-3 sm:py-3 min-w-[180px]">
                  Cálculo Dimensão
                </th>
                <th className="border-b border-brand-verde/20 px-2 py-2 sm:px-3 sm:py-3 min-w-[130px]">
                  Contrib. IAPS
                </th>
              </tr>
            </thead>
          <tbody>
            {memoriaCalculo.map((linha) => {
              const scoreInd =
                linha.score_individual_unidade ?? paraEscalaUnitaria(linha.score_individual);
              const scoreEq =
                linha.score_equipe_unidade ?? paraEscalaUnitaria(linha.score_equipe);
              const scoreFinal =
                linha.score_final_unidade ?? paraEscalaUnitaria(linha.score_final);
              const contribuicao =
                linha.contribuicao_iaps_unidade ?? paraEscalaUnitaria(linha.contribuicao_iaps);

              return (
                <tr
                  key={linha.dimensao}
                  className="group border-b border-gray-100 align-top transition hover:bg-brand-verde/[0.03]"
                >
                  <td className="sticky left-0 z-10 bg-white px-2 py-2 font-medium group-hover:bg-brand-verde/[0.03] sm:px-3 sm:py-3">
                    {linha.dimensao}
                  </td>
                  <td className="px-2 py-2 text-xs sm:px-3 sm:py-3">{linha.subpapel_linha || "—"}</td>
                  <td className="px-2 py-2 text-right sm:px-3 sm:py-3">{formatarPeso(linha.peso_dimensao)}</td>
                  <td className="px-2 py-2 sm:px-3 sm:py-3">
                    <CelulaIndicador
                      indicador={linha.indicador_individual}
                      definicoesIndicadores={definicoesIndicadores}
                    />
                  </td>
                  <td className="px-2 py-2 text-right font-semibold text-brand-verde sm:px-3 sm:py-3">
                    {formatarNumero(scoreInd)}
                  </td>
                  <td className="px-2 py-2 sm:px-3 sm:py-3">
                    <CelulaIndicador
                      indicador={linha.indicador_equipe}
                      definicoesIndicadores={definicoesIndicadores}
                    />
                  </td>
                  <td className="px-2 py-2 text-right font-semibold text-brand-verde sm:px-3 sm:py-3">
                    {formatarNumero(scoreEq)}
                  </td>
                  <td className="px-2 py-2 text-right font-bold text-brand-cinza sm:px-3 sm:py-3">
                    {formatarNumero(scoreFinal)}
                  </td>
                  <td className="px-2 py-2 text-center font-mono text-xs font-semibold sm:px-3 sm:py-3">
                    {linha.simbolo || "—"}
                  </td>
                  <td className="px-2 py-2 font-mono text-[10px] leading-relaxed text-brand-cinza/90 sm:px-3 sm:py-3">
                    {montarExpressaoDimensao(linha)}
                  </td>
                  <td className="px-2 py-2 font-mono text-[10px] leading-relaxed sm:px-3 sm:py-3">
                    <span className="text-brand-cinza/90">{montarExpressaoContribuicao(linha)}</span>
                    {contribuicao !== null && (
                      <p className="mt-1 text-right text-sm font-bold text-brand-verde">
                        {formatarNumero(contribuicao)}
                      </p>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
          <tfoot>
            <tr className="bg-gray-50 text-brand-cinza">
              <td className="px-3 py-4 text-xs leading-relaxed" colSpan={10}>
                <p className="font-semibold text-brand-cinza">Fórmula consolidada</p>
                <p className="mt-1 font-mono text-[11px] text-brand-cinza/90">
                  Score Dimensão = (Score Ind. × Peso Ind.) + (Score Eq. × Peso Eq.)
                </p>
                <p className="mt-1 font-mono text-[11px] text-brand-cinza/90">
                  {montarExpressaoIaps(memoriaCalculo, totalIapsUnidade)}
                </p>
                <p className="mt-2 text-[10px] text-brand-cinza/60">
                  Scores em escala 0–1 (conforme planilha de auditoria). Proporção Individual/Equipe:{" "}
                  {proporcao}.
                </p>
              </td>
              <td className="px-3 py-4 text-right">
                <p className="text-xs font-medium uppercase tracking-wide text-brand-cinza/70">
                  IAPS
                </p>
                <p className="text-2xl font-bold text-brand-verde">
                  {formatarNumero(totalIapsUnidade)}
                </p>
              </td>
            </tr>
          </tfoot>
        </table>
        </div>
        <p className="px-4 pb-3 text-[10px] text-brand-cinza/60 sm:px-5">
          Deslize horizontalmente para ver todas as colunas de auditoria.
        </p>
      </div>
    </section>
  );
}

export default DemonstrativoCalculo;
