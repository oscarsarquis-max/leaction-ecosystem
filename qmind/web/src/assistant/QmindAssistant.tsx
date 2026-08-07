import { useEffect, useId, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAssistant } from "@/assistant/AssistantProvider";
import type {
  AssistantQuickActionId,
  AssistantReply,
  AssistantReplyBlock,
} from "@/assistant/types";

const QUICK_ACTIONS: { id: AssistantQuickActionId; label: string }[] = [
  { id: "explain_stage", label: "Explique esta etapa" },
  { id: "what_now", label: "O que preciso fazer agora?" },
  { id: "what_pending", label: "O que está pendente?" },
  { id: "why_important", label: "Por que isso é importante?" },
  { id: "go_next", label: "Leve-me ao próximo passo" },
];

function ReplyBlocks({
  blocks,
  onNavigate,
}: {
  blocks: AssistantReplyBlock[];
  onNavigate: (href: string) => void;
}) {
  return (
    <div className="space-y-3 text-sm text-[var(--qm-ink)]">
      {blocks.map((b, i) => {
        if (b.type === "paragraph") {
          return (
            <p key={i} className="leading-relaxed text-[var(--qm-muted)]">
              {b.text}
            </p>
          );
        }
        if (b.type === "list") {
          return (
            <ul key={i} className="list-disc space-y-1 pl-5 text-[var(--qm-muted)]">
              {b.items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          );
        }
        if (b.type === "note") {
          return (
            <p
              key={i}
              className="rounded border border-[var(--qm-line)] bg-[var(--qm-surface-soft)] px-3 py-2 text-xs text-[var(--qm-muted)]"
            >
              {b.text}
            </p>
          );
        }
        return (
          <button
            key={i}
            type="button"
            className="qm-btn-primary text-sm"
            onClick={() => onNavigate(b.href)}
          >
            {b.label}
          </button>
        );
      })}
    </div>
  );
}

function isSafeHref(
  href: string,
  assessmentId: string | null,
  allowed: string[],
): boolean {
  if (!href.startsWith("/") || href.includes("://")) return false;
  if (href === "/assessments" || href === "/assessments/new") return true;
  if (assessmentId && href.startsWith(`/assessments/${assessmentId}`)) return true;
  return allowed.some((l) => href === l || href.startsWith(`${l}/`));
}

/**
 * Assistente QMind — orientação determinística (sem IA generativa nesta versão).
 * Fixo no canto inferior direito; painel lateral ao abrir.
 */
export function QmindAssistant() {
  const {
    context,
    open,
    setOpen,
    ask,
    greeting,
    reply,
    lastQuickAction,
    hasAttention,
  } = useAssistant();
  const navigate = useNavigate();
  const titleId = useId();
  const openBtnRef = useRef<HTMLButtonElement>(null);
  const closeBtnRef = useRef<HTMLButtonElement>(null);
  const greetedFocus = useRef(false);

  useEffect(() => {
    if (!open) {
      greetedFocus.current = false;
      return;
    }
    // Saudação acompanha o contexto da página enquanto não houver ação rápida.
    if (!lastQuickAction) {
      greeting();
    }
    if (!greetedFocus.current) {
      closeBtnRef.current?.focus();
      greetedFocus.current = true;
    }
  }, [open, context, lastQuickAction, greeting]);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        setOpen(false);
        openBtnRef.current?.focus();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, setOpen]);

  function go(href: string) {
    if (!isSafeHref(href, context.assessment_id, context.allowed_links)) return;
    setOpen(false);
    void navigate(href);
  }

  function onQuick(id: AssistantQuickActionId) {
    const out: AssistantReply = ask(id);
    if (id === "go_next" && out.navigateHref) {
      go(out.navigateHref);
    }
  }

  return (
    <>
      <button
        ref={openBtnRef}
        type="button"
        className="fixed bottom-4 right-4 z-40 flex items-center gap-2 rounded-full border border-[var(--qm-line)] bg-[var(--qm-surface)] px-3 py-2.5 shadow-md hover:border-[var(--qm-ink)]/30 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--qm-focus)] sm:bottom-6 sm:right-6"
        style={{ marginBottom: "env(safe-area-inset-bottom, 0)" }}
        aria-label={
          open
            ? "Fechar Assistente QMind"
            : hasAttention
              ? "Abrir Assistente QMind — há orientação importante"
              : "Abrir Assistente QMind"
        }
        aria-expanded={open}
        aria-controls="qmind-assistant-panel"
        data-testid="qmind-assistant-open"
        onClick={() => setOpen(!open)}
      >
        <span
          className="relative flex h-9 w-9 items-center justify-center rounded-full bg-[var(--qm-ink)] text-sm font-semibold text-[var(--qm-surface)]"
          aria-hidden
        >
          Q
          {hasAttention ? (
            <span
              className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full bg-amber-500 ring-2 ring-[var(--qm-surface)]"
              data-testid="qmind-assistant-attention"
            />
          ) : null}
        </span>
        <span className="hidden pr-1 text-sm font-semibold text-[var(--qm-ink)] sm:inline">
          Assistente
        </span>
      </button>

      {open ? (
        <>
          <div
            className="fixed inset-0 z-40 bg-[var(--qm-ink)]/25 sm:bg-[var(--qm-ink)]/10"
            aria-hidden
            onClick={() => setOpen(false)}
          />
          <div
            id="qmind-assistant-panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            data-testid="qmind-assistant-panel"
            className="fixed bottom-0 right-0 z-50 flex h-[min(100dvh,36rem)] w-full max-w-md flex-col border border-[var(--qm-line)] bg-[var(--qm-surface)] shadow-xl sm:bottom-4 sm:right-4 sm:h-[min(85dvh,34rem)] sm:rounded-lg"
          >
            <header className="flex items-start justify-between gap-3 border-b border-[var(--qm-line)] px-4 py-3">
              <div>
                <h2
                  id={titleId}
                  className="font-display text-lg text-[var(--qm-ink)]"
                >
                  Assistente QMind
                </h2>
                <p className="mt-0.5 text-xs text-[var(--qm-muted)]">
                  Estou aqui para orientar você em cada etapa da avaliação.
                </p>
              </div>
              <button
                ref={closeBtnRef}
                type="button"
                className="qm-btn-secondary !px-2.5 !py-1 text-sm"
                aria-label="Fechar painel do assistente"
                data-testid="qmind-assistant-close"
                onClick={() => {
                  setOpen(false);
                  openBtnRef.current?.focus();
                }}
              >
                Fechar
              </button>
            </header>

            <div
              className="flex-1 space-y-4 overflow-y-auto px-4 py-3"
              aria-live="polite"
              data-testid="qmind-assistant-body"
            >
              <div className="rounded border border-[var(--qm-line)] bg-[var(--qm-surface-soft)] px-3 py-2 text-xs text-[var(--qm-muted)]">
                <p>
                  <span className="font-semibold text-[var(--qm-ink)]">
                    {context.organization_name}
                  </span>
                  {context.assessment_label
                    ? ` · ${context.assessment_label}`
                    : ""}
                </p>
                {context.phase_label ? (
                  <p className="mt-1">Fase: {context.phase_label}</p>
                ) : null}
                <p className="mt-1">{context.stage_title}</p>
              </div>

              {reply ? (
                <section>
                  <h3 className="text-sm font-semibold text-[var(--qm-ink)]">
                    {reply.title}
                  </h3>
                  <div className="mt-2">
                    <ReplyBlocks blocks={reply.blocks} onNavigate={go} />
                  </div>
                </section>
              ) : null}
            </div>

            <footer className="space-y-2 border-t border-[var(--qm-line)] px-4 py-3">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-[var(--qm-muted)]">
                Ações rápidas
              </p>
              <div className="flex flex-wrap gap-2">
                {QUICK_ACTIONS.map((a) => (
                  <button
                    key={a.id}
                    type="button"
                    className={`rounded-md border px-2.5 py-1.5 text-left text-xs font-medium ${
                      lastQuickAction === a.id
                        ? "border-[var(--qm-ink)] bg-[var(--qm-surface-soft)] text-[var(--qm-ink)]"
                        : "border-[var(--qm-line)] text-[var(--qm-muted)] hover:border-[var(--qm-ink)]/40 hover:text-[var(--qm-ink)]"
                    }`}
                    data-testid={`qmind-assistant-action-${a.id}`}
                    onClick={() => onQuick(a.id)}
                  >
                    {a.label}
                  </button>
                ))}
              </div>
              <p className="text-[11px] text-[var(--qm-muted)]">
                Orientação por regras do percurso — sem escolher respostas por
                você.{" "}
                <Link
                  to="/assessments"
                  className="underline"
                  onClick={() => setOpen(false)}
                >
                  Minhas avaliações
                </Link>
              </p>
            </footer>
          </div>
        </>
      ) : null}
    </>
  );
}
