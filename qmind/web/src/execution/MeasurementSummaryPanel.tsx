import {
  formatMeasurementValue,
  formatTarget,
  MEASUREMENT_POSTURE_LABELS,
  measurementPostureTone,
  SUBSTANTIATION_LABELS,
  TARGET_NOT_EFFICACY_WARNING,
  TARGET_POSTURE_LABELS,
  TARGET_STATE_LABELS,
  targetPostureTone,
} from "@/execution/measurementLabels";
import { formatShortDate } from "@/execution/labels";
import type {
  MeasurementPosture,
  SubstantiationLevel,
  TargetEvaluation,
  TargetPosture,
} from "@/execution/api";

/**
 * The shape both projections share: the action-plan summary and the
 * improvement-case roll-up answer the same question with the same fields.
 */
export type MeasurementSummaryLike = {
  measurement_posture: MeasurementPosture;
  target_posture: TargetPosture;
  substantiation: SubstantiationLevel;
  indicator_count?: number;
  overdue_indicator_count?: number;
  evaluations?: TargetEvaluation[];
};

const TONE_CLASS: Record<string, string> = {
  danger: "execution-badge execution-badge--danger",
  warn: "execution-badge execution-badge--warn",
  muted: "execution-badge execution-badge--muted",
  ok: "execution-badge",
};

export function MeasurementPostureBadges({
  summary,
}: {
  summary: MeasurementSummaryLike;
}) {
  return (
    <div data-testid="measurement-postures">
      <span className={TONE_CLASS[measurementPostureTone(summary.measurement_posture)]}>
        {MEASUREMENT_POSTURE_LABELS[summary.measurement_posture]}
      </span>
      <span className={TONE_CLASS[targetPostureTone(summary.target_posture)]}>
        {TARGET_POSTURE_LABELS[summary.target_posture]}
      </span>
      <span className="execution-badge execution-badge--muted">
        {SUBSTANTIATION_LABELS[summary.substantiation]}
      </span>
    </div>
  );
}

/**
 * Read-only reading of what the numbers say. Used inside the card detail and
 * inside the improvement case, so both places tell the same story without a
 * second interpretation of the same fields.
 */
export function MeasurementSummaryPanel({
  summary,
  headline,
  whatToDoNext,
  testId = "measurement-summary",
}: {
  summary: MeasurementSummaryLike;
  headline?: string;
  whatToDoNext?: string;
  testId?: string;
}) {
  const evaluations = summary.evaluations ?? [];
  const overdue = summary.overdue_indicator_count ?? 0;

  return (
    <div className="space-y-3 text-sm" data-testid={testId}>
      {headline ? <p className="font-semibold">{headline}</p> : null}
      <MeasurementPostureBadges summary={summary} />
      <p className="text-[var(--qm-muted)]">
        {summary.indicator_count ?? 0} indicador(es) acompanhado(s)
        {overdue > 0 ? ` · ${overdue} com medição atrasada` : ""}
      </p>
      {whatToDoNext ? <p>{whatToDoNext}</p> : null}
      <p
        className="rounded border border-amber-200 bg-amber-50 px-3 py-2 text-amber-950"
        data-testid={`${testId}-efficacy-warning`}
      >
        {TARGET_NOT_EFFICACY_WARNING}
      </p>

      {evaluations.length === 0 ? (
        <p className="text-[var(--qm-muted)]">
          Nenhum indicador definido ainda — sem indicador não há como dizer se o
          resultado mudou.
        </p>
      ) : (
        <ul className="space-y-2" data-testid={`${testId}-evaluations`}>
          {evaluations.map((ev) => (
            <li
              key={ev.indicator_definition_id}
              className="border-t border-[var(--qm-line)] pt-2"
            >
              <p className="font-medium">{ev.indicator_name}</p>
              <p className="text-[var(--qm-muted)]">
                {TARGET_STATE_LABELS[ev.state]} · Meta{" "}
                {formatTarget(ev, ev.unit_label)} · Última medição{" "}
                {formatMeasurementValue(ev.latest_value, ev.unit_label)}
                {ev.latest_measured_at
                  ? ` em ${formatShortDate(ev.latest_measured_at)}`
                  : ""}
              </p>
              <p>{ev.headline}</p>
              {ev.is_measurement_overdue ? (
                <p className="text-[var(--qm-muted)]">
                  Medição atrasada — a leitura esperada não foi registrada.
                </p>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
