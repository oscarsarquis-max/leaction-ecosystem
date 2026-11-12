import type { ReactElement } from 'react';

export const MP_SECURITY_SCRIPT: {
  src: string;
  async: boolean;
  view: string;
};

export function optionalCpfDigits(raw: string | null | undefined): string | null;
export function readDeviceSessionId(source?: { MP_DEVICE_SESSION_ID?: string } | null): string;
export function OptionalPayerCpf(props: {
  value: string;
  onChange: (value: string) => void;
}): ReactElement;
