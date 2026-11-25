'use client';

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import axios from 'axios';
import { initMercadoPago, CardPayment } from '@mercadopago/sdk-react';
import { AlertCircle, CheckCircle2, Copy, Loader2 } from 'lucide-react';
import { CheckoutChrome } from '@/components/CheckoutChrome';
import { resolveClientBrand } from '@/lib/client-branding';
import { getHubApiBase } from '@/lib/hub-api';
import { PayerCpf, cpfDigits, CPF_FORM_MESSAGE } from '@/lib/card-payer';
import { presentCardFailure, UNMAPPED } from '@/lib/card-refusal';

const BRAND = resolveClientBrand('lojadepaes')!;

type SellerPix = {
  qr_code: string | null;
  qr_code_base64: string | null;
  ticket_url: string | null;
  date_of_expiration: string | null;
};

type SellerPublicCharge = {
  charge_id: string;
  amount_cents: number;
  description: string;
  payer_email: string | null;
  seller_nickname: string | null;
  public_key: string | null;
  status: string;
  method: string | null;
  pix: SellerPix | null;
  return_to: string | null;
};

type CardFormData = {
  token?: string;
  payment_method_id?: string;
  installments?: number;
  issuer_id?: string;
};

let mpInitKey = '';

function ensureMp(publicKey: string) {
  if (!publicKey) return;
  if (mpInitKey === publicKey) return;
  initMercadoPago(publicKey, { locale: 'pt-BR' });
  mpInitKey = publicKey;
}

function formatCents(cents: number): string {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(
    (Number(cents) || 0) / 100
  );
}

function SellerCheckoutContent() {
  const searchParams = useSearchParams();
  const chargeId = useMemo(() => (searchParams.get('charge') || '').trim(), [searchParams]);
  const token = useMemo(() => (searchParams.get('t') || '').trim(), [searchParams]);

  const [charge, setCharge] = useState<SellerPublicCharge | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [tab, setTab] = useState<'pix' | 'card'>('pix');
  const [copied, setCopied] = useState(false);
  const [cardError, setCardError] = useState('');
  const [cpf, setCpf] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [brickReady, setBrickReady] = useState(false);
  const cpfRef = useRef(cpf);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    cpfRef.current = cpf;
  }, [cpf]);

  const fetchPublic = useCallback(async () => {
    if (!chargeId || !token) {
      setLoadError('Link de pagamento incompleto.');
      setLoading(false);
      return null;
    }
    const res = await axios.get<SellerPublicCharge>(
      `${getHubApiBase()}/v1/sellers/charges/${encodeURIComponent(chargeId)}/public`,
      { params: { t: token }, timeout: 20000 }
    );
    return res.data;
  }, [chargeId, token]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setLoadError('');
      try {
        const data = await fetchPublic();
        if (cancelled || !data) return;
        setCharge(data);
        if (data.public_key) ensureMp(data.public_key);
      } catch (err) {
        if (cancelled) return;
        const status = axios.isAxiosError(err) ? err.response?.status : 0;
        if (status === 404) {
          setLoadError('Pagamento indisponível no momento.');
        } else if (status === 401) {
          setLoadError('Link de pagamento inválido ou expirado.');
        } else {
          setLoadError(
            axios.isAxiosError(err) && err.response?.data?.error
              ? String(err.response.data.error)
              : 'Não foi possível carregar a cobrança.'
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [fetchPublic]);

  useEffect(() => {
    if (!charge || charge.status === 'PAID') return;
    if (charge.status !== 'PENDING') return;

    pollRef.current = setInterval(async () => {
      try {
        const data = await fetchPublic();
        if (!data) return;
        setCharge(data);
        if (data.status === 'PAID' && data.return_to) {
          window.location.assign(data.return_to);
        }
      } catch {
        /* silencioso no poll */
      }
    }, 8000);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [charge?.status, charge?.return_to, fetchPublic]);

  const amountReais = useMemo(
    () => Math.round((Number(charge?.amount_cents) || 0)) / 100,
    [charge?.amount_cents]
  );

  const copyPix = useCallback(async () => {
    const code = charge?.pix?.qr_code;
    if (!code) return;
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCardError('Não foi possível copiar o código Pix.');
    }
  }, [charge?.pix?.qr_code]);

  const onCardSubmit = useCallback(
    async (formData: CardFormData) => {
      if (!chargeId || !token || !charge) {
        throw new Error('Cobrança inválida.');
      }
      const digits = cpfDigits(cpfRef.current);
      if (!digits) {
        setCardError(CPF_FORM_MESSAGE);
        throw new Error(CPF_FORM_MESSAGE);
      }
      if (!formData.token || !formData.payment_method_id) {
        setCardError('Dados do cartão incompletos.');
        throw new Error('Dados do cartão incompletos.');
      }
      setSubmitting(true);
      setCardError('');
      try {
        const { data } = await axios.post(
          `${getHubApiBase()}/v1/sellers/charges/${encodeURIComponent(chargeId)}/card`,
          {
            token: formData.token,
            payment_method_id: formData.payment_method_id,
            issuer_id: formData.issuer_id,
            installments: formData.installments || 1,
            payer: {
              email: charge.payer_email || '',
              identification: { type: 'CPF', number: digits },
            },
          },
          { params: { t: token }, timeout: 45000 }
        );
        if (data?.status === 'PAID') {
          if (charge.return_to) window.location.assign(charge.return_to);
          else setCharge({ ...charge, status: 'PAID' });
          return;
        }
        if (data?.status === 'PENDING') {
          setCharge({ ...charge, status: 'PENDING', method: 'card' });
          setCardError('Pagamento em análise. Aguarde a confirmação.');
          return;
        }
        setCardError(UNMAPPED);
        throw new Error(UNMAPPED);
      } catch (err) {
        if (axios.isAxiosError(err) && err.response?.data) {
          const body = err.response.data as { mp_status_detail?: string; error?: string };
          const detail = String(body.mp_status_detail || '').trim();
          if (detail) {
            const formatted = presentCardFailure({
              status: err.response.status,
              mp_status_detail: detail,
            });
            setCardError(formatted.message);
            throw err;
          }
          if (body.error) {
            setCardError(String(body.error));
            throw err;
          }
        }
        const msg = err instanceof Error ? err.message : UNMAPPED;
        setCardError(msg);
        throw err instanceof Error ? err : new Error(msg);
      } finally {
        setSubmitting(false);
      }
    },
    [charge, chargeId, token]
  );

  const nickname = charge?.seller_nickname?.trim() || 'parceiro';

  return (
    <CheckoutChrome brand={BRAND} subtitle="Pagamento ao parceiro">
      <main className="mx-auto max-w-3xl px-4 py-6 pb-16 md:px-6 md:py-10">
        <div className="mb-8 text-center md:text-left">
          <h2 className="text-3xl font-extrabold tracking-tight text-slate-900 md:text-4xl">
            Pagamento
          </h2>
          <p className="mt-3 text-slate-600">
            Pagamento para <strong>{nickname}</strong>
          </p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center gap-3 py-16 text-slate-600">
            <Loader2 className="size-6 animate-spin" aria-hidden />
            Carregando cobrança...
          </div>
        ) : loadError ? (
          <div
            className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-red-800"
            role="alert"
          >
            <AlertCircle className="mt-0.5 size-5 shrink-0" aria-hidden />
            <p>{loadError}</p>
          </div>
        ) : charge?.status === 'PAID' ? (
          <div
            className="flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-emerald-900"
            role="status"
          >
            <CheckCircle2 className="mt-0.5 size-5 shrink-0" aria-hidden />
            <div>
              <p className="font-semibold">Pagamento confirmado</p>
              <p className="mt-1 text-sm">
                {charge.return_to
                  ? 'Redirecionando…'
                  : 'Você já pode fechar esta página.'}
              </p>
            </div>
          </div>
        ) : charge ? (
          <>
            <article
              className="rounded-2xl border-2 bg-white p-6 shadow-lg md:p-8"
              style={{ borderColor: BRAND.colors.accent }}
            >
              <h3
                className="text-2xl font-bold"
                style={{ color: BRAND.colors.accentHover }}
              >
                {charge.description}
              </h3>
              <p className="mt-4 text-3xl font-black text-slate-900">
                {formatCents(charge.amount_cents)}
              </p>
              {charge.payer_email ? (
                <p className="mt-2 text-sm text-slate-500">{charge.payer_email}</p>
              ) : null}
            </article>

            {charge.status !== 'PENDING' ? (
              <p
                className="mt-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
                role="status"
              >
                Esta cobrança está como {charge.status} e não aceita novo pagamento.
              </p>
            ) : (
              <section className="mt-10 rounded-2xl border border-slate-200 bg-white p-6 shadow-md md:p-8">
                <div className="mb-6 flex gap-2 border-b border-slate-200 pb-3">
                  <button
                    type="button"
                    className={`rounded-lg px-4 py-2 text-sm font-semibold ${
                      tab === 'pix' ? 'text-white' : 'text-slate-600 hover:bg-slate-50'
                    }`}
                    style={
                      tab === 'pix'
                        ? { backgroundColor: BRAND.colors.accent }
                        : undefined
                    }
                    onClick={() => setTab('pix')}
                  >
                    Pix
                  </button>
                  <button
                    type="button"
                    className={`rounded-lg px-4 py-2 text-sm font-semibold ${
                      tab === 'card' ? 'text-white' : 'text-slate-600 hover:bg-slate-50'
                    }`}
                    style={
                      tab === 'card'
                        ? { backgroundColor: BRAND.colors.accent }
                        : undefined
                    }
                    onClick={() => setTab('card')}
                  >
                    Cartão
                  </button>
                </div>

                {tab === 'pix' ? (
                  <div className="space-y-4">
                    {charge.pix?.qr_code_base64 ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={`data:image/png;base64,${charge.pix.qr_code_base64}`}
                        alt="QR Code Pix"
                        className="mx-auto h-48 w-48 rounded-lg border border-slate-200 bg-white p-2"
                      />
                    ) : (
                      <p className="text-sm text-slate-600">
                        QR Code indisponível. Use o código copia e cola abaixo.
                      </p>
                    )}
                    {charge.pix?.qr_code ? (
                      <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">
                          Pix copia e cola
                        </label>
                        <div className="flex gap-2">
                          <input
                            readOnly
                            value={charge.pix.qr_code}
                            className="w-full rounded-xl border border-slate-300 px-3 py-3 text-xs text-slate-700"
                            aria-label="Código Pix"
                          />
                          <button
                            type="button"
                            onClick={() => void copyPix()}
                            className="inline-flex shrink-0 items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold text-white"
                            style={{ backgroundColor: BRAND.colors.accent }}
                          >
                            <Copy className="size-4" aria-hidden />
                            {copied ? 'Copiado' : 'Copiar'}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <p className="text-sm text-amber-800" role="status">
                        Aguarde a geração do Pix ou atualize a página.
                      </p>
                    )}
                    <p className="text-xs text-slate-500">
                      Após pagar, esta página confirma automaticamente em alguns segundos.
                    </p>
                  </div>
                ) : (
                  <div>
                    {!charge.public_key ? (
                      <p className="text-sm text-amber-800" role="alert">
                        Conta do recebedor sem chave pública. Peça para reconectar o Mercado Pago.
                      </p>
                    ) : !charge.payer_email?.includes('@') ? (
                      <p className="text-sm text-amber-800" role="alert">
                        Cobrança sem e-mail do pagador — cartão indisponível.
                      </p>
                    ) : (
                      <>
                        <PayerCpf value={cpf} onChange={setCpf} />
                        {submitting ? (
                          <div className="mb-3 flex items-center gap-2 text-sm text-slate-700">
                            <Loader2 className="size-4 animate-spin" aria-hidden />
                            Processando o pagamento…
                          </div>
                        ) : null}
                        {!brickReady ? (
                          <div className="mb-3 flex items-center gap-2 py-4 text-sm text-slate-500">
                            <Loader2 className="size-4 animate-spin" aria-hidden />
                            Preparando o formulário…
                          </div>
                        ) : null}
                        <CardPayment
                          locale="pt-BR"
                          initialization={{
                            amount: amountReais > 0 ? amountReais : 0.01,
                            payer: { email: charge.payer_email || '' },
                          }}
                          customization={{
                            paymentMethods: {
                              maxInstallments: amountReais < 10 ? 1 : 12,
                              minInstallments: 1,
                            },
                          }}
                          onSubmit={onCardSubmit}
                          onReady={() => setBrickReady(true)}
                          onError={(error) => {
                            if (error?.type === 'non_critical') return;
                            setCardError(UNMAPPED);
                          }}
                        />
                      </>
                    )}
                  </div>
                )}

                {cardError ? (
                  <p
                    className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
                    role="alert"
                  >
                    {cardError}
                  </p>
                ) : null}
              </section>
            )}
          </>
        ) : null}
      </main>
    </CheckoutChrome>
  );
}

export default function CheckoutSellerPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-slate-100 text-slate-600">
          <Loader2 className="size-8 animate-spin" aria-hidden />
        </div>
      }
    >
      <SellerCheckoutContent />
    </Suspense>
  );
}
