'use client';

import { useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import { PlanBuilder } from '@/components/admin/PlanBuilder';

function PlansPageInner() {
  const searchParams = useSearchParams();
  const appId = String(searchParams.get('app_id') || '').trim();
  return <PlanBuilder initialAppId={appId} />;
}

export default function AdminPlansPage() {
  return (
    <Suspense
      fallback={
        <div className="py-12 text-center text-sm text-stone-500">
          Carregando construtor…
        </div>
      }
    >
      <PlansPageInner />
    </Suspense>
  );
}
