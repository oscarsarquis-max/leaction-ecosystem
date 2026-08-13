'use client';

import { Suspense, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { AlertCircle, Loader2, Mail } from 'lucide-react';
import { CatalogPricingCards } from '@/components/CatalogPricingCards';
import { CheckoutChrome } from '@/components/CheckoutChrome';
import { resolveClientBrand } from '@/lib/client-branding';
import { fetchCatalogPlans, type CatalogPlanPublic } from '@/lib/catalog-api';

const APP_ID = 'inove4us-school';
const BRAND = resolveClientBrand(APP_ID)!;

function PedidoRecebido() {
  return (
    <main className="mx-auto max-w-2xl px-4 py-16 md:px-6">
      <div className="rounded-2xl border border-emerald-200 bg-white p-8 text-center shadow-sm">
        <Mail className="mx-auto mb-4 size-10 text-emerald-700" aria-hidden />
        <h2 className="text-2xl font-bold text-slate-900">Pedido recebido</h2>
        <p className="mt-3 text-slate-600">
          Pagamento em processamento. As credenciais de acesso à Torre de Controle serão enviadas
          para o e-mail informado no cadastro. Confira também a caixa de spam.
        </p>
        <p className="mt-4 text-sm text-slate-500">
          Ainda não existe sessão nesta página — o primeiro acesso é pelo link do e-mail.
        </p>
        <Link
          href="/ecossistema"
          className="mt-8 inline-flex rounded-xl bg-emerald-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-emerald-900"
        >
          Voltar à vitrine
        </Link>
      </div>
    </main>
  );
}

function EcossistemaHome() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const pedidoOk = searchParams.get('pedido') === 'ok';

  const [plans, setPlans] = useState<CatalogPlanPublic[]>([]);
  const [loadingPlans, setLoadingPlans] = useState(true);
  const [loadError, setLoadError] = useState('');

  useEffect(() => {
    if (pedidoOk) return undefined;
    let cancelled = false;
    (async () => {
      setLoadingPlans(true);
      setLoadError('');
      try {
        const items = await fetchCatalogPlans(APP_ID);
        if (cancelled) return;
        if (!items.length) {
          setLoadError(
            'Não há planos disponíveis no momento. Tente novamente em alguns minutos ou fale com o suporte.'
          );
        }
        setPlans(items);
      } catch {
        if (!cancelled) {
          setLoadError(
            'Não foi possível carregar os planos agora. Verifique sua conexão e tente novamente.'
          );
        }
      } finally {
        if (!cancelled) setLoadingPlans(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [pedidoOk]);

  const subtitle = useMemo(
    () =>
      pedidoOk ? 'Confirme o e-mail de acesso' : 'Planos da Torre de Controle para a sua escola',
    [pedidoOk]
  );

  return (
    <CheckoutChrome brand={BRAND} subtitle={subtitle}>
      {pedidoOk ? (
        <PedidoRecebido />
      ) : (
        <main className="mx-auto max-w-6xl px-4 py-8 pb-16 md:px-6 md:py-12">
          <div className="mb-10 max-w-3xl">
            <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-emerald-800">
              Ecossistema inove4us
            </p>
            <h2 className="mt-3 text-3xl font-extrabold tracking-tight text-slate-900 md:text-4xl">
              Uma torre de controle para a escola. Uma mesa de trabalho para o professor.
            </h2>
            <p className="mt-4 text-slate-600">
              Contrate o inove4us School por aqui. Não é preciso criar conta nesta página: escolha o
              plano, informe os dados da escola no passo seguinte e conclua o pagamento. As
              credenciais chegam no e-mail do cadastro.
            </p>
          </div>

          {loadingPlans ? (
            <div className="flex items-center justify-center gap-3 py-20 text-slate-600">
              <Loader2 className="size-6 animate-spin" aria-hidden />
              Carregando planos…
            </div>
          ) : loadError ? (
            <div
              className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-red-800"
              role="alert"
            >
              <AlertCircle className="mt-0.5 size-5 shrink-0" aria-hidden />
              <p>{loadError}</p>
            </div>
          ) : (
            <CatalogPricingCards
              plans={plans}
              brand={BRAND}
              ctaLabel="Contratar"
              onSelect={(plan) => {
                router.push(`/ecossistema/contratar?sku=${encodeURIComponent(plan.sku)}`);
              }}
            />
          )}
        </main>
      )}
    </CheckoutChrome>
  );
}

export default function EcossistemaPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-stone-100 text-stone-600">
          <Loader2 className="size-8 animate-spin" aria-hidden />
        </div>
      }
    >
      <EcossistemaHome />
    </Suspense>
  );
}
