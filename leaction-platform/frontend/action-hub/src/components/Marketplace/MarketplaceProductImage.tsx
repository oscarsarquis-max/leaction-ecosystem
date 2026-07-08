'use client';

import { useEffect, useMemo, useState } from 'react';
import { ShoppingBag } from 'lucide-react';
import {
  forceHttpsMarketplaceImageUrl,
  isMarketplacePlaceholderPath,
  isMercadoLivreCdnUrl,
  resolveMarketplaceImageUrl,
  toMarketplaceImageProxyPath,
} from '@/utils/marketplaceImages';

type MarketplaceProductImageProps = {
  src?: string | null;
  fallback?: boolean;
  title: string;
  className?: string;
  objectFit?: 'contain' | 'cover';
};

function MarketplaceIconFallback({ title }: { title: string }) {
  return (
    <div className="flex h-full w-full flex-col items-center justify-center gap-2 bg-gradient-to-br from-orange-50 to-slate-100 px-3 text-center">
      <ShoppingBag className="size-10 text-orange-400" aria-hidden />
      <span className="line-clamp-2 text-xs font-semibold text-slate-600">{title}</span>
    </div>
  );
}

function buildLiveImageAttemptQueue(src?: string | null): string[] {
  const queue: string[] = [];
  const pushUnique = (value: string | null) => {
    if (value && !queue.includes(value)) queue.push(value);
  };

  const primary = resolveMarketplaceImageUrl(src, { proxyMl: false });
  if (!primary) return queue;

  if (isMercadoLivreCdnUrl(primary)) {
    pushUnique(toMarketplaceImageProxyPath(forceHttpsMarketplaceImageUrl(primary)));
    pushUnique(forceHttpsMarketplaceImageUrl(primary));
  } else if (primary.startsWith('/marketplace-api/image')) {
    pushUnique(primary);
  } else {
    pushUnique(primary);
  }

  return queue;
}

export function MarketplaceProductImage({
  src,
  fallback = false,
  title,
  className = 'object-contain p-4',
  objectFit = 'contain',
}: MarketplaceProductImageProps) {
  const hasImage = Boolean(src && String(src).trim());
  const isPlaceholder = hasImage && isMarketplacePlaceholderPath(String(src));
  const useIconFallback = (fallback && !isPlaceholder) || !hasImage;

  const attempts = useMemo(
    () => (useIconFallback ? [] : buildLiveImageAttemptQueue(src)),
    [useIconFallback, src]
  );
  const [attemptIndex, setAttemptIndex] = useState(0);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setAttemptIndex(0);
    setFailed(false);
  }, [attempts]);

  if (useIconFallback || failed) {
    return <MarketplaceIconFallback title={title} />;
  }

  const currentSrc = attempts[attemptIndex] ?? null;
  const fitClass = objectFit === 'cover' ? 'object-cover' : 'object-contain';

  const handleError = () => {
    if (attemptIndex + 1 < attempts.length) {
      setAttemptIndex((index) => index + 1);
      return;
    }
    setFailed(true);
  };

  if (!currentSrc) {
    return <MarketplaceIconFallback title={title} />;
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={currentSrc}
      alt={title || 'Produto'}
      className={`h-full w-full ${fitClass} ${className}`}
      referrerPolicy="no-referrer"
      loading="lazy"
      decoding="async"
      onError={handleError}
    />
  );
}
