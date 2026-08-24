import { useMemo, useState } from "react";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import { useOrgMembers } from "@/hooks/useAssessmentDetail";
import {
  useActivateMeasurementPlan,
  useCorrectMeasurementRecord,
  useCreateIndicator,
  useCreateMeasurementPlan,
  useCreateMeasurementRecord,
  useIndicators,
  useMeasurementRecords,
  useMeasurementSummary,
  useReviseIndicator,
} from "@/execution/hooks";
import { seriesPositions } from "@/execution/decimalSeries";
import { formatShortDate } from "@/execution/labels";
import {
  BASELINE_STATUS_LABELS,
  formatMeasurementValue,
  formatTarget,
  INDICATOR_DIRECTION_LABELS,
  isRangeDirection,
  prefersReducedMotion,
  TARGET_NOT_EFFICACY_WARNING,
  TARGET_STATE_LABELS,
  UNIT_KIND_LABELS,
} from "@/execution/measurementLabels";
import { MeasurementPostureBadges } from "@/execution/MeasurementSummaryPanel";
import type {
  Indicator,
  IndicatorDirection,
  IndicatorUnitKind,
  MeasurementRecord,
  TargetEvaluation,
} from "@/execution/api";
import type { OrgMemberOption } from "@/api/scopeTeamApi";

/** A code the person never has to invent — derived from the indicator name. */
function deriveCode(name: string, taken: Set<string>): string {
  const base =
    name
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toUpperCase()
      .replace(/[^A-Z0-9]+/g, "-")
      .replace(/^-|-$/g, "")
      .slice(0, 55) || "INDICADOR";
  if (!taken.has(base)) return base;
  for (let n = 2; n < 100; n += 1) {
    const candidate = `${base}-${n}`;
    if (!taken.has(candidate)) return candidate;
  }
  return `${base}-${Date.now()}`;
}

function toIsoOrNull(local: string): string | null {
  if (!local) return null;
  const parsed = new Date(local);
  return Number.isNaN(parsed.getTime()) ? null : parsed.toISOString();
}

function nowLocalInput(): string {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 16);
}

/**
 * A trend only means something with at least two readings of the same
 * indicator version. With one reading we show the number and the table, and
 * say so — a single dot drawn as a line would suggest evolution that has not
 * been observed yet.
 */
function IndicatorHistory({
  indicator,
  records,
}: {
  indicator: Indicator;
  records: MeasurementRecord[];
}) {
  const ordered = useMemo(
    () =>
      [...records].sort(
        (a, b) => Date.parse(a.measured_at) - Date.parse(b.measured_at),
      ),
    [records],
  );
  // Baseline is the starting point, not a post-change reading — trend needs
  // two comparable measurements, otherwise a line would invent evolution.
  const readings = useMemo(
    () => ordered.filter((record) => record.measurement_kind !== "baseline"),
    [ordered],
  );
  // Positions are exact: the value itself is never converted to a number.
  const positions = useMemo(
    () => seriesPositions(readings.map((record) => record.value)),
    [readings],
  );

  if (ordered.length === 0) {
    return (
      <p className="text-xs text-[var(--qm-muted)]">
        Ainda sem medição registrada para este indicador.
      </p>
    );
  }

  const table = (
    <table className="mt-2 w-full text-left text-xs">
      <caption className="sr-only">
        Medições registradas de {indicator.name}
      </caption>
      <thead>
        <tr>
          <th scope="col" className="pr-3 font-semibold">
            Quando
          </th>
          <th scope="col" className="pr-3 font-semibold">
            Valor
          </th>
          <th scope="col" className="pr-3 font-semibold">
            Tipo
          </th>
          <th scope="col" className="font-semibold">
            Observação
          </th>
        </tr>
      </thead>
      <tbody>
        {ordered.map((record) => (
          <tr key={record.id}>
            <td className="pr-3">{formatShortDate(record.measured_at)}</td>
            <td className="pr-3">
              {formatMeasurementValue(record.value, indicator.unit_label)}
            </td>
            <td className="pr-3">
              {record.measurement_kind === "baseline"
                ? "Ponto de partida"
                : "Medição"}
            </td>
            <td>{record.note || "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );

  if (readings.length < 2) {
    return (
      <div data-testid={`measurement-history-${indicator.id}`}>
        {readings.length === 1 ? (
          <p className="text-xs text-[var(--qm-muted)]">
            Uma única medição — registre outra leitura para observar a evolução.
          </p>
        ) : null}
        {table}
      </div>
    );
  }

  // Geometry only: the displayed value stays the untouched string from the API.
  const path = positions
    ?.map((position, index) => {
      const x = (index / (positions.length - 1)) * 100;
      const y = 30 - position * 26;
      return `${index === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <div data-testid={`measurement-history-${indicator.id}`}>
      {path ? (
        <svg
          viewBox="0 0 100 32"
          className="mt-2 h-12 w-full"
          role="img"
          aria-label={`Evolução de ${indicator.name} em ${readings.length} medições, da mais antiga à mais recente`}
          // The line is static: no animation to disable under reduced motion.
          style={prefersReducedMotion() ? { transition: "none" } : undefined}
        >
          <path d={path} fill="none" stroke="currentColor" strokeWidth="1.5" />
        </svg>
      ) : null}
      {table}
    </div>
  );
}

function IndicatorCard({
  indicator,
  evaluation,
  records,
  ownerLabel,
  canMutate,
  planId,
  planActive,
}: {
  indicator: Indicator;
  evaluation: TargetEvaluation | undefined;
  records: MeasurementRecord[];
  ownerLabel: string;
  canMutate: boolean;
  planId: string;
  planActive: boolean;
}) {
  const revise = useReviseIndicator();
  const createRecord = useCreateMeasurementRecord(planId);
  const correct = useCorrectMeasurementRecord();

  const [baselineValue, setBaselineValue] = useState("");
  const [baselineReason, setBaselineReason] = useState("");
  const [value, setValue] = useState("");
  const [measuredAt, setMeasuredAt] = useState(nowLocalInput);
  const [note, setNote] = useState("");
  const [correctionId, setCorrectionId] = useState("");
  const [correctionValue, setCorrectionValue] = useState("");
  const [correctionReason, setCorrectionReason] = useState("");
  const [error, setError] = useState<unknown>(null);

  const needsBaseline = indicator.baseline_status === "missing";

  /**
   * The starting point is the indicator's first reading, so it is recorded as a
   * baseline measurement — not written onto the definition. When it genuinely
   * cannot be measured, the justification is what settles the question.
   */
  async function submitBaseline(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const value = baselineValue.trim();
    const reason = baselineReason.trim();
    if (!value && !reason) return;
    try {
      if (value) {
        await createRecord.mutateAsync({
          indicator_definition_id: indicator.id,
          value,
          measured_at: new Date().toISOString(),
          measurement_kind: "baseline",
          note: reason,
        });
      } else {
        await revise.mutateAsync({
          indicatorId: indicator.id,
          body: {
            revision_reason: "Ponto de partida indisponível",
            baseline_unavailable_reason: reason,
          },
        });
      }
      setBaselineValue("");
      setBaselineReason("");
    } catch (err) {
      setError(err);
    }
  }

  async function submitMeasurement(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const iso = toIsoOrNull(measuredAt);
    if (!value.trim() || !iso) return;
    try {
      await createRecord.mutateAsync({
        indicator_definition_id: indicator.id,
        value: value.trim(),
        measured_at: iso,
        note: note.trim(),
      });
      setValue("");
      setNote("");
    } catch (err) {
      setError(err);
    }
  }

  async function submitCorrection(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!correctionId || !correctionValue.trim() || !correctionReason.trim()) return;
    try {
      await correct.mutateAsync({
        recordId: correctionId,
        body: {
          value: correctionValue.trim(),
          correction_reason: correctionReason.trim(),
        },
      });
      setCorrectionId("");
      setCorrectionValue("");
      setCorrectionReason("");
    } catch (err) {
      setError(err);
    }
  }

  return (
    <li
      className="rounded border border-[var(--qm-line)] p-3 text-sm"
      data-testid={`measurement-indicator-${indicator.id}`}
    >
      <p className="font-semibold">{indicator.name}</p>
      {indicator.question ? (
        <p className="text-[var(--qm-muted)]">{indicator.question}</p>
      ) : null}
      <dl className="mt-2 grid gap-1 sm:grid-cols-2">
        <div>
          <dt className="text-[var(--qm-muted)]">Unidade</dt>
          <dd>{indicator.unit_label || "Sem unidade"}</dd>
        </div>
        <div>
          <dt className="text-[var(--qm-muted)]">Sentido desejado</dt>
          <dd>{INDICATOR_DIRECTION_LABELS[indicator.direction]}</dd>
        </div>
        <div>
          <dt className="text-[var(--qm-muted)]">Ponto de partida</dt>
          <dd data-testid={`measurement-baseline-${indicator.id}`}>
            {indicator.baseline_value != null
              ? formatMeasurementValue(
                  indicator.baseline_value,
                  indicator.unit_label,
                )
              : indicator.baseline_unavailable_reason ||
                BASELINE_STATUS_LABELS[indicator.baseline_status]}
          </dd>
        </div>
        <div>
          <dt className="text-[var(--qm-muted)]">Meta</dt>
          <dd>{formatTarget(indicator, indicator.unit_label)}</dd>
        </div>
        <div>
          <dt className="text-[var(--qm-muted)]">Quem responde por este número</dt>
          <dd data-testid={`measurement-indicator-owner-${indicator.id}`}>
            {ownerLabel}
          </dd>
        </div>
        <div>
          <dt className="text-[var(--qm-muted)]">Última medição</dt>
          <dd>
            {formatMeasurementValue(indicator.latest_value, indicator.unit_label)}
            {indicator.latest_measured_at
              ? ` em ${formatShortDate(indicator.latest_measured_at)}`
              : ""}
          </dd>
        </div>
      </dl>

      {evaluation ? (
        <p className="mt-2" data-testid={`measurement-state-${indicator.id}`}>
          <span className="execution-badge execution-badge--muted">
            {TARGET_STATE_LABELS[evaluation.state]}
          </span>
          {evaluation.is_measurement_overdue ? (
            <span className="execution-badge execution-badge--danger">
              Medição atrasada
            </span>
          ) : null}
        </p>
      ) : null}
      {evaluation ? (
        <p className="mt-1 text-[var(--qm-muted)]">{evaluation.what_to_do_next}</p>
      ) : null}

      <IndicatorHistory indicator={indicator} records={records} />

      {error ? (
        <div className="mt-3">
          <ApiErrorBanner error={error} title="Não foi possível registrar" />
        </div>
      ) : null}

      {canMutate && needsBaseline ? (
        <form
          className="mt-3 space-y-2"
          data-testid={`measurement-baseline-form-${indicator.id}`}
          onSubmit={(e) => void submitBaseline(e)}
        >
          <p className="text-xs text-[var(--qm-muted)]">
            Sem o valor de antes não é possível dizer que algo mudou. Informe o
            valor atual ou, se ele não puder ser medido, explique por quê —
            deixar o campo de valor vazio registra a justificativa.
          </p>
          <label className="block text-sm font-semibold">
            Valor de partida
            <input
              className="qm-field mt-1"
              inputMode="decimal"
              value={baselineValue}
              onChange={(e) => setBaselineValue(e.target.value)}
            />
          </label>
          <label className="block text-sm font-semibold">
            Observação ou motivo da indisponibilidade
            <input
              className="qm-field mt-1"
              value={baselineReason}
              onChange={(e) => setBaselineReason(e.target.value)}
            />
          </label>
          <button
            type="submit"
            className="qm-btn-secondary"
            disabled={revise.isPending || createRecord.isPending}
          >
            Registrar ponto de partida
          </button>
        </form>
      ) : null}

      {canMutate && !planActive ? (
        <p className="mt-3 text-xs text-[var(--qm-muted)]">
          As medições começam depois que o acompanhamento for iniciado.
        </p>
      ) : null}

      {canMutate && planActive ? (
        <form
          className="mt-3 space-y-2"
          data-testid={`measurement-record-form-${indicator.id}`}
          onSubmit={(e) => void submitMeasurement(e)}
        >
          <label className="block text-sm font-semibold">
            Valor medido
            <input
              className="qm-field mt-1"
              inputMode="decimal"
              required
              value={value}
              onChange={(e) => setValue(e.target.value)}
            />
          </label>
          <label className="block text-sm font-semibold">
            Quando foi medido
            <input
              className="qm-field mt-1"
              type="datetime-local"
              required
              value={measuredAt}
              onChange={(e) => setMeasuredAt(e.target.value)}
            />
          </label>
          <label className="block text-sm font-semibold">
            Observação sobre a medição
            <input
              className="qm-field mt-1"
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </label>
          <button
            type="submit"
            className="qm-btn-primary"
            disabled={createRecord.isPending}
          >
            Registrar medição
          </button>
        </form>
      ) : null}

      {canMutate && planActive && records.length > 0 ? (
        <form
          className="mt-3 space-y-2"
          data-testid={`measurement-correction-form-${indicator.id}`}
          onSubmit={(e) => void submitCorrection(e)}
        >
          <p className="text-xs text-[var(--qm-muted)]">
            Corrigir uma medição não apaga a anterior: o valor antigo continua no
            histórico com o motivo da correção.
          </p>
          <label className="block text-sm font-semibold">
            Medição a corrigir
            <select
              className="qm-field mt-1"
              value={correctionId}
              onChange={(e) => setCorrectionId(e.target.value)}
            >
              <option value="">Selecione a medição…</option>
              {records.map((record) => (
                <option key={record.id} value={record.id}>
                  {formatShortDate(record.measured_at)} ·{" "}
                  {formatMeasurementValue(record.value, indicator.unit_label)}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm font-semibold">
            Valor correto
            <input
              className="qm-field mt-1"
              inputMode="decimal"
              value={correctionValue}
              onChange={(e) => setCorrectionValue(e.target.value)}
            />
          </label>
          <label className="block text-sm font-semibold">
            Motivo da correção
            <input
              className="qm-field mt-1"
              value={correctionReason}
              onChange={(e) => setCorrectionReason(e.target.value)}
            />
          </label>
          <button
            type="submit"
            className="qm-btn-secondary"
            disabled={correct.isPending || !correctionId}
          >
            Corrigir medição
          </button>
        </form>
      ) : null}
    </li>
  );
}

function NewIndicatorForm({
  planId,
  existingCodes,
  members,
}: {
  planId: string;
  existingCodes: Set<string>;
  members: OrgMemberOption[];
}) {
  const createIndicator = useCreateIndicator(planId);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [question, setQuestion] = useState("");
  const [unitKind, setUnitKind] = useState<IndicatorUnitKind>("count");
  const [customUnitLabel, setCustomUnitLabel] = useState("");
  const [currencyCode, setCurrencyCode] = useState("BRL");
  const [owner, setOwner] = useState("");
  const [direction, setDirection] = useState<IndicatorDirection>("lower_is_better");
  const [targetValue, setTargetValue] = useState("");
  const [targetMin, setTargetMin] = useState("");
  const [targetMax, setTargetMax] = useState("");
  const [targetDue, setTargetDue] = useState("");
  const [frequency, setFrequency] = useState("");
  const [error, setError] = useState<unknown>(null);

  const isRange = isRangeDirection(direction);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!name.trim()) return;
    try {
      await createIndicator.mutateAsync({
        code: deriveCode(name, existingCodes),
        name: name.trim(),
        question: question.trim(),
        unit_kind: unitKind,
        custom_unit_label: unitKind === "custom" ? customUnitLabel.trim() : null,
        currency_code: unitKind === "currency" ? currencyCode.trim() : null,
        owner_membership_id: owner || null,
        direction,
        target_value: isRange ? null : targetValue.trim() || null,
        target_min: isRange ? targetMin.trim() || null : null,
        target_max: isRange ? targetMax.trim() || null : null,
        target_due_at: toIsoOrNull(targetDue),
        measurement_frequency_days: frequency.trim()
          ? Number.parseInt(frequency, 10)
          : null,
      });
      setOpen(false);
      setName("");
      setQuestion("");
      setCustomUnitLabel("");
      setOwner("");
      setTargetValue("");
      setTargetMin("");
      setTargetMax("");
      setTargetDue("");
      setFrequency("");
    } catch (err) {
      setError(err);
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        className="qm-btn-secondary mt-3"
        data-testid="measurement-add-indicator"
        onClick={() => setOpen(true)}
      >
        Adicionar indicador
      </button>
    );
  }

  return (
    <form
      className="mt-3 space-y-2"
      data-testid="measurement-indicator-form"
      onSubmit={(e) => void submit(e)}
    >
      <p className="text-xs text-[var(--qm-muted)]">
        Um indicador é o número que diz se o problema diminuiu. Exemplo:
        “Retrabalho na linha 2”, em peças por semana, quanto menor melhor.
      </p>
      <label className="block text-sm font-semibold">
        O que será medido?
        <input
          className="qm-field mt-1"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </label>
      <label className="block text-sm font-semibold">
        Que pergunta este número responde?
        <input
          className="qm-field mt-1"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
      </label>
      <label className="block text-sm font-semibold">
        Unidade
        <select
          className="qm-field mt-1"
          value={unitKind}
          onChange={(e) => setUnitKind(e.target.value as IndicatorUnitKind)}
        >
          {(Object.keys(UNIT_KIND_LABELS) as IndicatorUnitKind[]).map((kind) => (
            <option key={kind} value={kind}>
              {UNIT_KIND_LABELS[kind]}
            </option>
          ))}
        </select>
      </label>
      {unitKind === "custom" ? (
        <label className="block text-sm font-semibold">
          Como esta unidade se chama
          <input
            className="qm-field mt-1"
            placeholder="peças/semana, chamados/dia…"
            required
            value={customUnitLabel}
            onChange={(e) => setCustomUnitLabel(e.target.value)}
          />
        </label>
      ) : null}
      {unitKind === "currency" ? (
        <label className="block text-sm font-semibold">
          Moeda
          <input
            className="qm-field mt-1"
            placeholder="BRL"
            required
            value={currencyCode}
            onChange={(e) => setCurrencyCode(e.target.value.toUpperCase())}
          />
        </label>
      ) : null}
      <label className="block text-sm font-semibold">
        Quem responde por este número
        <select
          className="qm-field mt-1"
          data-testid="measurement-indicator-owner-select"
          value={owner}
          onChange={(e) => setOwner(e.target.value)}
        >
          <option value="">Quem está criando o indicador</option>
          {members.map((member) => (
            <option key={member.membership_id} value={member.membership_id}>
              {member.display_name || member.email}
            </option>
          ))}
        </select>
      </label>
      <label className="block text-sm font-semibold">
        Sentido desejado
        <select
          className="qm-field mt-1"
          value={direction}
          onChange={(e) => setDirection(e.target.value as IndicatorDirection)}
        >
          {(Object.keys(INDICATOR_DIRECTION_LABELS) as IndicatorDirection[]).map(
            (key) => (
              <option key={key} value={key}>
                {INDICATOR_DIRECTION_LABELS[key]}
              </option>
            ),
          )}
        </select>
      </label>
      {isRange ? (
        <>
          <label className="block text-sm font-semibold">
            Valor mínimo aceitável
            <input
              className="qm-field mt-1"
              inputMode="decimal"
              value={targetMin}
              onChange={(e) => setTargetMin(e.target.value)}
            />
          </label>
          <label className="block text-sm font-semibold">
            Valor máximo aceitável
            <input
              className="qm-field mt-1"
              inputMode="decimal"
              value={targetMax}
              onChange={(e) => setTargetMax(e.target.value)}
            />
          </label>
        </>
      ) : (
        <label className="block text-sm font-semibold">
          Meta
          <input
            className="qm-field mt-1"
            inputMode="decimal"
            value={targetValue}
            onChange={(e) => setTargetValue(e.target.value)}
          />
        </label>
      )}
      <label className="block text-sm font-semibold">
        Até quando a meta deve ser alcançada
        <input
          className="qm-field mt-1"
          type="datetime-local"
          value={targetDue}
          onChange={(e) => setTargetDue(e.target.value)}
        />
      </label>
      <label className="block text-sm font-semibold">
        A cada quantos dias medir
        <input
          className="qm-field mt-1"
          inputMode="numeric"
          value={frequency}
          onChange={(e) => setFrequency(e.target.value)}
        />
      </label>
      {error ? (
        <ApiErrorBanner error={error} title="Não foi possível criar o indicador" />
      ) : null}
      <div className="flex flex-wrap gap-2">
        <button
          type="submit"
          className="qm-btn-primary"
          disabled={createIndicator.isPending}
        >
          Salvar indicador
        </button>
        <button
          type="button"
          className="qm-btn-secondary"
          onClick={() => setOpen(false)}
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}

export function MeasurementSection({
  actionPlanId,
  canMutate,
}: {
  actionPlanId: string | undefined;
  canMutate: boolean;
}) {
  const summaryQuery = useMeasurementSummary(actionPlanId);
  const summary = summaryQuery.data;
  const plan = summary?.plan ?? null;

  const indicatorsQuery = useIndicators(plan?.id);
  const recordsQuery = useMeasurementRecords(plan?.id);
  const members = useOrgMembers();

  const createPlan = useCreateMeasurementPlan();
  const activatePlan = useActivateMeasurementPlan();

  const [objective, setObjective] = useState("");
  const [planOwner, setPlanOwner] = useState("");
  const [error, setError] = useState<unknown>(null);

  const indicators = indicatorsQuery.data ?? [];
  const records = recordsQuery.data ?? [];

  const evaluationsById = useMemo(() => {
    const map = new Map<string, TargetEvaluation>();
    for (const ev of summary?.evaluations ?? []) {
      map.set(ev.indicator_definition_id, ev);
    }
    return map;
  }, [summary]);

  const recordsByIndicator = useMemo(() => {
    const map = new Map<string, MeasurementRecord[]>();
    for (const record of records) {
      const list = map.get(record.indicator_definition_id) ?? [];
      list.push(record);
      map.set(record.indicator_definition_id, list);
    }
    return map;
  }, [records]);

  const memberOptions = useMemo(
    () => (members.data ?? []).filter((m) => m.status === "active"),
    [members.data],
  );

  const memberLabel = useMemo(() => {
    const byId = new Map(
      (members.data ?? []).map((m) => [
        m.membership_id,
        m.display_name || m.email,
      ]),
    );
    return (membershipId: string | null | undefined) =>
      (membershipId ? byId.get(membershipId) : null) || "Ainda sem responsável";
  }, [members.data]);

  /**
   * The API already resolves the owner's name, so the member list is only a
   * fallback for when it is missing.
   */
  const ownerLabelOf = useMemo(
    () =>
      (owner: {
        owner_display_name?: string | null;
        owner_email?: string | null;
        owner_membership_id?: string | null;
      }) =>
        owner.owner_display_name ||
        owner.owner_email ||
        memberLabel(owner.owner_membership_id),
    [memberLabel],
  );

  const existingCodes = useMemo(
    () => new Set(indicators.map((i) => i.code)),
    [indicators],
  );

  async function submitPlan(e: React.FormEvent) {
    e.preventDefault();
    if (!actionPlanId) return;
    setError(null);
    try {
      await createPlan.mutateAsync({
        action_plan_id: actionPlanId,
        objective: objective.trim(),
        owner_membership_id: planOwner || null,
      });
      setObjective("");
      setPlanOwner("");
    } catch (err) {
      setError(err);
    }
  }

  async function runActivate() {
    if (!plan) return;
    setError(null);
    try {
      await activatePlan.mutateAsync(plan.id);
    } catch (err) {
      setError(err);
    }
  }

  return (
    <section className="qm-panel px-6 py-5" data-testid="execution-measurement-section">
      <h3 className="font-semibold text-[var(--qm-ink)]">Medição do resultado</h3>
      <p className="mt-1 text-sm text-[var(--qm-muted)]">
        Concluir a ação não prova que o problema diminuiu. Aqui se registra o
        número de antes, a meta e as medições depois da mudança.
      </p>
      <p
        className="mt-3 rounded border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950"
        data-testid="measurement-efficacy-warning"
      >
        {TARGET_NOT_EFFICACY_WARNING}
      </p>

      {error ? (
        <div className="mt-3">
          <ApiErrorBanner error={error} title="Não foi possível concluir" />
        </div>
      ) : null}

      {summary ? (
        <div className="mt-4 space-y-2 text-sm">
          <MeasurementPostureBadges summary={summary} />
          <p className="font-semibold">{summary.headline}</p>
          <p className="text-[var(--qm-muted)]">{summary.what_to_do_next}</p>
        </div>
      ) : null}

      {!plan ? (
        <div className="mt-4">
          {canMutate ? (
            <form
              className="space-y-2"
              data-testid="measurement-plan-form"
              onSubmit={(e) => void submitPlan(e)}
            >
              <label className="block text-sm font-semibold">
                O que esta ação precisa provar?
                <input
                  className="qm-field mt-1"
                  placeholder="Ex.: reduzir o retrabalho na linha 2"
                  value={objective}
                  onChange={(e) => setObjective(e.target.value)}
                />
              </label>
              <label className="block text-sm font-semibold">
                Quem responde pelo acompanhamento
                <select
                  className="qm-field mt-1"
                  data-testid="measurement-plan-owner-select"
                  value={planOwner}
                  onChange={(e) => setPlanOwner(e.target.value)}
                >
                  <option value="">Quem está criando o plano</option>
                  {memberOptions.map((member) => (
                    <option key={member.membership_id} value={member.membership_id}>
                      {member.display_name || member.email}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="submit"
                className="qm-btn-primary"
                disabled={createPlan.isPending}
              >
                Criar plano de medição
              </button>
            </form>
          ) : (
            <p className="text-sm text-[var(--qm-muted)]">
              Nenhum plano de medição foi criado para esta ação. Seu perfil é
              somente leitura.
            </p>
          )}
        </div>
      ) : (
        <div className="mt-4 space-y-3">
          {plan.objective ? <p className="text-sm">{plan.objective}</p> : null}
          <p className="text-sm text-[var(--qm-muted)]" data-testid="measurement-plan-owner">
            Responsável pelo acompanhamento: {ownerLabelOf(plan)}
          </p>
          {plan.status === "draft" ? (
            <p className="text-sm text-[var(--qm-muted)]">
              O acompanhamento ainda não começou. Ative depois de definir pelo
              menos um indicador com ponto de partida.
            </p>
          ) : null}
          {canMutate && plan.status === "draft" ? (
            <button
              type="button"
              className="qm-btn-secondary"
              data-testid="measurement-activate-plan"
              disabled={activatePlan.isPending}
              onClick={() => void runActivate()}
            >
              Iniciar acompanhamento
            </button>
          ) : null}

          <ul className="space-y-3" data-testid="measurement-indicator-list">
            {indicators.length === 0 ? (
              <li className="text-sm text-[var(--qm-muted)]">
                Nenhum indicador ainda. Comece pelo número que representa o
                problema — por exemplo, quantas ocorrências acontecem por mês.
              </li>
            ) : (
              indicators.map((indicator) => (
                <IndicatorCard
                  key={indicator.id}
                  indicator={indicator}
                  evaluation={evaluationsById.get(indicator.id)}
                  records={recordsByIndicator.get(indicator.id) ?? []}
                  ownerLabel={ownerLabelOf(indicator)}
                  canMutate={canMutate}
                  planId={plan.id}
                  planActive={plan.status === "active"}
                />
              ))
            )}
          </ul>

          {canMutate ? (
            <NewIndicatorForm
              planId={plan.id}
              existingCodes={existingCodes}
              members={memberOptions}
            />
          ) : null}
        </div>
      )}
    </section>
  );
}
