'use client';

import { ActionHubBrandHeader } from '@/components/ActionHubBrandHeader';
import { HeaderAuthControls } from '@/components/HeaderAuthControls';

/** Header interno ActionHub — padrão home (logo inline + controles light). */
export function Header() {
  return (
    <ActionHubBrandHeader right={<HeaderAuthControls variant="light" />} />
  );
}
