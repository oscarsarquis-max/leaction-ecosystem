import {
  buildDimensionRows,
  buildDomainRows,
  formatScore,
  getClientStage,
} from '../utils/diagnosticScores';

function StagePill({ stage }) {
  return (
    <span className="inline-block rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700">
      {stage}
    </span>
  );
}

function ScoreCell({ value, highlightGap = false }) {
  const num = parseFloat(value);
  const gapClass =
    highlightGap && !Number.isNaN(num) && num > 0
      ? 'text-amber-700 font-semibold'
      : highlightGap
        ? 'text-emerald-700 font-semibold'
        : '';
  return <td className={`px-4 py-2.5 text-right tabular-nums ${gapClass}`}>{value}</td>;
}

function SectionRow({ label, colSpan = 5 }) {
  return (
    <tr className="bg-slate-50">
      <td
        colSpan={colSpan}
        className="px-4 py-2 text-xs font-bold uppercase tracking-wide text-slate-500"
      >
        {label}
      </td>
    </tr>
  );
}

export default function ScoreComparativeTable({
  scoreGeralPresente,
  scoreGeralFuturo,
  scoreGeralGap,
  scoresPresente = {},
  scoresFuturo = {},
  scoresGap = {},
  sectorDimensionLabel,
  domainLabels = {},
  title = 'Detalhamento e Comparativo de Notas',
}) {
  const dimPres = scoresPresente.pdim_scores || {};
  const dimFut = scoresFuturo.pdim_scores || {};
  const dimGap = scoresGap.pdim_scores || {};

  const domPres = scoresPresente.pdom_scores || {};
  const domFut = scoresFuturo.pdom_scores || {};
  const domGap = scoresGap.pdom_scores || {};

  const dimensionRows = buildDimensionRows(sectorDimensionLabel);
  const domainRows = buildDomainRows(domainLabels);

  const hasData =
    Object.keys(dimPres).length > 0 ||
    Object.keys(domPres).length > 0 ||
    scoreGeralPresente != null;

  if (!hasData) {
    return (
      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-800">{title}</h2>
        <p className="mt-3 text-sm text-slate-500">Sem dados comparativos disponíveis.</p>
      </section>
    );
  }

  const geralPres =
    scoreGeralPresente != null ? parseFloat(scoreGeralPresente).toFixed(2) : '0.00';
  const geralFut =
    scoreGeralFuturo != null ? parseFloat(scoreGeralFuturo).toFixed(2) : '0.00';
  const geralGap =
    scoreGeralGap != null ? parseFloat(scoreGeralGap).toFixed(2) : '0.00';

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-slate-800">{title}</h2>
      <div className="mt-4 overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead>
            <tr className="text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
              <th className="px-4 py-3">Maturidade</th>
              <th className="px-4 py-3 text-right">Realidade</th>
              <th className="px-4 py-3 text-right">Ambição</th>
              <th className="px-4 py-3 text-right">Lacuna</th>
              <th className="px-4 py-3">Estágio</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            <tr className="bg-chameleon/5 font-medium text-slate-900">
              <td className="px-4 py-3">Nota Geral de Maturidade</td>
              <ScoreCell value={geralPres} />
              <ScoreCell value={geralFut} />
              <ScoreCell value={geralGap} highlightGap />
              <td className="px-4 py-3">
                <StagePill stage={getClientStage(scoreGeralPresente)} />
              </td>
            </tr>

            <SectionRow label="Dimensão" />
            {dimensionRows.map((dim) => {
              const pres = formatScore(dimPres, dim.id);
              const fut = formatScore(dimFut, dim.id);
              const gap = formatScore(dimGap, dim.id);
              return (
                <tr key={`dim-${dim.id}`} className="text-slate-700">
                  <td className="px-4 py-2.5">{dim.name}</td>
                  <ScoreCell value={pres} />
                  <ScoreCell value={fut} />
                  <ScoreCell value={gap} highlightGap />
                  <td className="px-4 py-2.5">
                    <StagePill stage={getClientStage(pres)} />
                  </td>
                </tr>
              );
            })}

            <SectionRow label="Domínio" />
            {domainRows.map((dom) => {
              const pres = formatScore(domPres, dom.id);
              const fut = formatScore(domFut, dom.id);
              const gap = formatScore(domGap, dom.id);
              return (
                <tr key={`dom-${dom.id}`} className="text-slate-700">
                  <td className="px-4 py-2.5">{dom.name}</td>
                  <ScoreCell value={pres} />
                  <ScoreCell value={fut} />
                  <ScoreCell value={gap} highlightGap />
                  <td className="px-4 py-2.5">
                    <StagePill stage={getClientStage(pres)} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
