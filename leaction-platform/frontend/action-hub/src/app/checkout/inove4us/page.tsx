'use client';

import { Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import axios from 'axios';
import { AlertCircle, Loader2 } from 'lucide-react';
import { CatalogPricingCards } from '@/components/CatalogPricingCards';
import { CheckoutChrome } from '@/components/CheckoutChrome';
import { CheckoutPayerEmailField } from '@/components/CheckoutPayerEmailField';
import { resolveClientBrand } from '@/lib/client-branding';
import {
  fetchCatalogPlans,
  startCatalogCheckout,
  type CatalogPlanPublic,
} from '@/lib/catalog-api';
import { parseReturnOrigin, parseReturnTo } from '@/lib/hub-api';

const APP_ID = 'inove4us';
const BRAND = resolveClientBrand(APP_ID)!;

function CheckoutInove4usContent() {
  const searchParams = useSearchParams();

  const emailFromUrl = useMemo(() => (searchParams.get('email') || '').trim(), [searchParams]);
  const preselectedSku = useMemo(() => (searchParams.get('sku') || '').trim(), [searchParams]);
  const returnOrigin = useMemo(
    () => parseReturnOrigin(searchParams.get('return_origin')),
    [searchParams]
  );
  const returnTo = useMemo(() => parseReturnTo(searchParams.get('return_to')), [searchParams]);

  const [payerEmail, setPayerEmail] = useState(emailFromUrl);
  const [plans, setPlans] = useState<CatalogPlanPublic[]>([]);
  const [loadingPlans, setLoadingPlans] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [selectedSku, setSelectedSku] = useState<string | null>(null);
  const [processingSku, setProcessingSku] = useState<string | null>(null);
  const [checkoutError, setCheckoutError] = useState('');

  // Pedidos com ?checkout= vão ao dashboard (Brick)
  useEffect(() => {
    const checkoutId = (searchParams.get('checkout') || '').trim();
    if (!checkoutId) return;
    const params = new URLSearchParams(searchParams.toString());
    params.set('client', APP_ID);
    window.location.replace(`/dashboard?${params.toString()}`);
  }, [searchParams]);

  useEffect(() => {
    if (emailFromUrl) setPayerEmail(emailFromUrl);
  }, [emailFromUrl]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoadingPlans(true);
      setLoadError('');
      try {
        const items = await fetchCatalogPlans(APP_ID);
        if (cancelled) return;
        if (!items.length) {
          setLoadError(
            'Nenhum plano ativo para inove4us. No Action Hub, abra Admin → Planos e cadastre pacotes.'
          );
        }
        setPlans(items);
        if (preselectedSku) {
          const match = items.find((p) => p.sku === preselectedSku);
          if (match) setSelectedSku(match.sku);
        }
      } catch (err) {
        if (!cancelled) {
          setLoadError(err instanceof Error ? err.message : 'Erro ao carregar planos.');
        }
      } finally {
        if (!cancelled) setLoadingPlans(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [preselectedSku]);

  const iniciarPagamento = useCallback(
    async (plan: CatalogPlanPublic) => {
      const email = payerEmail.trim().toLowerCase();
      if (!email.includes('@')) {
        setCheckoutError('Informe um e-mail válido antes de continuar.');
        return;
      }

      setProcessingSku(plan.sku);
      setCheckoutError('');
      setSelectedSku(plan.sku);

      try {
        const checkoutUrl = await startCatalogCheckout({
          app_id: APP_ID,
          sku: plan.sku,
          subject_id: email,
          return_origin: returnOrigin || undefined,
          return_to: returnTo || '/mesa-do-inovador?paid=1',
        });
        window.location.assign(checkoutUrl);
      } catch (err) {
        console.error('[checkout/inove4us]', err);
        const msg =
          axios.isAxiosError(err) && err.response?.data?.error
            ? String(err.response.data.error)
            : 'Não foi possível iniciar o pagamento.';
        setCheckoutError(msg);
        setProcessingSku(null);
      }
    },
    [payerEmail, returnOrigin, returnTo]
  );

  return (
    <CheckoutChrome brand={BRAND} subtitle="Escolha o pacote e continue para o pagamento">
      <main className="mx-auto max-w-6xl px-4 py-6 pb-16 md:px-6 md:py-10">
        <div className="mb-10 text-center md:text-left">
          <h2 className="text-3xl font-extrabold tracking-tight text-slate-900 md:text-4xl">
            Planos inove4us
          </h2>
          <p className="mt-3 max-w-2xl text-slate-600">
            Selecione o pacote de créditos. Na próxima tela você finaliza o pagamento com a
            identidade inove4us.
          </p>
        </div>

        <CheckoutPayerEmailField
          value={payerEmail}
          onChange={setPayerEmail}
          disabled={!!processingSku}
        />

        {loadingPlans ? (
          <div className="flex items-center justify-center gap-3 py-20 text-slate-600">
            <Loader2 className="size-6 animate-spin" aria-hidden />
            Carregando planos...
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
            selectedSku={selectedSku}
            loadingSku={processingSku}
            onSelect={(plan) => void iniciarPagamento(plan)}
          />
        )}

        {checkoutError ? (
          <p className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
            {checkoutError}
          </p>
        ) : null}
      </main>
    </CheckoutChrome>
  );
}

export default function CheckoutInove4usPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-slate-100 text-slate-600">
          <Loader2 className="size-8 animate-spin" aria-hidden />
        </div>
      }
    >
      <CheckoutInove4usContent />
    </Suspense>
  );
}
