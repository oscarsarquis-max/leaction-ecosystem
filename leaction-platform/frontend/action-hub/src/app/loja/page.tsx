'use client';

import { Suspense, useEffect, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { AlertCircle, Loader2 } from 'lucide-react';
import { CatalogPricingCards } from '@/components/CatalogPricingCards';
import { CheckoutChrome } from '@/components/CheckoutChrome';
import { lojaBrand } from '@/lib/client-branding';
import { lojaReturnHref, safeLojaReturnOrigin, safeLojaReturnTo } from '@/lib/loja-return';
import { fetchCatalogPlans, type CatalogPlanPublic } from '@/lib/catalog-api';

const APP_ID = 'lojadepaes';
const BRAND = lojaBrand();

function LojaPlansContent() {
  const router = useRouter();
  const search = useSearchParams();
  const returnOrigin = safeLojaReturnOrigin(search.get('return_origin'));
  const returnTo = safeLojaReturnTo(search.get('return_to'));
  const email = (search.get('email') || '').trim();

  const [plans, setPlans] = useState<CatalogPlanPublic[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setLoadError('');
      try {
        const items = await fetchCatalogPlans(APP_ID);
        if (!cancelled) setPlans(items);
      } catch {
        if (!cancelled) setLoadError('Não foi possível carregar os planos agora.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const back = useMemo(() => lojaReturnHref(returnOrigin, returnTo), [returnOrigin, returnTo]);

  return (
    <CheckoutChrome brand={BRAND} title="Planos da Biblioteca" subtitle="Planos da Biblioteca">
      <main className="mx-auto max-w-5xl px-4 py-10 md:px-6 md:py-14">
        <a href={back} className="text-sm font-semibold hover:underline" style={{ color: BRAND.colors.accent }}>
          ← Voltar à Loja de Pães
        </a>
        <h1 className="mt-6 text-3xl font-black tracking-tight text-slate-900">Planos da Loja de Pães</h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-slate-600">
          A assinatura mensal traz 20 consultas de IA por ciclo e 10% de desconto nos produtos
          vendidos pela Loja. O pacote adicional é compra avulsa: 10 consultas de IA, sem renovação
          automática e sem desconto de assinante. Contratação e pagamento ficam nestes planos da
          Loja — não entram no pedido de pães.
        </p>

        {loading ? (
          <div className="mt-16 flex items-center justify-center gap-3 text-slate-600">
            <Loader2 className="size-6 animate-spin" aria-hidden />
            Carregando planos…
          </div>
        ) : loadError ? (
          <div
            className="mt-8 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-red-800"
            role="alert"
          >
            <AlertCircle className="mt-0.5 size-5 shrink-0" aria-hidden />
            <p>{loadError}</p>
          </div>
        ) : (
          <div className="mt-10">
            <CatalogPricingCards
              plans={plans}
              brand={BRAND}
              highlightMiddle={false}
              creditsNoun="consulta de IA"
              onSelect={(plan) => {
                const params = new URLSearchParams({
                  sku: plan.sku,
                  return_origin: returnOrigin,
                  return_to: returnTo,
                });
                if (email) params.set('email', email);
                router.push(`/loja/contratar?${params.toString()}`);
              }}
            />
          </div>
        )}
      </main>
    </CheckoutChrome>
  );
}

export default function LojaPlansPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center text-slate-600">
          <Loader2 className="size-6 animate-spin" aria-hidden />
        </div>
      }
    >
      <LojaPlansContent />
    </Suspense>
  );
}
