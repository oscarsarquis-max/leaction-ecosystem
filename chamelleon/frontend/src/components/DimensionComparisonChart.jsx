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
import {
  buildDimensionRows,
  DIM_SHORT,
  getNumericScore,
  sectorDimShort,
} from '../utils/diagnosticScores';
import {
  computeFocusedScale,
  createDiagGapPlugin,
  diagBarFill,
  DIAG_CHART,
} from '../utils/diagChartConfig';

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

function ChartLegend({ sectorLegendLabel = 'Setorial' }) {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-2 text-xs font-bold text-slate-600">
      <li className="inline-flex items-center gap-1.5">
        <span className="h-2.5 w-2.5 rounded-full bg-[#7c2d12]" />
        Realidade
      </li>
      <li className="inline-flex items-center gap-1.5">
        <span className="h-2.5 w-2.5 rounded-full bg-[#6c5ce7]" />
        Ambição
      </li>
      <li className="inline-flex items-center gap-1.5">
        <span className="h-2.5 w-2.5 rounded-full bg-[#d97706]" />
        {sectorLegendLabel}
      </li>
    </ul>
  );
}

export default function DimensionComparisonChart({
  scoresPresente = {},
  scoresFuturo = {},
  scoresGap = {},
  scoresSetorialPresente = {},
  sectorDimensionLabel,
  sectorLegendLabel,
}) {
  const pdimPres = scoresPresente.pdim_scores || {};
  const pdimFut = scoresFuturo.pdim_scores || {};
  const pdimGap = scoresGap.pdim_scores || {};
  const pdimSect = scoresSetorialPresente.pdim_scores || {};

  const dimShort = useMemo(() => {
    const sect = sectorDimShort(sectorDimensionLabel);
    return { ...DIM_SHORT, 4: sect };
  }, [sectorDimensionLabel]);

  const chartPayload = useMemo(() => {
    const dimensionRows = buildDimensionRows(sectorDimensionLabel);
    const labels = [];
    const dimNames = [];
    const clientScoresPresente = [];
    const clientScoresFuturo = [];
    const sectorScores = [];
    const gapItems = [];

    dimensionRows.forEach((dim) => {
      const id = String(dim.id);
      labels.push(dimShort[dim.id] || dim.name);
      dimNames.push(dim.name);
      const pres = getNumericScore(pdimPres[id]);
      const fut = getNumericScore(pdimFut[id]);
      const gap = getNumericScore(pdimGap[id]) || Math.max(0, fut - pres);
      clientScoresPresente.push(pres);
      clientScoresFuturo.push(fut);
      sectorScores.push(getNumericScore(pdimSect[id]));
      gapItems.push({ pres, fut, gap, index: gapItems.length });
    });

    const xScale = computeFocusedScale([
      ...clientScoresPresente,
      ...clientScoresFuturo,
      ...sectorScores,
    ]);

    const gapPlugin = createDiagGapPlugin(
      gapItems.filter((g) => g.gap > 0.001),
      'grouped',
      'dimGapPlugin',
    );

    return {
      dimNames,
      gapItems,
      xScale,
      gapPlugin,
      data: {
        labels,
        datasets: [
          {
            label: 'Realidade',
            data: clientScoresPresente,
            backgroundColor: diagBarFill(DIAG_CHART.realidade),
            borderColor: DIAG_CHART.realidade.border,
            borderWidth: 2,
            borderRadius: 4,
            borderSkipped: false,
          },
          {
            label: 'Ambição',
            data: clientScoresFuturo,
            backgroundColor: diagBarFill(DIAG_CHART.ambicao),
            borderColor: DIAG_CHART.ambicao.border,
            borderWidth: 2,
            borderRadius: 4,
            borderSkipped: false,
          },
          {
            label: sectorLegendLabel || 'Setorial',
            data: sectorScores,
            backgroundColor: diagBarFill(DIAG_CHART.setorial),
            borderColor: DIAG_CHART.setorial.border,
            borderWidth: 2,
            borderRadius: 4,
            borderSkipped: false,
          },
        ],
      },
    };
  }, [
    pdimPres,
    pdimFut,
    pdimGap,
    pdimSect,
    sectorDimensionLabel,
    sectorLegendLabel,
    dimShort,
  ]);

  if (Object.keys(pdimPres).length === 0) {
    return null;
  }

  const { data, dimNames, gapItems, xScale, gapPlugin } = chartPayload;

  const options = {
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
          font: DIAG_CHART.font,
          color: DIAG_CHART.tick,
        },
        grid: { color: DIAG_CHART.grid },
      },
      y: {
        ticks: {
          font: { ...DIAG_CHART.font, weight: '700' },
          color: '#4A2E80',
        },
        grid: { display: false },
      },
    },
    plugins: {
      legend: { display: false },
      title: { display: false },
      tooltip: {
        callbacks: {
          title: (items) => dimNames[items[0].dataIndex] || items[0].label,
          label: (item) => `${item.dataset.label}: ${Number(item.raw).toFixed(2)}`,
          afterBody: (items) => {
            const idx = items[0].dataIndex;
            const gapVal = gapItems[idx]?.gap ?? 0;
            return gapVal > 0.001 ? [`Lacuna: ${gapVal.toFixed(2)}`] : [];
          },
        },
      },
    },
  };

  return (
    <section className="rounded-2xl border border-violet-100 bg-white p-5 shadow-sm md:p-6">
      <header className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <span className="text-[0.68rem] font-extrabold uppercase tracking-wider text-amber-600">
            Análise detalhada
          </span>
          <h2 className="mt-1 text-xl font-extrabold text-[#4A2E80]">
            Dimensões — Realidade vs Ambição
          </h2>
          <p className="mt-1 max-w-xl text-sm text-slate-500">
            Escala ampliada para destacar lacunas pequenas entre realidade e ambição.
          </p>
        </div>
        <ChartLegend sectorLegendLabel={sectorLegendLabel || 'Setorial'} />
      </header>
      <div className="h-[300px]">
        <Bar data={data} options={options} plugins={[gapPlugin]} />
      </div>
    </section>
  );
}
