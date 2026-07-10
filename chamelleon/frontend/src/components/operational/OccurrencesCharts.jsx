import {
  ArcElement,
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  Tooltip,
} from 'chart.js';
import { Bar, Doughnut } from 'react-chartjs-2';

ChartJS.register(ArcElement, BarElement, CategoryScale, LinearScale, Tooltip, Legend);

const DOUGHNUT_COLORS = [
  '#ef4444',
  '#f97316',
  '#f59e0b',
  '#84cc16',
  '#06b6d4',
  '#6366f1',
  '#a855f7',
  '#ec4899',
  '#64748b',
  '#0ea5e9',
];

function formatChartDate(isoDate) {
  if (!isoDate) return '';
  const [year, month, day] = isoDate.split('-');
  return `${day}/${month}`;
}

export default function OccurrencesCharts({ occurrencesByType = [], occurrencesOverTime = [] }) {
  const hasTypeData = occurrencesByType.some((item) => item.count > 0);
  const hasTimeData = occurrencesOverTime.some((item) => item.count > 0);

  if (!hasTypeData && !hasTimeData) {
    return (
      <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
        Nenhuma ocorrência registrada no período selecionado.
      </div>
    );
  }

  const doughnutData = {
    labels: occurrencesByType.map((item) => item.label),
    datasets: [
      {
        data: occurrencesByType.map((item) => item.count),
        backgroundColor: occurrencesByType.map((_, index) => DOUGHNUT_COLORS[index % DOUGHNUT_COLORS.length]),
        borderWidth: 2,
        borderColor: '#ffffff',
      },
    ],
  };

  const barData = {
    labels: occurrencesOverTime.map((item) => formatChartDate(item.date)),
    datasets: [
      {
        label: 'Falhas registradas',
        data: occurrencesOverTime.map((item) => item.count),
        backgroundColor: '#6366f1',
        borderRadius: 6,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
        labels: { boxWidth: 12, font: { size: 11 } },
      },
    },
  };

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-900">Ocorrências por tipo</h3>
        <p className="mt-1 text-xs text-slate-500">Distribuição de falhas e alertas no período.</p>
        <div className="mt-4 h-64">
          {hasTypeData ? (
            <Doughnut data={doughnutData} options={chartOptions} />
          ) : (
            <p className="flex h-full items-center justify-center text-sm text-slate-500">
              Sem dados por tipo.
            </p>
          )}
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-900">Falhas ao longo do tempo</h3>
        <p className="mt-1 text-xs text-slate-500">Volume diário de ocorrências reportadas.</p>
        <div className="mt-4 h-64">
          {hasTimeData ? (
            <Bar
              data={barData}
              options={{
                ...chartOptions,
                scales: {
                  y: { beginAtZero: true, ticks: { precision: 0 } },
                },
              }}
            />
          ) : (
            <p className="flex h-full items-center justify-center text-sm text-slate-500">
              Sem dados temporais.
            </p>
          )}
        </div>
      </section>
    </div>
  );
}
