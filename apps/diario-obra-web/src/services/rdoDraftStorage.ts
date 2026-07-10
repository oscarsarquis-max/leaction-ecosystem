/** Persistência local de rascunhos RDO (offline / auto-save). */

import type { DailyLogPayload } from '../types';

const PREFIX = 'rdo_draft_v1';

export function draftStorageKey(projectId: string, date: string) {
  return `${PREFIX}:${projectId}:${date}`;
}

export interface LocalDraftEnvelope {
  saved_at: string;
  payload: Partial<DailyLogPayload> & Record<string, unknown>;
}

export function loadLocalDraft(projectId: string, date: string): LocalDraftEnvelope | null {
  try {
    const raw = localStorage.getItem(draftStorageKey(projectId, date));
    if (!raw) return null;
    return JSON.parse(raw) as LocalDraftEnvelope;
  } catch {
    return null;
  }
}

export function saveLocalDraft(
  projectId: string,
  date: string,
  payload: LocalDraftEnvelope['payload'],
) {
  const envelope: LocalDraftEnvelope = {
    saved_at: new Date().toISOString(),
    payload,
  };
  localStorage.setItem(draftStorageKey(projectId, date), JSON.stringify(envelope));
}

export function clearLocalDraft(projectId: string, date: string) {
  localStorage.removeItem(draftStorageKey(projectId, date));
}
