'use client';

import { InoveEcosystemHero } from '@/components/public-portal/InoveEcosystemHero';
import { resolveInove4usUrl } from '@/components/logged-area/mock-data';

type LoggedAreaMainProps = {
  userName: string;
};

export function LoggedAreaMain({ userName }: LoggedAreaMainProps) {
  const inoveUrl = resolveInove4usUrl();
  const schoolAcesso =
    (process.env.NEXT_PUBLIC_SCHOOL_URL || '').trim().replace(/\/$/, '') ||
    'https://school.inove4us.com.br';

  return (
    <div className="mx-auto w-full max-w-4xl space-y-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight text-stone-900 md:text-3xl">
          Bem-vindo de volta, {userName}
        </h1>
        <p className="mt-1.5 text-base text-stone-500">
          Ecossistema inove4us — professor, escola e o começo comum.
        </p>
      </header>

      <InoveEcosystemHero
        ctaLabel="Ver o começo do ecossistema"
        ctaHref="/comeco"
        showFoot={false}
        secondary={[
          { href: `${inoveUrl}/acesso`, label: 'Acessar Inove4Us', external: true },
          { href: `${schoolAcesso}/acesso`, label: 'Acessar School', external: true },
          { href: '/ecossistema', label: 'Planos da escola' },
        ]}
      />
    </div>
  );
}
