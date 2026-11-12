import type { ReactElement } from 'react';

export const CPF_FORM_MESSAGE: string;

export function cpfDigits(raw: string | null | undefined): string | null;

export function cardDocumentForSubmit(
  raw: string | null | undefined,
  required: boolean,
): { ok: boolean; digits: string | null; message: string };

export function PayerCpf(props: {
  value: string;
  onChange: (value: string) => void;
}): ReactElement;
