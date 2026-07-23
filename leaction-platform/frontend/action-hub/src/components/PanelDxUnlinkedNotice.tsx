import Link from 'next/link';

/** Tela amigável quando alguém abre um fluxo PanelDX desvinculado do Hub. */
export function PanelDxUnlinkedNotice({
  title = 'Integração PanelDX indisponível',
}: {
  title?: string;
}) {
  return (
    <main className="mx-auto flex min-h-[60vh] max-w-lg flex-col items-center justify-center px-6 py-16 text-center">
      <p className="text-xs font-bold uppercase tracking-[0.18em] text-stone-400">Action Hub</p>
      <h1 className="mt-2 text-2xl font-bold tracking-tight text-stone-900">{title}</h1>
      <p className="mt-3 text-sm leading-relaxed text-stone-500">
        O PanelDX não está vinculado a este Hub no momento. Use o marketplace e as integrações
        ativas (como o inove4us).
      </p>
      <Link
        href="/"
        className="mt-8 inline-flex rounded-xl bg-orange-500 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-orange-600"
      >
        Voltar ao Action Hub
      </Link>
    </main>
  );
}
