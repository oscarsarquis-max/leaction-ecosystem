import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { BRAND_COLORS } from "../theme/brand";
import { formatarData } from "../utils/datas";
import { IndicadorNomeComDefinicao } from "./IndicadorNomeComDefinicao";

const tooltipStyle = {
  borderRadius: "8px",
  border: "1px solid #E2E8F0",
  boxShadow: "0 4px 20px rgba(0, 75, 44, 0.08)",
};

const CLASSES_BADGE_DIMENSAO = {
  Performance: "bg-blue-100 text-blue-900",
  Eficiência: "bg-purple-100 text-purple-900",
  Atividade: "bg-gray-200 text-gray-800",
  Satisfação: "bg-yellow-100 text-yellow-900",
  Comunicação: "bg-orange-100 text-orange-900",
};

function BadgeDimensao({ dimensao }) {
  if (!dimensao) {
    return null;
  }

  const classes =
    CLASSES_BADGE_DIMENSAO[dimensao] ?? "bg-gray-100 text-brand-cinza";

  return (
    <span
      className={`inline-flex shrink-0 rounded-full px-2 py-1 text-xs font-semibold ${classes}`}
    >
      {dimensao}
    </span>
  );
}

function formatarScore(valor) {
  if (valor === null || valor === undefined || Number.isNaN(Number(valor))) {
    return "—";
  }

  return `${Number(valor).toFixed(1)}%`;
}

function limitarPercentual(valor) {
  if (valor === null || valor === undefined || Number.isNaN(Number(valor))) {
    return 0;
  }

  return Math.min(100, Math.max(0, Number(valor)));
}

function BarraComparativa({ rotulo, subtitulo, valor, corBarra, corTexto }) {
  const percentual = limitarPercentual(valor);
  const temValor = valor !== null && valor !== undefined && !Number.isNaN(Number(valor));

  return (
    <div className="space-y-2">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-cinza">
            {rotulo}
          </p>
          {subtitulo && (
            <p className="mt-0.5 truncate text-sm text-brand-cinza/75">{subtitulo}</p>
          )}
        </div>
        <span
          className="shrink-0 text-lg font-bold tabular-nums"
          style={{ color: temValor ? corTexto : BRAND_COLORS.cinza }}
        >
          {formatarScore(valor)}
        </span>
      </div>

      <div className="h-3 w-full overflow-hidden rounded-full bg-gray-200">
        <div
          className="h-full rounded-full transition-all duration-500 ease-out"
          style={{
            width: temValor ? `${percentual}%` : "0%",
            backgroundColor: corBarra,
          }}
        />
      </div>
    </div>
  );
}

function ComparativoPerformance({
  scoreSelecionado,
  scoreBaseline,
  subtituloAlvo,
  subtituloBaseline,
}) {
  return (
    <div className="flex h-full flex-col rounded-lg border border-gray-100 bg-gray-50/60 p-4">
      <h4 className="text-xs font-semibold uppercase tracking-wide text-brand-cinza">
        Comparativo de Performance
      </h4>
      <p className="mt-1 text-sm text-brand-cinza/80">
        Score do escopo selecionado frente ao referencial de comparação
      </p>

      <div className="mt-5 flex flex-1 flex-col justify-center gap-6">
        <BarraComparativa
          rotulo="Score do Colaborador"
          subtitulo={subtituloAlvo}
          valor={scoreSelecionado}
          corBarra={BRAND_COLORS.verde}
          corTexto={BRAND_COLORS.verde}
        />

        <BarraComparativa
          rotulo="Baseline / Referencial"
          subtitulo={subtituloBaseline}
          valor={scoreBaseline}
          corBarra={BRAND_COLORS.laranja}
          corTexto={BRAND_COLORS.cinza}
        />
      </div>
    </div>
  );
}

function ColunaEvolucao({ evolucao }) {
  const temDados = evolucao.length > 0;

  return (
    <div className="flex h-full flex-col rounded-lg border border-gray-100 bg-white p-4">
      <h4 className="text-xs font-semibold uppercase tracking-wide text-brand-cinza">
        Evolução Histórica
      </h4>
      <p className="mt-1 text-sm text-brand-cinza/80">Resultado vs referencial no período</p>

      <div className="mt-3 min-h-[200px] flex-1">
        {temDados ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={evolucao} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid vertical={false} horizontal={false} />
              <XAxis
                dataKey="data_referencia"
                tick={{ fontSize: 10, fill: BRAND_COLORS.cinza }}
                tickFormatter={formatarData}
                interval="preserveStartEnd"
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fontSize: 10, fill: BRAND_COLORS.cinza }}
                width={32}
              />
              <Tooltip contentStyle={tooltipStyle} labelFormatter={formatarData} />
              <Line
                type="monotone"
                dataKey="score"
                name="Alvo"
                stroke={BRAND_COLORS.verde}
                strokeWidth={2.5}
                dot={{ r: 3, fill: BRAND_COLORS.verde }}
                connectNulls
              />
              <Line
                type="monotone"
                dataKey="baseline"
                name="Referencial"
                stroke={BRAND_COLORS.cinza}
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={false}
                connectNulls
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <p className="py-12 text-center text-sm text-brand-cinza/60">Sem histórico disponível.</p>
        )}
      </div>
    </div>
  );
}

function PainelIndicador({ dados }) {
  const {
    cod_indicador,
    nome_metrica,
    dimensao,
    explicacao,
    importancia,
    score_selecionado,
    score_baseline,
    subtitulo_alvo,
    subtitulo_baseline,
    evolucao,
  } = dados;

  return (
    <article className="overflow-visible rounded-xl border border-gray-200 bg-white shadow-card">
      <header className="flex items-start justify-between gap-3 border-t-4 border-brand-verde bg-gray-50 px-5 py-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-xs font-medium uppercase tracking-wide text-brand-cinza/70">
              {cod_indicador}
            </p>
            <BadgeDimensao dimensao={dimensao} />
          </div>
          <div className="mt-0.5 flex flex-wrap items-center gap-2">
            <h3 className="text-base font-semibold leading-snug text-brand-cinza">
              <IndicadorNomeComDefinicao
                nome={nome_metrica}
                explicacao={explicacao}
                importancia={importancia}
              />
            </h3>
          </div>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-6 p-4 lg:grid-cols-2">
        <ComparativoPerformance
          scoreSelecionado={score_selecionado}
          scoreBaseline={score_baseline}
          subtituloAlvo={subtitulo_alvo}
          subtituloBaseline={subtitulo_baseline}
        />

        <ColunaEvolucao evolucao={evolucao} />
      </div>
    </article>
  );
}

export default PainelIndicador;
