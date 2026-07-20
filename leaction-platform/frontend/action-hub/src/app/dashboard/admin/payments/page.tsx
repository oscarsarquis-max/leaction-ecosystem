'use client';

import { useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import { PaymentsOps } from '@/components/admin/PaymentsOps';

function PaymentsPageInner() {
  const searchParams = useSearchParams();
  const appId = String(searchParams.get('app_id') || '').trim();
  return <PaymentsOps initialAppId={appId} />;
}

export default function AdminPaymentsPage() {
  return (
    <Suspense
      fallback={
        <div className="py-12 text-center text-sm text-stone-500">
          Carregando pagamentos…
        </div>
      }
    >
      <PaymentsPageInner />
    </Suspense>
  );
}
