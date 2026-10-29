'use client';

import { Suspense, useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import axios from 'axios';
import { AlertCircle, Loader2 } from 'lucide-react';
import { CheckoutChrome } from '@/components/CheckoutChrome';
import { lojaBrand } from '@/lib/client-branding';
import { lojaCheckoutTitle, lojaConsentBeforeCard, LOJA_EMAIL_HINT } from '@/lib/loja-checkout-copy';
import { safeLojaReturnOrigin, safeLojaReturnTo } from '@/lib/loja-return';
import {
  fetchCatalogPlans,
  formatCatalogCurrency,
  startCatalogCheckout,
  type CatalogPlanPublic,
} from '@/lib/catalog-api';

const APP_ID = 'lojadepaes';
const BRAND = lojaBrand();

function LojaContratarContent() {
  const search = useSearchParams();
  const sku = (search.get('sku') || '').trim();
  const returnOrigin = safeLojaReturnOrigin(search.get('return_origin'));
  const returnTo = safeLojaReturnTo(search.get('return_to'));
  const emailFromLoja = (search.get('email') || '').trim().toLowerCase();

  const [plan, setPlan] = useState<CatalogPlanPublic | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [payerEmail, setPayerEmail] = useState(emailFromLoja);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setLoadError('');
      try {
        const items = await fetchCatalogPlans(APP_ID);
        if (cancelled) return;
        const match = items.find((item) => item.sku === sku) || null;
        if (!match) {
          setLoadError('Oferta não encontrada. Volte aos planos e escolha novamente.');
        }
        setPlan(match);
      } catch {
        if (!cancelled) setLoadError('Não foi possível carregar a oferta agora.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sku]);

  const plansHref = `/loja?${new URLSearchParams({
    return_origin: returnOrigin,
    return_to: returnTo,
    ...(emailFromLoja ? { email: emailFromLoja } : {}),
  }).toString()}`;

  const iniciarPagamento = useCallback(async () => {
    if (!plan) return;
    const email = payerEmail.trim().toLowerCase();
    if (!email.includes('@')) {
      setFormError(LOJA_EMAIL_HINT);
      return;
    }
    setSubmitting(true);
    setFormError('');
    try {
      const checkoutUrl = await startCatalogCheckout({
        app_id: APP_ID,
        sku: plan.sku,
        subject_id: email,
        subject_type: 'customer',
        payer_email: email,
        return_origin: returnOrigin,
        return_to: returnTo,
      });
      window.location.assign(checkoutUrl);
    } catch (err) {
      const msg =
        axios.isAxiosError(err) && (err.response?.data as { error?: string } | undefined)?.error
          ? String((err.response?.data as { error?: string }).error)
          : 'Não foi possível iniciar o pagamento.';
      setFormError(
        axios.isAxiosError(err) && err.code === 'ECONNABORTED'
          ? 'A preparação do pagamento demorou. Tente de novo. Nenhuma cobrança foi feita nesta etapa.'
          : msg,
      );
      setSubmitting(false);
    }
  }, [plan, payerEmail, returnOrigin, returnTo]);

  const isPack = plan?.type === 'credit_pack';

  return (
    <CheckoutChrome
      brand={BRAND}
      title={lojaCheckoutTitle(isPack ? 'pack' : 'subscription')}
      subtitle={isPack ? 'Compra avulsa de consultas de IA' : 'Assinatura mensal'}
    >
      <main className="mx-auto max-w-xl px-4 py-8 pb-16 md:px-6 md:py-12">
        <Link href={plansHref} className="text-sm font-semibold hover:underline" style={{ color: BRAND.colors.accent }}>
          ← Voltar aos planos
        </Link>

        {loading ? (
          <div className="mt-16 flex items-center justify-center gap-3 text-slate-600">
            <Loader2 className="size-6 animate-spin" aria-hidden />
            Carregando oferta…
          </div>
        ) : loadError || !plan ? (
          <div
            className="mt-8 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-red-800"
            role="alert"
          >
            <AlertCircle className="mt-0.5 size-5 shrink-0" aria-hidden />
            <p>{loadError || 'Oferta indisponível.'}</p>
          </div>
        ) : (
          <>
            <div className="mt-6 rounded-2xl border border-stone-200 bg-white p-5">
              <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">
                {isPack ? 'Compra avulsa' : 'Assinatura mensal'}
              </p>
              <h2 className="mt-1 text-xl font-bold text-slate-900">{plan.name}</h2>
              <p className="mt-2 text-2xl font-black text-slate-900">
                {formatCatalogCurrency(plan.price, plan.currency)}
                <span className="ml-1 text-base font-semibold text-slate-500">
                  {isPack ? 'avulso' : '/mês'}
                </span>
              </p>
              {plan.credits != null ? (
                <p className="mt-2 text-sm" style={{ color: BRAND.colors.accentHover }}>
                  {plan.credits} consultas de IA
                </p>
              ) : null}
              <p className="mt-3 text-sm leading-relaxed text-slate-600">
                {isPack
                  ? 'Não é assinatura, não renova sozinho e não concede desconto de assinante, crédito de pão nem carimbo de fidelidade.'
                  : '20 consultas de IA por ciclo e 10% de desconto nos produtos vendidos pela Loja, depois da confirmação do pagamento. A autorização do cartão acontece na próxima etapa, no formulário do Mercado Pago — não enviamos e-mail para autorizar a recorrência.'}
              </p>
            </div>

            <form
              className="mt-8 space-y-5"
              onSubmit={(event) => {
                event.preventDefault();
                void iniciarPagamento();
              }}
            >
              <label className="block text-sm font-semibold text-slate-800">
                E-mail da conta da Loja
                <input
                  className="mt-1 w-full rounded-lg border border-stone-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none focus:border-amber-800 focus:ring-2 focus:ring-amber-800/20"
                  type="email"
                  autoComplete="email"
                  value={payerEmail}
                  onChange={(event) => setPayerEmail(event.target.value)}
                  required
                />
              </label>
              <p className="text-xs leading-relaxed text-slate-500">{LOJA_EMAIL_HINT}</p>
              <p className="text-sm leading-relaxed text-slate-600">{lojaConsentBeforeCard(isPack ? 'pack' : 'subscription')}</p>
              {formError ? (
                <p className="text-sm text-red-700" role="alert">
                  {formError}
                </p>
              ) : null}
              <button
                type="submit"
                disabled={submitting}
                className="inline-flex min-h-12 w-full items-center justify-center rounded-xl px-4 py-3 text-sm font-bold text-white disabled:cursor-wait disabled:opacity-70"
                style={{ backgroundColor: BRAND.colors.accent }}
              >
                {submitting
                  ? 'Preparando o pagamento…'
                  : isPack
                    ? 'Ir para o pagamento do pacote'
                    : 'Ir para autorizar a assinatura'}
              </button>
            </form>
          </>
        )}
      </main>
    </CheckoutChrome>
  );
}

export default function LojaContratarPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center text-slate-600">
          <Loader2 className="size-6 animate-spin" aria-hidden />
        </div>
      }
    >
      <LojaContratarContent />
    </Suspense>
  );
}
