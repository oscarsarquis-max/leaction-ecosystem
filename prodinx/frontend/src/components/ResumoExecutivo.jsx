import { useMemo } from "react";
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
import { calcularHistoricoIAPS, calcularIAPS, obterTitulosIaps } from "../utils/metricas";
import DetalhamentoDimensoes from "./DetalhamentoDimensoes";
import DemonstrativoCalculo from "./DemonstrativoCalculo";
import { buildDefinicoesIndicadores } from "./IndicadorNomeComDefinicao";

const DESCRICAO_IAPS = "Índice de Avaliação de Produtividade e Serviços";

const tooltipStyle = {
  borderRadius: "8px",
  border: "1px solid #E2E8F0",
  boxShadow: "0 4px 20px rgba(0, 75, 44, 0.08)",
  fontSize: "12px",
};

function formatarIaps(valor, { escalaUnitaria = false } = {}) {
  if (valor === null || valor === undefined || Number.isNaN(Number(valor))) {
    return "—";
  }

  let numero = Number(valor);
  if (escalaUnitaria && numero > 1) {
    numero /= 100;
  }

  return numero.toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function TooltipHistoricoIaps({ active, payload, label }) {
  if (!active || !payload?.length) {
    return null;
  }

  return (
    <div
      className="rounded-lg border border-gray-200 bg-white px-3 py-2 shadow-lg"
      style={tooltipStyle}
    >
      <p className="mb-1 text-xs font-semibold text-brand-cinza">{label}</p>
      {payload.map((entrada) => (
        <p
          key={entrada.dataKey}
          className="text-xs text-brand-cinza"
          style={{ color: entrada.color }}
        >
          {entrada.name}: {formatarIaps(entrada.value)}
        </p>
      ))}
    </div>
  );
}

function CardIaps({ titulo, valor, escalaUnitaria = false, corDestaque, barraCor }) {
  return (
    <article className="card-panel relative flex min-h-[220px] flex-col items-center justify-center overflow-hidden px-6 py-10 text-center">
      <div className={`absolute left-0 top-0 h-1 w-full ${barraCor}`} />

      <h3 className="text-sm font-semibold uppercase tracking-wide text-brand-cinza">
        {titulo}
      </h3>

      <p className="mt-6 text-5xl font-bold leading-none sm:text-6xl" style={{ color: corDestaque }}>
        {formatarIaps(valor, { escalaUnitaria })}
      </p>

      <p className="mt-4 max-w-xs text-xs leading-relaxed text-brand-cinza/70">
        {DESCRICAO_IAPS}
      </p>
    </article>
  );
}

function SparklineHistoricoIaps({ historico }) {
  if (!historico || historico.length === 0) {
    return null;
  }

  return (
    <article className="card-panel overflow-hidden p-4 sm:p-5">
      <div className="mb-3">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-brand-cinza">
          Evolução do IAPS
        </h4>
        <p className="mt-0.5 text-xs text-brand-cinza/70">
          Índice consolidado por mês de referência
        </p>
      </div>

      <div className="h-[140px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={historico} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid vertical={false} horizontal={false} />
            <XAxis
              dataKey="periodo"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 10, fill: BRAND_COLORS.cinza }}
              interval="preserveStartEnd"
              dy={4}
            />
            <YAxis hide domain={["auto", "auto"]} />
            <Tooltip content={<TooltipHistoricoIaps />} />
            <Line
              type="monotone"
              dataKey="iapsSelecionado"
              name="IAPS Alvo"
              stroke={BRAND_COLORS.verde}
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 4, fill: BRAND_COLORS.verde }}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="iapsBaseline"
              name="IAPS Baseline"
              stroke={BRAND_COLORS.cinza}
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
              activeDot={{ r: 4, fill: BRAND_COLORS.cinza }}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </article>
  );
}

function ResumoExecutivo({
  metricas,
  filtros,
  iapsCalculado,
  scoresDimensoes,
  memoriaCalculo,
  modoColaborador = false,
}) {
  const iapsLocal = calcularIAPS(metricas);
  const historicoIaps = calcularHistoricoIAPS(metricas);
  const { tituloSelecionado, tituloReferencial } = obterTitulosIaps(filtros);

  const iapsSelecionado = iapsCalculado?.valor ?? iapsLocal.iapsSelecionado;
  const iapsReferencial =
    iapsCalculado?.iaps_baseline ?? iapsLocal.iapsReferencial;
  const escalaUnitaria = Boolean(iapsCalculado?.id_colaborador);
  const definicoesIndicadores = useMemo(
    () => buildDefinicoesIndicadores(metricas),
    [metricas]
  );

  const semDados = iapsSelecionado === null && iapsReferencial === null;

  if (semDados) {
    return (
      <div className="card-panel border-dashed text-center text-sm text-brand-cinza">
        Nenhuma métrica com dimensão SPACE disponível para calcular o IAPS.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="mx-auto max-w-5xl space-y-6">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <CardIaps
            titulo={tituloSelecionado}
            valor={iapsSelecionado}
            escalaUnitaria={escalaUnitaria}
            corDestaque={BRAND_COLORS.verde}
            barraCor="bg-brand-verde"
          />
          <CardIaps
            titulo={tituloReferencial}
            valor={iapsReferencial}
            escalaUnitaria={escalaUnitaria}
            corDestaque={BRAND_COLORS.cinza}
            barraCor="bg-brand-cinza"
          />
        </div>

        {modoColaborador && (
          <DetalhamentoDimensoes
            scoresDimensoes={scoresDimensoes}
            colaboradorNome={iapsCalculado?.nome_colaborador}
          />
        )}

        <SparklineHistoricoIaps historico={historicoIaps} />
      </div>

      <DemonstrativoCalculo
        memoriaCalculo={memoriaCalculo}
        iapsCalculado={iapsCalculado}
        definicoesIndicadores={definicoesIndicadores}
      />
    </div>
  );
}

export default ResumoExecutivo;
