'use client';

import { useEffect, useMemo, useState } from 'react';
import { ShoppingBag } from 'lucide-react';
import {
  forceHttpsMarketplaceImageUrl,
  isMarketplacePlaceholderPath,
  isProxiedMarketplaceCdnUrl,
  resolveMarketplaceImageUrl,
  toMarketplaceImageProxyPath,
} from '@/utils/marketplaceImages';

type MarketplaceProductImageProps = {
  src?: string | null;
  /** Legado — ignorado para ocultar imagem; só mantido por compat. */
  fallback?: boolean;
  title: string;
  className?: string;
  objectFit?: 'contain' | 'cover';
};

const LOAD_TIMEOUT_MS = 4500;

function MarketplaceOrangeFallback({ title }: { title: string }) {
  return (
    <div
      className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-gradient-to-br from-orange-100 via-orange-50 to-amber-50 px-3 text-center"
      role="img"
      aria-label={title || 'Produto sem imagem'}
    >
      <span className="flex size-12 items-center justify-center rounded-2xl bg-orange-500/15 ring-1 ring-orange-300/60">
        <ShoppingBag className="size-7 text-orange-500" aria-hidden />
      </span>
      <span className="line-clamp-2 max-w-[90%] text-xs font-semibold text-orange-800/80">
        {title || 'Oferta'}
      </span>
    </div>
  );
}

function buildLiveImageAttemptQueue(src?: string | null): string[] {
  const queue: string[] = [];
  const pushUnique = (value: string | null | undefined) => {
    if (value && !queue.includes(value)) queue.push(value);
  };

  const raw = typeof src === 'string' ? src.trim() : '';
  if (!raw) return queue;

  if (raw.startsWith('/marketplace-api/image')) {
    pushUnique(raw);
    return queue;
  }

  if (isMarketplacePlaceholderPath(raw)) {
    pushUnique(resolveMarketplaceImageUrl(raw, { proxyMl: false }));
    return queue;
  }

  const https = forceHttpsMarketplaceImageUrl(
    raw.startsWith('//') ? `https:${raw}` : raw
  );

  // CDN ML/Amazon sempre via proxy same-origin (localhost costuma bloquear hotlink).
  if (isProxiedMarketplaceCdnUrl(https)) {
    pushUnique(toMarketplaceImageProxyPath(https));
    return queue;
  }

  pushUnique(resolveMarketplaceImageUrl(https, { proxyMl: true }));
  return queue;
}

export function MarketplaceProductImage({
  src,
  fallback: _legacyFallback = false,
  title,
  className = 'object-contain p-3',
  objectFit = 'contain',
}: MarketplaceProductImageProps) {
  const attempts = useMemo(() => buildLiveImageAttemptQueue(src), [src]);
  const [attemptIndex, setAttemptIndex] = useState(0);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setAttemptIndex(0);
    setFailed(false);
  }, [attempts]);

  // Timeout: se a imagem não carregar, tenta a próxima ou exibe fallback laranja.
  useEffect(() => {
    if (failed || attempts.length === 0) return undefined;
    const timer = window.setTimeout(() => {
      if (attemptIndex + 1 < attempts.length) {
        setAttemptIndex((index) => index + 1);
      } else {
        setFailed(true);
      }
    }, LOAD_TIMEOUT_MS);
    return () => window.clearTimeout(timer);
  }, [attemptIndex, attempts.length, failed]);

  if (failed || attempts.length === 0) {
    return (
      <div className="relative h-full min-h-full w-full">
        <MarketplaceOrangeFallback title={title} />
      </div>
    );
  }

  const currentSrc = attempts[attemptIndex] ?? null;
  if (!currentSrc) {
    return (
      <div className="relative h-full min-h-full w-full">
        <MarketplaceOrangeFallback title={title} />
      </div>
    );
  }

  const fitClass = objectFit === 'cover' ? 'object-cover' : 'object-contain';

  const advanceOrFail = () => {
    if (attemptIndex + 1 < attempts.length) {
      setAttemptIndex((index) => index + 1);
      return;
    }
    setFailed(true);
  };

  return (
    <div className="relative h-full w-full">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        key={currentSrc}
        src={currentSrc}
        alt={title || 'Produto'}
        className={`h-full w-full ${fitClass} ${className}`}
        referrerPolicy="no-referrer"
        loading="eager"
        decoding="async"
        onError={advanceOrFail}
        onLoad={(event) => {
          const img = event.currentTarget;
          if (!img.naturalWidth || !img.naturalHeight) {
            advanceOrFail();
          }
        }}
      />
    </div>
  );
}
