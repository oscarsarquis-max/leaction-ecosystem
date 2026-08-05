import { GUIDED_STEPS, type GuidedStep } from "@/api/guidedTypes";

type Props = {
  currentStep: GuidedStep;
  routeProgress?: { answered: number; total: number };
};

export function GuidedProgress({ currentStep, routeProgress }: Props) {
  const idx = GUIDED_STEPS.findIndex((s) => s.id === currentStep);
  const pct = Math.round(((Math.max(idx, 0) + 1) / GUIDED_STEPS.length) * 100);

  return (
    <div className="guided-progress" data-testid="guided-progress">
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--qm-muted)]">
          Progresso da avaliação
        </p>
        <p className="text-sm text-[var(--qm-ink)]">{pct}%</p>
      </div>
      <div
        className="mt-2 h-1.5 overflow-hidden rounded-full bg-[var(--qm-line)]"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="h-full rounded-full bg-[var(--qm-ink)] transition-[width] duration-300 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
      <ol className="mt-4 hidden gap-2 md:grid md:grid-cols-4 lg:grid-cols-8">
        {GUIDED_STEPS.map((step, i) => {
          const active = step.id === currentStep;
          const done = i < idx;
          return (
            <li
              key={step.id}
              className={
                active
                  ? "text-[var(--qm-ink)]"
                  : done
                    ? "text-[var(--qm-ink)]/70"
                    : "text-[var(--qm-muted)]"
              }
            >
              <p className="text-[11px] font-semibold leading-tight">{step.label}</p>
            </li>
          );
        })}
      </ol>
      {currentStep === "route" && routeProgress ? (
        <p className="mt-3 text-sm text-[var(--qm-muted)]">
          Roteiro: {routeProgress.answered} de {routeProgress.total} perguntas
          respondidas
        </p>
      ) : null}
    </div>
  );
}
