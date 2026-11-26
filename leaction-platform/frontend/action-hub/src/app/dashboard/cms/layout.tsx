'use client';

import type { ReactNode } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { AdminGuard } from '@/components/admin/AdminGuard';
import { AdminShell } from '@/components/admin/AdminShell';

const TABS = [
  { href: '/dashboard/cms', label: 'Posts', match: (p: string) => p === '/dashboard/cms' || p.startsWith('/dashboard/cms/novo') || /^\/dashboard\/cms\/\d+/.test(p) },
  { href: '/dashboard/cms/receitas', label: 'Receitas', match: (p: string) => p.startsWith('/dashboard/cms/receitas') },
  { href: '/dashboard/cms/enquetes', label: 'Enquetes', match: (p: string) => p.startsWith('/dashboard/cms/enquetes') },
  { href: '/dashboard/cms/sugestoes', label: 'Sugestões', match: (p: string) => p.startsWith('/dashboard/cms/sugestoes') },
];

function CmsTabs() {
  const pathname = usePathname() || '';
  return (
    <nav className="mb-6 flex flex-wrap gap-2 border-b border-stone-200 pb-3">
      {TABS.map((tab) => {
        const active = tab.match(pathname);
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={`rounded-xl px-3 py-2 text-sm font-semibold transition ${
              active
                ? 'bg-emerald-500 text-white'
                : 'border border-stone-300 bg-white text-stone-700 hover:bg-stone-50'
            }`}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}

export default function CmsLayout({ children }: { children: ReactNode }) {
  return (
    <AdminGuard>
      <AdminShell>
        <CmsTabs />
        {children}
      </AdminShell>
    </AdminGuard>
  );
}
