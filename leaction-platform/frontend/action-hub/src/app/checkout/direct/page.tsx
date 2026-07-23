'use client';

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import axios from 'axios';
import { AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';
import { CheckoutChrome } from '@/components/CheckoutChrome';
import { CheckoutPayerEmailField } from '@/components/CheckoutPayerEmailField';
import { MercadoPagoSubscriptionBrick } from '@/components/MercadoPagoSubscriptionBrick';
import { resolveClientBrand } from '@/lib/client-branding';
import {
  buildClientReturnUrl,
  getHubApiBase,
  parseReturnOrigin,
  parseReturnTo,
} from '@/lib/hub-api';
import {
  fetchPanelDxAddon,
  formatPanelDxCurrency,
  formatPanelDxSeatLabel,
  parseAddonIdParam,
  parseClientIdParam,
  type PanelDxAddonVitrine,
} from '@/lib/paneldx-api';
import { useHubPaymentConfig } from '@/lib/use-hub-payment-config';
import { isPanelDxHubLinked } from '@/lib/paneldx-hub-link';
import { PanelDxUnlinkedNotice } from '@/components/PanelDxUnlinkedNotice';

const PANELDX_BRAND = resolveClientBrand('paneldx')!;

function CheckoutDirectContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const startedRef = useRef(false);
  const { checkoutMode, mpEnabled, publicKey: mpPublicKey } = useHubPaymentConfig();

  const clientId = useMemo(() => parseClientIdParam(searchParams.get('client_id')), [searchParams]);
  const addonId = useMemo(() => parseAddonIdParam(searchParams.get('addon_id')), [searchParams]);
  const emailFromUrl = useMemo(() => (searchParams.get('email') || '').trim(), [searchParams]);
  const returnOrigin = useMemo(() => parseReturnOrigin(searchParams.get('return_origin')), [searchParams]);
  const returnTo = useMemo(() => parseReturnTo(searchParams.get('return_to')), [searchParams]);
  const clientReturnUrl = useMemo(
    () => buildClientReturnUrl(returnOrigin, returnTo),
    [returnOrigin, returnTo]
  );

  const [addon, setAddon] = useState<PanelDxAddonVitrine | null>(null);
  const [payerEmail, setPayerEmail] = useState(emailFromUrl);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [checkoutOrderId, setCheckoutOrderId] = useState('');
  const [paymentAmount, setPaymentAmount] = useState<number | null>(null);
  const [startingPayment, setStartingPayment] = useState(false);
  const [checkoutError, setCheckoutError] = useState('');

  useEffect(() => {
    if (emailFromUrl) setPayerEmail(emailFromUrl);
  }, [emailFromUrl]);

  const iniciarPagamento = useCallback(
    async (addonItem: PanelDxAddonVitrine) => {
      if (!clientId) {
        setCheckoutError('Identificador do cliente (client_id) ausente na URL.');
        return;
      }
      const email = payerEmail.trim();
      if (!email.includes('@')) {
        setCheckoutError('Informe um e-mail válido para continuar.');
        return;
      }

      setStartingPayment(true);
      setCheckoutError('');

      const paneldxOrigin =
        returnOrigin || process.env.NEXT_PUBLIC_PANELDX_URL || 'http://localhost:3000';
      const webhookUrl =
        (process.env.NEXT_PUBLIC_PANELDX_ADDON_WEBHOOK_URL || '').trim() ||
        `${paneldxOrigin.replace(/\/$/, '')}/api/webhooks/ativar-addon`;

      try {
        const res = await axios.post(`${getHubApiBase()}/v1/payments`, {
          client_id: 'paneldx',
          sku: 'PANELDX_ADDON',
          amount: addonItem.valor_mensal,
          id_clie: Number(clientId),
          id_plano: addonItem.id,
          plano_nome: addonItem.nome,
          quantidade: 1,
          customer: {
            email,
            name: 'Cliente PanelDX',
          },
          webhook_url: webhookUrl,
          hub_public_url: typeof window !== 'undefined' ? window.location.origin : '',
          return_to: returnTo,
          return_origin: returnOrigin,
        });

        const orderId = String(res.data?.payment_id || '').trim();
        if (!orderId) {
          throw new Error('Gateway não retornou payment_id.');
        }

        setCheckoutOrderId(orderId);
        setPaymentAmount(Number(addonItem.valor_mensal));

        const params = new URLSearchParams(searchParams.toString());
        params.set('checkout', orderId);
        router.replace(`/checkout/direct?${params.toString()}`, { scroll: false });
      } catch (err) {
        console.error('[checkout/direct]', err);
        const msg =
          axios.isAxiosError(err) && err.response?.data?.error
            ? String(err.response.data.error)
            : 'Não foi possível iniciar o pagamento.';
        setCheckoutError(msg);
      } finally {
        setStartingPayment(false);
      }
    },
    [clientId, payerEmail, returnOrigin, returnTo, router, searchParams]
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!addonId) {
        setLoadError('Parâmetro addon_id ausente na URL.');
        setLoading(false);
        return;
      }
      setLoading(true);
      setLoadError('');
      try {
        const item = await fetchPanelDxAddon(addonId, searchParams);
        if (cancelled) return;
        setAddon(item);
      } catch (err) {
        if (!cancelled) {
          setLoadError(err instanceof Error ? err.message : 'Erro ao carregar pacote.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [addonId, searchParams]);

  useEffect(() => {
    const checkoutId = (searchParams.get('checkout') || '').trim();
    if (checkoutId) {
      setCheckoutOrderId(checkoutId);
      if (addon) setPaymentAmount(Number(addon.valor_mensal));
      return;
    }
    if (!addon || startedRef.current || loading || loadError) return;
    if (!clientId || !payerEmail.trim().includes('@')) return;
    startedRef.current = true;
    void iniciarPagamento(addon);
  }, [addon, clientId, payerEmail, iniciarPagamento, loadError, loading, searchParams]);

  const checkoutFromUrl = searchParams.get('checkout') || checkoutOrderId;

  return (
    <CheckoutChrome brand={PANELDX_BRAND} subtitle="Pacote adicional de licenças">
      <main className="mx-auto max-w-3xl px-4 py-6 pb-16 md:px-6 md:py-10">
        <div className="mb-8 text-center md:text-left">
          <h2 className="text-3xl font-extrabold tracking-tight text-slate-900 md:text-4xl">
            Resumo do pedido
          </h2>
          <p className="mt-3 text-slate-600">
            Compra expressa de pacote extra — sem vitrine de planos. Liberação imediata após o
            pagamento.
          </p>
          {clientId ? (
            <p className="mt-2 text-sm font-medium text-slate-500">
              Cliente <strong>#{clientId}</strong>
              {payerEmail ? ` · ${payerEmail}` : ''}
            </p>
          ) : null}
        </div>

        {loading || startingPayment ? (
          <div className="flex items-center justify-center gap-3 py-16 text-slate-600">
            <Loader2 className="size-6 animate-spin" aria-hidden />
            {startingPayment ? 'Preparando pagamento...' : 'Carregando pacote...'}
          </div>
        ) : loadError ? (
          <div
            className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-red-800"
            role="alert"
          >
            <AlertCircle className="mt-0.5 size-5 shrink-0" aria-hidden />
            <p>{loadError}</p>
          </div>
        ) : addon ? (
          <article className="rounded-2xl border-2 bg-white p-6 shadow-lg md:p-8" style={{ borderColor: PANELDX_BRAND.colors.accent }}>
            <h3 className="text-2xl font-bold" style={{ color: PANELDX_BRAND.colors.accentHover }}>
              {addon.nome}
            </h3>
            <p className="mt-4 text-3xl font-black text-slate-900">
              {formatPanelDxCurrency(addon.valor_mensal)}
              <span className="ml-2 text-base font-semibold text-slate-500">
                / {addon.periodicidade || 'Mensal'}
              </span>
            </p>
            <p
              className="mt-4 inline-flex rounded-lg px-3 py-1.5 text-sm font-bold"
              style={{
                color: PANELDX_BRAND.colors.accentHover,
                backgroundColor: `${PANELDX_BRAND.colors.accent}14`,
              }}
            >
              {formatPanelDxSeatLabel(addon.max_usuarios)}
            </p>
            <ul className="mt-6 space-y-2 text-sm text-slate-700">
              <li className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 size-4 shrink-0" style={{ color: PANELDX_BRAND.colors.success }} />
                Soma ao limite do seu plano base — sem upgrade de plano
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 size-4 shrink-0" style={{ color: PANELDX_BRAND.colors.success }} />
                Ativação automática na tela Meu Time após confirmação
              </li>
            </ul>
          </article>
        ) : null}

        {checkoutError ? (
          <p className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
            {checkoutError}
          </p>
        ) : null}

        {checkoutFromUrl && addon && paymentAmount ? (
          <section className="mt-10 rounded-2xl border border-slate-200 bg-white p-6 shadow-md md:p-8">
            <h3 className="text-xl font-bold text-slate-900">Pagamento seguro</h3>
            <p className="mt-2 text-sm text-slate-600">
              Pedido <strong>{checkoutFromUrl}</strong> · {formatPanelDxCurrency(paymentAmount)} /{' '}
              {addon.periodicidade}
            </p>
            <div className="mt-6">
              <CheckoutPayerEmailField
                value={payerEmail}
                onChange={setPayerEmail}
                disabled={startingPayment}
              />
              <MercadoPagoSubscriptionBrick
                payerEmail={payerEmail}
                orderId={checkoutFromUrl}
                amount={paymentAmount}
                checkoutMode={checkoutMode}
                publicKey={mpPublicKey}
                onSuccess={() => {
                  if (clientReturnUrl) window.location.assign(clientReturnUrl);
                }}
                onError={(msg) => setCheckoutError(msg)}
              />
            </div>
          </section>
        ) : !checkoutFromUrl && addon && !payerEmail.trim().includes('@') ? (
          <section className="mt-10 rounded-2xl border border-slate-200 bg-white p-6 shadow-md md:p-8">
            <CheckoutPayerEmailField value={payerEmail} onChange={setPayerEmail} />
            <p className="text-sm text-slate-600">
              Informe o e-mail para preparar o pagamento do pacote <strong>{addon.nome}</strong>.
            </p>
          </section>
        ) : null}
      </main>
    </CheckoutChrome>
  );
}

export default function CheckoutDirectPage() {
  if (!isPanelDxHubLinked()) {
    return <PanelDxUnlinkedNotice title="Checkout de pacote PanelDX indisponível" />;
  }
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-slate-100 text-slate-600">
          <Loader2 className="size-8 animate-spin" aria-hidden />
        </div>
      }
    >
      <CheckoutDirectContent />
    </Suspense>
  );
}
