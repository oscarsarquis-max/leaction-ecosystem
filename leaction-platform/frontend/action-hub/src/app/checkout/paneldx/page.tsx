'use client';

import { Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import axios from 'axios';
import { AlertCircle, Loader2 } from 'lucide-react';
import { CheckoutChrome } from '@/components/CheckoutChrome';
import { CheckoutPayerEmailField } from '@/components/CheckoutPayerEmailField';
import { PanelDxPricingCards } from '@/components/PanelDxPricingCards';
import { resolveClientBrand } from '@/lib/client-branding';
import {
  getHubApiBase,
  parseReturnOrigin,
  parseReturnTo,
} from '@/lib/hub-api';
import {
  fetchPanelDxPlanosVitrine,
  parseClientIdParam,
  parsePlanIdParam,
  parseAddonIdParam,
  type PanelDxPlanoVitrine,
} from '@/lib/paneldx-api';
import { isPanelDxHubLinked } from '@/lib/paneldx-hub-link';
import { PanelDxUnlinkedNotice } from '@/components/PanelDxUnlinkedNotice';

const PANELDX_BRAND = resolveClientBrand('paneldx')!;

function CheckoutPanelDxContent() {
  const searchParams = useSearchParams();

  const clientId = useMemo(() => parseClientIdParam(searchParams.get('client_id')), [searchParams]);
  const emailFromUrl = useMemo(() => (searchParams.get('email') || '').trim(), [searchParams]);
  const preselectedPlanId = useMemo(() => parsePlanIdParam(searchParams.get('plan_id')), [searchParams]);
  const idMatuHandoff = useMemo(() => parseAddonIdParam(searchParams.get('id_matu')), [searchParams]);
  const returnOrigin = useMemo(() => parseReturnOrigin(searchParams.get('return_origin')), [searchParams]);
  const returnTo = useMemo(() => parseReturnTo(searchParams.get('return_to')), [searchParams]);

  const [payerEmail, setPayerEmail] = useState(emailFromUrl);
  const [planos, setPlanos] = useState<PanelDxPlanoVitrine[]>([]);
  const [loadingPlanos, setLoadingPlanos] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null);
  const [processingPlanId, setProcessingPlanId] = useState<number | null>(null);
  const [checkoutError, setCheckoutError] = useState('');

  // Pedidos com ?checkout= devem ir ao dashboard (pagamento + histórico).
  useEffect(() => {
    const checkoutId = (searchParams.get('checkout') || '').trim();
    if (!checkoutId) return;
    const params = new URLSearchParams(searchParams.toString());
    params.set('client', 'paneldx');
    window.location.replace(`/dashboard?${params.toString()}`);
  }, [searchParams]);

  useEffect(() => {
    if (emailFromUrl) setPayerEmail(emailFromUrl);
  }, [emailFromUrl]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoadingPlanos(true);
      setLoadError('');
      try {
        const items = await fetchPanelDxPlanosVitrine();
        if (cancelled) return;
        if (!items.length) {
          setLoadError(
            'Nenhum plano no cache do ActionHub. No CRM PanelDX, use "Salvar e publicar vitrine".'
          );
        }
        setPlanos(items);
        if (preselectedPlanId) {
          const match = items.find((p) => String(p.id) === preselectedPlanId);
          if (match) setSelectedPlanId(match.id);
        }
      } catch (err) {
        if (!cancelled) {
          setLoadError(err instanceof Error ? err.message : 'Erro ao carregar vitrine.');
        }
      } finally {
        if (!cancelled) setLoadingPlanos(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [preselectedPlanId]);

  const iniciarPagamento = useCallback(
    async (plano: PanelDxPlanoVitrine) => {
      if (!clientId) {
        setCheckoutError('Identificador do cliente (client_id) ausente na URL.');
        return;
      }
      const email = payerEmail.trim();
      if (!email.includes('@')) {
        setCheckoutError('Informe um e-mail válido antes de assinar.');
        return;
      }

      setProcessingPlanId(plano.id);
      setCheckoutError('');
      setSelectedPlanId(plano.id);

      const webhookUrl =
        (process.env.NEXT_PUBLIC_PANELDX_WEBHOOK_URL || '').trim() ||
        `${returnOrigin || process.env.NEXT_PUBLIC_PANELDX_URL || 'http://localhost:3000'}/api/hub/payment-webhook`;

      try {
        const res = await axios.post(`${getHubApiBase()}/v1/payments`, {
          client_id: 'paneldx',
          sku: 'PANELDX_SUBSCRIPTION',
          amount: plano.valor_mensal,
          id_clie: Number(clientId),
          id_plano: plano.id,
          id_matu: idMatuHandoff ? Number(idMatuHandoff) : undefined,
          plano_nome: plano.nome,
          periodicidade: plano.periodicidade,
          customer: {
            email,
            name: 'Cliente PanelDX',
          },
          webhook_url: webhookUrl,
          hub_public_url: typeof window !== 'undefined' ? window.location.origin : '',
          return_to: returnTo,
          return_origin: returnOrigin,
        });

        const checkoutUrl = String(res.data?.checkout_url || '').trim();
        if (!checkoutUrl) {
          throw new Error('Gateway não retornou checkout_url.');
        }

        window.location.assign(checkoutUrl);
      } catch (err) {
        console.error('[checkout/paneldx]', err);
        const msg =
          axios.isAxiosError(err) && err.response?.data?.error
            ? String(err.response.data.error)
            : 'Não foi possível iniciar o pagamento.';
        setCheckoutError(msg);
        setProcessingPlanId(null);
      }
    },
    [clientId, idMatuHandoff, payerEmail, returnOrigin, returnTo]
  );

  return (
    <CheckoutChrome
      brand={PANELDX_BRAND}
      subtitle="Escolha o plano ideal para sua empresa"
    >
      <main className="mx-auto max-w-6xl px-4 py-6 pb-16 md:px-6 md:py-10">
        <div className="mb-10 text-center md:text-left">
          <h2 className="text-3xl font-extrabold tracking-tight text-slate-900 md:text-4xl">
            Planos PanelDX
          </h2>
          <p className="mt-3 max-w-2xl text-slate-600">
            Selecione o plano e continue para o pagamento. Na próxima tela você verá seu histórico
            de compras e o checkout Mercado Pago.
          </p>
          {clientId ? (
            <p className="mt-2 text-sm font-medium text-slate-500">
              Contratação vinculada ao cliente <strong>#{clientId}</strong>
            </p>
          ) : (
            <p className="mt-2 text-sm font-medium text-amber-700">
              Acesso via PanelDX recomendado — parâmetro <code>client_id</code> ausente.
            </p>
          )}
        </div>

        <CheckoutPayerEmailField
          value={payerEmail}
          onChange={setPayerEmail}
          disabled={!!processingPlanId}
        />

        {loadingPlanos ? (
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
          <PanelDxPricingCards
            planos={planos}
            brand={PANELDX_BRAND}
            clientId={clientId}
            selectedPlanId={selectedPlanId}
            loadingPlanId={processingPlanId}
            onAssinar={(plano) => void iniciarPagamento(plano)}
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

export default function CheckoutPanelDxPage() {
  if (!isPanelDxHubLinked()) {
    return <PanelDxUnlinkedNotice title="Checkout PanelDX indisponível" />;
  }
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-slate-100 text-slate-600">
          <Loader2 className="size-8 animate-spin" aria-hidden />
        </div>
      }
    >
      <CheckoutPanelDxContent />
    </Suspense>
  );
}
