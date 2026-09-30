import type { PendingWrite } from "./api";

type Listener = () => void;

let unknownWrite: PendingWrite | null = null;
let reviewBeforeRelogin = false;
const listeners = new Set<Listener>();

function notify() {
  listeners.forEach((listener) => listener());
}

export function subscribeUnknownWrite(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getUnknownWrite(): PendingWrite | null {
  return unknownWrite;
}

export function rememberUnknownWrite(pending: PendingWrite): void {
  unknownWrite = pending;
  notify();
}

export function clearUnknownWrite(): void {
  unknownWrite = null;
  notify();
}

export function markReviewBeforeRelogin(): void {
  if (unknownWrite) {
    reviewBeforeRelogin = true;
    notify();
  }
}

export function consumeReviewBeforeRelogin(): boolean {
  const value = reviewBeforeRelogin;
  reviewBeforeRelogin = false;
  return value;
}

export function dropUnknownWriteIfActorChanged(actorId: string | null | undefined): void {
  if (!unknownWrite) {
    return;
  }
  if (!actorId || unknownWrite.actorId !== actorId) {
    unknownWrite = null;
    reviewBeforeRelogin = false;
    notify();
  }
}

export function sameActorAndCompany(pending: PendingWrite, actorId: string, companyId: string): boolean {
  return pending.actorId === actorId && pending.companyId === companyId;
}
