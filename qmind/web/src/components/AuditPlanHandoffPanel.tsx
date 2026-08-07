import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  useConcludeAuditPlanning,
  useMarkAuditPlanReady,
  useStartAuditFieldExecution,
} from "@/hooks/useAuditPlan";
import type { AuditPlan } from "@/api/auditPlanTypes";

type DialogKind =
  | null
  | "conclude_plan"
  | "conclude_planning"
  | "reconfirm"
  | "start_field";

function Explain({
  title,
  happens,
  locks,
  canChange,
  fixLater,
  next,
}: {
  title: string;
  happens: string;
  locks: string;
  canChange: string;
  fixLater: string;
  next: string;
}) {
  return (
    <div
      className="mt-3 space-y-2 rounded-md border border-amber-300/70 bg-amber-50/90 p-4 text-sm text-amber-950"
      role="dialog"
      aria-labelledby="handoff-dialog-title"
    >
      <h3 id="handoff-dialog-title" className="font-semibold">
        {title}
      </h3>
      <ul className="space-y-1.5 text-amber-950/90">
        <li>
          <span className="font-semibold">O que acontecerá: </span>
          {happens}
        </li>
        <li>
          <span className="font-semibold">O que ficará bloqueado: </span>
          {locks}
        </li>
        <li>
          <span className="font-semibold">O que ainda poderá alterar: </span>
          {canChange}
        </li>
        <li>
          <span className="font-semibold">Como corrigir depois: </span>
          {fixLater}
        </li>
        <li>
          <span className="font-semibold">Próxima etapa: </span>
          {next}
        </li>
      </ul>
    </div>
  );
}

/**
 * Ações governadas do handoff Planejamento → Campo (único caminho principal).
 */
export function AuditPlanHandoffPanel({
  assessmentId,
  plan,
  assessmentStatus,
  canMutate,
  openingSatisfied,
  onError,
  onPlanUpdated,
}: {
  assessmentId: string;
  plan: AuditPlan;
  assessmentStatus: string | undefined;
  canMutate: boolean;
  openingSatisfied: boolean;
  onError: (err: unknown) => void;
  onPlanUpdated: (plan: AuditPlan) => void;
}) {
  const navigate = useNavigate();
  const markReady = useMarkAuditPlanReady(assessmentId);
  const conclude = useConcludeAuditPlanning(assessmentId);
  const startField = useStartAuditFieldExecution(assessmentId);
  const [dialog, setDialog] = useState<DialogKind>(null);
  const [info, setInfo] = useState<string | null>(null);

  const status = assessmentStatus ?? "draft";
  const planStatus = plan.plan_status;
  const checklistReady = plan.readiness.ready;
  const busy =
    markReady.isPending || conclude.isPending || startField.isPending;

  const showConcludePlan =
    canMutate &&
    checklistReady &&
    (planStatus === "draft" || planStatus === "amended") &&
    (status === "draft" || status === "planned");

  const showConcludePlanning =
    canMutate && status === "draft" && planStatus === "ready";

  const showStartField =
    canMutate &&
    status === "planned" &&
    planStatus === "ready" &&
    openingSatisfied;

  const showStartBlocked =
    canMutate &&
    status === "planned" &&
    (planStatus === "amended" || !openingSatisfied || planStatus !== "ready");

  async function runConcludePlan() {
    try {
      const saved = await markReady.mutateAsync(plan.updated_at);
      onPlanUpdated(saved);
      setDialog(null);
      setInfo(
        "O plano está completo e pronto para ser formalizado. A próxima etapa confirmará o planejamento da avaliação.",
      );
    } catch (err) {
      onError(err);
    }
  }

  async function runConcludePlanning() {
    try {
      const out = await conclude.mutateAsync({
        expected_updated_at: plan.updated_at,
        mark_ready_if_needed: false,
      });
      onPlanUpdated(out.plan);
      setDialog(null);
      setInfo(
        out.message ||
          "Planejamento concluído. A avaliação está planejada; registre a reunião de abertura e inicie o campo quando estiver pronto.",
      );
    } catch (err) {
      onError(err);
    }
  }

  async function runStartField() {
    try {
      const out = await startField.mutateAsync();
      setDialog(null);
      void navigate(out.redirect_href || `/assessments/${assessmentId}/work`);
    } catch (err) {
      onError(err);
    }
  }

  if (!canMutate && status !== "in_progress") {
    return (
      <p className="text-sm text-[var(--qm-muted)]">
        Seu papel é somente leitura — as ações de handoff ficam com quem pode
        editar o plano.
      </p>
    );
  }

  return (
    <section
      className="space-y-3 rounded-md border border-[var(--qm-line)] bg-[var(--qm-surface)] px-4 py-4"
      data-testid="audit-plan-handoff"
    >
      <div>
        <h3 className="font-display text-lg text-[var(--qm-ink)]">
          Encaminhamento do plano
        </h3>
        <p className="mt-1 text-sm text-[var(--qm-muted)]">
          Cada ação tem um efeito claro. Leia o que muda antes de confirmar.
        </p>
      </div>

      {info ? (
        <p
          className="rounded-md border border-qmind-semantic-success/30 bg-qmind-semantic-success/10 px-3 py-2 text-sm"
          data-testid="audit-plan-handoff-info"
        >
          {info}
        </p>
      ) : null}

      {planStatus === "amended" ? (
        <p
          className="rounded-md border border-amber-300/60 bg-amber-50 px-3 py-2 text-sm"
          data-testid="audit-plan-amendment-banner"
        >
          Há uma emenda pendente. O início do campo fica bloqueado até você
          revisar e reconfirmar o plano com «Concluir Plano».
        </p>
      ) : null}

      <div className="flex flex-wrap gap-2">
        {showConcludePlan ? (
          <button
            type="button"
            className="qm-btn-primary"
            disabled={busy}
            data-testid="handoff-conclude-plan"
            onClick={() =>
              setDialog(planStatus === "amended" ? "reconfirm" : "conclude_plan")
            }
          >
            {planStatus === "amended" ? "Revisar e reconfirmar plano" : "Concluir Plano"}
          </button>
        ) : null}

        {showConcludePlanning ? (
          <button
            type="button"
            className="qm-btn-primary"
            disabled={busy}
            data-testid="handoff-conclude-planning"
            onClick={() => setDialog("conclude_planning")}
          >
            Concluir planejamento
          </button>
        ) : null}

        {showStartField ? (
          <button
            type="button"
            className="qm-btn-primary"
            disabled={busy}
            data-testid="handoff-start-field"
            onClick={() => setDialog("start_field")}
          >
            Iniciar execução em campo
          </button>
        ) : null}
      </div>

      {showStartBlocked && !showStartField ? (
        <p className="text-sm text-[var(--qm-muted)]" data-testid="handoff-start-blocked">
          {planStatus === "amended"
            ? "Início bloqueado: reconfirme o plano após a emenda."
            : !openingSatisfied
              ? "Início bloqueado: registre a reunião de abertura como realizada ou dispense-a com justificativa."
              : "Início bloqueado: o plano precisa estar pronto."}
        </p>
      ) : null}

      {dialog === "conclude_plan" || dialog === "reconfirm" ? (
        <Explain
          title={
            dialog === "reconfirm"
              ? "Revisar e reconfirmar o plano?"
              : "Concluir Plano?"
          }
          happens={
            dialog === "reconfirm"
              ? "O plano volta para «pronto» após a emenda. A avaliação permanece planejada."
              : "O checklist é validado e o plano passa a «pronto». A avaliação ainda não muda de estado."
          }
          locks="Nada da avaliação é congelado ainda — só o status do plano."
          canChange="Você ainda pode ajustar o plano (com motivo se já estiver planejada)."
          fixLater="Se precisar mudar depois, edite com motivo de emenda e reconfirme."
          next="Concluir planejamento (formaliza a avaliação como planejada)."
        />
      ) : null}

      {dialog === "conclude_planning" ? (
        <Explain
          title="Concluir planejamento?"
          happens="A avaliação passa de rascunho para planejada. Escopo e equipe oficiais são congelados conforme o domínio."
          locks="Escopo e equipe da avaliação ficam imutáveis; alterações relevantes no plano exigirão emenda com motivo."
          canChange="Programação, reuniões e detalhes operacionais do plano (com emenda quando necessário)."
          fixLater="Emenda com motivo + reconfirmação do plano; reabertura controlada só em casos excepcionais."
          next="Registrar reunião de abertura e, em seguida, iniciar a execução em campo."
        />
      ) : null}

      {dialog === "start_field" ? (
        <Explain
          title="Iniciar execução em campo?"
          happens="A avaliação passa de planejada para em execução. A fase atual vira Execução em campo."
          locks="Você não volta ao rascunho sem fluxo de reabertura. Emendas no plano bloqueiam novo início até reconfirmação."
          canChange="Entrevistas, evidências e registros de campo."
          fixLater="Ajuste programação e registre ocorrências; emendas estruturais exigem motivo e reconfirmação."
          next="Abrir a Central de Campo para coletar entrevistas e evidências."
        />
      ) : null}

      {dialog ? (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="qm-btn-primary"
            disabled={busy}
            data-testid="handoff-confirm"
            onClick={() => {
              if (dialog === "conclude_plan" || dialog === "reconfirm") {
                void runConcludePlan();
              } else if (dialog === "conclude_planning") {
                void runConcludePlanning();
              } else {
                void runStartField();
              }
            }}
          >
            {busy
              ? "Processando…"
              : dialog === "conclude_plan"
                ? "Concluir Plano"
                : dialog === "reconfirm"
                  ? "Revisar e reconfirmar plano"
                  : dialog === "conclude_planning"
                    ? "Concluir planejamento"
                    : "Iniciar execução em campo"}
          </button>
          <button
            type="button"
            className="qm-btn-secondary"
            disabled={busy}
            onClick={() => setDialog(null)}
          >
            Cancelar
          </button>
        </div>
      ) : null}
    </section>
  );
}
