'use client';

import { MarketplaceProductImage } from '@/components/Marketplace/MarketplaceProductImage';
import type { PreviewOffer } from '@/components/Marketplace/curationApi';

export function PreviewMiniCard({ offer }: { offer: PreviewOffer }) {
  return (
    <article className="flex gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
      <div className="relative h-16 w-16 shrink-0 overflow-hidden rounded-lg bg-slate-100">
        <MarketplaceProductImage
          src={offer.image}
          title={offer.title}
          className="p-1"
          objectFit="cover"
        />
      </div>
      <div className="min-w-0 flex-1">
        <p className="line-clamp-2 text-xs font-semibold leading-snug text-red-950">
          {offer.title}
        </p>
        <p className="mt-1 text-sm font-bold text-red-600">{offer.price_label || 'Consulte'}</p>
      </div>
    </article>
  );
}
