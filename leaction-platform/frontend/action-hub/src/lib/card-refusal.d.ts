import type { ReactElement } from 'react';

export const EXACT: Record<string, string>;
export const GENERIC: string;

export function customerCardMessage(statusDetail: string | null | undefined): string;
export function messageLeaksTechnical(text: string): boolean;
export function checkoutSafetyLine(sandbox: boolean): string;
export function CardRefusalNotice(props: {
  message: string;
  pixHref?: string | null;
}): ReactElement;
