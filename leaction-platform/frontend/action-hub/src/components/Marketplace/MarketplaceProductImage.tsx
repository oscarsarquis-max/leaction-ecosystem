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
  /** Legado — ignorado; mantido por compat. */
  fallback?: boolean;
  title: string;
  className?: string;
  objectFit?: 'contain' | 'cover';
};

const FILE_PLACEHOLDER = '/marketplace/placeholders/default.svg';
const LOAD_TIMEOUT_MS = 15000;

function MarketplaceOrangeFallback({ title }: { title: string }) {
  return (
    <div
      className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-gradient-to-br from-emerald-100 via-emerald-50 to-amber-50 px-3 text-center"
      role="img"
      aria-label={title || 'Produto sem imagem'}
    >
      <span className="flex size-12 items-center justify-center rounded-2xl bg-emerald-500/15 ring-1 ring-emerald-300/60">
        <ShoppingBag className="size-7 text-emerald-500" aria-hidden />
      </span>
      <span className="line-clamp-2 max-w-[90%] text-xs font-semibold text-emerald-800/80">
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
  if (!raw) {
    pushUnique(FILE_PLACEHOLDER);
    return queue;
  }

  if (raw.startsWith('/marketplace-api/image') || raw.startsWith('data:')) {
    pushUnique(raw);
    pushUnique(FILE_PLACEHOLDER);
    return queue;
  }

  if (isMarketplacePlaceholderPath(raw)) {
    pushUnique(resolveMarketplaceImageUrl(raw, { proxyMl: false }));
    pushUnique(FILE_PLACEHOLDER);
    return queue;
  }

  const https = forceHttpsMarketplaceImageUrl(
    raw.startsWith('//') ? `https:${raw}` : raw
  );

  if (isProxiedMarketplaceCdnUrl(https)) {
    pushUnique(toMarketplaceImageProxyPath(https));
  } else {
    pushUnique(resolveMarketplaceImageUrl(https, { proxyMl: true }));
  }
  pushUnique(FILE_PLACEHOLDER);
  return queue;
}

/**
 * Slot de imagem do marketplace.
 * - Preenche o container com absolute inset-0 (pai deve ter altura explícita)
 * - Não rejeita SVG via naturalWidth (quebrava placeholders)
 * - Cadeia: src/proxy → default.svg → ícone laranja (só após falha total)
 * - Nunca empilha o fallback laranja atrás da foto (object-contain vazava o fundo)
 */
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
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    setAttemptIndex(0);
    setFailed(false);
    setLoaded(false);
  }, [attempts]);

  useEffect(() => {
    if (failed || loaded || attempts.length === 0) return undefined;
    const timer = window.setTimeout(() => {
      if (attemptIndex + 1 < attempts.length) {
        setAttemptIndex((index) => index + 1);
      } else {
        setFailed(true);
      }
    }, LOAD_TIMEOUT_MS);
    return () => window.clearTimeout(timer);
  }, [attemptIndex, attempts.length, failed, loaded]);

  const fitClass = objectFit === 'cover' ? 'object-cover' : 'object-contain';
  const currentSrc = attempts[attemptIndex] ?? null;

  const advanceOrFail = () => {
    setLoaded(false);
    if (attemptIndex + 1 < attempts.length) {
      setAttemptIndex((index) => index + 1);
      return;
    }
    setFailed(true);
  };

  if (failed || !currentSrc) {
    return (
      <div className="relative h-full w-full min-h-[11rem]">
        <MarketplaceOrangeFallback title={title} />
      </div>
    );
  }

  return (
    <div className="relative h-full w-full min-h-[11rem] bg-emerald-50/50">
      {/* Skeleton neutro só enquanto carrega — nunca empilha o fallback sob a foto */}
      {!loaded ? (
        <div
          className="absolute inset-0 animate-pulse bg-gradient-to-br from-stone-100 to-stone-50"
          aria-hidden
        />
      ) : null}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        key={currentSrc}
        src={currentSrc}
        alt={title || 'Produto'}
        className={[
          'absolute inset-0 z-[1] h-full w-full transition-opacity duration-200',
          fitClass,
          className,
          loaded ? 'opacity-100' : 'opacity-0',
        ].join(' ')}
        referrerPolicy="no-referrer"
        loading="eager"
        decoding="async"
        onError={advanceOrFail}
        onLoad={() => {
          // Aceita SVG/webp/jpeg — NÃO usar naturalWidth (SVG pode reportar 0)
          setLoaded(true);
        }}
      />
    </div>
  );
}
