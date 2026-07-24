'use client';

import type { ReactNode } from 'react';
import { LoggedAreaFrame } from '@/components/logged-area/LoggedAreaFrame';

/** Mantém o menu da área logada ao abrir Curadoria. */
export default function CuradoriaLayout({ children }: { children: ReactNode }) {
  return (
    <LoggedAreaFrame activeNav={null}>
      <div className="mx-auto w-full max-w-6xl">{children}</div>
    </LoggedAreaFrame>
  );
}
