import { Suspense } from 'react';
import { CmsPostForm } from '@/components/admin/CmsPostForm';

export default function CmsNovoPage() {
  return (
    <Suspense
      fallback={
        <div className="px-4 py-10 text-sm text-stone-500">Carregando formulário…</div>
      }
    >
      <CmsPostForm />
    </Suspense>
  );
}
