'use client';

import { ExternalLink, ShoppingCart } from 'lucide-react';
import { MarketplaceProductImage } from '@/components/Marketplace/MarketplaceProductImage';
import { openExternalUrl } from '@/utils/openExternalUrl';
import { useCart } from '@/context/CartContext';
import { VendorBadge } from './VendorBadge';

export function OfferCard({ offer }) {
  const { addToCart, cartItems } = useCart();
  const inCart = cartItems.some((item) => String(item.id) === String(offer.id));

  const openLink = (event) => {
    event.preventDefault();
    event.stopPropagation();
    openExternalUrl(offer.link);
  };

  const handleAdd = (event) => {
    event.preventDefault();
    event.stopPropagation();
    addToCart({
      id: offer.id,
      sku: offer.id,
      nome: offer.title,
      price: offer.price,
      price_label: offer.price_label,
      image: offer.image,
      link: offer.link,
      vendor: offer.vendor,
    });
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
        <div className="mt-auto flex flex-col gap-2">
          <span className="text-sm font-bold text-red-600">
            {offer.price_label || 'Consulte'}
          </span>
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              aria-label={inCart ? `Já no carrinho: ${offer.title}` : `Adicionar ao carrinho: ${offer.title}`}
              onClick={handleAdd}
              disabled={inCart}
              className="inline-flex flex-1 items-center justify-center gap-1 rounded-md border border-orange-200 bg-orange-50 px-2 py-1.5 text-xs font-semibold text-orange-800 transition hover:bg-orange-100 disabled:cursor-default disabled:opacity-70"
            >
              <ShoppingCart className="size-3.5 shrink-0" aria-hidden />
              {inCart ? 'No carrinho' : 'Carrinho'}
            </button>
            <button
              type="button"
              aria-label={`Ver oferta: ${offer.title}`}
              onClick={openLink}
              className="inline-flex items-center gap-1 rounded-md px-2 py-1.5 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 hover:text-orange-700"
            >
              Abrir
              <ExternalLink className="size-3.5 shrink-0" aria-hidden />
            </button>
          </div>
        </div>
      </div>
    </article>
  );
}
