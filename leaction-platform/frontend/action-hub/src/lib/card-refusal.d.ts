import type { ReactElement } from 'react';

export const EXACT: Record<string, string>;
export const GENERIC: string;
export const UNMAPPED: string;

export function customerCardMessage(statusDetail: string | null | undefined): string;
export function presentCardFailure(input?: {
  status?: number;
  mp_status_detail?: string | null;
}): { message: string; refused: boolean };
export function messageLeaksTechnical(text: string): boolean;
export function checkoutSafetyLine(sandbox: boolean): string;
export function CardRefusalNotice(props: {
  message: string;
  pixHref?: string | null;
}): ReactElement;
