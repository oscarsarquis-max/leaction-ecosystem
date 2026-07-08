import { BRAND_COLORS } from "../theme/brand";

const ORDEM_DIMENSOES = [
  "Satisfação",
  "Performance",
  "Atividade",
  "Comunicação",
  "Eficiência",
];

const CORES_DIMENSAO = {
  Satisfação: BRAND_COLORS.laranja,
  Performance: BRAND_COLORS.verde,
  Atividade: BRAND_COLORS.cinza,
  Comunicação: BRAND_COLORS.vermelho,
  Eficiência: "#1B6B47",
};

const ABREV_DIMENSAO = {
  Satisfação: "SAT",
  Performance: "PER",
  Atividade: "ATV",
  Comunicação: "COM",
  Eficiência: "EFI",
};

function formatarScore(valor) {
  if (valor === null || valor === undefined || Number.isNaN(Number(valor))) {
    return "—";
  }

  return Number(valor).toLocaleString("pt-BR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
}

function AnelProgresso({ valor, cor, tamanho = 72 }) {
  const score = Math.max(0, Math.min(100, Number(valor) || 0));
  const stroke = 6;
  const raio = (tamanho - stroke) / 2;
  const circunferencia = 2 * Math.PI * raio;
  const offset = circunferencia - (score / 100) * circunferencia;
  const centro = tamanho / 2;

  return (
    <svg
      width={tamanho}
      height={tamanho}
      viewBox={`0 0 ${tamanho} ${tamanho}`}
      className="mx-auto"
      aria-hidden
    >
      <circle
        cx={centro}
        cy={centro}
        r={raio}
        fill="none"
        stroke="#E5E7EB"
        strokeWidth={stroke}
      />
      <circle
        cx={centro}
        cy={centro}
        r={raio}
        fill="none"
        stroke={cor}
        strokeWidth={stroke}
        strokeLinecap="round"
        strokeDasharray={circunferencia}
        strokeDashoffset={offset}
        transform={`rotate(-90 ${centro} ${centro})`}
      />
    </svg>
  );
}

function MiniCardDimensao({ dimensao, scoreDimensao, pesoDimensao, notaIndividual, notaEquipe }) {
  const cor = CORES_DIMENSAO[dimensao] || BRAND_COLORS.verde;
  const temScore = scoreDimensao !== null && scoreDimensao !== undefined;

  return (
    <article
      className="flex flex-col items-center rounded-xl border border-gray-100 bg-white px-2 py-3 text-center shadow-sm transition-shadow hover:shadow-md"
      title={
        temScore
          ? `${dimensao}: Individual ${formatarScore(notaIndividual)} · Equipe ${formatarScore(notaEquipe)}`
          : dimensao
      }
    >
      <div className="relative flex h-[72px] w-[72px] items-center justify-center">
        <AnelProgresso valor={temScore ? scoreDimensao : 0} cor={cor} />
        <span
          className="absolute text-sm font-bold leading-none"
          style={{ color: temScore ? cor : BRAND_COLORS.cinza }}
        >
          {formatarScore(scoreDimensao)}
        </span>
      </div>

      <p className="mt-2 text-[10px] font-semibold uppercase tracking-wide text-brand-cinza/60">
        {ABREV_DIMENSAO[dimensao] || dimensao.slice(0, 3)}
      </p>
      <p className="mt-0.5 line-clamp-2 text-xs font-semibold leading-tight text-brand-cinza">
        {dimensao}
      </p>
      {pesoDimensao != null && (
        <p className="mt-1 text-[10px] text-brand-cinza/50">
          Peso{" "}
          {(pesoDimensao * 100).toLocaleString("pt-BR", { maximumFractionDigits: 0 })}%
        </p>
      )}
      {(notaIndividual != null || notaEquipe != null) && (
        <p className="mt-1 text-[10px] leading-tight text-brand-cinza/60">
          Ind.{" "}
          {notaIndividual != null
            ? (notaIndividual > 1 ? notaIndividual / 100 : notaIndividual).toLocaleString("pt-BR", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })
            : "—"}{" "}
          · Eq.{" "}
          {notaEquipe != null
            ? (notaEquipe > 1 ? notaEquipe / 100 : notaEquipe).toLocaleString("pt-BR", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })
            : "—"}
        </p>
      )}
    </article>
  );
}

function ordenarDimensoes(scoresDimensoes) {
  const porNome = new Map(scoresDimensoes.map((item) => [item.dimensao, item]));

  return ORDEM_DIMENSOES.map((dimensao) => porNome.get(dimensao)).filter(Boolean);
}

function DetalhamentoDimensoes({ scoresDimensoes, colaboradorNome }) {
  if (!scoresDimensoes?.length) {
    return null;
  }

  const dimensoesOrdenadas = ordenarDimensoes(scoresDimensoes);

  return (
    <section className="card-panel overflow-hidden p-4 sm:p-5">
      <div className="mb-4 flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-brand-cinza">
            Detalhamento por Dimensão
          </h4>
          <p className="mt-0.5 text-xs text-brand-cinza/70">
            Score final por dimensão SPACE · detalhe do cálculo na tabela de auditoria abaixo
          </p>
        </div>
        {colaboradorNome && (
          <p className="text-xs font-medium text-brand-verde">{colaboradorNome}</p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {dimensoesOrdenadas.map((item) => (
          <MiniCardDimensao
            key={item.dimensao}
            dimensao={item.dimensao}
            scoreDimensao={item.score_dimensao}
            pesoDimensao={item.peso_dimensao}
            notaIndividual={item.nota_individual}
            notaEquipe={item.nota_equipe}
          />
        ))}
      </div>
    </section>
  );
}

export default DetalhamentoDimensoes;
