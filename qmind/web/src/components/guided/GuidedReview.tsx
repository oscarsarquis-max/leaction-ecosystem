import type { ReactNode } from "react";
import {
  ANSWER_OPTIONS,
  GUIDED_STEPS,
  type GuidedQuestion,
  type GuidedSession,
} from "@/api/guidedTypes";

type Props = {
  session: GuidedSession;
  questions: GuidedQuestion[];
};

function labelAnswer(value: string | null | undefined): string {
  if (!value) return "Sem resposta";
  return ANSWER_OPTIONS.find((o) => o.value === value)?.label ?? value;
}

export function GuidedReview({ session, questions }: Props) {
  const ctx = session.context;
  const byId = new Map(session.answers.map((a) => [a.question_id, a]));

  return (
    <div className="space-y-8" data-testid="guided-review">
      <p className="text-base text-[var(--qm-muted)]">
        Resumo do que foi registrado. Nada aqui gera automaticamente conformidade
        ou não conformidade — qualquer conclusão fica pendente de revisão humana.
      </p>

      <Section title="Organização">
        <Row label="Nome" value={ctx.organization_profile.trade_name} />
        <Row label="Resumo" value={ctx.organization_profile.summary} />
        <Row label="Porte" value={ctx.organization_profile.size_band} />
      </Section>

      <Section title="Escopo do SGQ">
        <Row label="Escopo" value={ctx.qms_scope.description} />
        <Row label="Exclusões" value={ctx.qms_scope.exclusions} />
        <Row label="Justificativa" value={ctx.qms_scope.exclusion_justification} />
      </Section>

      <ListSection
        title="Produtos e serviços"
        items={ctx.products_services.map((p) => p.name || "(sem nome)")}
      />
      <ListSection
        title="Unidades e locais"
        items={ctx.sites.map((s) => s.name || "(sem nome)")}
      />
      <ListSection
        title="Processos"
        items={ctx.processes.map((p) => p.name || "(sem nome)")}
      />
      <ListSection
        title="Partes interessadas"
        items={ctx.stakeholders.map((s) => s.name || "(sem nome)")}
      />

      <Section title="Roteiro orientado">
        <p className="mb-3 text-sm text-[var(--qm-muted)]">
          {session.answered_count} de {session.question_count} perguntas com
          resposta
        </p>
        <ul className="space-y-4">
          {questions.map((q) => {
            const a = byId.get(q.id);
            return (
              <li key={q.id} className="border-b border-[var(--qm-line)] pb-3">
                <p className="text-sm font-semibold text-[var(--qm-ink)]">
                  {q.question}
                </p>
                <p className="mt-1 text-sm text-[var(--qm-muted)]">
                  Resposta: {labelAnswer(a?.answer_value)}
                  {a?.provide_later ? " · evidência depois" : null}
                  {a?.evidence_ids?.length
                    ? ` · ${a.evidence_ids.length} evidência(s)`
                    : null}
                </p>
              </li>
            );
          })}
        </ul>
      </Section>

      <p className="text-xs text-[var(--qm-muted)]">
        Etapas: {GUIDED_STEPS.map((s) => s.label).join(" · ")}
      </p>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section>
      <h3 className="font-display text-xl text-[var(--qm-ink)]">{title}</h3>
      <div className="mt-3 space-y-2">{children}</div>
    </section>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <p className="text-sm text-[var(--qm-muted)]">
      <span className="font-semibold text-[var(--qm-ink)]">{label}: </span>
      {value?.trim() ? value : "—"}
    </p>
  );
}

function ListSection({ title, items }: { title: string; items: string[] }) {
  return (
    <Section title={title}>
      {items.length === 0 ? (
        <p className="text-sm text-[var(--qm-muted)]">Nenhum item informado.</p>
      ) : (
        <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--qm-muted)]">
          {items.map((item, i) => (
            <li key={`${item}-${i}`}>{item}</li>
          ))}
        </ul>
      )}
    </Section>
  );
}
