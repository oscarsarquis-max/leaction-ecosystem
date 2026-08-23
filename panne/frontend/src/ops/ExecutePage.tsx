import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError } from "../api/errors";
import type { Catalog, ExecutionBatch, ExecutionView } from "../api/types";
import { ErrorState, LoadingState, StatusBadge } from "../components/Feedback";
import {
  CONSUMPTION_LABEL,
  OCCURRENCE_LABEL,
  SEVERITY_LABEL,
  WEIGH_STATE_LABEL,
  YIELD_LABEL,
  actionLabel,
  catalogLabel,
  formatDateTime,
  formatDecimal,
  statusLabel,
} from "../format";
import { useOrganization } from "../session/OrganizationContext";
import { parseQuantityInput } from "./parseQuantity";
import { useCommand } from "./useCommand";

const POLL_MS = 20000;

function tone(status: string): "sucesso" | "atencao" | "erro" | "info" | "neutro" {
  if (status === "completed") return "sucesso";
  if (status === "short_closed" || status === "cancelled") return "erro";
  if (status === "on_hold" || status === "rejected") return "atencao";
  if (status === "in_progress" || status === "in_weighing") return "info";
  return "neutro";
}

function elapsed(startedAt: string | null, endedAt: string | null, now: number): string {
  if (!startedAt) return "—";
  const start = new Date(startedAt).getTime();
  const end = endedAt ? new Date(endedAt).getTime() : now;
  if (Number.isNaN(start) || Number.isNaN(end)) return "—";
  const seconds = Math.max(0, Math.floor((end - start) / 1000));
  const minutes = Math.floor(seconds / 60);
  return `${String(minutes).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

export function ExecutePage() {
  const { orderId = "" } = useParams();
  const { api, me, active } = useOrganization();
  const command = useCommand();
  const [view, setView] = useState<ExecutionView | null>(null);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [batchId, setBatchId] = useState<string>("");
  const [dirty, setDirty] = useState(false);
  const [now, setNow] = useState(Date.now());
  const [confirm, setConfirm] = useState<{ title: string; run: () => Promise<void> } | null>(null);
  const dirtyRef = useRef(false);
  dirtyRef.current = dirty;

  async function reload() {
    const [execution, catalogResponse] = await Promise.all([api.getExecution(orderId), api.getCatalog()]);
    setView(execution.data);
    setCatalog(catalogResponse.data);
    setBatchId((current) => current || execution.data.batches[0]?.id || "");
  }

  useEffect(() => {
    let ativo = true;
    setView(null);
    setCatalog(null);
    setBatchId("");
    setDirty(false);
    setConfirm(null);
    setError(null);
    reload()
      .catch((err) => {
        if (ativo) setError(err);
      });
    return () => {
      ativo = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, orderId, active?.organization_id]);

  useEffect(() => {
    const tick = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(tick);
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => {
      if (document.hidden || dirtyRef.current || command.pending) return;
      void reload().catch(() => undefined);
    }, POLL_MS);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, orderId, command.pending]);

  const batch = useMemo(
    () => view?.batches.find((item) => item.id === batchId) ?? view?.batches[0] ?? null,
    [view, batchId],
  );

  async function send(fingerprint: string, path: string, body?: unknown, ifMatch?: number | null) {
    try {
      await command.run(fingerprint, (key) =>
        api.command(path, { body, idempotencyKey: key, ifMatch }),
      );
      setDirty(false);
      await reload();
    } catch {
      /* o erro fica no painel persistente */
    }
  }

  if (error) return <ErrorState error={error} onRetry={() => void reload().catch(setError)} />;
  if (!view || !catalog || !batch) return <LoadingState>Carregando execução…</LoadingState>;

  const policy = view.policy ?? {};
  const secondPerson = policy.verification_policy === "second_person";
  const openSession = batch.sessions.find((item) => item.status === "open") ?? null;
  const can = view.readiness.permissions;
  const conflict = command.error instanceof ApiError && command.error.code === "conflito";

  return (
    <article className="ops" key={active?.organization_id ?? "org"}>
      <header className="ops-bar">
        <p>
          <Link to="/producao">← Quadro</Link>
          {" · "}
          <Link to={`/ordens/${orderId}`}>Detalhe</Link>
        </p>
        <h1>
          Executar {view.order.public_code}
        </h1>
        <p>
          <StatusBadge tone={tone(view.order.status)} label={statusLabel(view.order.status)} />{" "}
          {view.product?.display_name ?? "Produto"} · {view.establishment?.display_name ?? "Estabelecimento"} ·{" "}
          {me?.display_name}
        </p>
        <p className="meta">
          Batelada{" "}
          <label>
            <span className="visually-hidden">Batelada</span>
            <select value={batch.id} onChange={(event) => setBatchId(event.target.value)}>
              {view.batches.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.operational_code} · {statusLabel(item.status)}
                </option>
              ))}
            </select>
          </label>
          {" · "}
          próxima ação: {actionLabel(view.next_action)}
          {view.blocked ? " · ordem bloqueada" : ""}
          {" · atualizado "}
          {formatDateTime(view.updated_at)}
        </p>
      </header>
      {command.error ? (
        <div className="feedback" role="alert">
          <p>{command.error.message}</p>
          {conflict ? (
            <button type="button" className="primary" onClick={() => void reload()}>
              Recarregar
            </button>
          ) : null}
        </div>
      ) : null}

      <section className="section">
        <h2>1. Batelada</h2>
        <p>
          Alvo {formatDecimal(batch.target_quantity)} · estado {statusLabel(batch.status)} ·
          planejado {formatDateTime(batch.planned_start_at)}
        </p>
        {view.dependencies.map((item) => (
          <p key={item.id}>Depende de {item.predecessor_order_id}</p>
        ))}
      </section>

      <WeighingSection
        batch={batch}
        catalog={catalog}
        view={view}
        secondPerson={secondPerson}
        openSession={openSession}
        pending={command.pending}
        canRecord={Boolean(can.weighing_record)}
        canVerify={Boolean(can.weighing_verify)}
        markDirty={() => setDirty(true)}
        onConfirm={setConfirm}
        onSend={send}
      />

      <StepsSection
        batch={batch}
        now={now}
        pending={command.pending}
        canStep={Boolean(can.step)}
        markDirty={() => setDirty(true)}
        onSend={send}
      />

      <ConsumptionSection
        batch={batch}
        catalog={catalog}
        pending={command.pending}
        canConsume={Boolean(can.consumption)}
        markDirty={() => setDirty(true)}
        onSend={send}
      />

      <OccurrenceSection
        view={view}
        batch={batch}
        catalog={catalog}
        pending={command.pending}
        canRecord={Boolean(can.occurrence_record)}
        canResolve={Boolean(can.occurrence_resolve)}
        markDirty={() => setDirty(true)}
        onSend={send}
      />

      <YieldSection
        batch={batch}
        catalog={catalog}
        pending={command.pending}
        canYield={Boolean(can.step)}
        markDirty={() => setDirty(true)}
        onSend={send}
      />

      <CloseSection
        view={view}
        orderId={orderId}
        pending={command.pending}
        onConfirm={setConfirm}
        onSend={send}
      />

      <SheetSection
        view={view}
        orderId={orderId}
        pending={command.pending}
        canIssue={Boolean(can.sheet)}
        onSend={send}
      />

      {confirm ? (
        <div className="confirm" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
          <h2 id="confirm-title">{confirm.title}</h2>
          <button
            type="button"
            className="primary"
            disabled={command.pending}
            onClick={() => {
              void confirm.run().finally(() => setConfirm(null));
            }}
          >
            Confirmar
          </button>
          <button type="button" className="ghost" onClick={() => setConfirm(null)}>
            Voltar
          </button>
        </div>
      ) : null}
    </article>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="ops-field">
      {label}
      {children}
    </label>
  );
}

function WeighingSection({
  batch,
  catalog,
  view,
  secondPerson,
  openSession,
  pending,
  canRecord,
  canVerify,
  markDirty,
  onConfirm,
  onSend,
}: {
  batch: ExecutionBatch;
  catalog: Catalog;
  view: ExecutionView;
  secondPerson: boolean;
  openSession: { id: string; row_version: number } | null;
  pending: boolean;
  canRecord: boolean;
  canVerify: boolean;
  markDirty: () => void;
  onConfirm: (value: { title: string; run: () => Promise<void> } | null) => void;
  onSend: (fingerprint: string, path: string, body?: unknown, ifMatch?: number | null) => Promise<void>;
}) {
  const [materialId, setMaterialId] = useState(batch.materials[0]?.id ?? "");
  const [quantity, setQuantity] = useState("");
  const [unitId, setUnitId] = useState(catalog.mass_units[0]?.id ?? "");
  const [lot, setLot] = useState("");
  const [justification, setJustification] = useState("");
  const material = batch.materials.find((item) => item.id === materialId) ?? batch.materials[0];
  const requireLot = Boolean(view.policy && view.policy.require_manual_lot);
  const parsed = parseQuantityInput(quantity);

  return (
    <section className="section actual">
      <h2>2. Materiais e pesagem</h2>
      <ul>
        {batch.materials.map((item) => (
          <li key={item.id}>
            {item.name}: planejado {formatDecimal(item.planned_gross)} {item.unit} · pesado{" "}
            {formatDecimal(item.weighed_canonical)} g · {catalogLabel(WEIGH_STATE_LABEL, item.weigh_state)}
          </li>
        ))}
      </ul>
      {canRecord && !openSession ? (
        <button
          type="button"
          className="primary"
          disabled={pending}
          onClick={() =>
            void onSend(`open-weigh:${batch.id}`, `/batches/${batch.id}/weighing-sessions`, undefined, batch.row_version)
          }
        >
          Abrir pesagem
        </button>
      ) : null}
      {openSession && canRecord ? (
        <form
          className="ops-form"
          onSubmit={(event) => {
            event.preventDefault();
            if (!parsed || !material) return;
            void onSend(
              `weigh:${openSession.id}:${material.id}:${parsed}:${unitId}:${lot}:${justification}`,
              `/weighing-sessions/${openSession.id}/entries`,
              {
                batch_material_id: material.id,
                quantity: parsed,
                measurement_unit_id: unitId,
                lot_code: lot || null,
                justification: justification || null,
              },
            );
          }}
        >
          <Field label="Material">
            <select value={material?.id ?? ""} onChange={(event) => { setMaterialId(event.target.value); markDirty(); }}>
              {batch.materials.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Quantidade pesada">
            <input
              inputMode="decimal"
              value={quantity}
              onChange={(event) => {
                setQuantity(event.target.value);
                markDirty();
              }}
            />
          </Field>
          <Field label="Unidade">
            <select value={unitId} onChange={(event) => { setUnitId(event.target.value); markDirty(); }}>
              {catalog.mass_units.map((unit) => (
                <option key={unit.id} value={unit.id}>
                  {unit.symbol}
                </option>
              ))}
            </select>
          </Field>
          {requireLot ? (
            <Field label="Lote">
              <input value={lot} onChange={(event) => { setLot(event.target.value); markDirty(); }} required />
            </Field>
          ) : null}
          <Field label="Justificativa">
            <input value={justification} onChange={(event) => { setJustification(event.target.value); markDirty(); }} />
          </Field>
          <button type="submit" className="primary" disabled={pending || !parsed}>
            Registrar pesagem
          </button>
        </form>
      ) : null}
      {batch.weighings.map((entry) => {
        const sameOperator = entry.operator_user_id === view.viewer.user_id;
        const awaiting = secondPerson && !entry.verification;
        return (
          <div key={entry.id} className="ops-entry">
            <p>
              informado {formatDecimal(entry.entered_quantity)} {entry.entered_unit} → canônico{" "}
              {formatDecimal(entry.canonical_quantity)} {entry.canonical_unit} · diferença{" "}
              {formatDecimal(entry.absolute_difference)} ({formatDecimal(entry.percent_difference)}%)
              {entry.within_tolerance ? " · dentro da tolerância" : " · fora da tolerância"}
            </p>
            {awaiting ? <p>Aguardando conferência por outro usuário.</p> : null}
            {canVerify && awaiting && sameOperator ? (
              <p>Saia e entre com outro usuário para conferir. A identidade não é trocada aqui.</p>
            ) : null}
            {canVerify && awaiting && !sameOperator ? (
              <div className="ops-actions">
                <button
                  type="button"
                  className="primary"
                  disabled={pending}
                  onClick={() =>
                    void onSend(`verify:${entry.id}:accepted`, `/weighing-entries/${entry.id}/verify`, {
                      decision: "accepted",
                    })
                  }
                >
                  Aceitar
                </button>
                <button
                  type="button"
                  className="ghost"
                  disabled={pending}
                  onClick={() =>
                    void onSend(`verify:${entry.id}:rejected:${justification}`, `/weighing-entries/${entry.id}/verify`, {
                      decision: "rejected",
                      justification: justification || "rejeitada na conferência",
                    })
                  }
                >
                  Rejeitar
                </button>
              </div>
            ) : null}
            {canRecord ? (
              <div className="ops-actions">
                <button
                  type="button"
                  className="ghost"
                  disabled={pending}
                  onClick={() =>
                    onConfirm({
                      title: "Reverter esta pesagem?",
                      run: () => onSend(`reverse:${entry.id}`, `/weighing-entries/${entry.id}/reverse`),
                    })
                  }
                >
                  Reverter
                </button>
                <button
                  type="button"
                  className="ghost"
                  disabled={pending || !parsed}
                  onClick={() =>
                    onConfirm({
                      title: "Corrigir com novo lançamento?",
                      run: () =>
                        onSend(`correct:${entry.id}:${parsed}:${unitId}`, `/weighing-entries/${entry.id}/correct`, {
                          quantity: parsed,
                          measurement_unit_id: unitId,
                          justification: justification || null,
                        }),
                    })
                  }
                >
                  Corrigir
                </button>
              </div>
            ) : null}
          </div>
        );
      })}
      {openSession && canRecord ? (
        <div className="ops-actions">
          <button
            type="button"
            className="primary"
            disabled={pending}
            onClick={() =>
              void onSend(
                `complete-session:${openSession.id}`,
                `/weighing-sessions/${openSession.id}/complete`,
                undefined,
                openSession.row_version,
              )
            }
          >
            Concluir sessão
          </button>
          <button
            type="button"
            className="ghost"
            disabled={pending}
            onClick={() =>
              onConfirm({
                title: "Cancelar a sessão de pesagem?",
                run: () =>
                  onSend(
                    `cancel-session:${openSession.id}`,
                    `/weighing-sessions/${openSession.id}/cancel`,
                    { reason: justification || "sessão cancelada" },
                    openSession.row_version,
                  ),
              })
            }
          >
            Cancelar sessão
          </button>
        </div>
      ) : null}
    </section>
  );
}

function StepsSection({
  batch,
  now,
  pending,
  canStep,
  markDirty,
  onSend,
}: {
  batch: ExecutionBatch;
  now: number;
  pending: boolean;
  canStep: boolean;
  markDirty: () => void;
  onSend: (fingerprint: string, path: string, body?: unknown, ifMatch?: number | null) => Promise<void>;
}) {
  const [reason, setReason] = useState("");
  return (
    <section className="section">
      <h2>3. Etapas</h2>
      <ol>
        {batch.steps.map((step) => {
          const base = `/batches/${step.batch_id}/steps/${step.order_step_id}`;
          return (
            <li key={`${step.batch_id}-${step.order_step_id}`}>
              <strong>{step.title}</strong> · {statusLabel(step.status)}
              <p>{step.instructions}</p>
              <p className="meta">
                Planejado {step.duration_seconds ?? "—"} s · {formatDecimal(step.temperature_value)}{" "}
                {step.temperature_unit ?? ""}
              </p>
              <p className="meta">
                Operador {step.operator_name ?? "—"} · cronômetro {elapsed(step.started_at, step.ended_at, now)}
              </p>
              {canStep ? (
                <div className="ops-actions">
                  {["pending"].includes(step.status) ? (
                    <button type="button" disabled={pending} onClick={() => void onSend(`ready:${step.order_step_id}`, `${base}/ready`, undefined, step.row_version)}>
                      Preparar
                    </button>
                  ) : null}
                  {["pending", "ready"].includes(step.status) ? (
                    <button type="button" className="primary" disabled={pending} onClick={() => void onSend(`start:${step.order_step_id}`, `${base}/start`, undefined, step.row_version)}>
                      Iniciar
                    </button>
                  ) : null}
                  {step.status === "in_progress" ? (
                    <>
                      <button type="button" disabled={pending} onClick={() => void onSend(`hold:${step.order_step_id}:${reason}`, `${base}/hold`, { reason: reason || "pausa operacional" }, step.row_version)}>
                        Pausar
                      </button>
                      <button type="button" className="primary" disabled={pending} onClick={() => void onSend(`complete:${step.order_step_id}`, `${base}/complete`, undefined, step.row_version)}>
                        Concluir
                      </button>
                    </>
                  ) : null}
                  {step.status === "on_hold" ? (
                    <button type="button" className="primary" disabled={pending} onClick={() => void onSend(`resume:${step.order_step_id}`, `${base}/resume`, undefined, step.row_version)}>
                      Retomar
                    </button>
                  ) : null}
                  {["pending", "ready", "on_hold"].includes(step.status) ? (
                    <>
                      <button type="button" disabled={pending} onClick={() => void onSend(`skip:${step.order_step_id}:${reason}`, `${base}/skip`, { reason: reason || "etapa pulada" }, step.row_version)}>
                        Pular
                      </button>
                      <button type="button" disabled={pending} onClick={() => void onSend(`cancel-step:${step.order_step_id}:${reason}`, `${base}/cancel`, { reason: reason || "etapa cancelada" }, step.row_version)}>
                        Cancelar etapa
                      </button>
                    </>
                  ) : null}
                </div>
              ) : null}
            </li>
          );
        })}
      </ol>
      {canStep ? (
        <Field label="Motivo da pausa, pulo ou cancelamento">
          <input value={reason} onChange={(event) => { setReason(event.target.value); markDirty(); }} />
        </Field>
      ) : null}
    </section>
  );
}

function ConsumptionSection({
  batch,
  catalog,
  pending,
  canConsume,
  markDirty,
  onSend,
}: {
  batch: ExecutionBatch;
  catalog: Catalog;
  pending: boolean;
  canConsume: boolean;
  markDirty: () => void;
  onSend: (fingerprint: string, path: string, body?: unknown) => Promise<void>;
}) {
  const [materialId, setMaterialId] = useState(batch.materials[0]?.id ?? "");
  const [type, setType] = useState(catalog.consumption_types[0] ?? "consume");
  const [quantity, setQuantity] = useState("");
  const [unitId, setUnitId] = useState(catalog.mass_units[0]?.id ?? "");
  const [reason, setReason] = useState("");
  const parsed = parseQuantityInput(quantity);
  const needsReason = type !== "consume";
  return (
    <section className="section">
      <h2>4. Apontamentos e ocorrências</h2>
      <h3>Consumo</h3>
      <ul>
        {batch.materials.map((item) => (
          <li key={item.id}>
            {item.name}: planejado {formatDecimal(item.planned_gross)} · pesado{" "}
            {formatDecimal(item.weighed_canonical)} · consumido {formatDecimal(item.consumption.consume)} ·
            retornado {formatDecimal(item.consumption.return)} · desperdício {formatDecimal(item.consumption.waste)}
          </li>
        ))}
      </ul>
      {canConsume ? (
        <form
          className="ops-form"
          onSubmit={(event) => {
            event.preventDefault();
            if (!parsed) return;
            void onSend(`cons:${batch.id}:${materialId}:${type}:${parsed}`, `/batches/${batch.id}/consumptions`, {
              batch_material_id: materialId,
              consumption_type: type,
              quantity: parsed,
              measurement_unit_id: unitId,
              reason: needsReason ? reason || "ajuste operacional" : reason || null,
            });
          }}
        >
          <Field label="Material">
            <select value={materialId} onChange={(event) => { setMaterialId(event.target.value); markDirty(); }}>
              {batch.materials.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Tipo">
            <select value={type} onChange={(event) => { setType(event.target.value); markDirty(); }}>
              {catalog.consumption_types.map((item) => (
                <option key={item} value={item}>
                  {catalogLabel(CONSUMPTION_LABEL, item)}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Quantidade consumida">
            <input inputMode="decimal" value={quantity} onChange={(event) => { setQuantity(event.target.value); markDirty(); }} />
          </Field>
          <Field label="Unidade">
            <select value={unitId} onChange={(event) => setUnitId(event.target.value)}>
              {catalog.mass_units.map((unit) => (
                <option key={unit.id} value={unit.id}>
                  {unit.symbol}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Motivo">
            <input value={reason} required={needsReason} onChange={(event) => { setReason(event.target.value); markDirty(); }} />
          </Field>
          <button type="submit" className="primary" disabled={pending || !parsed}>
            Registrar consumo
          </button>
        </form>
      ) : null}
    </section>
  );
}

function OccurrenceSection({
  view,
  batch,
  catalog,
  pending,
  canRecord,
  canResolve,
  markDirty,
  onSend,
}: {
  view: ExecutionView;
  batch: ExecutionBatch;
  catalog: Catalog;
  pending: boolean;
  canRecord: boolean;
  canResolve: boolean;
  markDirty: () => void;
  onSend: (fingerprint: string, path: string, body?: unknown) => Promise<void>;
}) {
  const [category, setCategory] = useState(catalog.occurrence_categories[0] ?? "other");
  const [severity, setSeverity] = useState(catalog.occurrence_severities[0] ?? "medium");
  const [description, setDescription] = useState("");
  const [blocking, setBlocking] = useState(false);
  const [notes, setNotes] = useState("");
  return (
    <section className="section">
      <h3>Ocorrências</h3>
      {view.occurrences.map((item) => (
        <div key={item.id} className={item.is_blocking && item.status === "open" ? "blocked" : undefined}>
          <p>
            {catalogLabel(OCCURRENCE_LABEL, item.category)} · {catalogLabel(SEVERITY_LABEL, item.severity)} ·{" "}
            {statusLabel(item.status)}
            {item.is_blocking ? " · bloqueante" : ""}
          </p>
          <p>{item.description}</p>
          {canResolve && item.status === "open" ? (
            <button
              type="button"
              disabled={pending}
              onClick={() =>
                void onSend(`resolve:${item.id}:${notes}`, `/occurrences/${item.id}/resolve`, {
                  notes: notes || "ocorrência resolvida",
                })
              }
            >
              Resolver
            </button>
          ) : null}
        </div>
      ))}
      {canRecord ? (
        <form
          className="ops-form"
          onSubmit={(event) => {
            event.preventDefault();
            void onSend(`occ:${category}:${description}`, `/orders/${view.order.id}/occurrences`, {
              category,
              severity,
              description,
              is_blocking: blocking,
              batch_id: batch.id,
            });
          }}
        >
          <Field label="Categoria">
            <select value={category} onChange={(event) => setCategory(event.target.value)}>
              {catalog.occurrence_categories.map((item) => (
                <option key={item} value={item}>
                  {catalogLabel(OCCURRENCE_LABEL, item)}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Severidade">
            <select value={severity} onChange={(event) => setSeverity(event.target.value)}>
              {catalog.occurrence_severities.map((item) => (
                <option key={item} value={item}>
                  {catalogLabel(SEVERITY_LABEL, item)}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Descrição factual">
            <textarea value={description} required onChange={(event) => { setDescription(event.target.value); markDirty(); }} />
          </Field>
          <label className="ops-field">
            <input type="checkbox" checked={blocking} onChange={(event) => setBlocking(event.target.checked)} />
            Bloqueante
          </label>
          <Field label="Notas de resolução">
            <input value={notes} onChange={(event) => setNotes(event.target.value)} />
          </Field>
          <button type="submit" className="primary" disabled={pending}>
            Registrar ocorrência
          </button>
        </form>
      ) : null}
    </section>
  );
}

function YieldSection({
  batch,
  catalog,
  pending,
  canYield,
  markDirty,
  onSend,
}: {
  batch: ExecutionBatch;
  catalog: Catalog;
  pending: boolean;
  canYield: boolean;
  markDirty: () => void;
  onSend: (fingerprint: string, path: string, body?: unknown) => Promise<void>;
}) {
  const [type, setType] = useState(catalog.yield_types[0] ?? "pre_bake_mass");
  const [quantity, setQuantity] = useState("");
  const [unitId, setUnitId] = useState(catalog.mass_units[0]?.id ?? "");
  const parsed = parseQuantityInput(quantity);
  const projection = batch.yield_projection;
  return (
    <section className="section">
      <h2>5. Rendimento</h2>
      <p>
        Massa final {formatDecimal(projection.final_mass)} · unidades vendáveis{" "}
        {formatDecimal(projection.sellable_units)} · perda {formatDecimal(projection.loss_absolute)} (
        {formatDecimal(projection.loss_percent)}%) · desvio {formatDecimal(projection.target_deviation)} ·{" "}
        {projection.completeness === "complete" ? "completo" : "incompleto"}
        {projection.within_tolerance == null
          ? ""
          : projection.within_tolerance
            ? " · dentro da tolerância"
            : " · fora da tolerância"}
      </p>
      {canYield ? (
        <form
          className="ops-form"
          onSubmit={(event) => {
            event.preventDefault();
            if (!parsed) return;
            void onSend(`yield:${batch.id}:${type}:${parsed}`, `/batches/${batch.id}/yields`, {
              measurement_type: type,
              quantity: parsed,
              measurement_unit_id: unitId,
            });
          }}
        >
          <Field label="Tipo">
            <select value={type} onChange={(event) => setType(event.target.value)}>
              {catalog.yield_types.map((item) => (
                <option key={item} value={item}>
                  {catalogLabel(YIELD_LABEL, item)}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Quantidade de rendimento">
            <input inputMode="decimal" value={quantity} onChange={(event) => { setQuantity(event.target.value); markDirty(); }} />
          </Field>
          <Field label="Unidade">
            <select value={unitId} onChange={(event) => setUnitId(event.target.value)}>
              {catalog.mass_units.map((unit) => (
                <option key={unit.id} value={unit.id}>
                  {unit.symbol}
                </option>
              ))}
            </select>
          </Field>
          <button type="submit" className="primary" disabled={pending || !parsed}>
            Registrar rendimento
          </button>
        </form>
      ) : null}
    </section>
  );
}

function CloseSection({
  view,
  orderId,
  pending,
  onConfirm,
  onSend,
}: {
  view: ExecutionView;
  orderId: string;
  pending: boolean;
  onConfirm: (value: { title: string; run: () => Promise<void> } | null) => void;
  onSend: (fingerprint: string, path: string, body?: unknown, ifMatch?: number | null) => Promise<void>;
}) {
  const [reason, setReason] = useState("");
  const ready = view.readiness;
  const items = [
    ["Pesagem", ready.weighing],
    ["Conferências", ready.verifications],
    ["Etapas", ready.steps],
    ["Consumos", ready.consumptions],
    ["Rendimentos", ready.yields],
    ["Dependências", ready.dependencies],
    ["Ocorrências bloqueantes", ready.blocking_occurrences],
  ] as const;
  const canComplete = ready.permissions.complete;
  const canShort = ready.permissions.short_close;
  const started = !["draft", "scheduled", "released"].includes(view.order.status);
  return (
    <section className="section">
      <h2>6. Encerramento</h2>
      <ul>
        {items.map(([label, item]) => (
          <li key={label}>
            {label}: {item.ok ? "pronta" : item.reason}
          </li>
        ))}
        <li>Permissão de conclusão: {canComplete ? "sim" : "não"}</li>
        <li>Permissão de encerramento parcial: {canShort ? "sim" : "não"}</li>
      </ul>
      {canComplete ? (
        <button
          type="button"
          className="primary"
          disabled={pending}
          onClick={() =>
            onConfirm({
              title: `Concluir ${view.order.public_code} no alvo ${formatDecimal(view.order.target_quantity)}?`,
              run: () => onSend(`complete-order:${orderId}`, `/orders/${orderId}/complete`, undefined, view.order.row_version),
            })
          }
        >
          Concluir ordem
        </button>
      ) : null}
      {canShort ? (
        <div className="short-close">
          <p>Encerramento parcial não é conclusão normal. Os fatos são preservados.</p>
          <Field label="Motivo do encerramento parcial">
            <input value={reason} onChange={(event) => setReason(event.target.value)} />
          </Field>
          <button
            type="button"
            className="danger"
            disabled={pending || !reason.trim()}
            onClick={() =>
              onConfirm({
                title: "Confirmar encerramento parcial? Esta ordem não será concluída no alvo.",
                run: () =>
                  onSend(
                    `short:${orderId}:${reason}`,
                    `/orders/${orderId}/short-close`,
                    { reason },
                    view.order.row_version,
                  ),
              })
            }
          >
            Encerrar parcialmente
          </button>
        </div>
      ) : null}
      {started ? (
        <p className="meta">Cancelamento vazio não é oferecido depois de iniciada a produção.</p>
      ) : null}
    </section>
  );
}

function SheetSection({
  view,
  orderId,
  pending,
  canIssue,
  onSend,
}: {
  view: ExecutionView;
  orderId: string;
  pending: boolean;
  canIssue: boolean;
  onSend: (fingerprint: string, path: string, body?: unknown) => Promise<void>;
}) {
  return (
    <section className="section">
      <h2>7. Ficha</h2>
      {view.sheets.map((item) => (
        <p key={item.id}>
          <Link to={`/ordens/${orderId}/fichas/${item.id}`}>Ficha {item.issue_number}</Link>
          {item.previous_issue_id ? " · reemissão" : ""}
        </p>
      ))}
      {canIssue ? (
        <button
          type="button"
          className="primary"
          disabled={pending}
          onClick={() =>
            void onSend(`sheet:${orderId}:${view.sheets.length}`, `/orders/${orderId}/sheets`, {
              purpose: "operational",
            })
          }
        >
          {view.sheets.length ? "Reemitir ficha" : "Emitir ficha"}
        </button>
      ) : null}
    </section>
  );
}
