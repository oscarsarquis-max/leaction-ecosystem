import { useEffect, useMemo, useRef, useState } from "react";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import {
  fetchReportPdfDownloadUrl,
  fetchReportPdfJob,
  useAssessmentReports,
  useBeginAssessmentReport,
  useCloseAssessment,
  useCreateReport,
  useExportReportPdf,
  useRefreshReportSnapshot,
  useReopenAssessment,
  useReportTransition,
  type ReportPdfJob,
} from "@/hooks/useReports";
import { canPublishReport } from "@/lib/permissions";
import { labelWorkflowStatus } from "@/lib/labels";

type ReportRow = {
  id: string;
  version_no: number;
  status: string;
  structured_content?: Record<string, unknown> | null;
  maturity_assessment_id?: string | null;
  supersedes_report_id?: string | null;
  author_membership_id?: string | null;
  published_at?: string | null;
  published_by?: string | null;
  discard_reason?: string | null;
  export_storage_key?: string | null;
  created_at?: string;
  updated_at?: string;
};

type ExportJob = ReportPdfJob;

function snapshotSummary(content: Record<string, unknown> | null | undefined) {
  if (!content) return { findings: 0, hasMaturity: false, hasPlan: false };
  const findings = Array.isArray(content.findings) ? content.findings.length : 0;
  const hasMaturity = content.maturity != null;
  const hasPlan = content.action_plan != null;
  return { findings, hasMaturity: !!hasMaturity, hasPlan: !!hasPlan };
}

export function ReportPanel({
  assessmentId,
  assessmentStatus,
  canElaborate,
  canReview,
  canBeginReport,
  canClose,
  canReopen,
  membershipId,
  roles,
}: {
  assessmentId: string;
  assessmentStatus: string | undefined;
  canElaborate: boolean;
  canReview: boolean;
  canBeginReport: boolean;
  canClose: boolean;
  canReopen: boolean;
  membershipId: string | null;
  roles: readonly string[];
}) {
  const reports = useAssessmentReports(assessmentId);
  const beginReport = useBeginAssessmentReport(assessmentId);
  const createReport = useCreateReport(assessmentId);
  const refresh = useRefreshReportSnapshot(assessmentId);
  const transition = useReportTransition(assessmentId);
  const exportPdf = useExportReportPdf(assessmentId);
  const closeAssessment = useCloseAssessment(assessmentId);
  const reopenAssessment = useReopenAssessment(assessmentId);

  const busyRef = useRef(false);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [includeMaturity, setIncludeMaturity] = useState(true);
  const [includePlan, setIncludePlan] = useState(true);
  const [reason, setReason] = useState("");
  const [waiver, setWaiver] = useState("");
  const [lastJob, setLastJob] = useState<ExportJob | null>(null);
  const [downloadBusy, setDownloadBusy] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const list = (reports.data as ReportRow[] | undefined) ?? [];
  const active =
    list.find((r) => r.id === activeId) ??
    list.find((r) => r.status === "draft" || r.status === "in_review") ??
    list.find((r) => r.status === "published") ??
    list[0] ??
    null;

  useEffect(() => {
    if (!lastJob?.id) return;
    if (lastJob.status === "succeeded" || lastJob.status === "failed") return;
    let cancelled = false;
    const tick = async () => {
      try {
        const next = await fetchReportPdfJob(lastJob.id);
        if (!cancelled) setLastJob(next);
        if (next.status === "succeeded") {
          void reports.refetch();
        }
      } catch {
        /* keep last known status; next poll retries */
      }
    };
    const id = window.setInterval(() => void tick(), 2000);
    void tick();
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [lastJob?.id, lastJob?.status, reports]);

  useEffect(() => {
    if (active && active.id !== activeId) setActiveId(active.id);
  }, [active, activeId]);

  const snap = useMemo(
    () => snapshotSummary(active?.structured_content ?? null),
    [active?.structured_content],
  );

  const isAuthor =
    !!membershipId &&
    !!active?.author_membership_id &&
    membershipId === active.author_membership_id;
  const mayPublish = canPublishReport(
    roles,
    membershipId,
    active?.author_membership_id,
  );

  async function runOnce(fn: () => Promise<unknown>) {
    if (busyRef.current) return;
    busyRef.current = true;
    try {
      await fn();
    } catch {
      // mutation banners
    } finally {
      busyRef.current = false;
    }
  }

  return (
    <section className="space-y-4" data-testid="report-panel">
      <header>
        <h2 className="font-display text-2xl text-teal-950">Relatório</h2>
        <p className="mt-1 text-sm text-teal-950/70">
          Snapshot imutável após submissão · revisão · publicação com SoD · versionamento ·
          exportação PDF assíncrona · fechamento/reabertura da avaliação.
        </p>
      </header>

      {assessmentStatus === "actions" && canBeginReport ? (
        <div
          className="rounded-md border border-amber-300/70 bg-amber-50/90 px-3 py-2 text-sm text-amber-950"
          data-testid="report-begin-phase"
        >
          Avaliação em <span className="font-semibold">ações</span>. Abra a fase de relatório
          para criar snapshots.
          <button
            type="button"
            className="ml-3 rounded-md bg-teal-900 px-3 py-1 text-xs font-semibold text-white disabled:opacity-50"
            disabled={beginReport.isPending}
            data-testid="report-begin"
            onClick={() => void runOnce(() => beginReport.mutateAsync())}
          >
            Abrir fase de relatório
          </button>
        </div>
      ) : null}

      {beginReport.isError ? (
        <ApiErrorBanner title="Erro ao abrir fase de relatório" error={beginReport.error} />
      ) : null}
      {createReport.isError ? (
        <ApiErrorBanner title="Erro ao criar relatório" error={createReport.error} />
      ) : null}
      {refresh.isError ? (
        <ApiErrorBanner title="Erro ao atualizar snapshot" error={refresh.error} />
      ) : null}
      {transition.isError ? (
        <div data-testid="report-transition-error">
          <ApiErrorBanner title="Erro na transição do relatório" error={transition.error} />
        </div>
      ) : null}
      {exportPdf.isError ? (
        <ApiErrorBanner title="Erro ao enfileirar exportação" error={exportPdf.error} />
      ) : null}
      {closeAssessment.isError ? (
        <ApiErrorBanner title="Erro ao fechar avaliação" error={closeAssessment.error} />
      ) : null}
      {reopenAssessment.isError ? (
        <ApiErrorBanner title="Erro ao reabrir avaliação" error={reopenAssessment.error} />
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,14rem)_1fr]">
        <aside className="rounded-lg border border-teal-900/10 bg-white/70 p-3">
          <h3 className="font-display text-lg text-teal-950">Versões</h3>
          {reports.isLoading ? (
            <p className="mt-2 text-sm text-teal-950/60">Carregando…</p>
          ) : reports.isError ? (
            <ApiErrorBanner
              title="Erro ao listar relatórios"
              error={reports.error}
              onRetry={() => void reports.refetch()}
            />
          ) : list.length === 0 ? (
            <p className="mt-2 text-sm text-teal-950/60" data-testid="reports-empty">
              Nenhum relatório.
            </p>
          ) : (
            <ul className="mt-2 space-y-1" data-testid="reports-list">
              {list.map((r) => (
                <li key={r.id}>
                  <button
                    type="button"
                    onClick={() => setActiveId(r.id)}
                    className={`w-full rounded px-2 py-1.5 text-left text-sm ${
                      active?.id === r.id
                        ? "bg-teal-900/10 font-semibold text-teal-950"
                        : "text-teal-950/80 hover:bg-teal-900/5"
                    }`}
                    data-testid={`report-select-${r.id}`}
                  >
                    <span data-testid={`report-version-${r.id}`}>v{r.version_no}</span>
                    {" · "}
                    <span data-testid={`report-status-${r.id}`}>
                      {labelWorkflowStatus(r.status)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}

          {canElaborate &&
          (assessmentStatus === "actions" || assessmentStatus === "report") ? (
            <div className="mt-3 space-y-2 border-t border-teal-900/10 pt-3">
              <label className="flex items-center gap-2 text-xs text-teal-950">
                <input
                  type="checkbox"
                  checked={includeMaturity}
                  onChange={(e) => setIncludeMaturity(e.target.checked)}
                  data-testid="report-include-maturity"
                />
                Incluir maturidade aprovada
              </label>
              <label className="flex items-center gap-2 text-xs text-teal-950">
                <input
                  type="checkbox"
                  checked={includePlan}
                  onChange={(e) => setIncludePlan(e.target.checked)}
                  data-testid="report-include-plan"
                />
                Incluir plano de ação
              </label>
              <button
                type="button"
                className="w-full rounded-md bg-teal-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
                disabled={createReport.isPending}
                data-testid="report-create"
                onClick={() =>
                  void runOnce(async () => {
                    const rep = await createReport.mutateAsync({
                      include_maturity: includeMaturity,
                      include_action_plan: includePlan,
                    });
                    setActiveId(rep.id);
                  })
                }
              >
                Criar rascunho (snapshot)
              </button>
            </div>
          ) : null}
        </aside>

        <div className="space-y-4">
          {!active ? (
            <p className="text-sm text-teal-950/60" data-testid="report-no-active">
              Selecione ou crie um relatório.
            </p>
          ) : (
            <>
              <div
                className="rounded-lg border border-teal-900/10 bg-white/70 px-4 py-3"
                data-testid="report-meta"
              >
                <dl className="grid gap-2 text-sm text-teal-950 sm:grid-cols-2">
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-teal-950/50">Versão</dt>
                    <dd data-testid="report-version">v{active.version_no}</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-teal-950/50">Situação</dt>
                    <dd data-testid="report-status">
                      {labelWorkflowStatus(active.status)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-teal-950/50">Autor</dt>
                    <dd className="font-mono text-xs" data-testid="report-author">
                      {active.author_membership_id ?? "—"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-teal-950/50">
                      Substitui
                    </dt>
                    <dd className="font-mono text-xs" data-testid="report-supersedes">
                      {active.supersedes_report_id ?? "—"}
                    </dd>
                  </div>
                </dl>

                <div
                  className="mt-3 rounded-md border border-teal-900/10 bg-teal-50/40 px-3 py-2 text-sm"
                  data-testid="report-snapshot-summary"
                >
                  Snapshot: {snap.findings} constatação(ões) aprovada(s)
                  {snap.hasMaturity ? " · maturidade" : " · sem maturidade"}
                  {snap.hasPlan ? " · plano de ação" : " · sem plano"}
                  {active.status !== "draft" ? (
                    <span className="ml-2 text-xs font-semibold uppercase tracking-wide text-teal-900">
                      imutável
                    </span>
                  ) : null}
                </div>
              </div>

              {isAuthor && active.status === "in_review" ? (
                <div
                  className="rounded-md border border-amber-400/60 bg-amber-50 px-3 py-2 text-sm text-amber-950"
                  data-testid="report-sod-banner"
                  role="status"
                >
                  Separação de funções (SoD): você é o autor deste relatório e não pode
                  publicá-lo. Peça a um revisor (`org_admin` / `quality_manager`) distinto.
                </div>
              ) : null}

              <div className="flex flex-wrap gap-2">
                {canElaborate && active.status === "draft" ? (
                  <>
                    <button
                      type="button"
                      disabled={refresh.isPending}
                      className="rounded-md border border-teal-900/30 px-3 py-1.5 text-xs font-semibold text-teal-950 disabled:opacity-50"
                      data-testid="report-refresh"
                      onClick={() =>
                        void runOnce(() => refresh.mutateAsync(active.id))
                      }
                    >
                      Atualizar snapshot
                    </button>
                    <button
                      type="button"
                      disabled={transition.isPending}
                      className="rounded-md bg-teal-900 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
                      data-testid="report-submit"
                      onClick={() =>
                        void runOnce(() =>
                          transition.mutateAsync({
                            reportId: active.id,
                            transition: { kind: "submit" },
                          }),
                        )
                      }
                    >
                      Enviar para revisão
                    </button>
                    <button
                      type="button"
                      disabled={transition.isPending}
                      className="rounded-md border border-rose-400/50 px-3 py-1.5 text-xs font-semibold text-rose-900 disabled:opacity-50"
                      data-testid="report-discard"
                      onClick={() =>
                        void runOnce(() =>
                          transition.mutateAsync({
                            reportId: active.id,
                            transition: {
                              kind: "discard",
                              reason: reason.trim() || null,
                            },
                          }),
                        )
                      }
                    >
                      Descartar
                    </button>
                  </>
                ) : null}

                {canReview && active.status === "in_review" ? (
                  <>
                    <button
                      type="button"
                      disabled={transition.isPending || !mayPublish}
                      className="rounded-md bg-teal-900 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
                      data-testid="report-publish"
                      title={
                        !mayPublish
                          ? "SoD ou papel insuficiente — autor não publica"
                          : "Publicar relatório"
                      }
                      onClick={() =>
                        void runOnce(() =>
                          transition.mutateAsync({
                            reportId: active.id,
                            transition: { kind: "publish" },
                          }),
                        )
                      }
                    >
                      Publicar
                    </button>
                    <button
                      type="button"
                      disabled={transition.isPending || !reason.trim()}
                      className="rounded-md border border-amber-400/50 px-3 py-1.5 text-xs font-semibold text-amber-950 disabled:opacity-50"
                      data-testid="report-request-changes"
                      onClick={() =>
                        void runOnce(() =>
                          transition.mutateAsync({
                            reportId: active.id,
                            transition: {
                              kind: "request_changes",
                              reason: reason.trim(),
                            },
                          }),
                        )
                      }
                    >
                      Solicitar alterações
                    </button>
                    <button
                      type="button"
                      disabled={transition.isPending || !reason.trim()}
                      className="rounded-md border border-rose-400/50 px-3 py-1.5 text-xs font-semibold text-rose-900 disabled:opacity-50"
                      data-testid="report-discard-review"
                      onClick={() =>
                        void runOnce(() =>
                          transition.mutateAsync({
                            reportId: active.id,
                            transition: {
                              kind: "discard",
                              reason: reason.trim(),
                            },
                          }),
                        )
                      }
                    >
                      Descartar (revisão)
                    </button>
                  </>
                ) : null}

                {canReview &&
                active.status === "published" &&
                assessmentStatus === "closed" ? (
                  <button
                    type="button"
                    disabled={transition.isPending}
                    className="rounded-md border border-teal-900/30 px-3 py-1.5 text-xs font-semibold text-teal-950 disabled:opacity-50"
                    data-testid="report-archive"
                    onClick={() =>
                      void runOnce(() =>
                        transition.mutateAsync({
                          reportId: active.id,
                          transition: { kind: "archive" },
                        }),
                      )
                    }
                  >
                    Arquivar
                  </button>
                ) : null}

                {["published", "archived", "superseded"].includes(active.status) ? (
                  <button
                    type="button"
                    disabled={exportPdf.isPending}
                    className="rounded-md border border-teal-900/30 px-3 py-1.5 text-xs font-semibold text-teal-950 disabled:opacity-50"
                    data-testid="report-export-pdf"
                    onClick={() =>
                      void runOnce(async () => {
                        const job = await exportPdf.mutateAsync(active.id);
                        setLastJob(job as ExportJob);
                      })
                    }
                  >
                    Exportar PDF (fila)
                  </button>
                ) : null}
              </div>

              {(active.status === "in_review" || active.status === "draft") &&
              (canReview || canElaborate) ? (
                <label className="block text-xs text-teal-950/70">
                  Motivo (alterações / descarte)
                  <input
                    className="mt-1 w-full max-w-md rounded border border-teal-900/20 bg-white px-2 py-1.5 text-sm"
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    data-testid="report-reason"
                  />
                </label>
              ) : null}

              {lastJob ? (
                <div
                  className="rounded-md border border-teal-900/15 bg-white/80 px-3 py-2 text-sm text-teal-950"
                  data-testid="report-export-job"
                  role="status"
                >
                  Exportação PDF: job{" "}
                  <span className="font-mono text-xs">{lastJob.id}</span> · status{" "}
                  <strong data-testid="report-export-status">{lastJob.status}</strong>
                  {lastJob.attempt_count != null ? (
                    <span className="text-xs text-teal-950/60">
                      {" "}
                      · tentativa {lastJob.attempt_count}/{lastJob.max_attempts ?? "?"}
                    </span>
                  ) : null}
                  {lastJob.status === "failed" && lastJob.error_safe_message ? (
                    <span className="mt-1 block text-xs text-qmind-semantic-danger" data-testid="report-export-error">
                      {lastJob.error_safe_message}
                    </span>
                  ) : null}
                  {(lastJob.status === "succeeded" || !!active.export_storage_key) && (
                    <button
                      type="button"
                      className="mt-2 rounded-md bg-teal-900 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
                      data-testid="report-pdf-download"
                      disabled={downloadBusy}
                      onClick={() =>
                        void runOnce(async () => {
                          setDownloadBusy(true);
                          setDownloadError(null);
                          try {
                            const { url } = await fetchReportPdfDownloadUrl(active.id);
                            window.open(url, "_blank", "noopener,noreferrer");
                          } catch (err) {
                            setDownloadError(
                              err instanceof Error ? err.message : "Falha ao obter download",
                            );
                          } finally {
                            setDownloadBusy(false);
                          }
                        })
                      }
                    >
                      Baixar PDF
                    </button>
                  )}
                  {downloadError ? (
                    <span className="mt-1 block text-xs text-qmind-semantic-danger">{downloadError}</span>
                  ) : null}
                </div>
              ) : null}

              {canClose ? (
                <div
                  className="rounded-lg border border-teal-900/10 bg-white/70 p-4"
                  data-testid="assessment-close-box"
                >
                  <h3 className="font-display text-lg text-teal-950">Fechar avaliação</h3>
                  <p className="mt-1 text-xs text-teal-950/70">
                    `report` → `closed`. Normalmente exige relatório publicado; waiver só para
                    QM/admin.
                  </p>
                  <label className="mt-2 block text-xs text-teal-950/70">
                    Dispensa (opcional)
                    <input
                      className="mt-1 w-full rounded border border-teal-900/20 bg-white px-2 py-1.5 text-sm"
                      value={waiver}
                      onChange={(e) => setWaiver(e.target.value)}
                      data-testid="assessment-close-waiver"
                    />
                  </label>
                  <button
                    type="button"
                    className="mt-2 rounded-md bg-teal-900 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
                    disabled={closeAssessment.isPending}
                    data-testid="assessment-close"
                    onClick={() =>
                      void runOnce(() =>
                        closeAssessment.mutateAsync(waiver.trim() || null),
                      )
                    }
                  >
                    Fechar avaliação
                  </button>
                </div>
              ) : null}

              {canReopen ? (
                <div
                  className="rounded-lg border border-teal-900/10 bg-white/70 p-4"
                  data-testid="assessment-reopen-box"
                >
                  <h3 className="font-display text-lg text-teal-950">Reabrir avaliação</h3>
                  <p className="mt-1 text-xs text-teal-950/70">
                    `closed` → `report`. Histórico publicado permanece imutável.
                  </p>
                  <label className="mt-2 block text-xs text-teal-950/70">
                    Motivo (obrigatório)
                    <input
                      className="mt-1 w-full rounded border border-teal-900/20 bg-white px-2 py-1.5 text-sm"
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      data-testid="assessment-reopen-reason"
                    />
                  </label>
                  <button
                    type="button"
                    className="mt-2 rounded-md bg-teal-900 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
                    disabled={reopenAssessment.isPending || !reason.trim()}
                    data-testid="assessment-reopen"
                    onClick={() =>
                      void runOnce(() => reopenAssessment.mutateAsync(reason.trim()))
                    }
                  >
                    Reabrir
                  </button>
                </div>
              ) : null}
            </>
          )}
        </div>
      </div>
    </section>
  );
}
