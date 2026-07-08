'use client';

import { ExternalLink } from 'lucide-react';
import { MarketplaceProductImage } from '@/components/Marketplace/MarketplaceProductImage';
import { openExternalUrl } from '@/utils/openExternalUrl';
import { VendorBadge } from './VendorBadge';

export function OfferCard({ offer }) {
  const openLink = (event) => {
    event.preventDefault();
    event.stopPropagation();
    openExternalUrl(offer.link);
  };

  return (
    <article className="flex h-full flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm transition hover:border-orange-300 hover:shadow-md">
      <div className="relative aspect-square overflow-hidden bg-slate-100">
        <MarketplaceProductImage
          src={offer.image}
          fallback={offer.fallback}
          title={offer.title}
          className="p-2"
          objectFit="cover"
        />
        <div className="absolute left-2 top-2 z-10 pointer-events-none">
          <VendorBadge vendor={offer.vendor} />
        </div>
      </div>
      <div className="flex flex-1 flex-col gap-2 p-3">
        <p className="line-clamp-2 text-xs font-medium leading-snug text-slate-700 md:text-sm">
          {offer.title}
        </p>
        <div className="mt-auto flex items-center justify-between gap-2">
          <span className="text-sm font-bold text-red-600">
            {offer.price_label || 'Consulte'}
          </span>
          <button
            type="button"
            aria-label={`Ver no Mercado Livre: ${offer.title}`}
            onClick={openLink}
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-semibold text-slate-600 transition hover:bg-orange-50 hover:text-orange-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-500"
          >
            Abrir
            <ExternalLink className="size-3.5 shrink-0" aria-hidden />
          </button>
        </div>
      </div>
    </article>
  );
}
