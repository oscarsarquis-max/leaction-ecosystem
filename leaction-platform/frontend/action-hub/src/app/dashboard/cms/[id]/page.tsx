import { Suspense } from 'react';
import { CmsPostForm } from '@/components/admin/CmsPostForm';

export default async function CmsEditPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const postId = Number(id);
  if (!Number.isInteger(postId) || postId < 1) {
    return <p className="px-4 py-10 text-sm text-stone-600">Post não encontrado.</p>;
  }
  return (
    <Suspense
      fallback={
        <div className="px-4 py-10 text-sm text-stone-500">Carregando formulário…</div>
      }
    >
      <CmsPostForm postId={postId} />
    </Suspense>
  );
}
