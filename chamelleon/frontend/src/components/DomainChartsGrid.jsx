import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';
import { useMemo } from 'react';
import { DOMAIN_ROWS, getNumericScore, sectorDimShort } from '../utils/diagnosticScores';
import {
  computeFocusedScale,
  createDiagGapPlugin,
  diagBarFill,
  DIAG_CHART,
} from '../utils/diagChartConfig';

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

function DomainMiniChart({ dom, scorePres, scoreFut, scoreSect, gap, sectShort, sectFullLabel }) {
  const { data, options, gapPlugin } = useMemo(() => {
    const xScale = computeFocusedScale([scorePres, scoreFut, scoreSect], 1.0);
    const gapBarData =
      gap > 0.001
        ? [[Math.min(scorePres, scoreFut), Math.max(scorePres, scoreFut)], null, null]
        : [null, null, null];

    const labels = ['Real.', 'Amb.', sectShort];
    const tooltipMap = {
      'Real.': 'Realidade',
      'Amb.': 'Ambição',
      [sectShort]: sectFullLabel,
    };

    const gapPluginLocal = createDiagGapPlugin(
      [{ pres: scorePres, fut: scoreFut, gap }],
      'rows',
      `domGap_${dom.id}`,
    );

    return {
      gapPlugin: gapPluginLocal,
      data: {
        labels,
        datasets: [
          {
            label: 'Lacuna',
            data: gapBarData,
            backgroundColor: 'rgba(185, 28, 28, 0.55)',
            borderColor: DIAG_CHART.gapLine,
            borderWidth: 2,
            borderRadius: 3,
            borderSkipped: false,
            barThickness: 9,
            order: 2,
          },
          {
            label: 'Nota',
            data: [scorePres, scoreFut, scoreSect],
            backgroundColor: [
              diagBarFill(DIAG_CHART.realidade),
              diagBarFill(DIAG_CHART.ambicao),
              diagBarFill(DIAG_CHART.setorial),
            ],
            borderColor: [
              DIAG_CHART.realidade.border,
              DIAG_CHART.ambicao.border,
              DIAG_CHART.setorial.border,
            ],
            borderWidth: 2,
            borderRadius: 6,
            borderSkipped: false,
            order: 1,
          },
        ],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        scales: {
          x: {
            min: xScale.min,
            max: xScale.max,
            ticks: {
              stepSize: 0.5,
              font: { ...DIAG_CHART.font, size: 9 },
              color: DIAG_CHART.tick,
              maxTicksLimit: 5,
            },
            grid: { color: DIAG_CHART.grid },
          },
          y: {
            ticks: {
              font: { ...DIAG_CHART.font, weight: '700', size: 10 },
              color: '#4A2E80',
            },
            grid: { display: false },
          },
        },
        plugins: {
          legend: { display: false },
          title: { display: false },
          tooltip: {
            filter: (item) => item.dataset.label !== 'Lacuna',
            callbacks: {
              title: (items) => tooltipMap[items[0].label] || items[0].label,
              label: (item) => {
                const lines = [`Nota: ${Number(item.raw).toFixed(2)}`];
                if (item.label === 'Amb.' && gap > 0.001) {
                  lines.push(`Lacuna: ${gap.toFixed(2)}`);
                }
                return lines;
              },
            },
          },
        },
      },
    };
  }, [dom.id, scorePres, scoreFut, scoreSect, gap, sectShort, sectFullLabel]);

  return (
    <article className="rounded-xl border border-violet-100 bg-white p-3 shadow-sm">
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <span className="inline-block rounded-md bg-violet-100 px-2 py-0.5 text-[0.65rem] font-extrabold uppercase tracking-wide text-[#4A2E80]">
            {dom.sigla}
          </span>
          <h3 className="mt-1 text-sm font-bold leading-snug text-slate-800">{dom.shortName}</h3>
        </div>
        {gap > 0.001 && (
          <span className="shrink-0 rounded-full bg-red-600 px-2 py-0.5 text-[0.65rem] font-bold text-white">
            Δ {gap.toFixed(1)}
          </span>
        )}
      </div>
      <div className="h-[110px]">
        <Bar data={data} options={options} plugins={[gapPlugin]} />
      </div>
    </article>
  );
}

export default function DomainChartsGrid({
  scoresPresente = {},
  scoresFuturo = {},
  scoresGap = {},
  scoresSetorialPresente = {},
  sectorDimensionLabel,
  sectorLegendLabel,
}) {
  const pdomPres = scoresPresente.pdom_scores || {};
  const pdomFut = scoresFuturo.pdom_scores || {};
  const pdomGap = scoresGap.pdom_scores || {};
  const pdomSect = scoresSetorialPresente.pdom_scores || {};

  const sectShort = sectorDimShort(sectorDimensionLabel);
  const sectFullLabel = sectorLegendLabel || 'Setor';

  if (Object.keys(pdomPres).length === 0) {
    return null;
  }

  return (
    <section className="rounded-2xl border border-violet-100 bg-white p-5 shadow-sm md:p-6">
      <header className="mb-4">
        <span className="text-[0.68rem] font-extrabold uppercase tracking-wider text-amber-600">
          Comparativo
        </span>
        <h2 className="mt-1 text-xl font-extrabold text-[#4A2E80]">
          Domínios — Realidade, Ambição e Referência Setorial
        </h2>
      </header>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {DOMAIN_ROWS.map((dom) => {
          const id = String(dom.id);
          const scorePres = getNumericScore(pdomPres[id]);
          const scoreFut = getNumericScore(pdomFut[id]);
          const scoreSect = getNumericScore(pdomSect[id]);
          const gap = getNumericScore(pdomGap[id]) || Math.max(0, scoreFut - scorePres);
          return (
            <DomainMiniChart
              key={dom.id}
              dom={dom}
              scorePres={scorePres}
              scoreFut={scoreFut}
              scoreSect={scoreSect}
              gap={gap}
              sectShort={sectShort}
              sectFullLabel={sectFullLabel}
            />
          );
        })}
      </div>
    </section>
  );
}
