'use client';

import { Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { IdentidadeGestao } from '@/components/admin/IdentidadeGestao';

function IdentidadePageInner() {
  const searchParams = useSearchParams();
  const sistema = String(searchParams.get('sistema') || '').trim();
  return <IdentidadeGestao initialSistema={sistema} />;
}

export default function IdentidadePage() {
  return (
    <Suspense
      fallback={
        <div className="py-12 text-center text-sm text-stone-500">
          Carregando gestão de identidade…
        </div>
      }
    >
      <IdentidadePageInner />
    </Suspense>
  );
}
