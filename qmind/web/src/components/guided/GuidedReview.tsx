import type { ReactNode } from "react";
import {
  ANSWER_OPTIONS,
  GUIDED_STEPS,
  type AnswerValue,
  type GuidedAnswer,
  type GuidedClauseGroup,
  type GuidedQuestion,
  type GuidedSession,
} from "@/api/guidedTypes";
import {
  clauseMajor,
  groupQuestionsByClause,
} from "@/lib/guidedShowWhen";

type Props = {
  session: GuidedSession;
  questions: GuidedQuestion[];
  clauseGroups?: GuidedClauseGroup[];
};

function labelAnswer(value: string | null | undefined): string {
  if (!value) return "ainda sem resposta";
  return ANSWER_OPTIONS.find((o) => o.value === value)?.label ?? value;
}

function toneFor(value: AnswerValue | null | undefined): string {
  switch (value) {
    case "yes":
      return "prático e presente";
    case "partial":
      return "parcial ou em evolução";
    case "no":
      return "ainda não estabelecido";
    case "unknown":
      return "ainda sem clareza para a equipe";
    case "not_applicable":
      return "considerado não aplicável neste contexto";
    default:
      return "pendente de resposta";
  }
}

function narrativeForGroup(
  label: string,
  groupQuestions: GuidedQuestion[],
  byId: Map<string, GuidedAnswer>,
): string {
  const answered = groupQuestions
    .map((q) => ({ q, a: byId.get(q.id) }))
    .filter((x) => x.a?.answer_value);

  if (answered.length === 0) {
    return `Sobre ${label.toLowerCase()}, ainda não há respostas suficientes para uma leitura.`;
  }

  const yes = answered.filter((x) => x.a?.answer_value === "yes").length;
  const partial = answered.filter((x) => x.a?.answer_value === "partial").length;
  const no = answered.filter((x) => x.a?.answer_value === "no").length;
  const unknown = answered.filter((x) => x.a?.answer_value === "unknown").length;
  const na = answered.filter(
    (x) => x.a?.answer_value === "not_applicable",
  ).length;

  const parts: string[] = [];
  if (yes > 0) {
    parts.push(
      `${yes} ponto(s) descritos como já praticados`,
    );
  }
  if (partial > 0) {
    parts.push(`${partial} em evolução ou parcial(is)`);
  }
  if (no > 0) {
    parts.push(`${no} ainda sem prática estabelecida`);
  }
  if (unknown > 0) {
    parts.push(`${unknown} sem clareza no momento`);
  }
  if (na > 0) {
    parts.push(`${na} marcado(s) como não aplicável`);
  }

  const highlight = answered.find(
    (x) =>
      x.a?.answer_value === "no" ||
      x.a?.answer_value === "partial" ||
      x.a?.answer_value === "unknown",
  );
  const strength = answered.find((x) => x.a?.answer_value === "yes");

  let reading = `Em ${label.toLowerCase()}, a leitura atual aponta: ${parts.join("; ")}.`;
  if (strength) {
    reading += ` Um ponto de apoio citado: “${strength.q.theme}” parece ${toneFor(strength.a?.answer_value)}.`;
  }
  if (highlight) {
    reading += ` Atenção especial a “${highlight.q.theme}”: ${toneFor(highlight.a?.answer_value)}.`;
    if (highlight.a?.description?.trim()) {
      reading += ` Observação registrada: ${highlight.a.description.trim()}`;
    }
  }
  return reading;
}

export function GuidedReview({ session, questions, clauseGroups }: Props) {
  const ctx = session.context;
  const byId = new Map(session.answers.map((a) => [a.question_id, a]));
  const groups = groupQuestionsByClause(questions);
  const groupLabel = (major: string) =>
    clauseGroups?.find((g) => g.id === major)?.label ?? `Cláusula ${major}`;

  return (
    <div className="space-y-8" data-testid="guided-review">
      <p className="text-base text-[var(--qm-muted)]">
        Leitura do que você informou — como um consultor organizaria o retorno
        inicial. Nada aqui gera automaticamente conformidade ou não conformidade;
        qualquer conclusão técnica fica para revisão humana.
      </p>

      <Section title="Retrato da organização">
        <Row label="Nome" value={ctx.organization_profile.trade_name} />
        <Row label="Resumo" value={ctx.organization_profile.summary} />
        <Row label="Porte" value={ctx.organization_profile.size_band} />
        <Row label="Escopo do SGQ" value={ctx.qms_scope.description} />
        <Row label="Exclusões" value={ctx.qms_scope.exclusions} />
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

      <Section title="Leitura por cláusula">
        <p className="mb-4 text-sm text-[var(--qm-muted)]">
          {session.answered_count} de {session.question_count} perguntas
          aplicáveis com resposta
          {questions.length !== session.question_count
            ? ` · ${questions.length} visíveis nesta sessão`
            : ""}
        </p>
        <ul className="space-y-5" data-testid="guided-clause-summary">
          {groups.map(({ major, questions: gq }) => (
            <li
              key={major}
              className="rounded-qmind border border-[var(--qm-line)] bg-[var(--qm-app)]/40 p-4"
            >
              <p className="text-sm font-semibold text-[var(--qm-ink)]">
                Cláusula {major} — {groupLabel(major)}
              </p>
              <p className="mt-2 text-sm leading-relaxed text-[var(--qm-muted)]">
                {narrativeForGroup(groupLabel(major), gq, byId)}
              </p>
              <details className="mt-3">
                <summary className="cursor-pointer text-xs font-semibold text-[var(--qm-ink)]">
                  Ver respostas desta cláusula
                </summary>
                <ul className="mt-3 space-y-3">
                  {gq.map((q) => {
                    const a = byId.get(q.id);
                    return (
                      <li key={q.id} className="border-t border-[var(--qm-line)] pt-2">
                        <p className="text-sm font-medium text-[var(--qm-ink)]">
                          {q.question}
                        </p>
                        <p className="mt-1 text-sm text-[var(--qm-muted)]">
                          Resposta: {labelAnswer(a?.answer_value)}
                          {a?.provide_later ? " · evidência depois" : null}
                          {a?.evidence_ids?.length
                            ? ` · ${a.evidence_ids.length} evidência(s)`
                            : null}
                        </p>
                        {a?.description?.trim() ? (
                          <p className="mt-1 text-sm text-[var(--qm-muted)]">
                            Detalhe: {a.description.trim()}
                          </p>
                        ) : null}
                      </li>
                    );
                  })}
                </ul>
              </details>
            </li>
          ))}
        </ul>
      </Section>

      <p className="text-xs text-[var(--qm-muted)]">
        Etapas: {GUIDED_STEPS.map((s) => s.label).join(" · ")}
        {" · "}
        Referências tocadas:{" "}
        {[...new Set(questions.map((q) => clauseMajor(q.clause_ref)))]
          .sort((a, b) => Number(a) - Number(b))
          .join(", ")}
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
