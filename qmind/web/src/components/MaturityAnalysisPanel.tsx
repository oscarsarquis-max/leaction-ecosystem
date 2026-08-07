import { useEffect, useMemo, useRef, useState } from "react";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import { useAssessmentEvidences } from "@/hooks/useFieldExecution";
import {
  useMaturityPackages,
  useMaturityTransition,
  useOpenMaturityPackage,
  useUpsertMaturityScores,
  type Applicability,
  type ScoreDraft,
} from "@/hooks/useMaturity";
import {
  canApproveMaturity,
  canEditMaturityScores,
  maturityEvidenceHint,
} from "@/lib/permissions";
import { labelWorkflowStatus } from "@/lib/labels";

const LEVEL_LABELS: Record<number, string> = {
  1: "1 — inicial",
  2: "2 — definido",
  3: "3 — gerenciado",
  4: "4 — medido",
  5: "5 — otimizando",
};

type ScoreRow = {
  id: string;
  criterion_id: string;
  criterion_code?: string | null;
  criterion_title?: string | null;
  dimension_id?: string | null;
  dimension_code?: string | null;
  dimension_title?: string | null;
  anchor_l3?: string | null;
  applicability: Applicability;
  level: number | null;
  na_rationale: string | null;
  rationale: string | null;
  evidence_ids: string[];
};

type PackageRow = {
  id: string;
  status: string;
  version_no: number;
  model_code?: string | null;
  model_version?: string | null;
  global_score?: string | number | null;
  author_membership_id: string;
  updated_at?: string;
  scores: ScoreRow[];
  dimension_scores: Array<{
    dimension_id: string;
    dimension_code: string;
    dimension_title?: string | null;
    score: string | number;
    applicable_count: number;
  }>;
};

function scoreToDraft(s: ScoreRow): ScoreDraft {
  return {
    criterion_id: s.criterion_id,
    applicability: s.applicability,
    level: s.level,
    na_rationale: s.na_rationale,
    rationale: s.rationale,
    evidence_ids: [...(s.evidence_ids ?? [])],
  };
}

function formatScore(v: string | number | null | undefined): string {
  if (v == null || v === "") return "—";
  return String(v);
}

export function MaturityAnalysisPanel({
  assessmentId,
  canElaborate,
  canReview,
  membershipId,
  roles,
  assessmentStatus,
}: {
  assessmentId: string;
  canElaborate: boolean;
  canReview: boolean;
  membershipId: string | null;
  roles: readonly string[];
  assessmentStatus: string | undefined;
}) {
  const packages = useMaturityPackages(assessmentId);
  const openPkg = useOpenMaturityPackage(assessmentId);
  const evidences = useAssessmentEvidences(assessmentId);
  const [activeId, setActiveId] = useState<string | null>(null);

  const list = (packages.data as PackageRow[] | undefined) ?? [];
  const active =
    list.find((p) => p.id === activeId) ??
    list.find((p) => p.status === "draft" || p.status === "in_review" || p.status === "rejected") ??
    list[0] ??
    null;

  useEffect(() => {
    if (active && active.id !== activeId) setActiveId(active.id);
  }, [active, activeId]);

  const approvedEvidence = (evidences.data ?? []).filter((e) => e.status === "approved");

  async function onOpen() {
    try {
      const pkg = await openPkg.mutateAsync();
      setActiveId(pkg.id);
    } catch {
      // banner
    }
  }

  return (
    <section className="space-y-4" data-testid="maturity-analysis">
      <header>
        <h2 className="font-display text-2xl text-teal-950">Maturidade</h2>
        <p className="mt-1 text-sm text-teal-950/70">
          Seis dimensões / 18 critérios. Níveis de maturidade de dimensão e global vêm{" "}
          <span className="font-semibold">somente do servidor</span> (half-up). Níveis
          identificados por texto (não só cor). SoD: autor não aprova.
        </p>
      </header>

      <div className="flex flex-wrap items-center gap-2">
        {canElaborate ? (
          <button
            type="button"
            disabled={openPkg.isPending}
            onClick={() => void onOpen()}
            className="rounded-md bg-teal-900 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-60"
            data-testid="maturity-open"
          >
            {openPkg.isPending ? "Abrindo…" : "Criar / abrir pacote corrente"}
          </button>
        ) : null}
        {list.length > 0 ? (
          <label className="text-sm text-teal-950">
            Versão do pacote
            <select
              className="field ml-2"
              value={active?.id ?? ""}
              onChange={(e) => setActiveId(e.target.value)}
              data-testid="maturity-version-select"
            >
              {list.map((p) => (
                <option key={p.id} value={p.id}>
                  v{p.version_no} · {labelWorkflowStatus(p.status)}
                  {p.global_score != null ? ` · global ${formatScore(p.global_score)}` : ""}
                </option>
              ))}
            </select>
          </label>
        ) : null}
      </div>

      {openPkg.isError ? (
        <ApiErrorBanner title="Falha ao abrir pacote" error={openPkg.error} />
      ) : null}
      {packages.isError ? (
        <ApiErrorBanner
          title="Erro ao listar pacotes"
          error={packages.error}
          onRetry={() => void packages.refetch()}
        />
      ) : null}

      {packages.isLoading ? (
        <p className="text-sm text-teal-950/60">Carregando maturidade…</p>
      ) : !active ? (
        <p className="text-sm text-teal-950/60" data-testid="maturity-empty">
          Nenhum pacote ainda. Abra o pacote corrente para iniciar.
        </p>
      ) : (
        <PackageWorkspace
          assessmentId={assessmentId}
          assessmentStatus={assessmentStatus}
          pkg={active}
          canElaborate={canElaborate}
          canReview={canReview}
          membershipId={membershipId}
          roles={roles}
          approvedEvidenceIds={approvedEvidence.map((e) => e.id)}
          onPackageId={(id) => setActiveId(id)}
        />
      )}
    </section>
  );
}

function PackageWorkspace({
  assessmentId,
  assessmentStatus,
  pkg,
  canElaborate,
  canReview,
  membershipId,
  roles,
  approvedEvidenceIds,
  onPackageId,
}: {
  assessmentId: string;
  assessmentStatus: string | undefined;
  pkg: PackageRow;
  canElaborate: boolean;
  canReview: boolean;
  membershipId: string | null;
  roles: readonly string[];
  approvedEvidenceIds: string[];
  onPackageId: (id: string) => void;
}) {
  const upsert = useUpsertMaturityScores(assessmentId);
  const transition = useMaturityTransition(assessmentId);
  const busyRef = useRef(false);
  const [drafts, setDrafts] = useState<Record<string, ScoreDraft>>({});
  const [reason, setReason] = useState("");
  const [selectedCriterion, setSelectedCriterion] = useState<string | null>(null);

  useEffect(() => {
    const next: Record<string, ScoreDraft> = {};
    for (const s of pkg.scores) next[s.criterion_id] = scoreToDraft(s);
    setDrafts(next);
    setSelectedCriterion((prev) =>
      prev && next[prev] ? prev : (pkg.scores[0]?.criterion_id ?? null),
    );
  }, [pkg.id, pkg.updated_at, pkg.status, pkg.scores]);

  const editable = canEditMaturityScores(roles, assessmentStatus, pkg.status);
  const author = membershipId === pkg.author_membership_id;
  const mayApprove =
    pkg.status === "in_review" &&
    canApproveMaturity(roles, membershipId, pkg.author_membership_id);
  const sodBlocks = pkg.status === "in_review" && canReview && author;

  const byDimension = useMemo(() => {
    const map = new Map<string, ScoreRow[]>();
    for (const s of pkg.scores) {
      const key = s.dimension_code ?? "unknown";
      const arr = map.get(key) ?? [];
      arr.push(s);
      map.set(key, arr);
    }
    return map;
  }, [pkg.scores]);

  const dimScoreMap = useMemo(() => {
    const m = new Map<string, PackageRow["dimension_scores"][number]>();
    for (const d of pkg.dimension_scores) m.set(d.dimension_code, d);
    return m;
  }, [pkg.dimension_scores]);

  const fullyNaDims = useMemo(() => {
    const out: string[] = [];
    for (const [code, rows] of byDimension) {
      if (rows.length > 0 && rows.every((r) => r.applicability === "not_applicable")) {
        out.push(code);
      }
    }
    return out;
  }, [byDimension]);

  async function runOnce(fn: () => Promise<void>) {
    if (busyRef.current) return;
    busyRef.current = true;
    try {
      await fn();
    } catch {
      // mutation error banner
    } finally {
      busyRef.current = false;
    }
  }

  async function saveAll() {
    if (!editable) return;
    await runOnce(async () => {
      const scores = Object.values(drafts);
      await upsert.mutateAsync({ packageId: pkg.id, scores });
      transition.reset();
    });
  }

  function patchCriterion(criterionId: string, patch: Partial<ScoreDraft>) {
    setDrafts((prev) => {
      const cur = prev[criterionId];
      if (!cur) return prev;
      const next = { ...cur, ...patch };
      if (next.applicability === "not_applicable") {
        next.level = null;
      } else if (next.applicability === "insufficient_info") {
        next.level = null;
        next.na_rationale = null;
      } else if (next.applicability === "applicable" && next.level == null) {
        next.level = 3;
      }
      return { ...prev, [criterionId]: next };
    });
  }

  const selected = pkg.scores.find((s) => s.criterion_id === selectedCriterion) ?? null;
  const selectedDraft = selected ? drafts[selected.criterion_id] : null;
  const evidenceHint = maturityEvidenceHint(selectedDraft?.level);

  return (
    <div className="space-y-4 rounded-lg border border-teal-900/10 bg-white/70 p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <p className="text-sm text-teal-950" data-testid="maturity-package-meta">
            Modelo{" "}
            <span className="font-semibold">
              {pkg.model_code}@{pkg.model_version}
            </span>
            {" · "}
            Pacote <span className="font-semibold">v{pkg.version_no}</span>
            {" · "}
            <span className="tracking-wide" data-testid="maturity-status">
              {labelWorkflowStatus(pkg.status)}
            </span>
          </p>
          <p className="mt-1 text-xs text-teal-950/60" data-testid="maturity-sod">
            {author ? "Autor: você" : "Autor: outro membro da equipe"}
            {sodBlocks
              ? " — Você não pode aprovar este pacote (SoD / segregação de funções)."
              : null}
          </p>
        </div>
        <div className="text-right" data-testid="maturity-global-score">
          <p className="text-xs uppercase tracking-wide text-teal-950/60">
            Nível de maturidade global
          </p>
          <p className="font-display text-3xl text-teal-950">
            {formatScore(pkg.global_score)}
          </p>
          <p className="text-[11px] text-teal-950/50">calculado pelo servidor</p>
        </div>
      </div>

      {fullyNaDims.length > 0 ? (
        <p
          className="rounded-md border border-amber-300/60 bg-amber-50/80 px-3 py-2 text-sm text-amber-950"
          data-testid="maturity-full-na"
        >
          Dimensões totalmente N/A (fora do global):{" "}
          {fullyNaDims
            .map((c) => dimScoreMap.get(c)?.dimension_title || c)
            .join(", ")}
        </p>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" data-testid="maturity-dim-scores">
        {[...byDimension.keys()].map((code) => {
          const dim = dimScoreMap.get(code);
          const title =
            dim?.dimension_title ||
            byDimension.get(code)?.[0]?.dimension_title ||
            code;
          const fullyNa = fullyNaDims.includes(code);
          return (
            <div
              key={code}
              className="rounded-md border border-teal-900/10 bg-teal-50/40 px-3 py-2"
              data-testid={`maturity-dim-${code}`}
            >
              <p className="text-xs font-semibold text-teal-950">{title}</p>
              <p className="mt-1 font-mono text-lg text-teal-950">
                {fullyNa ? "N/A (omitida)" : formatScore(dim?.score)}
              </p>
              {!fullyNa && dim ? (
                <p className="text-[11px] text-teal-950/50">
                  {dim.applicable_count} critério(s) aplicável(is)
                </p>
              ) : null}
            </div>
          );
        })}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div>
          <h3 className="font-display text-lg text-teal-950">Critérios</h3>
          <ul className="mt-2 max-h-[28rem] space-y-1 overflow-y-auto" data-testid="maturity-criteria-list">
            {pkg.scores.map((s) => {
              const d = drafts[s.criterion_id];
              const levelText =
                d?.applicability === "applicable" && d.level
                  ? LEVEL_LABELS[d.level]
                  : d?.applicability === "not_applicable"
                    ? "N/A"
                    : "info insuficiente";
              return (
                <li key={s.criterion_id}>
                  <button
                    type="button"
                    onClick={() => setSelectedCriterion(s.criterion_id)}
                    className={`w-full rounded px-2 py-1.5 text-left text-sm ${
                      selectedCriterion === s.criterion_id
                        ? "bg-teal-900/10 font-semibold text-teal-900"
                        : "text-teal-950"
                    }`}
                    data-testid={`maturity-criterion-${s.criterion_code}`}
                  >
                    <span className="font-mono text-xs">{s.criterion_code}</span>
                    {" · "}
                    {s.criterion_title}
                    <span className="mt-0.5 block text-xs text-teal-950/60">
                      {levelText}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>

        {selected && selectedDraft ? (
          <div className="space-y-3" data-testid="maturity-criterion-editor">
            <h3 className="font-display text-lg text-teal-950">
              {selected.criterion_code} — {selected.criterion_title}
            </h3>
            {selected.anchor_l3 ? (
              <p className="text-xs text-teal-950/70">
                Âncora L3: {selected.anchor_l3}
              </p>
            ) : null}

            <label className="block text-sm">
              Aplicabilidade
              <select
                className="field mt-1 w-full"
                disabled={!editable}
                value={selectedDraft.applicability}
                onChange={(e) =>
                  patchCriterion(selected.criterion_id, {
                    applicability: e.target.value as Applicability,
                  })
                }
                data-testid="maturity-applicability"
              >
                <option value="applicable">aplicável</option>
                <option value="not_applicable">não aplicável (exige justificativa)</option>
                <option value="insufficient_info">
                  informação insuficiente (só rascunho; bloqueia envio)
                </option>
              </select>
            </label>

            {selectedDraft.applicability === "applicable" ? (
              <fieldset>
                <legend className="text-sm font-semibold text-teal-950">Nível (1–5)</legend>
                <div className="mt-1 space-y-1">
                  {[1, 2, 3, 4, 5].map((n) => (
                    <label key={n} className="flex items-center gap-2 text-sm">
                      <input
                        type="radio"
                        name={`level-${selected.criterion_id}`}
                        disabled={!editable}
                        checked={selectedDraft.level === n}
                        onChange={() =>
                          patchCriterion(selected.criterion_id, { level: n })
                        }
                        data-testid={`maturity-level-${n}`}
                      />
                      <span>{LEVEL_LABELS[n]}</span>
                    </label>
                  ))}
                </div>
              </fieldset>
            ) : null}

            {selectedDraft.applicability === "not_applicable" ? (
              <label className="block text-sm">
                Justificativa N/A (obrigatória)
                <textarea
                  className="field mt-1 w-full"
                  rows={2}
                  disabled={!editable}
                  value={selectedDraft.na_rationale ?? ""}
                  onChange={(e) =>
                    patchCriterion(selected.criterion_id, {
                      na_rationale: e.target.value,
                    })
                  }
                  data-testid="maturity-na-rationale"
                />
              </label>
            ) : null}

            {selectedDraft.applicability === "applicable" ? (
              <label className="block text-sm">
                Justificativa / medição / melhoria
                <textarea
                  className="field mt-1 w-full"
                  rows={2}
                  disabled={!editable}
                  value={selectedDraft.rationale ?? ""}
                  onChange={(e) =>
                    patchCriterion(selected.criterion_id, {
                      rationale: e.target.value,
                    })
                  }
                  data-testid="maturity-rationale"
                />
              </label>
            ) : null}

            {evidenceHint ? (
              <p className="text-xs text-amber-900" data-testid="maturity-evidence-hint">
                {evidenceHint}
              </p>
            ) : null}

            {selectedDraft.applicability === "applicable" &&
            (selectedDraft.level ?? 0) >= 3 ? (
              <fieldset className="space-y-1">
                <legend className="text-sm font-semibold text-teal-950">
                  Evidências aprovadas
                </legend>
                {approvedEvidenceIds.length === 0 ? (
                  <p className="text-xs text-amber-900">Nenhuma evidência aprovada.</p>
                ) : (
                  approvedEvidenceIds.map((eid) => (
                    <label key={eid} className="flex items-center gap-2 font-mono text-xs">
                      <input
                        type="checkbox"
                        disabled={!editable}
                        checked={selectedDraft.evidence_ids.includes(eid)}
                        onChange={() => {
                          const has = selectedDraft.evidence_ids.includes(eid);
                          patchCriterion(selected.criterion_id, {
                            evidence_ids: has
                              ? selectedDraft.evidence_ids.filter((x) => x !== eid)
                              : [...selectedDraft.evidence_ids, eid],
                          });
                        }}
                      />
                      {eid}
                    </label>
                  ))
                )}
              </fieldset>
            ) : null}

            {editable ? (
              <button
                type="button"
                disabled={upsert.isPending}
                onClick={() => void saveAll()}
                className="rounded-md bg-teal-900 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-60"
                data-testid="maturity-save"
              >
                {upsert.isPending
                  ? "Salvando…"
                  : "Salvar nível de maturidade (servidor recalcula)"}
              </button>
            ) : (
              <p className="text-xs text-amber-900" data-testid="maturity-immutable">
                Pacote “{labelWorkflowStatus(pkg.status)}” — edição bloqueada (versão
                aprovada/imóvel).
              </p>
            )}
          </div>
        ) : null}
      </div>

      {upsert.isError ? (
        <ApiErrorBanner
          title="Falha ao salvar nível de maturidade"
          error={upsert.error}
        />
      ) : null}

      <div className="space-y-2 border-t border-teal-900/10 pt-3">
        <h4 className="text-sm font-semibold text-teal-950">Transições</h4>
        <div className="flex flex-wrap gap-2">
          {pkg.status === "draft" && canElaborate ? (
            <button
              type="button"
              disabled={transition.isPending}
              className="rounded-md bg-teal-900 px-2 py-1 text-xs font-semibold text-white disabled:opacity-60"
              data-testid="maturity-submit"
              onClick={() =>
                void runOnce(async () => {
                  await transition.mutateAsync({
                    packageId: pkg.id,
                    transition: { kind: "submit" },
                  });
                })
              }
            >
              Enviar para revisão
            </button>
          ) : null}

          {pkg.status === "in_review" && canReview ? (
            <>
              <button
                type="button"
                disabled={transition.isPending || !mayApprove}
                className="rounded-md bg-teal-900 px-2 py-1 text-xs font-semibold text-white disabled:opacity-40"
                data-testid="maturity-approve"
                title={sodBlocks ? "SoD: autor não pode aprovar" : "Aprovar"}
                onClick={() =>
                  void runOnce(async () => {
                    await transition.mutateAsync({
                      packageId: pkg.id,
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
                className="rounded-md border border-qmind-semantic-danger/30 bg-qmind-semantic-future px-2 py-1 text-xs font-semibold text-qmind-semantic-danger"
                data-testid="maturity-reject"
                onClick={() =>
                  void runOnce(async () => {
                    await transition.mutateAsync({
                      packageId: pkg.id,
                      transition: { kind: "reject", reason: reason.trim() },
                    });
                  })
                }
              >
                Rejeitar
              </button>
            </>
          ) : null}

          {pkg.status === "rejected" && canElaborate ? (
            <button
              type="button"
              disabled={transition.isPending}
              className="rounded-md border border-teal-900/20 bg-white px-2 py-1 text-xs font-semibold"
              data-testid="maturity-rework"
              onClick={() =>
                void runOnce(async () => {
                  await transition.mutateAsync({
                    packageId: pkg.id,
                    transition: { kind: "rework" },
                  });
                })
              }
            >
                Retrabalho → rascunho
            </button>
          ) : null}

          {pkg.status === "approved" && canReview ? (
            <button
              type="button"
              disabled={transition.isPending || !reason.trim()}
              className="rounded-md border border-amber-400/60 bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-950"
              data-testid="maturity-supersede"
              onClick={() =>
                void runOnce(async () => {
                  const res = await transition.mutateAsync({
                    packageId: pkg.id,
                    transition: { kind: "supersede", reason: reason.trim() },
                  });
                  if (res.new_package_id) onPackageId(res.new_package_id);
                  else if (res.package?.id) onPackageId(res.package.id);
                })
              }
            >
              Substituir → nova versão
            </button>
          ) : null}
        </div>

        {(pkg.status === "in_review" || pkg.status === "approved") && canReview ? (
          <label className="block text-sm">
            Motivo (rejeição / substituição)
            <input
              className="field mt-1 w-full"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              data-testid="maturity-reason"
            />
          </label>
        ) : null}

        {transition.isError ? (
          <ApiErrorBanner title="Falha na transição" error={transition.error} />
        ) : null}
      </div>
    </div>
  );
}
