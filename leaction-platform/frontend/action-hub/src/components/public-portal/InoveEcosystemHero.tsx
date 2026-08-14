'use client';

import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { INOVE_HERO } from '@/components/public-portal/mock-data';
import '@/components/public-portal/portal-hero.css';

type InoveEcosystemHeroProps = {
  /** CTA principal (padrão: /comeco). */
  ctaHref?: string;
  ctaLabel?: string;
  showFoot?: boolean;
  /** Links extras abaixo do CTA (ex.: área logada). */
  secondary?: Array<{ href: string; label: string; external?: boolean }>;
};

/** Identidade /comeco — reutilizado na home pública e na área logada (código, não CMS). */
export function InoveEcosystemHero({
  ctaHref = INOVE_HERO.href,
  ctaLabel = INOVE_HERO.cta,
  showFoot = true,
  secondary,
}: InoveEcosystemHeroProps) {
  return (
    <article className="portal-hero">
      <p className="portal-hero__eyebrow">{INOVE_HERO.eyebrow}</p>

      <h1 className="portal-hero__title">
        Uma <em>trincheira</em> para o professor. Uma <em>torre de controle</em> para a escola.
      </h1>

      <p className="portal-hero__lead">{INOVE_HERO.lead}</p>

      <div className="portal-hero__actions">
        <Link href={ctaHref} className="portal-hero__cta">
          {ctaLabel}
          <ArrowRight className="size-4" aria-hidden />
        </Link>
        {secondary?.map((item) =>
          item.external ? (
            <a
              key={item.href + item.label}
              href={item.href}
              target="_blank"
              rel="noopener noreferrer"
              className="portal-hero__cta-ghost"
            >
              {item.label}
            </a>
          ) : (
            <Link
              key={item.href + item.label}
              href={item.href}
              className="portal-hero__cta-ghost"
            >
              {item.label}
            </Link>
          )
        )}
      </div>

      <div className="portal-hero__split">
        {INOVE_HERO.products.map((product) => (
          <div
            key={product.id}
            className={`portal-hero__side portal-hero__side--${product.tone}`}
          >
            <img
              className="portal-hero__logo"
              src={product.logo}
              alt={product.logoAlt}
            />
            <p className="portal-hero__kicker">{product.kicker}</p>
            <h3>{product.name}</h3>
            <p>{product.concept}</p>
          </div>
        ))}
      </div>

      {showFoot ? (
        <p className="portal-hero__foot">
          ActionHub — Plataforma Contextual de Serviços de TI.
        </p>
      ) : null}
    </article>
  );
}
