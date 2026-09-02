import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { resolveGuide } from "../guide/routes";
import { useAuth } from "../auth/AuthContext";
import { useOrganization } from "../session/OrganizationContext";
import { readOperationalContext } from "../session/operationalContext";
import type { LiveOverlay, LivePageContext, PageKind } from "./liveContext";

export type SpecificFlow = {
  code: string;
  title: string;
  steps: string[];
  step: number;
  note: string;
};

type AssistantState = {
  open: boolean;
  minimized: boolean;
  dismissed: boolean;
  flow: SpecificFlow | null;
  dirty: boolean;
  pendingCommand: boolean;
  live: LivePageContext;
  openAssistant: () => void;
  closeAssistant: () => void;
  minimizeAssistant: () => void;
  dismissAssistant: () => void;
  setFlow: (flow: SpecificFlow | null) => void;
  setDirty: (value: boolean) => void;
  setPendingCommand: (value: boolean) => void;
  publishLive: (overlay: LiveOverlay | null) => void;
};

const AssistantContext = createContext<AssistantState | null>(null);

function kindCopy(kind: PageKind, guideNext: string): { pending: string; blocked: string; next: string } {
  if (kind === "loading") return { pending: "Carregando.", blocked: "", next: "Aguardar o recorte." };
  if (kind === "empty") return { pending: "Nenhum item neste recorte.", blocked: "", next: "Criar, limpar filtro ou trocar contexto." };
  if (kind === "error") return { pending: "", blocked: "Erro recuperável.", next: "Tentar de novo." };
  if (kind === "denied") return { pending: "", blocked: "Sem permissão neste recorte.", next: "Trocar de perfil ou voltar." };
  return { pending: "", blocked: "", next: guideNext };
}

export function AssistantProvider({ children }: { children: ReactNode }) {
  const location = useLocation();
  const { session } = useAuth();
  const { active, me, hasPermission } = useOrganization();
  const [open, setOpen] = useState(false);
  const [minimized, setMinimized] = useState(true);
  const [dismissed, setDismissed] = useState(false);
  const [flow, setFlow] = useState<SpecificFlow | null>(null);
  const [dirty, setDirty] = useState(false);
  const [pendingCommand, setPendingCommand] = useState(false);
  const [overlay, setOverlay] = useState<LiveOverlay | null>(null);

  useEffect(() => {
    setOverlay(null);
    setDirty(false);
    setPendingCommand(false);
    setOpen((was) => (was ? false : was));
  }, [location.pathname]);

  useEffect(() => {
    setOverlay(null);
    setFlow(null);
    setDirty(false);
    setPendingCommand(false);
  }, [active?.organization_id]);

  useEffect(() => {
    if (session) return;
    setOpen(false);
    setMinimized(true);
    setDismissed(false);
    setFlow(null);
    setOverlay(null);
    setDirty(false);
    setPendingCommand(false);
  }, [session]);

  const openAssistant = useCallback(() => {
    setDismissed(false);
    setMinimized(false);
    setOpen(true);
  }, []);

  const { guide, specific } = resolveGuide(location.pathname);
  const operational = active
    ? readOperationalContext(active.organization_id, me?.display_name || "sessao")
    : null;
  const pageKind = overlay?.pageKind ?? "ok";
  const copies = kindCopy(pageKind, overlay?.next || guide.next);
  const live = useMemo<LivePageContext>(
    () => ({
      route: location.pathname,
      domain: guide.domain,
      section: guide.section,
      title: guide.title,
      goal: overlay?.goal || guide.goal,
      organization: active?.display_name || "",
      entity: guide.entity,
      entityLabel: overlay?.entityLabel || guide.entity,
      status: overlay?.status || (specific ? "guia específico" : "guia mínimo"),
      permissions: (me?.permissions ?? []).filter((code) => guide.permissions.includes(code) || hasPermission(code)),
      actions: guide.actions.filter((action) => action),
      pending: overlay?.pending || copies.pending || guide.pending,
      blocked: overlay ? overlay.blocked || "" : copies.blocked || guide.blocks,
      next: copies.next,
      dirty,
      pendingCommand,
      operational: operational
        ? `${operational.establishment_name} · ${operational.shift} · ${operational.area}`
        : "",
      related: guide.related,
      destinations: guide.destinations
        .filter((item) => !item.permission || hasPermission(item.permission))
        .map((item) => ({ to: item.to, label: item.label })),
      pageKind,
      guideSpecific: specific,
    }),
    [
      location.pathname,
      guide,
      specific,
      active?.display_name,
      me?.permissions,
      hasPermission,
      overlay,
      copies.pending,
      copies.blocked,
      copies.next,
      dirty,
      pendingCommand,
      operational,
    ],
  );

  const value = useMemo<AssistantState>(
    () => ({
      open,
      minimized,
      dismissed,
      flow,
      dirty,
      pendingCommand,
      live,
      openAssistant,
      closeAssistant: () => {
        setOpen(false);
        queueMicrotask(() => {
          document.querySelector<HTMLButtonElement>('[aria-label="Abrir Gigio"]')?.focus();
        });
      },
      minimizeAssistant: () => {
        setMinimized(true);
        setOpen(false);
        queueMicrotask(() => {
          document.querySelector<HTMLButtonElement>('[aria-label="Abrir Gigio"]')?.focus();
        });
      },
      dismissAssistant: () => {
        setDismissed(true);
        setOpen(false);
        setFlow(null);
        queueMicrotask(() => {
          document.querySelector<HTMLButtonElement>('[aria-label="Abrir Gigio"]')?.focus();
        });
      },
      setFlow,
      setDirty,
      setPendingCommand,
      publishLive: setOverlay,
    }),
    [open, minimized, dismissed, flow, dirty, pendingCommand, live, openAssistant],
  );

  return <AssistantContext.Provider value={value}>{children}</AssistantContext.Provider>;
}

export function useAssistant(): AssistantState {
  const value = useContext(AssistantContext);
  if (!value) throw new Error("useAssistant exige AssistantProvider.");
  return value;
}

export function useAssistantOptional(): AssistantState | null {
  return useContext(AssistantContext);
}
