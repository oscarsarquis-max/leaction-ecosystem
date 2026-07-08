'use client';

import Link from 'next/link';
import type { ReactNode } from 'react';

export const ACTION_HUB_LOGO_LAYOUT = { heightPx: 150, marginTopPx: 28 };

const LOGO_FRAME_STYLE = {
  marginTop: `${ACTION_HUB_LOGO_LAYOUT.marginTopPx}px`,
  border: '1px solid #b8c2cc',
  boxShadow:
    'inset 0 1px 0 rgba(255,255,255,0.95), inset 0 -1px 0 rgba(15,23,42,0.16), inset 1px 0 0 rgba(255,255,255,0.8), inset -1px 0 0 rgba(15,23,42,0.12), 0 6px 18px rgba(15,23,42,0.22)',
} as const;

type ActionHubBrandHeaderProps = {
  left?: ReactNode;
};

/** Barra 60px + logo pendurada à direita (mesmo visual da home / PanelDX). */
export function ActionHubBrandHeader({ left }: ActionHubBrandHeaderProps) {
  return (
    <header className="relative sticky top-0 z-[60] h-[60px] w-full overflow-visible border-b border-black/20 bg-red-950 shadow-md">
      <div className="mx-auto flex h-[60px] max-w-6xl items-center px-4 md:px-6">{left}</div>

      <div className="pointer-events-none absolute right-2 top-0 z-[61] sm:right-4 md:right-8 lg:right-12 xl:right-16">
        <Link
          href="/"
          className="pointer-events-auto block shrink-0 rounded-sm bg-white p-px"
          style={LOGO_FRAME_STYLE}
          aria-label="ActionHub — início"
        >
          <span className="block rounded-[2px] bg-red-950 px-2.5 py-1.5 md:px-3 md:py-2">
            <img
              src="/logo.png"
              alt="ActionHub"
              className="block w-auto object-contain"
              style={{
                height: `${ACTION_HUB_LOGO_LAYOUT.heightPx}px`,
                maxWidth: 'min(240px, 38vw)',
              }}
            />
          </span>
        </Link>
      </div>
    </header>
  );
}
