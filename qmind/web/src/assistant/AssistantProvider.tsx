import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useOrganization } from "@/org/OrganizationProvider";
import {
  defaultAssistantEngine,
  DeterministicAssistantEngine,
} from "@/assistant/engine";
import type {
  AssistantContext,
  AssistantEngine,
  AssistantQuickActionId,
  AssistantReply,
  AssistantSessionUi,
} from "@/assistant/types";

type AssistantProviderValue = {
  context: AssistantContext;
  /** Páginas registram snapshot; null limpa ao desmontar. */
  setPageContext: (ctx: AssistantContext | null) => void;
  open: boolean;
  setOpen: (open: boolean) => void;
  lastQuickAction: AssistantQuickActionId | null;
  reply: AssistantReply | null;
  ask: (action: AssistantQuickActionId) => AssistantReply;
  greeting: () => AssistantReply;
  hasAttention: boolean;
  engine: AssistantEngine;
};

const AssistantReactContext = createContext<AssistantProviderValue | null>(null);

const SESSION_PREFIX = "qmind.assistant.ui.";

function readUi(orgId: string | null): AssistantSessionUi {
  if (!orgId || typeof sessionStorage === "undefined") {
    return { open: false, lastQuickAction: null };
  }
  try {
    const raw = sessionStorage.getItem(`${SESSION_PREFIX}${orgId}`);
    if (!raw) return { open: false, lastQuickAction: null };
    const parsed = JSON.parse(raw) as AssistantSessionUi;
    return {
      open: !!parsed.open,
      lastQuickAction: parsed.lastQuickAction ?? null,
    };
  } catch {
    return { open: false, lastQuickAction: null };
  }
}

function writeUi(orgId: string | null, ui: AssistantSessionUi) {
  if (!orgId || typeof sessionStorage === "undefined") return;
  try {
    sessionStorage.setItem(`${SESSION_PREFIX}${orgId}`, JSON.stringify(ui));
  } catch {
    /* ignore quota */
  }
}

function fallbackContext(
  organizationId: string | null,
  organizationName: string,
  roles: string[],
): AssistantContext {
  return {
    organization_id: organizationId,
    organization_name: organizationName,
    assessment_id: null,
    assessment_label: null,
    route: typeof window !== "undefined" ? window.location.pathname : "/",
    page: "generic",
    phase_label: null,
    assessment_status: null,
    user_roles: roles,
    can_mutate: false,
    next_action: {
      label: "Ir às avaliações",
      hint: "Escolha ou crie uma avaliação para receber orientação específica.",
      href: "/assessments",
    },
    pendencies: [],
    blockers: [],
    progress_summary: null,
    allowed_links: ["/assessments"],
    stage_title: "QMind",
    stage_explanation:
      "Selecione uma avaliação para receber orientação da etapa em que você está.",
  };
}

export function AssistantProvider({
  children,
  engine = defaultAssistantEngine,
}: {
  children: ReactNode;
  engine?: AssistantEngine;
}) {
  const org = useOrganization();
  const orgId = org.currentOrganizationId;
  const orgName =
    org.currentOrganization?.organizationName?.trim() || "Organização";
  const roles = org.currentOrganization?.roles ?? [];

  const [pageContext, setPageContextState] = useState<AssistantContext | null>(
    null,
  );
  const [open, setOpenState] = useState(false);
  const [lastQuickAction, setLastQuickAction] =
    useState<AssistantQuickActionId | null>(null);
  const [reply, setReply] = useState<AssistantReply | null>(null);

  // Troca de organização: limpa contexto de avaliação e UI da sessão anterior.
  useEffect(() => {
    setPageContextState(null);
    setReply(null);
    const ui = readUi(orgId);
    setOpenState(ui.open);
    setLastQuickAction(ui.lastQuickAction);
  }, [orgId]);

  const setOpen = useCallback(
    (next: boolean) => {
      setOpenState(next);
      writeUi(orgId, { open: next, lastQuickAction });
    },
    [orgId, lastQuickAction],
  );

  const setPageContext = useCallback((ctx: AssistantContext | null) => {
    setPageContextState(ctx);
  }, []);

  const context = useMemo(() => {
    if (pageContext) {
      // Cross-org: nunca usar snapshot de outra organização.
      if (
        orgId &&
        pageContext.organization_id &&
        pageContext.organization_id !== orgId
      ) {
        return fallbackContext(orgId, orgName, roles);
      }
      return pageContext;
    }
    return fallbackContext(orgId, orgName, roles);
  }, [pageContext, orgId, orgName, roles]);

  const ask = useCallback(
    (action: AssistantQuickActionId) => {
      const out = engine.answer(action, context);
      setLastQuickAction(action);
      setReply(out);
      writeUi(orgId, { open: true, lastQuickAction: action });
      setOpenState(true);
      return out;
    },
    [engine, context, orgId],
  );

  const greeting = useCallback(() => {
    const g =
      engine instanceof DeterministicAssistantEngine
        ? engine.greeting(context)
        : {
            title: "Assistente QMind",
            blocks: [
              {
                type: "paragraph" as const,
                text: "Estou aqui para orientar você em cada etapa da avaliação.",
              },
            ],
          };
    setReply(g);
    return g;
  }, [engine, context]);

  const hasAttention =
    context.blockers.length > 0 ||
    context.pendencies.some((p) => !!p.href) ||
    (context.next_action?.mutates === true && context.can_mutate);

  const value = useMemo<AssistantProviderValue>(
    () => ({
      context,
      setPageContext,
      open,
      setOpen,
      lastQuickAction,
      reply,
      ask,
      greeting,
      hasAttention:
        hasAttention &&
        (context.blockers.length > 0 || context.pendencies.length > 0),
      engine,
    }),
    [
      context,
      setPageContext,
      open,
      setOpen,
      lastQuickAction,
      reply,
      ask,
      greeting,
      hasAttention,
      engine,
    ],
  );

  return (
    <AssistantReactContext.Provider value={value}>
      {children}
    </AssistantReactContext.Provider>
  );
}

export function useAssistant() {
  const ctx = useContext(AssistantReactContext);
  if (!ctx) {
    throw new Error("useAssistant must be used within AssistantProvider");
  }
  return ctx;
}

/** Registro seguro — no-op se o provider não estiver montado (testes/páginas isoladas). */
export function useRegisterAssistantContext(ctx: AssistantContext | null) {
  const assistant = useContext(AssistantReactContext);
  useEffect(() => {
    if (!assistant) return;
    assistant.setPageContext(ctx);
    return () => assistant.setPageContext(null);
  }, [assistant, ctx]);
}
