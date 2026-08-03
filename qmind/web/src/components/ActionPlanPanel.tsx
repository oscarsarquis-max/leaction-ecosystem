import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import { useAssessmentTeam } from "@/hooks/useAssessmentDetail";
import { useAssessmentFindings } from "@/hooks/useFindings";
import {
  useActionItemTransition,
  useActionPlanItems,
  useActionPlans,
  useActionPlanTransition,
  useCreateActionItem,
  useCreateActionPlan,
  useOpenAssessmentActions,
  type ActionKind,
} from "@/hooks/useActionPlans";
import {
  canActAsActionValidator,
  isActionItemOverdueDisplay,
} from "@/lib/permissions";

const ACTION_KINDS: ActionKind[] = [
  "correction",
  "corrective_action",
  "improvement",
];

const KIND_LABELS: Record<ActionKind, string> = {
  correction: "Correção",
  corrective_action: "Ação corretiva",
  improvement: "Melhoria",
};

const STATUS_LABELS: Record<string, string> = {
  draft: "rascunho",
  active: "ativo",
  completed: "concluído",
  cancelled: "cancelado",
  open: "aberta",
  in_progress: "em execução",
  implemented: "implementada",
  validated: "validada (eficácia pendente)",
  done: "concluída",
  ineffective: "ineficaz",
  ineffective_closed: "ineficaz (fechada)",
};

type PlanRow = {
  id: string;
  status: string;
  empty_plan_rationale?: string | null;
  created_at?: string;
  updated_at?: string;
};

type ItemRow = {
  id: string;
  finding_id?: string | null;
  action_kind: ActionKind;
  description: string;
  owner_membership_id: string;
  due_at: string;
  status: string;
  is_overdue?: boolean;
  efficacy_required: boolean;
  source_finding_withdrawn?: boolean;
  reject_reason?: string | null;
  efficacy_fail_reason?: string | null;
  cancel_reason?: string | null;
};

type FindingOpt = {
  id: string;
  title: string;
  status: string;
  finding_type?: string;
};

export function ActionPlanPanel({
  assessmentId,
  assessmentStatus,
  canManage,
  membershipId,
  roles,
}: {
  assessmentId: string;
  assessmentStatus: string | undefined;
  canManage: boolean;
  membershipId: string | null;
  roles: readonly string[];
}) {
  const plans = useActionPlans(assessmentId);
  const findings = useAssessmentFindings(assessmentId);
  const team = useAssessmentTeam(assessmentId);
  const openActions = useOpenAssessmentActions(assessmentId);
  const createPlan = useCreateActionPlan(assessmentId);
  const planTransition = useActionPlanTransition(assessmentId);
  const busyRef = useRef(false);
  const [activePlanId, setActivePlanId] = useState<string | null>(null);
  const [emptyRationale, setEmptyRationale] = useState("");

  const list = (plans.data as PlanRow[] | undefined) ?? [];
  const active =
    list.find((p) => p.id === activePlanId) ??
    list.find((p) => p.status === "draft" || p.status === "active") ??
    list[0] ??
    null;

  useEffect(() => {
    if (active && active.id !== activePlanId) setActivePlanId(active.id);
  }, [active, activePlanId]);

  const findingOptions = ((findings.data as FindingOpt[] | undefined) ?? []).filter(
    (f) => f.status === "approved" || f.status === "withdrawn",
  );

  async function runOnce(fn: () => Promise<unknown>) {
    if (busyRef.current) return;
    busyRef.current = true;
    try {
      await fn();
    } catch {
      // banner via mutation error
    } finally {
      busyRef.current = false;
    }
  }

  return (
    <section className="space-y-4" data-testid="action-plan">
      <header>
        <h2 className="font-display text-2xl text-teal-950">Plano de ação</h2>
        <p className="mt-1 text-sm text-teal-950/70">
          Plano draft → ativo → itens (execução → validação → eficácia). SoD: dono da ação
          não valida nem confirma eficácia. Scores/agregados não se aplicam aqui — o backend
          é a autoridade das transições.
        </p>
      </header>

      {assessmentStatus === "analysis" && canManage ? (
        <div
          className="rounded-md border border-amber-300/70 bg-amber-50/90 px-3 py-2 text-sm text-amber-950"
          data-testid="action-open-phase"
        >
          Assessment ainda em <span className="font-semibold">analysis</span>. Abra a fase de
          ações para alinhar o ciclo de vida.
          <button
            type="button"
            className="ml-3 rounded-md bg-teal-900 px-3 py-1 text-xs font-semibold text-white disabled:opacity-50"
            disabled={openActions.isPending}
            data-testid="action-open-actions"
            onClick={() => void runOnce(() => openActions.mutateAsync())}
          >
            Abrir fase actions
          </button>
        </div>
      ) : null}

      {openActions.isError ? (
        <ApiErrorBanner title="Erro ao abrir fase actions" error={openActions.error} />
      ) : null}
      {createPlan.isError ? (
        <ApiErrorBanner title="Erro ao criar plano" error={createPlan.error} />
      ) : null}
      {planTransition.isError ? (
        <ApiErrorBanner title="Erro na transição do plano" error={planTransition.error} />
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,14rem)_1fr]">
        <aside className="rounded-lg border border-teal-900/10 bg-white/70 p-3">
          <h3 className="font-display text-lg text-teal-950">Planos</h3>
          {plans.isLoading ? (
            <p className="mt-2 text-sm text-teal-950/60">Carregando…</p>
          ) : plans.isError ? (
            <ApiErrorBanner
              title="Erro ao listar planos"
              error={plans.error}
              onRetry={() => void plans.refetch()}
            />
          ) : list.length === 0 ? (
            <p className="mt-2 text-sm text-teal-950/60" data-testid="action-plans-empty">
              Nenhum plano.
            </p>
          ) : (
            <ul className="mt-2 space-y-1" data-testid="action-plans-list">
              {list.map((p) => (
                <li key={p.id}>
                  <button
                    type="button"
                    onClick={() => setActivePlanId(p.id)}
                    className={`w-full rounded px-2 py-1.5 text-left text-sm ${
                      active?.id === p.id
                        ? "bg-teal-900/10 font-semibold text-teal-950"
                        : "text-teal-950/80 hover:bg-teal-900/5"
                    }`}
                    data-testid={`action-plan-select-${p.id}`}
                  >
                    <span className="block font-mono text-[11px]">{p.id.slice(0, 8)}…</span>
                    <span data-testid={`action-plan-status-${p.id}`}>
                      {STATUS_LABELS[p.status] ?? p.status}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}

          {canManage &&
          (assessmentStatus === "analysis" || assessmentStatus === "actions") ? (
            <div className="mt-3 space-y-2 border-t border-teal-900/10 pt-3">
              <label className="block text-xs text-teal-950/70">
                Justificativa de plano vazio (opcional)
                <textarea
                  className="mt-1 w-full rounded border border-teal-900/20 bg-white px-2 py-1 text-sm"
                  rows={2}
                  value={emptyRationale}
                  onChange={(e) => setEmptyRationale(e.target.value)}
                  data-testid="action-empty-rationale"
                />
              </label>
              <button
                type="button"
                className="w-full rounded-md bg-teal-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
                disabled={createPlan.isPending}
                data-testid="action-create-plan"
                onClick={() =>
                  void runOnce(async () => {
                    const plan = await createPlan.mutateAsync(
                      emptyRationale.trim() || null,
                    );
                    setActivePlanId(plan.id);
                    setEmptyRationale("");
                  })
                }
              >
                Criar plano
              </button>
            </div>
          ) : null}
        </aside>

        <div>
          {!active ? (
            <p className="text-sm text-teal-950/60" data-testid="action-no-active">
              Selecione ou crie um plano.
            </p>
          ) : (
            <PlanWorkspace
              assessmentId={assessmentId}
              plan={active}
              canManage={canManage}
              membershipId={membershipId}
              roles={roles}
              findingOptions={findingOptions}
              teamMembers={(team.data ?? []).map((m) => ({
                membership_id: m.membership_id,
              }))}
              onActivate={() =>
                void runOnce(() =>
                  planTransition.mutateAsync({ planId: active.id, kind: "activate" }),
                )
              }
              onComplete={() =>
                void runOnce(() =>
                  planTransition.mutateAsync({ planId: active.id, kind: "complete" }),
                )
              }
              onCancel={() =>
                void runOnce(() =>
                  planTransition.mutateAsync({ planId: active.id, kind: "cancel" }),
                )
              }
              planTransitionPending={planTransition.isPending}
            />
          )}
        </div>
      </div>
    </section>
  );
}

function PlanWorkspace({
  assessmentId,
  plan,
  canManage,
  membershipId,
  roles,
  findingOptions,
  teamMembers,
  onActivate,
  onComplete,
  onCancel,
  planTransitionPending,
}: {
  assessmentId: string;
  plan: PlanRow;
  canManage: boolean;
  membershipId: string | null;
  roles: readonly string[];
  findingOptions: FindingOpt[];
  teamMembers: Array<{ membership_id: string }>;
  onActivate: () => void;
  onComplete: () => void;
  onCancel: () => void;
  planTransitionPending: boolean;
}) {
  const itemsQ = useActionPlanItems(plan.id);
  const createItem = useCreateActionItem(assessmentId, plan.id);
  const itemTransition = useActionItemTransition(assessmentId, plan.id);
  const busyRef = useRef(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const items = (itemsQ.data as ItemRow[] | undefined) ?? [];
  const selected = items.find((i) => i.id === selectedId) ?? null;

  const findingTitle = useMemo(() => {
    const map = new Map(findingOptions.map((f) => [f.id, f.title]));
    return (id: string | null | undefined) =>
      id ? (map.get(id) ?? id.slice(0, 8)) : "— (sem finding)";
  }, [findingOptions]);

  async function runOnce(fn: () => Promise<unknown>) {
    if (busyRef.current) return;
    busyRef.current = true;
    try {
      await fn();
    } catch {
      // banner
    } finally {
      busyRef.current = false;
    }
  }

  return (
    <div className="space-y-4" data-testid="action-plan-workspace">
      <div
        className="flex flex-wrap items-center gap-3 rounded-lg border border-teal-900/10 bg-white/70 px-4 py-3"
        data-testid="action-plan-meta"
      >
        <span className="text-sm text-teal-950">
          Status:{" "}
          <strong data-testid="action-plan-status">
            {STATUS_LABELS[plan.status] ?? plan.status}
          </strong>
        </span>
        {plan.empty_plan_rationale ? (
          <span className="text-xs text-teal-950/70" data-testid="action-plan-empty-note">
            Plano vazio justificado
          </span>
        ) : null}
        {canManage && plan.status === "draft" ? (
          <button
            type="button"
            className="rounded-md bg-teal-900 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
            disabled={planTransitionPending}
            data-testid="action-activate"
            onClick={onActivate}
          >
            Ativar plano
          </button>
        ) : null}
        {canManage && plan.status === "active" ? (
          <>
            <button
              type="button"
              className="rounded-md border border-teal-900/30 px-3 py-1.5 text-xs font-semibold text-teal-950 disabled:opacity-50"
              disabled={planTransitionPending}
              data-testid="action-complete"
              onClick={onComplete}
            >
              Concluir plano
            </button>
            <button
              type="button"
              className="rounded-md border border-rose-400/50 px-3 py-1.5 text-xs font-semibold text-rose-900 disabled:opacity-50"
              disabled={planTransitionPending}
              data-testid="action-cancel-plan"
              onClick={onCancel}
            >
              Cancelar plano
            </button>
          </>
        ) : null}
      </div>

      {plan.status === "draft" && canManage ? (
        <CreateItemForm
          findingOptions={findingOptions}
          teamMembers={teamMembers}
          defaultOwner={membershipId}
          pending={createItem.isPending}
          error={createItem.error}
          onSubmit={(input) =>
            void runOnce(async () => {
              const item = await createItem.mutateAsync(input);
              setSelectedId(item.id);
            })
          }
        />
      ) : null}

      {createItem.isError ? (
        <ApiErrorBanner title="Erro ao criar item" error={createItem.error} />
      ) : null}
      {itemTransition.isError ? (
        <ApiErrorBanner title="Erro na transição do item" error={itemTransition.error} />
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-lg border border-teal-900/10 bg-white/70 p-4">
          <h3 className="font-display text-xl text-teal-950">Itens</h3>
          {itemsQ.isLoading ? (
            <p className="mt-2 text-sm text-teal-950/60">Carregando…</p>
          ) : itemsQ.isError ? (
            <ApiErrorBanner
              title="Erro ao listar itens"
              error={itemsQ.error}
              onRetry={() => void itemsQ.refetch()}
            />
          ) : items.length === 0 ? (
            <p className="mt-2 text-sm text-teal-950/60" data-testid="action-items-empty">
              Nenhum item. Ative o plano com ≥1 item ou justificativa de plano vazio.
            </p>
          ) : (
            <ul className="mt-2 divide-y divide-teal-900/10" data-testid="action-items-list">
              {items.map((item) => {
                const overdue = isActionItemOverdueDisplay(item);
                return (
                  <li key={item.id}>
                    <button
                      type="button"
                      onClick={() => setSelectedId(item.id)}
                      className={`w-full py-2 text-left text-sm ${
                        selectedId === item.id
                          ? "font-semibold text-teal-900"
                          : "text-teal-950"
                      }`}
                      data-testid={`action-item-select-${item.id}`}
                    >
                      <span className="block">
                        {KIND_LABELS[item.action_kind]} ·{" "}
                        {STATUS_LABELS[item.status] ?? item.status}
                      </span>
                      <span className="block truncate text-xs text-teal-950/70">
                        {item.description}
                      </span>
                      {overdue ? (
                        <span
                          className="mt-1 inline-block text-xs font-semibold uppercase tracking-wide text-rose-800"
                          data-testid={`action-item-overdue-${item.id}`}
                        >
                          Atrasada (prazo {new Date(item.due_at).toLocaleDateString()})
                        </span>
                      ) : null}
                      {item.source_finding_withdrawn ? (
                        <span
                          className="mt-1 ml-2 inline-block text-xs font-semibold uppercase tracking-wide text-amber-900"
                          data-testid={`action-item-withdrawn-${item.id}`}
                        >
                          Finding origem retirada
                        </span>
                      ) : null}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        <ItemDetail
          item={selected}
          findingTitle={findingTitle(selected?.finding_id)}
          membershipId={membershipId}
          roles={roles}
          planActive={plan.status === "active"}
          pending={itemTransition.isPending}
          onTransition={(transition) => {
            if (!selected) return;
            void runOnce(() =>
              itemTransition.mutateAsync({ itemId: selected.id, transition }),
            );
          }}
        />
      </div>
    </div>
  );
}

function CreateItemForm({
  findingOptions,
  teamMembers,
  defaultOwner,
  pending,
  error,
  onSubmit,
}: {
  findingOptions: FindingOpt[];
  teamMembers: Array<{ membership_id: string }>;
  defaultOwner: string | null;
  pending: boolean;
  error: unknown;
  onSubmit: (input: {
    finding_id?: string | null;
    action_kind: ActionKind;
    description: string;
    owner_membership_id: string;
    due_at: string;
    efficacy_required?: boolean | null;
  }) => void;
}) {
  const [findingId, setFindingId] = useState("");
  const [kind, setKind] = useState<ActionKind>("corrective_action");
  const [description, setDescription] = useState("");
  const [owner, setOwner] = useState(defaultOwner ?? "");
  const [dueLocal, setDueLocal] = useState("");
  const [efficacy, setEfficacy] = useState(true);

  useEffect(() => {
    if (defaultOwner && !owner) setOwner(defaultOwner);
  }, [defaultOwner, owner]);

  useEffect(() => {
    setEfficacy(kind === "corrective_action");
  }, [kind]);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!description.trim() || !owner || !dueLocal) return;
    onSubmit({
      finding_id: findingId || null,
      action_kind: kind,
      description: description.trim(),
      owner_membership_id: owner,
      due_at: new Date(dueLocal).toISOString(),
      efficacy_required: efficacy,
    });
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-3 rounded-lg border border-teal-900/10 bg-white/70 p-4"
      data-testid="action-create-item-form"
    >
      <h3 className="font-display text-lg text-teal-950">Novo item (plano draft)</h3>
      <label className="block text-xs text-teal-950/70">
        Finding vinculada (aprovada)
        <select
          className="mt-1 w-full rounded border border-teal-900/20 bg-white px-2 py-1.5 text-sm"
          value={findingId}
          onChange={(e) => setFindingId(e.target.value)}
          data-testid="action-item-finding"
        >
          <option value="">— nenhuma —</option>
          {findingOptions
            .filter((f) => f.status === "approved")
            .map((f) => (
              <option key={f.id} value={f.id}>
                {f.finding_type ?? "finding"} · {f.title}
              </option>
            ))}
        </select>
      </label>
      <label className="block text-xs text-teal-950/70">
        Tipo de ação
        <select
          className="mt-1 w-full rounded border border-teal-900/20 bg-white px-2 py-1.5 text-sm"
          value={kind}
          onChange={(e) => setKind(e.target.value as ActionKind)}
          data-testid="action-item-kind"
        >
          {ACTION_KINDS.map((k) => (
            <option key={k} value={k}>
              {KIND_LABELS[k]} ({k})
            </option>
          ))}
        </select>
      </label>
      <label className="block text-xs text-teal-950/70">
        Descrição
        <textarea
          className="mt-1 w-full rounded border border-teal-900/20 bg-white px-2 py-1.5 text-sm"
          rows={2}
          required
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          data-testid="action-item-description"
        />
      </label>
      <label className="block text-xs text-teal-950/70">
        Responsável (owner)
        <select
          className="mt-1 w-full rounded border border-teal-900/20 bg-white px-2 py-1.5 text-sm"
          required
          value={owner}
          onChange={(e) => setOwner(e.target.value)}
          data-testid="action-item-owner"
        >
          <option value="">— selecione —</option>
          {teamMembers.map((m) => (
            <option key={m.membership_id} value={m.membership_id}>
              {m.membership_id}
            </option>
          ))}
          {defaultOwner &&
          !teamMembers.some((m) => m.membership_id === defaultOwner) ? (
            <option value={defaultOwner}>{defaultOwner} (você)</option>
          ) : null}
        </select>
      </label>
      <label className="block text-xs text-teal-950/70">
        Prazo
        <input
          type="datetime-local"
          className="mt-1 w-full rounded border border-teal-900/20 bg-white px-2 py-1.5 text-sm"
          required
          value={dueLocal}
          onChange={(e) => setDueLocal(e.target.value)}
          data-testid="action-item-due"
        />
      </label>
      <label className="flex items-center gap-2 text-sm text-teal-950">
        <input
          type="checkbox"
          checked={efficacy}
          onChange={(e) => setEfficacy(e.target.checked)}
          data-testid="action-item-efficacy"
        />
        Exige confirmação de eficácia
      </label>
      {error ? <ApiErrorBanner title="Erro ao criar item" error={error} /> : null}
      <button
        type="submit"
        disabled={pending}
        className="rounded-md bg-teal-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
        data-testid="action-create-item"
      >
        Adicionar item
      </button>
    </form>
  );
}

function ItemDetail({
  item,
  findingTitle,
  membershipId,
  roles,
  planActive,
  pending,
  onTransition,
}: {
  item: ItemRow | null;
  findingTitle: string;
  membershipId: string | null;
  roles: readonly string[];
  planActive: boolean;
  pending: boolean;
  onTransition: (
    t:
      | { kind: "start" }
      | { kind: "mark_implemented" }
      | { kind: "validate" }
      | { kind: "reject_implementation"; reason: string }
      | { kind: "confirm_efficacy" }
      | { kind: "fail_efficacy"; reason: string }
      | { kind: "reopen" }
      | { kind: "close_ineffective" }
      | { kind: "cancel"; reason: string },
  ) => void;
}) {
  const [reason, setReason] = useState("");

  if (!item) {
    return (
      <section className="rounded-lg border border-teal-900/10 bg-white/40 p-4 text-sm text-teal-950/60">
        Selecione um item para ver detalhes e transições.
      </section>
    );
  }

  const overdue = isActionItemOverdueDisplay(item);
  const isOwner = !!membershipId && membershipId === item.owner_membership_id;
  const canValidate = canActAsActionValidator(
    roles,
    membershipId,
    item.owner_membership_id,
    "validate",
  );
  const canEfficacy = canActAsActionValidator(
    roles,
    membershipId,
    item.owner_membership_id,
    "efficacy",
  );
  const sodBlocksValidate = isOwner && item.status === "implemented";
  const sodBlocksEfficacy = isOwner && item.status === "validated";

  return (
    <section
      className="space-y-3 rounded-lg border border-teal-900/10 bg-white/70 p-4"
      data-testid="action-item-detail"
    >
      <h3 className="font-display text-xl text-teal-950">Detalhe do item</h3>
      <dl className="grid gap-2 text-sm text-teal-950">
        <div>
          <dt className="text-xs uppercase tracking-wide text-teal-950/50">Status</dt>
          <dd data-testid="action-item-status">
            {STATUS_LABELS[item.status] ?? item.status}
            <span className="ml-2 font-mono text-xs text-teal-950/50">({item.status})</span>
          </dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-teal-950/50">Tipo</dt>
          <dd>
            {KIND_LABELS[item.action_kind]}{" "}
            <span className="font-mono text-xs">({item.action_kind})</span>
          </dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-teal-950/50">Descrição</dt>
          <dd>{item.description}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-teal-950/50">Finding</dt>
          <dd data-testid="action-item-finding-label">{findingTitle}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-teal-950/50">Owner</dt>
          <dd className="font-mono text-xs" data-testid="action-item-owner-id">
            {item.owner_membership_id}
          </dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-teal-950/50">Prazo</dt>
          <dd data-testid="action-item-due-display">
            {new Date(item.due_at).toLocaleString()}
            {overdue ? (
              <span
                className="ml-2 font-semibold uppercase tracking-wide text-rose-800"
                data-testid="action-item-overdue-badge"
              >
                · atrasada
              </span>
            ) : (
              <span className="ml-2 text-teal-950/60">· no prazo</span>
            )}
          </dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-teal-950/50">Eficácia</dt>
          <dd data-testid="action-item-efficacy-flag">
            {item.efficacy_required ? "obrigatória" : "não exigida"}
          </dd>
        </div>
      </dl>

      {item.source_finding_withdrawn ? (
        <div
          className="rounded-md border border-amber-400/60 bg-amber-50 px-3 py-2 text-sm text-amber-950"
          data-testid="action-withdrawn-banner"
          role="status"
        >
          A finding de origem foi retirada. O item permanece no fluxo — revise se a ação ainda
          faz sentido.
        </div>
      ) : null}

      {sodBlocksValidate || sodBlocksEfficacy ? (
        <div
          className="rounded-md border border-amber-400/60 bg-amber-50 px-3 py-2 text-sm text-amber-950"
          data-testid="action-sod-banner"
          role="status"
        >
          Separação de funções (SoD): você é o owner deste item e não pode{" "}
          {sodBlocksValidate ? "validar a implementação" : "confirmar a eficácia"}. Peça a outro
          revisor com papel adequado.
        </div>
      ) : null}

      {item.reject_reason ? (
        <p className="text-sm text-rose-900" data-testid="action-reject-reason">
          Rejeição: {item.reject_reason}
        </p>
      ) : null}
      {item.efficacy_fail_reason ? (
        <p className="text-sm text-rose-900" data-testid="action-efficacy-fail-reason">
          Eficácia falhou: {item.efficacy_fail_reason}
        </p>
      ) : null}

      {planActive ? (
        <div className="flex flex-wrap gap-2 border-t border-teal-900/10 pt-3">
          {item.status === "open" ? (
            <button
              type="button"
              disabled={pending}
              className="rounded-md bg-teal-900 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
              data-testid="action-item-start"
              onClick={() => onTransition({ kind: "start" })}
            >
              Iniciar execução
            </button>
          ) : null}
          {item.status === "in_progress" ? (
            <button
              type="button"
              disabled={pending}
              className="rounded-md bg-teal-900 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
              data-testid="action-item-mark-implemented"
              onClick={() => onTransition({ kind: "mark_implemented" })}
            >
              Marcar implementada
            </button>
          ) : null}
          {item.status === "implemented" ? (
            <>
              <button
                type="button"
                disabled={pending || !canValidate}
                className="rounded-md bg-teal-900 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
                data-testid="action-item-validate"
                title={
                  !canValidate
                    ? "SoD ou papel insuficiente — owner não valida"
                    : "Validar implementação"
                }
                onClick={() => onTransition({ kind: "validate" })}
              >
                Validar implementação
              </button>
              <ReasonActions
                reason={reason}
                setReason={setReason}
                pending={pending}
                disabled={!canValidate}
                testId="action-item-reject"
                label="Rejeitar implementação"
                onGo={() =>
                  onTransition({
                    kind: "reject_implementation",
                    reason: reason.trim(),
                  })
                }
              />
            </>
          ) : null}
          {item.status === "validated" ? (
            <>
              <button
                type="button"
                disabled={pending || !canEfficacy}
                className="rounded-md bg-teal-900 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
                data-testid="action-item-confirm-efficacy"
                title={
                  !canEfficacy
                    ? "SoD ou papel insuficiente — owner não confirma eficácia"
                    : "Confirmar eficácia"
                }
                onClick={() => onTransition({ kind: "confirm_efficacy" })}
              >
                Confirmar eficácia
              </button>
              <ReasonActions
                reason={reason}
                setReason={setReason}
                pending={pending}
                disabled={!canEfficacy}
                testId="action-item-fail-efficacy"
                label="Falhar eficácia"
                onGo={() =>
                  onTransition({ kind: "fail_efficacy", reason: reason.trim() })
                }
              />
            </>
          ) : null}
          {item.status === "ineffective" ? (
            <>
              <button
                type="button"
                disabled={pending}
                className="rounded-md border border-teal-900/30 px-3 py-1.5 text-xs font-semibold text-teal-950 disabled:opacity-50"
                data-testid="action-item-reopen"
                onClick={() => onTransition({ kind: "reopen" })}
              >
                Reabrir
              </button>
              <button
                type="button"
                disabled={pending}
                className="rounded-md border border-rose-400/50 px-3 py-1.5 text-xs font-semibold text-rose-900 disabled:opacity-50"
                data-testid="action-item-close-ineffective"
                onClick={() => onTransition({ kind: "close_ineffective" })}
              >
                Fechar como ineficaz
              </button>
            </>
          ) : null}
          {!["done", "cancelled", "ineffective_closed"].includes(item.status) ? (
            <ReasonActions
              reason={reason}
              setReason={setReason}
              pending={pending}
              disabled={false}
              testId="action-item-cancel"
              label="Cancelar item"
              onGo={() => onTransition({ kind: "cancel", reason: reason.trim() })}
            />
          ) : null}
        </div>
      ) : (
        <p className="text-xs text-teal-950/60" data-testid="action-item-plan-locked">
          Transições de item só após ativar o plano.
        </p>
      )}
    </section>
  );
}

function ReasonActions({
  reason,
  setReason,
  pending,
  disabled,
  testId,
  label,
  onGo,
}: {
  reason: string;
  setReason: (v: string) => void;
  pending: boolean;
  disabled: boolean;
  testId: string;
  label: string;
  onGo: () => void;
}) {
  return (
    <div className="flex flex-wrap items-end gap-2">
      <label className="block text-xs text-teal-950/70">
        Motivo
        <input
          className="mt-1 block w-48 rounded border border-teal-900/20 bg-white px-2 py-1 text-sm"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          data-testid={`${testId}-reason`}
        />
      </label>
      <button
        type="button"
        disabled={pending || disabled || !reason.trim()}
        className="rounded-md border border-rose-400/50 px-3 py-1.5 text-xs font-semibold text-rose-900 disabled:opacity-50"
        data-testid={testId}
        onClick={onGo}
      >
        {label}
      </button>
    </div>
  );
}
