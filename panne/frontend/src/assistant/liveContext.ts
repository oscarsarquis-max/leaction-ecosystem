export type PageKind = "ok" | "loading" | "empty" | "error" | "denied";

export type LiveOverlay = {
  entityLabel?: string;
  status?: string;
  goal?: string;
  pending?: string;
  blocked?: string;
  next?: string;
  pageKind?: PageKind;
};

export type LivePageContext = {
  route: string;
  domain: string;
  section: string;
  title: string;
  goal: string;
  organization: string;
  entity: string;
  entityLabel: string;
  status: string;
  permissions: string[];
  actions: string[];
  pending: string;
  blocked: string;
  next: string;
  dirty: boolean;
  pendingCommand: boolean;
  operational: string;
  related: string[];
  destinations: Array<{ to: string; label: string }>;
  pageKind: PageKind;
  guideSpecific: boolean;
};
