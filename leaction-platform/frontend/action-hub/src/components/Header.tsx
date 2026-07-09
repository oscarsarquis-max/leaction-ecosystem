'use client';

import { usePathname } from 'next/navigation';
import { ActionHubBrandHeader } from '@/components/ActionHubBrandHeader';
import { HeaderAuthControls } from '@/components/HeaderAuthControls';

export function Header() {
  const pathname = usePathname();
  const isHome = pathname === '/';

  return (
    <ActionHubBrandHeader
      variant={isHome ? 'light' : 'classic'}
      left={
        <div className={isHome ? 'w-full' : 'pr-28 sm:pr-36 md:pr-44'}>
          <HeaderAuthControls variant={isHome ? 'light' : 'dark'} />
        </div>
      }
    />
  );
}
