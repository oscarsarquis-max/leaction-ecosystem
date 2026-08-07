import { useMemo, useState, type FormEvent, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import { AssessmentSectionNav } from "@/components/navigation/AssessmentSectionNav";
import {
  AccessDeniedPanel,
  EmptyPanel,
  LoadingPanel,
} from "@/components/StatePanels";
import { useAssessment, useAssessmentTeam } from "@/hooks/useAssessmentDetail";
import { useAssessmentPermissions } from "@/hooks/useAssessmentPermissions";
import {
  useAcceptEvolutionSuggestion,
  useConvertEvolutionSuggestion,
  useDismissEvolutionSuggestion,
  useEvolutionMap,
  useGenerateEvolutionMap,
  useInvestigateEvolutionSuggestion,
} from "@/hooks/useEvolutionMap";
import { useActionPlans, useOpenAssessmentActions } from "@/hooks/useActionPlans";
import { useRegisterAssistantContext } from "@/assistant/AssistantProvider";
import { baseAssessmentContext } from "@/assistant/contextBuilders";
import type { AssistantContext } from "@/assistant/types";
import { useOrganization } from "@/org/OrganizationProvider";
import { QmindApiError } from "@/api/qmindApi";
import {
  EVOLUTION_CATEGORY_ORDER,
  labelEvolutionCategory,
  labelEvolutionConfidence,
  labelEvolutionEffort,
  labelEvolutionImpact,
  labelEvolutionMode,
  labelEvolutionPriority,
  labelEvolutionStatus,
} from "@/lib/evolutionLabels";
import { labelAssessmentStatus } from "@/lib/labels";
import { canReviewEvolutionMap } from "@/lib/permissions";

type Suggestion = {
  id: string;
  rule_id: string;
  category: string;
  title: string;
  observation: string;
  business_rationale: string;
  suggested_evolution: string;
  expected_benefit: string;
  first_step: string;
  impact: string;
  effort: string;
  priority: string;
  confidence: string;
  is_priority: boolean;
  status: string;
  dismiss_reason?: string | null;
  investigate_note?: string | null;
  related_clauses?: string[];
  source_references?: Array<{
    kind: string;
    id?: string | null;
    question_id?: string | null;
    question_version?: string | null;
    label?: string | null;
    detail?: string | null;
  }>;
  action_item_id?: string | null;
  action_plan_id?: string | null;
};

type Package = {
  id: string;
  package_version: number;
  generation_mode: string;
  catalog_version: string;
  generated_at: string;
  source_snapshot?: Record<string, unknown>;
  priority_suggestions: Suggestion[];
  secondary_suggestions: Suggestion[];
  regeneration_diff?: {
    new_rule_ids: string[];
    retained_rule_ids: string[];
    superseded_rule_ids: string[];
    preserved_accepted_rule_ids: string[];
  } | null;
};

export function AssessmentEvolutionPage() {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const org = useOrganization();
  const assessment = useAssessment(assessmentId);
  const mapQ = useEvolutionMap(assessmentId);
  const perms = useAssessmentPermissions(assessment.data?.status);
  const canReview = canReviewEvolutionMap(perms.roles);
  const team = useAssessmentTeam(assessmentId);
  const plans = useActionPlans(assessmentId);

  const generate = useGenerateEvolutionMap(assessmentId ?? "");
  const accept = useAcceptEvolutionSuggestion(assessmentId ?? "");
  const dismiss = useDismissEvolutionSuggestion(assessmentId ?? "");
  const investigate = useInvestigateEvolutionSuggestion(assessmentId ?? "");
  const convert = useConvertEvolutionSuggestion(assessmentId ?? "");
  const openActions = useOpenAssessmentActions(assessmentId ?? "");

  const [actionError, setActionError] = useState<unknown>(null);
  const [lastDiff, setLastDiff] = useState<Package["regeneration_diff"]>(null);
  const [confirmRegen, setConfirmRegen] = useState(false);
  const [sourcesFor, setSourcesFor] = useState<Suggestion | null>(null);
  const [dismissFor, setDismissFor] = useState<Suggestion | null>(null);
  const [investigateFor, setInvestigateFor] = useState<Suggestion | null>(null);
  const [convertFor, setConvertFor] = useState<Suggestion | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const pkg = (mapQ.data as Package | null) ?? null;
  const status = assessment.data?.status;

  const assistantCtx = useMemo((): AssistantContext | null => {
    if (!assessmentId || !assessment.data || !org.currentOrganizationId) return null;
    const priority = pkg?.priority_suggestions ?? [];
    const needsReview = priority.filter((s) => s.status === "proposed").length;
    const top = [...priority].sort((a, b) => {
      const order = { now: 0, investigate: 1, next_cycle: 2, future: 3 };
      return (order[a.priority as keyof typeof order] ?? 9) -
        (order[b.priority as keyof typeof order] ?? 9);
    })[0];
    return {
      ...baseAssessmentContext({
        organizationId: org.currentOrganizationId,
        organizationName: org.currentOrganization?.organizationName || "Organização",
        assessmentId,
        assessmentType: assessment.data.type,
        status: assessment.data.status,
        roles: org.currentOrganization?.roles ?? [],
        canMutate: canReview,
        route: `/assessments/${assessmentId}/evolution`,
        page: "evolution_map",
        stage_title: "Mapa de Evolução Empresarial",
        stage_explanation:
          "Este mapa transforma respostas, evidências e resultados em sugestões práticas. Não é certificação nem julgamento automático — revise antes de virar ação.",
        next_action: {
          label: pkg
            ? needsReview > 0
              ? "Revisar sugestões prioritárias"
              : "Atualizar mapa ou converter aceitas"
            : "Gerar mapa de evolução",
          hint: top
            ? `Maior prioridade agora: ${top.title}`
            : "Gere o pacote a partir das fontes da avaliação.",
          href: `/assessments/${assessmentId}/evolution`,
          mutates: false,
        },
        pendencies: needsReview
          ? [
              {
                key: "evo-review",
                problem: `${needsReview} sugestão(ões) ainda sem revisão humana`,
                impact: "Sem revisão, o relatório não inclui oportunidades aceitas",
                actionLabel: "Revisar no mapa",
                href: `/assessments/${assessmentId}/evolution`,
              },
            ]
          : [],
        progress_summary: pkg
          ? `Pacote v${pkg.package_version} · ${priority.length} prioritárias · ${pkg.secondary_suggestions.length} secundárias`
          : "Mapa ainda não gerado",
      }),
      evolution: {
        hasPackage: !!pkg,
        priorityCount: priority.length,
        secondaryCount: pkg?.secondary_suggestions.length ?? 0,
        needsReviewCount: needsReview,
        topPriorityTitle: top?.title ?? null,
        generationMode: pkg?.generation_mode ?? null,
      },
    };
  }, [
    assessmentId,
    assessment.data,
    org.currentOrganizationId,
    org.currentOrganization,
    pkg,
    canReview,
  ]);

  useRegisterAssistantContext(assistantCtx);

  if (!assessmentId) {
    return <EmptyPanel title="Avaliação inválida" />;
  }
  if (assessment.isLoading || mapQ.isLoading) {
    return <LoadingPanel title="Carregando mapa de evolução…" />;
  }
  if (assessment.isError) {
    const err = assessment.error;
    if (err instanceof QmindApiError && (err.status === 401 || err.status === 403)) {
      return <AccessDeniedPanel message={err.message} />;
    }
    return <ApiErrorBanner title="Erro ao carregar avaliação" error={err} />;
  }
  if (mapQ.isError) {
    const err = mapQ.error;
    if (err instanceof QmindApiError && (err.status === 401 || err.status === 403)) {
      return <AccessDeniedPanel message={err.message} />;
    }
    return (
      <ApiErrorBanner
        title="Erro ao carregar mapa"
        error={err}
        onRetry={() => void mapQ.refetch()}
      />
    );
  }

  const priority = pkg?.priority_suggestions ?? [];
  const secondary = pkg?.secondary_suggestions ?? [];
  const byCategory = groupByCategory(priority);

  async function runGenerate() {
    setActionError(null);
    setConfirmRegen(false);
    try {
      const mode =
        status === "analysis" ||
        status === "actions" ||
        status === "report" ||
        status === "closed"
          ? "analysis_ready"
          : "preliminary";
      const out = (await generate.mutateAsync({ mode })) as Package;
      setLastDiff(out.regeneration_diff ?? null);
    } catch (e) {
      setActionError(e);
    }
  }

  async function withBusy(id: string, fn: () => Promise<void>) {
    setBusyId(id);
    setActionError(null);
    try {
      await fn();
    } catch (e) {
      setActionError(e);
    } finally {
      setBusyId(null);
    }
  }

  const snap = pkg?.source_snapshot as
    | {
        answer_count?: number;
        evidence_count?: number;
        finding_count?: number;
      }
    | undefined;

  return (
    <section className="space-y-8" data-testid="evolution-map-page">
      <AssessmentSectionNav assessmentId={assessmentId} />

      <header className="space-y-3">
        <p className="text-sm text-teal-950/60">
          <Link to={`/assessments/${assessmentId}`} className="hover:underline">
            Visão geral
          </Link>
          {" / "}
          Mapa de Evolução Empresarial
        </p>
        <h1 className="font-display text-3xl tracking-tight text-teal-950">
          Mapa de Evolução Empresarial
        </h1>
        <p className="max-w-3xl text-sm leading-relaxed text-teal-950/75">
          Este mapa transforma respostas, evidências e resultados da avaliação em
          sugestões práticas para fortalecer a organização. As sugestões não
          representam certificação ou julgamento automático e devem ser revisadas
          antes de virar ações.
        </p>
        <p className="text-xs text-teal-950/55">
          Fase da avaliação: {labelAssessmentStatus(status)} · Catálogo de regras
          determinístico (sem IA generativa).
        </p>
      </header>

      {!canReview ? (
        <p
          className="rounded-md border border-amber-300/60 bg-amber-50/80 px-3 py-2 text-sm text-amber-950"
          data-testid="evolution-reader-notice"
        >
          Você pode visualizar o mapa, mas não revisar, descartar ou converter
          sugestões com o papel atual.
        </p>
      ) : null}

      {actionError ? <ApiErrorBanner error={actionError} /> : null}

      {!pkg ? (
        <EmptyGenerate
          canReview={canReview}
          pending={generate.isPending}
          onGenerate={() => void runGenerate()}
        />
      ) : (
        <>
          <section
            className="grid gap-3 rounded-xl border border-teal-900/10 bg-white/70 p-4 sm:grid-cols-2 lg:grid-cols-3"
            data-testid="evolution-package-meta"
          >
            <Meta label="Versão do pacote" value={`v${pkg.package_version}`} />
            <Meta label="Tipo de leitura" value={labelEvolutionMode(pkg.generation_mode)} />
            <Meta
              label="Gerado em"
              value={new Date(pkg.generated_at).toLocaleString("pt-BR")}
            />
            <Meta label="Sugestões principais" value={String(priority.length)} />
            <Meta label="Sugestões secundárias" value={String(secondary.length)} />
            <Meta
              label="Fontes consideradas"
              value={[
                snap?.answer_count != null ? `${snap.answer_count} respostas` : null,
                snap?.evidence_count != null
                  ? `${snap.evidence_count} evidências`
                  : null,
                snap?.finding_count != null
                  ? `${snap.finding_count} constatações`
                  : null,
              ]
                .filter(Boolean)
                .join(" · ") || "Snapshot do pacote"}
            />
          </section>

          <p className="text-sm text-teal-950/70" data-testid="evolution-human-review-notice">
            Revisão humana obrigatória: aceite, aprofunde ou descarte antes de
            incluir no relatório ou converter em ação.
          </p>

          {canReview ? (
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                className="qm-btn-secondary"
                data-testid="evolution-regen-open"
                onClick={() => setConfirmRegen(true)}
              >
                Atualizar mapa
              </button>
              <Link
                to={`/assessments/${assessmentId}/advanced`}
                className="qm-btn-secondary"
              >
                Ir para análise, ações e relatório
              </Link>
            </div>
          ) : null}

          {confirmRegen ? (
            <RegenConfirm
              pending={generate.isPending}
              onCancel={() => setConfirmRegen(false)}
              onConfirm={() => void runGenerate()}
            />
          ) : null}

          {lastDiff ? <DiffPanel diff={lastDiff} /> : null}

          {priority.length === 0 ? (
            <EmptyPanel
              title="Nenhuma sugestão prioritária neste pacote"
              message="Nenhuma regra aplicável foi encontrada com as fontes atuais. Isso não significa conformidade — revise respostas e evidências e atualize o mapa."
            />
          ) : (
            <div className="space-y-8" data-testid="evolution-priority-list">
              {EVOLUTION_CATEGORY_ORDER.map((cat) => {
                const items = byCategory.get(cat) ?? [];
                if (!items.length) return null;
                return (
                  <section key={cat} data-testid={`evolution-cat-${cat}`}>
                    <h2 className="font-display text-xl text-teal-950">
                      {labelEvolutionCategory(cat)}
                    </h2>
                    <ul className="mt-3 space-y-4">
                      {items.map((s) => (
                        <SuggestionCard
                          key={s.id}
                          suggestion={s}
                          canReview={canReview}
                          busy={busyId === s.id}
                          assessmentStatus={status}
                          onSources={() => setSourcesFor(s)}
                          onAccept={() =>
                            void withBusy(s.id, async () => {
                              await accept.mutateAsync(s.id);
                            })
                          }
                          onDismiss={() => setDismissFor(s)}
                          onInvestigate={() => setInvestigateFor(s)}
                          onConvert={() => setConvertFor(s)}
                        />
                      ))}
                    </ul>
                  </section>
                );
              })}
            </div>
          )}

          {secondary.length > 0 ? (
            <details className="rounded-lg border border-teal-900/10 bg-white/50 p-4">
              <summary className="cursor-pointer font-semibold text-teal-950">
                Sugestões secundárias ({secondary.length})
              </summary>
              <ul className="mt-3 space-y-2 text-sm text-teal-950/80">
                {secondary.map((s) => (
                  <li key={s.id}>
                    {s.title} · {labelEvolutionStatus(s.status)} ·{" "}
                    {labelEvolutionPriority(s.priority)}
                  </li>
                ))}
              </ul>
            </details>
          ) : null}
        </>
      )}

      {sourcesFor ? (
        <SourcesModal suggestion={sourcesFor} onClose={() => setSourcesFor(null)} />
      ) : null}
      {dismissFor ? (
        <DismissModal
          pending={busyId === dismissFor.id}
          onClose={() => setDismissFor(null)}
          onConfirm={(reason) =>
            void withBusy(dismissFor.id, async () => {
              await dismiss.mutateAsync({
                suggestionId: dismissFor.id,
                reason,
              });
              setDismissFor(null);
            })
          }
        />
      ) : null}
      {investigateFor ? (
        <InvestigateModal
          pending={busyId === investigateFor.id}
          onClose={() => setInvestigateFor(null)}
          onConfirm={(missing) =>
            void withBusy(investigateFor.id, async () => {
              await investigate.mutateAsync({
                suggestionId: investigateFor.id,
                missing_information: missing,
              });
              setInvestigateFor(null);
            })
          }
        />
      ) : null}
      {convertFor ? (
        <ConvertModal
          suggestion={convertFor}
          assessmentStatus={status}
          teamMembers={(team.data ?? []).map((m: { membership_id: string }) => m.membership_id)}
          plans={(plans.data ?? []) as Array<{ id: string; status: string }>}
          pending={busyId === convertFor.id}
          openActionsPending={openActions.isPending}
          onOpenActions={() =>
            void withBusy(convertFor.id, async () => {
              await openActions.mutateAsync();
              await assessment.refetch();
            })
          }
          onClose={() => setConvertFor(null)}
          onConfirm={(body) =>
            void withBusy(convertFor.id, async () => {
              await convert.mutateAsync({
                suggestionId: convertFor.id,
                ...body,
              });
              setConvertFor(null);
            })
          }
        />
      ) : null}
    </section>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-teal-950/50">
        {label}
      </p>
      <p className="mt-0.5 text-sm text-teal-950">{value}</p>
    </div>
  );
}

function groupByCategory(items: Suggestion[]) {
  const map = new Map<string, Suggestion[]>();
  for (const s of items) {
    const list = map.get(s.category) ?? [];
    list.push(s);
    map.set(s.category, list);
  }
  return map;
}

function EmptyGenerate({
  canReview,
  pending,
  onGenerate,
}: {
  canReview: boolean;
  pending: boolean;
  onGenerate: () => void;
}) {
  return (
    <section
      className="rounded-xl border border-dashed border-teal-900/20 bg-teal-50/40 p-6"
      data-testid="evolution-empty"
    >
      <h2 className="font-display text-xl text-teal-950">Ainda sem pacote</h2>
      <p className="mt-2 max-w-2xl text-sm text-teal-950/75">
        O motor analisará respostas do Wizard, evidências vinculadas, constatações
        revisadas e maturidade aprovada (quando existir). Nada será convertido em
        ação automaticamente.
      </p>
      <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-teal-950/70">
        <li>Pré-condição mínima: avaliação existente com contexto ou respostas.</li>
        <li>Leitura preliminar após a preparação; leitura com análise na fase Análise.</li>
      </ul>
      {canReview ? (
        <button
          type="button"
          className="qm-btn-primary mt-4"
          disabled={pending}
          data-testid="evolution-generate"
          onClick={onGenerate}
        >
          {pending ? "Gerando…" : "Gerar mapa"}
        </button>
      ) : (
        <p className="mt-4 text-sm text-amber-900">
          Seu papel permite visualizar, mas não gerar o mapa.
        </p>
      )}
    </section>
  );
}

function RegenConfirm({
  pending,
  onCancel,
  onConfirm,
}: {
  pending: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <div
      className="rounded-lg border border-teal-900/20 bg-white p-4 shadow-sm"
      data-testid="evolution-regen-confirm"
      role="dialog"
    >
      <h3 className="font-display text-lg text-teal-950">Atualizar mapa?</h3>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-teal-950/75">
        <li>Novas respostas e evidências serão consideradas.</li>
        <li>Sugestões aceitas não serão apagadas.</li>
        <li>Ações existentes permanecerão.</li>
        <li>Versões anteriores do pacote serão preservadas (supersede).</li>
      </ul>
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          className="qm-btn-primary"
          disabled={pending}
          data-testid="evolution-regen-confirm-btn"
          onClick={onConfirm}
        >
          {pending ? "Atualizando…" : "Confirmar atualização"}
        </button>
        <button type="button" className="qm-btn-secondary" onClick={onCancel}>
          Cancelar
        </button>
      </div>
    </div>
  );
}

function DiffPanel({
  diff,
}: {
  diff: NonNullable<Package["regeneration_diff"]>;
}) {
  return (
    <section
      className="rounded-lg border border-teal-900/10 bg-teal-50/50 p-4 text-sm"
      data-testid="evolution-regen-diff"
    >
      <h3 className="font-semibold text-teal-950">Diferenças após atualizar</h3>
      <ul className="mt-2 space-y-1 text-teal-950/75">
        <li>Novas: {diff.new_rule_ids.length || "nenhuma"}</li>
        <li>Mantidas: {diff.retained_rule_ids.length || "nenhuma"}</li>
        <li>Superadas: {diff.superseded_rule_ids.length || "nenhuma"}</li>
        <li>
          Aceitas preservadas: {diff.preserved_accepted_rule_ids.length || "nenhuma"}
        </li>
      </ul>
    </section>
  );
}

function SuggestionCard({
  suggestion: s,
  canReview,
  busy,
  assessmentStatus,
  onSources,
  onAccept,
  onDismiss,
  onInvestigate,
  onConvert,
}: {
  suggestion: Suggestion;
  canReview: boolean;
  busy: boolean;
  assessmentStatus?: string;
  onSources: () => void;
  onAccept: () => void;
  onDismiss: () => void;
  onInvestigate: () => void;
  onConvert: () => void;
}) {
  const convertible =
    s.status === "accepted" &&
    (assessmentStatus === "actions" ||
      assessmentStatus === "report" ||
      assessmentStatus === "closed" ||
      assessmentStatus === "analysis");

  return (
    <li
      className="rounded-xl border border-teal-900/10 bg-white p-4 shadow-sm"
      data-testid={`evolution-suggestion-${s.id}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className="font-display text-lg text-teal-950">{s.title}</h3>
        <span className="rounded bg-teal-900/10 px-2 py-0.5 text-xs font-semibold">
          {labelEvolutionStatus(s.status)}
        </span>
      </div>
      <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
        <Field label="O que observamos" value={s.observation} />
        <Field label="Por que importa" value={s.business_rationale} />
        <Field label="Evolução sugerida" value={s.suggested_evolution} />
        <Field label="Benefício esperado" value={s.expected_benefit} />
        <Field label="Primeiro passo" value={s.first_step} />
        <div className="grid grid-cols-2 gap-2">
          <Field label="Prioridade" value={labelEvolutionPriority(s.priority)} />
          <Field label="Confiança" value={labelEvolutionConfidence(s.confidence)} />
          <Field label="Impacto" value={labelEvolutionImpact(s.impact)} />
          <Field label="Esforço" value={labelEvolutionEffort(s.effort)} />
        </div>
      </dl>
      {s.investigate_note ? (
        <p className="mt-2 text-sm text-amber-900">
          Aprofundar: {s.investigate_note}
        </p>
      ) : null}
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          className="qm-btn-secondary"
          data-testid="evolution-sources"
          onClick={onSources}
        >
          Por que esta sugestão apareceu?
        </button>
        {canReview && s.status === "proposed" ? (
          <>
            <button
              type="button"
              className="qm-btn-primary"
              disabled={busy}
              data-testid="evolution-accept"
              onClick={onAccept}
            >
              Aceitar sugestão
            </button>
            <button
              type="button"
              className="qm-btn-secondary"
              disabled={busy}
              data-testid="evolution-investigate"
              onClick={onInvestigate}
            >
              Aprofundar
            </button>
            <button
              type="button"
              className="qm-btn-secondary"
              disabled={busy}
              data-testid="evolution-dismiss"
              onClick={onDismiss}
            >
              Descartar
            </button>
          </>
        ) : null}
        {canReview && convertible ? (
          <button
            type="button"
            className="qm-btn-primary"
            disabled={busy || s.status === "converted_to_action"}
            data-testid="evolution-convert"
            onClick={onConvert}
          >
            Converter em ação
          </button>
        ) : null}
        {s.action_item_id ? (
          <span className="text-sm font-semibold text-teal-800">
            Já convertida em ação
          </span>
        ) : null}
      </div>
    </li>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase tracking-wide text-teal-950/50">
        {label}
      </dt>
      <dd className="mt-0.5 text-teal-950/85">{value}</dd>
    </div>
  );
}

function SourcesModal({
  suggestion,
  onClose,
}: {
  suggestion: Suggestion;
  onClose: () => void;
}) {
  const refs = suggestion.source_references ?? [];
  return (
    <div
      className="fixed inset-0 z-40 flex items-end justify-center bg-black/30 p-4 sm:items-center"
      role="dialog"
      aria-modal
      data-testid="evolution-sources-modal"
    >
      <div className="max-h-[85vh] w-full max-w-lg overflow-auto rounded-xl bg-white p-5 shadow-xl">
        <h3 className="font-display text-xl text-teal-950">
          Por que esta sugestão apareceu?
        </h3>
        <p className="mt-1 text-sm text-teal-950/65">{suggestion.title}</p>
        {suggestion.related_clauses?.length ? (
          <p className="mt-3 text-sm text-teal-950/80">
            Referência de cláusula (QMind):{" "}
            {suggestion.related_clauses.map((c) => `tema ${c}`).join(", ")}
          </p>
        ) : null}
        <ul className="mt-4 space-y-3">
          {refs.length === 0 ? (
            <li className="text-sm text-teal-950/60">Sem fontes detalhadas.</li>
          ) : (
            refs.map((r, i) => (
              <li
                key={`${r.kind}-${r.question_id ?? r.id ?? i}`}
                className="rounded-md border border-teal-900/10 px-3 py-2 text-sm"
              >
                <p className="font-semibold text-teal-950">
                  {sourceKindLabel(r.kind)}
                  {r.label ? ` — ${r.label}` : ""}
                </p>
                {r.question_id ? (
                  <p className="text-teal-950/70">Pergunta: {r.question_id}</p>
                ) : null}
                {r.detail ? (
                  <p className="text-teal-950/70">{r.detail}</p>
                ) : null}
              </li>
            ))
          )}
        </ul>
        <button type="button" className="qm-btn-secondary mt-4" onClick={onClose}>
          Fechar
        </button>
      </div>
    </div>
  );
}

function sourceKindLabel(kind: string): string {
  const map: Record<string, string> = {
    question: "Pergunta relacionada",
    guided_answer: "Resposta do Wizard",
    evidence: "Evidência",
    finding: "Constatação",
    maturity_assessment: "Maturidade (pacote)",
    maturity_score: "Maturidade (critério)",
    action_item: "Ação existente",
    wizard_context: "Contexto do Wizard",
  };
  return map[kind] ?? kind;
}

function DismissModal({
  pending,
  onClose,
  onConfirm,
}: {
  pending: boolean;
  onClose: () => void;
  onConfirm: (reason: string) => void;
}) {
  const [reason, setReason] = useState("");
  return (
    <ModalShell title="Descartar sugestão" onClose={onClose} testId="evolution-dismiss-modal">
      <p className="text-sm text-teal-950/75">
        Informe o motivo. A sugestão não entrará no relatório nem poderá ser
        convertida.
      </p>
      <textarea
        className="mt-3 w-full rounded border border-teal-900/20 px-2 py-1.5 text-sm"
        rows={3}
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        data-testid="evolution-dismiss-reason"
      />
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          className="qm-btn-primary"
          disabled={pending || reason.trim().length < 3}
          data-testid="evolution-dismiss-confirm"
          onClick={() => onConfirm(reason.trim())}
        >
          Confirmar descarte
        </button>
        <button type="button" className="qm-btn-secondary" onClick={onClose}>
          Cancelar
        </button>
      </div>
    </ModalShell>
  );
}

function InvestigateModal({
  pending,
  onClose,
  onConfirm,
}: {
  pending: boolean;
  onClose: () => void;
  onConfirm: (missing: string) => void;
}) {
  const [missing, setMissing] = useState("");
  return (
    <ModalShell title="Aprofundar" onClose={onClose} testId="evolution-investigate-modal">
      <p className="text-sm text-teal-950/75">
        Qual informação está faltando para decidir com mais segurança?
      </p>
      <textarea
        className="mt-3 w-full rounded border border-teal-900/20 px-2 py-1.5 text-sm"
        rows={3}
        value={missing}
        onChange={(e) => setMissing(e.target.value)}
        data-testid="evolution-investigate-note"
      />
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          className="qm-btn-primary"
          disabled={pending || missing.trim().length < 3}
          data-testid="evolution-investigate-confirm"
          onClick={() => onConfirm(missing.trim())}
        >
          Marcar para aprofundar
        </button>
        <button type="button" className="qm-btn-secondary" onClick={onClose}>
          Cancelar
        </button>
      </div>
    </ModalShell>
  );
}

function ConvertModal({
  suggestion,
  assessmentStatus,
  teamMembers,
  plans,
  pending,
  openActionsPending,
  onOpenActions,
  onClose,
  onConfirm,
}: {
  suggestion: Suggestion;
  assessmentStatus?: string;
  teamMembers: string[];
  plans: Array<{ id: string; status: string }>;
  pending: boolean;
  openActionsPending: boolean;
  onOpenActions: () => void;
  onClose: () => void;
  onConfirm: (body: {
    action_plan_id?: string | null;
    create_plan_if_missing?: boolean;
    action_kind: "correction" | "corrective_action" | "improvement";
    description: string;
    owner_membership_id: string;
    due_at: string;
    efficacy_required?: boolean | null;
    title?: string | null;
  }) => void;
}) {
  const [title, setTitle] = useState(suggestion.title);
  const [description, setDescription] = useState(
    `${suggestion.suggested_evolution}\n\nBenefício esperado: ${suggestion.expected_benefit}\nPrimeiro passo: ${suggestion.first_step}`,
  );
  const [owner, setOwner] = useState(teamMembers[0] ?? "");
  const [dueLocal, setDueLocal] = useState("");
  const [kind, setKind] = useState<"correction" | "corrective_action" | "improvement">(
    "improvement",
  );
  const [efficacy, setEfficacy] = useState(false);
  const editablePlan = plans.find((p) => p.status === "draft" || p.status === "active");

  if (assessmentStatus === "analysis") {
    return (
      <ModalShell
        title="Abrir fase de ações"
        onClose={onClose}
        testId="evolution-convert-phase-gate"
      >
        <p className="text-sm text-teal-950/75">
          A avaliação ainda está em análise. Para converter sugestões em ações,
          abra explicitamente a fase de ações — isso não acontece em silêncio.
        </p>
        <div className="mt-4 flex gap-2">
          <button
            type="button"
            className="qm-btn-primary"
            disabled={openActionsPending}
            data-testid="evolution-open-actions"
            onClick={onOpenActions}
          >
            Abrir fase de ações
          </button>
          <button type="button" className="qm-btn-secondary" onClick={onClose}>
            Cancelar
          </button>
        </div>
      </ModalShell>
    );
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!owner || !dueLocal || !description.trim()) return;
    onConfirm({
      action_plan_id: editablePlan?.id ?? null,
      create_plan_if_missing: !editablePlan,
      action_kind: kind,
      description: description.trim(),
      owner_membership_id: owner,
      due_at: new Date(dueLocal).toISOString(),
      efficacy_required: efficacy,
      title: title.trim(),
    });
  }

  return (
    <ModalShell
      title="Converter em ação"
      onClose={onClose}
      testId="evolution-convert-modal"
    >
      <p className="text-sm text-teal-950/75">
        Revise o formulário e confirme. A criação do item e a marcação
        “convertida em ação” ocorrem juntas.
      </p>
      <form className="mt-3 space-y-3" onSubmit={handleSubmit}>
        <label className="block text-xs text-teal-950/70">
          Título
          <input
            className="mt-1 w-full rounded border border-teal-900/20 px-2 py-1.5 text-sm"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </label>
        <label className="block text-xs text-teal-950/70">
          Descrição
          <textarea
            className="mt-1 w-full rounded border border-teal-900/20 px-2 py-1.5 text-sm"
            rows={4}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </label>
        <label className="block text-xs text-teal-950/70">
          Tipo
          <select
            className="mt-1 w-full rounded border border-teal-900/20 px-2 py-1.5 text-sm"
            value={kind}
            onChange={(e) => setKind(e.target.value as typeof kind)}
          >
            <option value="improvement">Melhoria</option>
            <option value="corrective_action">Ação corretiva</option>
            <option value="correction">Correção</option>
          </select>
        </label>
        <label className="block text-xs text-teal-950/70">
          Responsável (membership)
          <select
            className="mt-1 w-full rounded border border-teal-900/20 px-2 py-1.5 text-sm"
            value={owner}
            onChange={(e) => setOwner(e.target.value)}
            required
          >
            <option value="">—</option>
            {teamMembers.map((id) => (
              <option key={id} value={id}>
                {id.slice(0, 8)}…
              </option>
            ))}
          </select>
        </label>
        <label className="block text-xs text-teal-950/70">
          Prazo
          <input
            type="datetime-local"
            className="mt-1 w-full rounded border border-teal-900/20 px-2 py-1.5 text-sm"
            value={dueLocal}
            onChange={(e) => setDueLocal(e.target.value)}
            required
          />
        </label>
        <label className="flex items-center gap-2 text-sm text-teal-950/80">
          <input
            type="checkbox"
            checked={efficacy}
            onChange={(e) => setEfficacy(e.target.checked)}
          />
          Exige verificação de eficácia
        </label>
        <p className="text-xs text-teal-950/55">
          Origem: sugestão do Mapa de Evolução (vínculo tipado).
          {!editablePlan
            ? " Um plano de ação em rascunho será criado explicitamente."
            : null}
        </p>
        <div className="flex gap-2">
          <button
            type="submit"
            className="qm-btn-primary"
            disabled={pending}
            data-testid="evolution-convert-confirm"
          >
            Confirmar conversão
          </button>
          <button type="button" className="qm-btn-secondary" onClick={onClose}>
            Cancelar
          </button>
        </div>
      </form>
    </ModalShell>
  );
}

function ModalShell({
  title,
  onClose,
  testId,
  children,
}: {
  title: string;
  onClose: () => void;
  testId: string;
  children: ReactNode;
}) {
  return (
    <div
      className="fixed inset-0 z-40 flex items-end justify-center bg-black/30 p-4 sm:items-center"
      role="dialog"
      aria-modal
      data-testid={testId}
    >
      <div className="w-full max-w-lg rounded-xl bg-white p-5 shadow-xl">
        <div className="flex items-start justify-between gap-3">
          <h3 className="font-display text-xl text-teal-950">{title}</h3>
          <button type="button" className="text-sm text-teal-950/60" onClick={onClose}>
            Fechar
          </button>
        </div>
        <div className="mt-3">{children}</div>
      </div>
    </div>
  );
}
