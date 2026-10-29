import type { BreadBuilderState } from "./state";
import type { BuilderProposal, BuilderTip } from "./builderApi";

export const GIGIO_OPEN_EVENT = "lojadepaes:gigio-open";
export const BUILDER_PROPOSAL_EVENT = "lojadepaes:builder-proposal";

export function proposalSearchToken(search = window.location.search): string {
  return new URLSearchParams(search).get("proposta") || "";
}

export function hasBuilderWork(state: Pick<BreadBuilderState, "massId" | "flourId" | "shapeId" | "extraIds" | "freeText">): boolean {
  return Boolean(state.massId || state.flourId || state.shapeId || state.extraIds.length || state.freeText.trim());
}

export function proposalDiffers(
  state: Pick<BreadBuilderState, "massId" | "flourId" | "shapeId" | "extraIds" | "freeText">,
  proposal: BuilderProposal,
): boolean {
  if ((state.flourId || "") !== (proposal.flour_id || "")) return true;
  if ((state.massId || "") !== (proposal.dough_id || "")) return true;
  if ((state.shapeId || "") !== (proposal.shape_id || "")) return true;
  if ((state.freeText || "") !== (proposal.free_text || "")) return true;
  const current = [...state.extraIds].sort().join(",");
  const incoming = [...(proposal.ingredient_ids || [])].sort().join(",");
  return current !== incoming;
}

export function proposalToPartial(proposal: BuilderProposal): Partial<BreadBuilderState> {
  return {
    flourId: proposal.flour_id || "",
    flourName: proposal.flour_name || "",
    massId: proposal.dough_id || "",
    massName: proposal.dough_name || "",
    extraIds: proposal.ingredient_ids || [],
    extraNames: proposal.ingredient_names || [],
    shapeId: proposal.shape_id || "",
    shapeName: proposal.shape_name || "",
    freeText: proposal.free_text || "",
  };
}

export function tipCacheKey(state: Pick<BreadBuilderState, "flourId" | "massId" | "shapeId" | "extraIds" | "freeText">, occasion = ""): string {
  return [state.flourId, state.massId, state.shapeId, [...state.extraIds].sort().join(","), state.freeText.trim(), occasion.trim()].join("|");
}

export function compositionReady(state: Pick<BreadBuilderState, "flourId" | "massId">): boolean {
  return Boolean(state.flourId && state.massId);
}

export function openGigioWithBuilder(detail: {
  flour: string;
  preparation: string;
  inclusions: string[];
  shape: string;
  note: string;
}): void {
  window.dispatchEvent(new CustomEvent(GIGIO_OPEN_EVENT, { detail }));
}

export function describeTipChanges(tip: BuilderTip): string {
  const changes = tip.suggestion?.changes || [];
  if (!changes.length) return "";
  return changes.map((item) => `${item.from || "—"} → ${item.to || "—"}`).join("; ");
}
