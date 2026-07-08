import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { BRAND_COLORS } from "../theme/brand";

const ABREV_DIMENSAO = {
  Satisfação: "SAT",
  Performance: "PER",
  Atividade: "ATV",
  Comunicação: "COM",
  Eficiência: "EFI",
};

function normalizarScore(valor) {
  if (valor === null || valor === undefined || Number.isNaN(Number(valor))) {
    return null;
  }

  const numero = Number(valor);
  return numero <= 1 ? Number((numero * 100).toFixed(1)) : Number(numero.toFixed(1));
}

function TooltipDimensoes({ active, payload, label }) {
  if (!active || !payload?.length) {
    return null;
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs shadow-lg">
      <p className="mb-1 font-semibold text-brand-cinza">{label}</p>
      {payload.map((entrada) => (
        <p key={entrada.dataKey} style={{ color: entrada.color }}>
          {entrada.name}: {entrada.value ?? "—"}
        </p>
      ))}
    </div>
  );
}

function GraficoDimensoes({ scoresDimensoes }) {
  const dados = useMemo(
    () =>
      (scoresDimensoes || []).map((item) => ({
        dimensao: ABREV_DIMENSAO[item.dimensao] || item.dimensao,
        individual: normalizarScore(item.nota_individual),
        equipe: normalizarScore(item.nota_equipe),
      })),
    [scoresDimensoes]
  );

  if (!dados.length) {
    return null;
  }

  return (
    <article className="card-panel p-4 sm:p-5">
      <div className="mb-4">
        <h4 className="text-sm font-semibold text-brand-verde">Individual vs. Equipe por Dimensão</h4>
        <p className="mt-0.5 text-xs text-brand-cinza/70">
          Contraste SPACE que alimenta a análise cruzada
        </p>
      </div>
      <div className="h-[260px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={dados} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
            <XAxis dataKey="dimensao" tick={{ fontSize: 11, fill: BRAND_COLORS.cinza }} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: BRAND_COLORS.cinza }} />
            <Tooltip content={<TooltipDimensoes />} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Bar
              dataKey="individual"
              name="Individual"
              fill={BRAND_COLORS.verde}
              radius={[4, 4, 0, 0]}
            />
            <Bar
              dataKey="equipe"
              name="Equipe"
              fill={BRAND_COLORS.laranja}
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </article>
  );
}

function GraficoGapsIndicadores({ memoriaCalculo }) {
  const dados = useMemo(() => {
    const itens = [];

    (memoriaCalculo || []).forEach((linha) => {
      const ind = linha.indicador_individual;
      const eq = linha.indicador_equipe;

      if (!ind?.cod_indicador && !eq?.cod_indicador) {
        return;
      }

      const scoreInd = ind?.score ?? null;
      const scoreEq = eq?.score ?? null;

      if (scoreInd === null && scoreEq === null) {
        return;
      }

      itens.push({
        codigo: ind?.cod_indicador || eq?.cod_indicador,
        individual: scoreInd,
        equipe: scoreEq,
        gap: scoreInd != null && scoreEq != null ? Number((scoreInd - scoreEq).toFixed(1)) : null,
      });
    });

    return itens
      .sort((a, b) => Math.abs(b.gap || 0) - Math.abs(a.gap || 0))
      .slice(0, 8);
  }, [memoriaCalculo]);

  if (!dados.length) {
    return null;
  }

  return (
    <article className="card-panel p-4 sm:p-5">
      <div className="mb-4">
        <h4 className="text-sm font-semibold text-brand-verde">Gaps por Indicador</h4>
        <p className="mt-0.5 text-xs text-brand-cinza/70">
          Maiores discrepâncias entre nota individual e baseline de equipe
        </p>
      </div>
      <div className="h-[280px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={dados}
            layout="vertical"
            margin={{ top: 4, right: 16, left: 8, bottom: 4 }}
          >
            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#E5E7EB" />
            <XAxis type="number" domain={[-100, 100]} tick={{ fontSize: 10 }} />
            <YAxis
              type="category"
              dataKey="codigo"
              width={48}
              tick={{ fontSize: 11, fill: BRAND_COLORS.cinza }}
            />
            <Tooltip
              formatter={(valor, nome) => [valor ?? "—", nome]}
              contentStyle={{ fontSize: 12, borderRadius: 8 }}
            />
            <Bar
              dataKey="gap"
              name="Gap (Ind − Eq)"
              fill={BRAND_COLORS.vermelho}
              radius={[0, 4, 4, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </article>
  );
}

function GraficosAnaliseCruzada({ scoresDimensoes, memoriaCalculo }) {
  return (
    <div className="space-y-6">
      <GraficoDimensoes scoresDimensoes={scoresDimensoes} />
      <GraficoGapsIndicadores memoriaCalculo={memoriaCalculo} />
    </div>
  );
}

export default GraficosAnaliseCruzada;
