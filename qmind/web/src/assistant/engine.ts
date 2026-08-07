import { JOURNEY_PHASES, phaseForStatus } from "@/lib/auditJourney";
import { getConsultiveOpening } from "@/lib/guidedNarrative";
import type {
  AssistantContext,
  AssistantEngine,
  AssistantQuickActionId,
  AssistantReply,
  AssistantReplyBlock,
} from "@/assistant/types";

const ANSWER_MEANINGS: { value: string; meaning: string }[] = [
  {
    value: "Sim",
    meaning: "A prática existe de forma consistente e você consegue descrevê-la.",
  },
  {
    value: "Parcialmente",
    meaning: "Existe em parte, em alguns processos, ou ainda está em implantação.",
  },
  {
    value: "Não",
    meaning: "A prática ainda não está estabelecida na organização.",
  },
  {
    value: "Não sei",
    meaning: "Falta informação — útil sinalizar para esclarecer depois, sem inventar.",
  },
  {
    value: "Não aplicável",
    meaning: "A pergunta não se aplica ao escopo; justifique o motivo.",
  },
];

function phaseDef(ctx: AssistantContext) {
  if (!ctx.assessment_status) return null;
  const id = phaseForStatus(ctx.assessment_status, {
    preparationReady: ctx.page !== "wizard",
  });
  return JOURNEY_PHASES.find((p) => p.id === id) ?? null;
}

function isAllowed(ctx: AssistantContext, href: string | undefined): href is string {
  if (!href) return false;
  if (!href.startsWith("/") || href.includes("://")) return false;
  if (href === "/assessments" || href === "/assessments/new") return true;
  if (
    ctx.assessment_id &&
    href.startsWith(`/assessments/${ctx.assessment_id}`)
  ) {
    return true;
  }
  return ctx.allowed_links.some(
    (l) => href === l || href.startsWith(`${l}/`) || l.startsWith(`${href}/`),
  );
}

function nextHref(ctx: AssistantContext): string | undefined {
  const href = ctx.next_action?.href;
  if (!isAllowed(ctx, href)) return undefined;
  if (ctx.next_action?.mutates && !ctx.can_mutate) return undefined;
  return href;
}

function greetingBlocks(ctx: AssistantContext): AssistantReplyBlock[] {
  const lines: string[] = [
    `Você está em ${ctx.organization_name}.`,
  ];
  if (ctx.assessment_label) {
    lines.push(`Avaliação em foco: ${ctx.assessment_label}.`);
  } else if (ctx.page === "org_home") {
    lines.push("Nenhuma avaliação selecionada ainda.");
  }
  if (ctx.phase_label) {
    lines.push(`Fase atual: ${ctx.phase_label}.`);
  }
  lines.push(ctx.stage_explanation);
  if (ctx.next_action) {
    lines.push(`Próxima ação recomendada: ${ctx.next_action.label}.`);
  }
  return lines.map((text) => ({ type: "paragraph" as const, text }));
}

function explainStage(ctx: AssistantContext): AssistantReply {
  if (ctx.page === "wizard" && ctx.wizard) {
    const w = ctx.wizard;
    const blocks: AssistantReplyBlock[] = [
      { type: "paragraph", text: w.explanation || "Esta pergunta ajuda a mapear a prática na organização." },
      {
        type: "paragraph",
        text: `Por que responder: ${w.whyNeeded}`,
      },
    ];
    if (w.practiceExamples.length) {
      blocks.push({
        type: "list",
        items: w.practiceExamples.slice(0, 4).map((e) => `Prática: ${e}`),
      });
    }
    if (w.evidenceExamples.length) {
      blocks.push({
        type: "list",
        items: w.evidenceExamples.slice(0, 4).map((e) => `Evidência possível: ${e}`),
      });
    }
    blocks.push({
      type: "list",
      items: ANSWER_MEANINGS.map((a) => `${a.value}: ${a.meaning}`),
    });
    blocks.push({
      type: "note",
      text: "O assistente não escolhe a resposta por você — descreva a realidade da organização.",
    });
    return { title: w.questionTheme || "Entenda esta pergunta", blocks };
  }

  if (ctx.page === "audit_plan" && ctx.plan) {
    const p = ctx.plan;
    return {
      title: "Plano da Auditoria — o que esta etapa faz",
      blocks: [
        {
          type: "paragraph",
          text: "Objetivo: organizar propósito, processos, pessoas e agenda antes do campo.",
        },
        {
          type: "list",
          items: [
            "Plano pronto (ready): checklist do plano concluído — ainda não inicia o campo.",
            "Planejamento concluído (avaliação planejada): status formal após handoff — libera abertura e início do campo.",
            p.freezeNote,
            p.needsAmendment
              ? "Há emenda: reconfirme o plano antes de avançar."
              : "Sem emenda pendente no momento.",
          ],
        },
        {
          type: "paragraph",
          text: p.readinessNext
            ? `Próximo no checklist: ${p.readinessNext}`
            : "Use o Plano para preparar o campo com previsibilidade.",
        },
      ],
    };
  }

  if (ctx.page === "field_central" && ctx.field) {
    const f = ctx.field;
    return {
      title: "Central de Campo — o que esta etapa faz",
      blocks: [
        {
          type: "paragraph",
          text: "Objetivo: executar o que foi planejado — entrevistas, evidências e pendências do dia.",
        },
        {
          type: "list",
          items: [
            f.currentActivityTitle
              ? `Atividade em foco: ${f.currentActivityTitle}`
              : "Nenhuma atividade em foco agora.",
            `Evidências antecipadas disponíveis: ${f.earlyEvidenceCount}`,
            `Evidências pendentes/em verificação: ${f.pendingEvidenceCount}`,
            f.closingPrepShow
              ? "É momento de preparar o encerramento do campo."
              : "Encerramento ainda não é o foco principal.",
          ],
        },
        {
          type: "note",
          text: "Arquivo anexado não é conformidade automática.",
        },
      ],
    };
  }

  const phase = phaseDef(ctx);
  if (phase) {
    return {
      title: `${phase.label} — o que esta etapa faz`,
      blocks: [
        { type: "paragraph", text: `Objetivo: ${phase.objective}` },
        { type: "list", items: phase.activities.map((a) => a) },
        {
          type: "paragraph",
          text: `Resultado esperado: ${phase.expectedResult}`,
        },
        {
          type: "paragraph",
          text: `Para avançar: ${phase.advanceCriteria}`,
        },
      ],
    };
  }

  return {
    title: ctx.stage_title || "Esta etapa",
    blocks: [
      { type: "paragraph", text: ctx.stage_explanation },
      ...(ctx.progress_summary
        ? [{ type: "paragraph" as const, text: `Progresso: ${ctx.progress_summary}` }]
        : []),
    ],
  };
}

function whatNow(ctx: AssistantContext): AssistantReply {
  if (!ctx.assessment_id && ctx.page === "org_home") {
    const href = ctx.can_mutate ? "/assessments/new" : undefined;
    const blocks: AssistantReplyBlock[] = [
      {
        type: "paragraph",
        text: ctx.can_mutate
          ? "Crie uma avaliação ou abra uma existente na lista."
          : "Abra uma avaliação existente na lista (seu papel é somente leitura).",
      },
    ];
    if (href && isAllowed(ctx, href)) {
      blocks.push({ type: "link", label: "Nova avaliação", href });
    }
    return {
      title: "O que fazer agora",
      blocks,
      navigateHref: href && isAllowed(ctx, href) ? href : nextHref(ctx),
    };
  }

  const action = ctx.next_action;
  if (!action) {
    return {
      title: "O que fazer agora",
      blocks: [
        {
          type: "paragraph",
          text: "Não há uma ação prioritária calculada neste momento. Revise o mapa da avaliação.",
        },
      ],
    };
  }

  const blocks: AssistantReplyBlock[] = [
    { type: "paragraph", text: action.label },
    { type: "paragraph", text: action.hint },
  ];

  if (action.mutates && !ctx.can_mutate) {
    blocks.push({
      type: "note",
      text: "Seu papel não permite alterar esta avaliação — você pode acompanhar e navegar nas telas permitidas.",
    });
    return { title: "O que fazer agora", blocks };
  }

  const href = nextHref(ctx);
  if (href) {
    blocks.push({ type: "link", label: action.label, href });
  }

  return { title: "O que fazer agora", blocks, navigateHref: href };
}

function whatPending(ctx: AssistantContext): AssistantReply {
  if (ctx.blockers.length === 0 && ctx.pendencies.length === 0) {
    return {
      title: "Pendências",
      blocks: [
        {
          type: "paragraph",
          text: "Nenhuma pendência acionável registrada neste contexto.",
        },
      ],
    };
  }

  const blocks: AssistantReplyBlock[] = [];
  if (ctx.blockers.length) {
    blocks.push({
      type: "list",
      items: ctx.blockers.slice(0, 5).map((b) => `Bloqueio: ${b}`),
    });
  }
  for (const p of ctx.pendencies.slice(0, 6)) {
    blocks.push({
      type: "paragraph",
      text: `${p.problem} — ${p.impact}`,
    });
    if (p.href && isAllowed(ctx, p.href)) {
      blocks.push({ type: "link", label: p.actionLabel, href: p.href });
    } else {
      blocks.push({
        type: "note",
        text: `Ação sugerida: ${p.actionLabel}`,
      });
    }
  }
  return { title: "O que está pendente", blocks };
}

function whyImportant(ctx: AssistantContext): AssistantReply {
  if (ctx.page === "wizard" && ctx.wizard) {
    const opening = getConsultiveOpening(
      // theme often carries clause; fallback to generic
      ctx.wizard.questionTheme.match(/\b([4-9]|10)\b/)?.[1] ?? "",
    );
    return {
      title: "Por que isso é importante",
      blocks: [
        {
          type: "paragraph",
          text: ctx.wizard.whyNeeded,
        },
        ...(opening
          ? [
              {
                type: "paragraph" as const,
                text: opening.whyItMatters,
              },
              {
                type: "list" as const,
                items: opening.expectedBenefits.slice(0, 3),
              },
              {
                type: "paragraph" as const,
                text: `Ajuda a evitar: ${opening.problemsAvoided.slice(0, 2).join("; ")}`,
              },
            ]
          : []),
        {
          type: "note",
          text: "Responder com precisão melhora o plano e reduz improvisação no campo — sem prometer conformidade.",
        },
      ],
    };
  }

  if (ctx.page === "audit_plan") {
    return {
      title: "Por que o Plano importa",
      blocks: [
        {
          type: "paragraph",
          text: "Um plano claro reduz entrevistas improvisadas, alinha expectativas e protege o tempo da equipe.",
        },
        {
          type: "list",
          items: [
            "Benefício: todos sabem o que acontece e quando.",
            "Evita: campo sem abertura, escopo confuso e retrabalho.",
          ],
        },
      ],
    };
  }

  if (ctx.page === "field_central") {
    return {
      title: "Por que a Central de Campo importa",
      blocks: [
        {
          type: "paragraph",
          text: "É aqui que a avaliação vira evidência factual — base para constatações e decisões.",
        },
        {
          type: "list",
          items: [
            "Benefício: registro rastreável do que foi ouvido e visto.",
            "Evita: lacunas de cobertura e encerramento sem preparação.",
          ],
        },
        {
          type: "note",
          text: "Nenhuma evidência sozinha garante conformidade.",
        },
      ],
    };
  }

  const phase = phaseDef(ctx);
  return {
    title: "Por que esta etapa importa",
    blocks: [
      {
        type: "paragraph",
        text:
          phase?.objective ||
          "Cada etapa reduz risco e aumenta clareza para a liderança.",
      },
      {
        type: "paragraph",
        text: phase
          ? `Resultado esperado: ${phase.expectedResult}`
          : "Seguir a ordem do percurso evita pular etapas críticas.",
      },
      {
        type: "note",
        text: "O QMind orienta o trabalho — não certifica nem julga conformidade automaticamente.",
      },
    ],
  };
}

function goNext(ctx: AssistantContext): AssistantReply {
  const href = nextHref(ctx);
  if (!href) {
    return {
      title: "Próximo passo",
      blocks: [
        {
          type: "paragraph",
          text: ctx.next_action
            ? `${ctx.next_action.label}. ${ctx.next_action.hint}`
            : "Não há um destino permitido calculado agora.",
        },
        {
          type: "note",
          text: "O assistente não executa alterações por você — apenas orienta e navega em links permitidos.",
        },
      ],
    };
  }
  return {
    title: "Próximo passo",
    blocks: [
      {
        type: "paragraph",
        text: ctx.next_action?.hint || "Vamos à próxima ação recomendada.",
      },
      { type: "link", label: ctx.next_action?.label || "Continuar", href },
      {
        type: "note",
        text: "Navegação apenas — nenhuma mutação automática.",
      },
    ],
    navigateHref: href,
  };
}

export class DeterministicAssistantEngine implements AssistantEngine {
  answer(action: AssistantQuickActionId, ctx: AssistantContext): AssistantReply {
    switch (action) {
      case "explain_stage":
        return explainStage(ctx);
      case "what_now":
        return whatNow(ctx);
      case "what_pending":
        return whatPending(ctx);
      case "why_important":
        return whyImportant(ctx);
      case "go_next":
        return goNext(ctx);
      default:
        return {
          title: "Assistente QMind",
          blocks: [{ type: "paragraph", text: "Escolha uma das ações rápidas." }],
        };
    }
  }

  /** Saudação do painel (não é chat livre). */
  greeting(ctx: AssistantContext): AssistantReply {
    return {
      title: "Assistente QMind",
      blocks: [
        {
          type: "paragraph",
          text: "Estou aqui para orientar você em cada etapa da avaliação.",
        },
        ...greetingBlocks(ctx),
      ],
    };
  }
}

export const defaultAssistantEngine = new DeterministicAssistantEngine();
