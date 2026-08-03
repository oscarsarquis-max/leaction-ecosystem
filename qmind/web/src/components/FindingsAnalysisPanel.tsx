import { useEffect, useRef, useState, type FormEvent } from "react";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import { useAssessmentScopes } from "@/hooks/useAssessmentDetail";
import { useAssessmentEvidences } from "@/hooks/useFieldExecution";
import {
  useAssessmentFindings,
  useCreateFinding,
  useFindingTransition,
  useUpdateFinding,
  type FindingDraftInput,
  type FindingType,
} from "@/hooks/useFindings";
import {
  canApproveFinding,
  isFindingAuthor,
} from "@/lib/permissions";

const TYPES: FindingType[] = [
  "conformity",
  "nonconformity",
  "opportunity",
  "observation",
];

type FindingRow = {
  id: string;
  status: string;
  finding_type: FindingType;
  title: string;
  body: string;
  severity?: string | null;
  requirement_ids?: string[];
  evidence_ids?: string[];
  insufficient_evidence?: boolean;
  insufficient_evidence_rationale?: string | null;
  author_membership_id: string;
  withdrawn_reason?: string | null;
  discard_reason?: string | null;
  rework_of_finding_id?: string | null;
};

function emptyDraft(defaultReq?: string): FindingDraftInput {
  return {
    finding_type: "observation",
    title: "",
    body: "",
    severity: null,
    requirement_ids: defaultReq ? [defaultReq] : [],
    evidence_ids: [],
    insufficient_evidence: false,
    insufficient_evidence_rationale: null,
  };
}

export function FindingsAnalysisPanel({
  assessmentId,
  canCreate,
  canReview,
  membershipId,
  roles,
}: {
  assessmentId: string;
  canCreate: boolean;
  canReview: boolean;
  membershipId: string | null;
  roles: readonly string[];
}) {
  const findings = useAssessmentFindings(assessmentId);
  const scopes = useAssessmentScopes(assessmentId);
  const evidences = useAssessmentEvidences(assessmentId);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const requirementOptions = (scopes.data ?? [])
    .filter((s) => s.requirement_id)
    .map((s) => s.requirement_id as string);
  const approvedEvidence = (evidences.data ?? []).filter((e) => e.status === "approved");

  const selected =
    (findings.data as FindingRow[] | undefined)?.find((f) => f.id === selectedId) ?? null;

  return (
    <section className="space-y-6" data-testid="findings-analysis">
      <header>
        <h2 className="font-display text-2xl text-teal-950">Findings (análise)</h2>
        <p className="mt-1 text-sm text-teal-950/70">
          Rascunho → revisão → aprovado|rejeitado. Conformidade exige Evidence{" "}
          <span className="font-semibold">approved</span>; evidência insuficiente é bloqueada
          para conformity/opportunity. SoD: autor não aprova a própria Finding.
        </p>
      </header>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-lg border border-teal-900/10 bg-white/70 p-4">
          <h3 className="font-display text-xl text-teal-950">Lista</h3>
          {findings.isLoading ? (
            <p className="mt-3 text-sm text-teal-950/60">Carregando…</p>
          ) : findings.isError ? (
            <div className="mt-3">
              <ApiErrorBanner
                title="Erro ao listar findings"
                error={findings.error}
                onRetry={() => void findings.refetch()}
              />
            </div>
          ) : (findings.data?.length ?? 0) === 0 ? (
            <p className="mt-3 text-sm text-teal-950/60" data-testid="findings-empty">
              Nenhuma finding.
            </p>
          ) : (
            <ul className="mt-3 divide-y divide-teal-900/10" data-testid="findings-list">
              {(findings.data as FindingRow[]).map((f) => (
                <li key={f.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedId(f.id)}
                    className={`w-full py-2 text-left text-sm ${
                      selectedId === f.id ? "font-semibold text-teal-900" : "text-teal-950"
                    }`}
                    data-testid={`finding-select-${f.id}`}
                  >
                    <span className="uppercase tracking-wide">{f.status}</span>
                    {" · "}
                    {f.finding_type}
                    {" · "}
                    {f.title}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <FindingEditor
          assessmentId={assessmentId}
          canCreate={canCreate}
          canReview={canReview}
          membershipId={membershipId}
          roles={roles}
          selected={selected}
          requirementOptions={requirementOptions}
          approvedEvidenceIds={approvedEvidence.map((e) => e.id)}
          onCreated={(id) => setSelectedId(id)}
          onCleared={() => setSelectedId(null)}
        />
      </div>
    </section>
  );
}

function FindingEditor({
  assessmentId,
  canCreate,
  canReview,
  membershipId,
  roles,
  selected,
  requirementOptions,
  approvedEvidenceIds,
  onCreated,
  onCleared,
}: {
  assessmentId: string;
  canCreate: boolean;
  canReview: boolean;
  membershipId: string | null;
  roles: readonly string[];
  selected: FindingRow | null;
  requirementOptions: string[];
  approvedEvidenceIds: string[];
  onCreated: (id: string) => void;
  onCleared: () => void;
}) {
  const create = useCreateFinding(assessmentId);
  const update = useUpdateFinding(assessmentId);
  const transition = useFindingTransition(assessmentId);
  const busyRef = useRef(false);
  const [draft, setDraft] = useState<FindingDraftInput>(() =>
    emptyDraft(requirementOptions[0]),
  );
  const [reason, setReason] = useState("");
  const [mode, setMode] = useState<"create" | "edit">("create");

  useEffect(() => {
    if (!selected) {
      setMode("create");
      setDraft(emptyDraft(requirementOptions[0]));
      return;
    }
    setMode("edit");
    setDraft({
      finding_type: selected.finding_type,
      title: selected.title,
      body: selected.body,
      severity: selected.severity ?? null,
      requirement_ids: selected.requirement_ids ?? [],
      evidence_ids: selected.evidence_ids ?? [],
      insufficient_evidence: !!selected.insufficient_evidence,
      insufficient_evidence_rationale: selected.insufficient_evidence_rationale ?? null,
    });
  }, [selected, requirementOptions]);

  const editable = canCreate && (!selected || selected.status === "draft");
  const author = isFindingAuthor(membershipId, selected?.author_membership_id);
  const mayApprove =
    !!selected &&
    selected.status === "in_review" &&
    canApproveFinding(roles, membershipId, selected.author_membership_id);
  const sodBlocksApprove =
    !!selected &&
    selected.status === "in_review" &&
    canReview &&
    author;

  async function runOnce(fn: () => Promise<void>) {
    if (busyRef.current) return;
    busyRef.current = true;
    try {
      await fn();
    } catch {
      // Surfaced via mutation.error / ApiErrorBanner
    } finally {
      busyRef.current = false;
    }
  }

  async function onSave(e: FormEvent) {
    e.preventDefault();
    if (!editable) return;
    await runOnce(async () => {
      if (mode === "create" || !selected) {
        const row = await create.mutateAsync(draft);
        onCreated(row.id);
        return;
      }
      await update.mutateAsync({ findingId: selected.id, input: draft });
    });
  }

  function toggleReq(id: string) {
    setDraft((d) => ({
      ...d,
      requirement_ids: d.requirement_ids.includes(id)
        ? d.requirement_ids.filter((x) => x !== id)
        : [...d.requirement_ids, id],
    }));
  }

  function toggleEv(id: string) {
    setDraft((d) => ({
      ...d,
      evidence_ids: d.evidence_ids.includes(id)
        ? d.evidence_ids.filter((x) => x !== id)
        : [...d.evidence_ids, id],
    }));
  }

  const insuffAllowed =
    draft.finding_type === "nonconformity" || draft.finding_type === "observation";

  return (
    <section className="rounded-lg border border-teal-900/10 bg-white/70 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-display text-xl text-teal-950">
          {selected ? "Detalhe / edição" : "Nova finding"}
        </h3>
        {selected ? (
          <button
            type="button"
            className="text-xs font-semibold text-teal-900 underline"
            onClick={onCleared}
            data-testid="finding-new"
          >
            Nova
          </button>
        ) : null}
      </div>

      {selected ? (
        <p className="mt-2 text-xs text-teal-950/60" data-testid="finding-sod-banner">
          Autor: <span className="font-mono">{selected.author_membership_id}</span>
          {author ? " (você)" : ""}
          {sodBlocksApprove
            ? " — SoD: você não pode aprovar finding da qual é autor."
            : null}
        </p>
      ) : null}

      <form className="mt-3 space-y-3" onSubmit={(e) => void onSave(e)} data-testid="finding-form">
        <label className="block text-sm">
          Tipo
          <select
            className="field mt-1 w-full"
            disabled={!editable}
            value={draft.finding_type}
            onChange={(e) => {
              const finding_type = e.target.value as FindingType;
              setDraft((d) => ({
                ...d,
                finding_type,
                insufficient_evidence:
                  finding_type === "conformity" || finding_type === "opportunity"
                    ? false
                    : d.insufficient_evidence,
              }));
            }}
            data-testid="finding-type"
          >
            {TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>

        <label className="block text-sm">
          Título
          <input
            className="field mt-1 w-full"
            disabled={!editable}
            value={draft.title}
            onChange={(e) => setDraft((d) => ({ ...d, title: e.target.value }))}
            required
            data-testid="finding-title"
          />
        </label>

        <label className="block text-sm">
          Corpo
          <textarea
            className="field mt-1 w-full"
            rows={4}
            disabled={!editable}
            value={draft.body}
            onChange={(e) => setDraft((d) => ({ ...d, body: e.target.value }))}
            required
            data-testid="finding-body"
          />
        </label>

        <fieldset className="space-y-1">
          <legend className="text-sm font-semibold text-teal-950">Requisitos</legend>
          {requirementOptions.length === 0 ? (
            <p className="text-xs text-amber-900">Nenhum requirement no escopo.</p>
          ) : (
            requirementOptions.map((rid) => (
              <label key={rid} className="flex items-center gap-2 text-xs font-mono">
                <input
                  type="checkbox"
                  disabled={!editable}
                  checked={draft.requirement_ids.includes(rid)}
                  onChange={() => toggleReq(rid)}
                />
                {rid}
              </label>
            ))
          )}
        </fieldset>

        <fieldset className="space-y-1">
          <legend className="text-sm font-semibold text-teal-950">
            Evidências approved
          </legend>
          {approvedEvidenceIds.length === 0 ? (
            <p className="text-xs text-amber-900" data-testid="finding-no-approved-evidence">
              Nenhuma Evidence approved — conformidade não poderá ser submetida.
            </p>
          ) : (
            approvedEvidenceIds.map((eid) => (
              <label key={eid} className="flex items-center gap-2 text-xs font-mono">
                <input
                  type="checkbox"
                  disabled={!editable}
                  checked={draft.evidence_ids.includes(eid)}
                  onChange={() => toggleEv(eid)}
                  data-testid={`finding-evidence-${eid}`}
                />
                {eid}
              </label>
            ))
          )}
        </fieldset>

        {insuffAllowed ? (
          <label className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              disabled={!editable}
              checked={draft.insufficient_evidence}
              onChange={(e) =>
                setDraft((d) => ({
                  ...d,
                  insufficient_evidence: e.target.checked,
                }))
              }
              data-testid="finding-insufficient"
            />
            <span>
              Evidência insuficiente
              <textarea
                className="field mt-1 w-full"
                rows={2}
                disabled={!editable || !draft.insufficient_evidence}
                placeholder="Justificativa obrigatória"
                value={draft.insufficient_evidence_rationale ?? ""}
                onChange={(e) =>
                  setDraft((d) => ({
                    ...d,
                    insufficient_evidence_rationale: e.target.value,
                  }))
                }
                data-testid="finding-insufficient-rationale"
              />
            </span>
          </label>
        ) : (
          <p className="text-xs text-teal-950/60" data-testid="finding-insuff-forbidden">
            Para `{draft.finding_type}`, evidência insuficiente não é permitida.
          </p>
        )}

        {editable ? (
          <button
            type="submit"
            disabled={create.isPending || update.isPending}
            className="rounded-md bg-teal-900 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-60"
            data-testid="finding-save"
          >
            {create.isPending || update.isPending
              ? "Salvando…"
              : mode === "create"
                ? "Criar draft"
                : "Salvar draft"}
          </button>
        ) : null}
      </form>

      {create.isError ? (
        <div className="mt-2">
          <ApiErrorBanner title="Falha ao criar" error={create.error} />
        </div>
      ) : null}
      {update.isError ? (
        <div className="mt-2">
          <ApiErrorBanner title="Falha ao atualizar" error={update.error} />
        </div>
      ) : null}

      {selected ? (
        <div className="mt-4 space-y-2 border-t border-teal-900/10 pt-3">
          <h4 className="text-sm font-semibold text-teal-950">Transições</h4>
          <div className="flex flex-wrap gap-2">
            {selected.status === "draft" && canCreate ? (
              <>
                <button
                  type="button"
                  disabled={transition.isPending}
                  className="rounded-md bg-teal-900 px-2 py-1 text-xs font-semibold text-white disabled:opacity-60"
                  data-testid="finding-submit"
                  onClick={() =>
                    void runOnce(async () => {
                      await transition.mutateAsync({
                        findingId: selected.id,
                        transition: { kind: "submit" },
                      });
                    })
                  }
                >
                  Submeter
                </button>
                <button
                  type="button"
                  disabled={transition.isPending}
                  className="rounded-md border border-amber-400/60 bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-950"
                  data-testid="finding-discard"
                  onClick={() =>
                    void runOnce(async () => {
                      await transition.mutateAsync({
                        findingId: selected.id,
                        transition: { kind: "discard", reason: reason || undefined },
                      });
                      onCleared();
                    })
                  }
                >
                  Discard
                </button>
              </>
            ) : null}

            {selected.status === "in_review" && canReview ? (
              <>
                <button
                  type="button"
                  disabled={transition.isPending || !mayApprove}
                  className="rounded-md bg-teal-900 px-2 py-1 text-xs font-semibold text-white disabled:opacity-40"
                  data-testid="finding-approve"
                  title={
                    sodBlocksApprove
                      ? "SoD: autor não pode aprovar"
                      : "Aprovar finding"
                  }
                  onClick={() =>
                    void runOnce(async () => {
                      await transition.mutateAsync({
                        findingId: selected.id,
                        transition: { kind: "approve" },
                      });
                    })
                  }
                >
                  Aprovar
                </button>
                <button
                  type="button"
                  disabled={transition.isPending || !reason.trim()}
                  className="rounded-md border border-red-300 bg-red-50 px-2 py-1 text-xs font-semibold text-red-900"
                  data-testid="finding-reject"
                  onClick={() =>
                    void runOnce(async () => {
                      await transition.mutateAsync({
                        findingId: selected.id,
                        transition: { kind: "reject", reason: reason.trim() },
                      });
                    })
                  }
                >
                  Rejeitar
                </button>
              </>
            ) : null}

            {selected.status === "rejected" && canCreate ? (
              <button
                type="button"
                disabled={transition.isPending}
                className="rounded-md border border-teal-900/20 bg-white px-2 py-1 text-xs font-semibold"
                data-testid="finding-rework"
                onClick={() =>
                  void runOnce(async () => {
                    await transition.mutateAsync({
                      findingId: selected.id,
                      transition: { kind: "rework" },
                    });
                  })
                }
              >
                Rework → draft
              </button>
            ) : null}

            {selected.status === "approved" && canReview ? (
              <button
                type="button"
                disabled={transition.isPending || !reason.trim()}
                className="rounded-md border border-amber-400/60 bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-950"
                data-testid="finding-withdraw"
                onClick={() =>
                  void runOnce(async () => {
                    await transition.mutateAsync({
                      findingId: selected.id,
                      transition: { kind: "withdraw", reason: reason.trim() },
                    });
                  })
                }
              >
                Withdraw
              </button>
            ) : null}

            {selected.status === "withdrawn" && canCreate ? (
              <button
                type="button"
                disabled={transition.isPending}
                className="rounded-md bg-teal-900 px-2 py-1 text-xs font-semibold text-white"
                data-testid="finding-new-version"
                onClick={() =>
                  void runOnce(async () => {
                    const res = await transition.mutateAsync({
                      findingId: selected.id,
                      transition: { kind: "rework" },
                    });
                    onCreated(res.finding.id);
                  })
                }
              >
                Nova versão (draft)
              </button>
            ) : null}
          </div>

          {(selected.status === "in_review" ||
            selected.status === "approved" ||
            selected.status === "draft") &&
          (canReview || canCreate) ? (
            <label className="mt-2 block text-sm">
              Motivo (reject / withdraw / discard)
              <input
                className="field mt-1 w-full"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                data-testid="finding-reason"
              />
            </label>
          ) : null}

          {transition.isError ? (
            <div className="mt-2" data-testid="finding-transition-error">
              <ApiErrorBanner title="Falha na transição" error={transition.error} />
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
