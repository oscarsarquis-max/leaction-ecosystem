'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { initMercadoPago, CardPayment } from '@mercadopago/sdk-react';
import axios from 'axios';
import { Loader2 } from 'lucide-react';
import { getHubApiBase, MP_PUBLIC_KEY } from '@/lib/hub-api';
import { presentCardFailure, UNMAPPED } from '@/lib/card-refusal';
import { CPF_FORM_MESSAGE, cardDocumentForSubmit } from '@/lib/card-payer';

type MercadoPagoSubscriptionBrickProps = {
  payerEmail: string;
  orderId: string;
  amount?: number;
  checkoutMode?: 'card' | 'subscription';
  /** Preferir a public_key do gateway (/config/payments) — evita mismatch com NEXT_PUBLIC. */
  publicKey?: string;
  /** Só exibe cartões de teste quando true (credenciais TEST-). */
  sandboxMode?: boolean;
  onSuccess: () => void;
  onError: (message: string) => void;
  /** Recusa do cartão: a tela pai mostra o aviso uma vez e o caminho de Pix. */
  onCardRefused?: (message: string) => void;
  /** CPF digitado no formulário. Na Loja ele é obrigatório. */
  payerDocument?: string;
  requirePayerDocument?: boolean;
};

type CardPaymentFormData = {
  token?: string;
  payment_method_id?: string;
  installments?: number;
  issuer_id?: string;
  transaction_amount?: number;
};

let mercadoPagoInitialized = false;
let mercadoPagoPublicKey = '';

function normalizeBrickAmount(value: number | undefined): number {
  const n = Math.round(Number(value || 0) * 100) / 100;
  if (!Number.isFinite(n) || n <= 0) return 0.01;
  return n;
}

function ensureMercadoPagoInit(publicKey: string) {
  if (!publicKey) return;
  if (mercadoPagoInitialized && mercadoPagoPublicKey === publicKey) return;
  initMercadoPago(publicKey, { locale: 'pt-BR' });
  mercadoPagoInitialized = true;
  mercadoPagoPublicKey = publicKey;
}

function formatBrickError(err: unknown): { message: string; refused: boolean } {
  if (axios.isAxiosError(err) && err.response?.data) {
    const body = err.response.data as {
      mp_status_detail?: string;
      pending?: boolean;
    };
    const detail = String(body.mp_status_detail || '').trim();
    if (detail) console.warn('[pagamento] status_detail', detail);
    if (err.response.status === 202 || body.pending) {
      return presentCardFailure({ status: 202, mp_status_detail: detail });
    }
    return presentCardFailure({ status: err.response.status, mp_status_detail: detail });
  }
  return { message: UNMAPPED, refused: true };
}

export function MercadoPagoSubscriptionBrick({
  payerEmail,
  orderId,
  amount = 1,
  checkoutMode = 'card',
  publicKey: publicKeyProp,
  sandboxMode = false,
  onSuccess,
  onError,
  onCardRefused,
  payerDocument = '',
  requirePayerDocument = false,
}: MercadoPagoSubscriptionBrickProps) {
  const [ready, setReady] = useState(false);
  const [showBrick, setShowBrick] = useState(false);
  const [brickMounted, setBrickMounted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [brickTimedOut, setBrickTimedOut] = useState(false);
  const [brickNonce, setBrickNonce] = useState(0);
  const onErrorRef = useRef(onError);
  const onSuccessRef = useRef(onSuccess);
  const onCardRefusedRef = useRef(onCardRefused);
  const payerDocumentRef = useRef(payerDocument);

  const publicKey = (publicKeyProp || MP_PUBLIC_KEY || '').trim();
  const stableEmail = payerEmail.trim();
  const emailReady = stableEmail.includes('@');
  const isCardMode = checkoutMode !== 'subscription';
  const brickAmount = normalizeBrickAmount(amount);
  const brickContainerId = useMemo(
    () => `cardPaymentBrick_${orderId.replace(/[^a-zA-Z0-9_-]/g, '')}`,
    [orderId]
  );

  const initialization = useMemo(
    () => ({
      amount: brickAmount,
      payer: {
        email: stableEmail,
      },
    }),
    [brickAmount, stableEmail]
  );

  const customization = useMemo(
    () => ({
      paymentMethods: {
        maxInstallments: brickAmount < 10 ? 1 : 12,
        minInstallments: 1,
      },
    }),
    [brickAmount]
  );

  useEffect(() => {
    onErrorRef.current = onError;
    onSuccessRef.current = onSuccess;
    onCardRefusedRef.current = onCardRefused;
    payerDocumentRef.current = payerDocument;
  }, [onError, onSuccess, onCardRefused, payerDocument]);

  useEffect(() => {
    if (!publicKey) {
      onErrorRef.current('Pagamento indisponível no momento. Tente novamente em instantes.');
      return;
    }
    ensureMercadoPagoInit(publicKey);
    setReady(true);
  }, [publicKey]);

  useEffect(() => {
    if (!ready || !emailReady) {
      setShowBrick(false);
      setBrickMounted(false);
      return;
    }
    const timer = window.setTimeout(() => setShowBrick(true), 200);
    return () => window.clearTimeout(timer);
  }, [ready, emailReady, orderId, brickNonce]);

  useEffect(() => {
    if (!showBrick || brickMounted) {
      setBrickTimedOut(false);
      return;
    }
    const timer = window.setTimeout(() => setBrickTimedOut(true), 20000);
    return () => window.clearTimeout(timer);
  }, [showBrick, brickMounted, brickNonce]);

  const handleReady = useCallback(() => {
    setBrickMounted(true);
  }, []);

  const handleSubmit = useCallback(
    async (formData: CardPaymentFormData) => {
      const token = formData?.token;
      const paymentMethodId = formData?.payment_method_id;

      if (!token) {
        const msg = 'Token do cartão não gerado pelo Mercado Pago.';
        onErrorRef.current(msg);
        throw new Error(msg);
      }

      if (!stableEmail.includes('@')) {
        const msg = 'Informe um e-mail válido antes de pagar.';
        onErrorRef.current(msg);
        throw new Error(msg);
      }

      if (!orderId) {
        const msg = 'Pedido de checkout inválido.';
        onErrorRef.current(msg);
        throw new Error(msg);
      }

      if (isCardMode && !paymentMethodId) {
        const msg = 'Método de pagamento não identificado pelo Mercado Pago.';
        onErrorRef.current(msg);
        throw new Error(msg);
      }

      const documentGate = cardDocumentForSubmit(
        payerDocumentRef.current,
        isCardMode && requirePayerDocument,
      );
      if (!documentGate.ok) {
        onErrorRef.current(documentGate.message);
        throw new Error(documentGate.message);
      }

      setSubmitting(true);
      try {
        if (isCardMode) {
          const brickForm = formData as CardPaymentFormData & {
            payer?: { identification?: { type?: string; number?: string } };
            identification?: { type?: string; number?: string };
          };
          const payerId = requirePayerDocument
            ? null
            : brickForm.payer?.identification || brickForm.identification || null;
          const { data } = await axios.post(
            `${getHubApiBase()}/payments/card`,
            {
              card_token_id: token,
              payment_method_id: paymentMethodId,
              payer_email: stableEmail,
              order_id: orderId,
              installments: formData.installments || 1,
              ...(payerId ? { payer_identification: payerId } : {}),
              ...(documentGate.digits ? { payer_document: documentGate.digits } : {}),
            },
            { timeout: 45000 }
          );

          if (data.already_paid || data.success) {
            onSuccessRef.current();
            return;
          }

          const msg = 'Pagamento não confirmado pelo gateway.';
          onErrorRef.current(msg);
          throw new Error(msg);
        }

        await axios.post(
          `${getHubApiBase()}/subscriptions/preapproval`,
          {
            card_token_id: token,
            payer_email: stableEmail,
            order_id: orderId,
          },
          { timeout: 45000 }
        );
        onSuccessRef.current();
      } catch (err: unknown) {
        const formatted = formatBrickError(err);
        if (formatted.refused && onCardRefusedRef.current) {
          onCardRefusedRef.current(formatted.message);
        } else {
          onErrorRef.current(formatted.message);
        }
        throw err instanceof Error ? err : new Error(formatted.message);
      } finally {
        setSubmitting(false);
      }
    },
    [isCardMode, orderId, requirePayerDocument, stableEmail]
  );

  const handleBrickError = useCallback(
    (error: { message?: string; type?: string; cause?: string }) => {
      if (error?.type === 'non_critical') {
        return;
      }
      const ignoredWhileTyping = new Set([
        'no_payment_method_for_provided_bin',
        'missing_payment_information',
      ]);
      const message = String(error?.message || error?.cause || '').trim();
      if (ignoredWhileTyping.has(message) || message === CPF_FORM_MESSAGE) {
        return;
      }
      const msg =
        message.includes('Secure Fields') || message.includes('secure_fields')
          ? 'Não foi possível carregar o formulário de pagamento. Tente novamente ou fale com o suporte.'
          : UNMAPPED;
      if (onCardRefusedRef.current) onCardRefusedRef.current(msg);
      else onErrorRef.current(msg);
    },
    []
  );

  if (!publicKey) {
    return (
      <p className="text-sm text-amber-700" role="alert">
        Configure NEXT_PUBLIC_MP_PUBLIC_KEY no .env.local para habilitar o checkout com Mercado Pago.
      </p>
    );
  }

  if (!orderId) {
    return (
      <p className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800" role="alert">
        Pedido de checkout inválido. Volte à seleção de plano e tente novamente.
      </p>
    );
  }

  if (!ready) {
    return (
      <div className="flex items-center justify-center gap-2 py-8 text-slate-500">
        <Loader2 className="size-5 animate-spin" />
        Carregando formulário de pagamento...
      </div>
    );
  }

  if (!emailReady) {
    return (
      <p className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800" role="status">
        Confirme o e-mail na etapa anterior para liberar o formulário do cartão.
      </p>
    );
  }

  return (
    <div className="mp-brick-root">
      {submitting ? (
        <div className="mb-3 flex items-center gap-2 text-sm font-medium text-slate-700">
          <Loader2 className="size-4 animate-spin" />
          {isCardMode ? 'Processando o pagamento…' : 'Processando sua autorização…'}
        </div>
      ) : null}

      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
          {isCardMode
            ? `Pagamento — R$ ${brickAmount.toFixed(2).replace('.', ',')}`
            : `Assinatura mensal — R$ ${brickAmount.toFixed(2).replace('.', ',')}`}
        </p>
        {sandboxMode || publicKey.startsWith('TEST-') ? (
          <p className="mb-4 text-xs text-slate-500">
            Ambiente de teste: use o cartão de demonstração indicado pelo suporte para simular o
            pagamento.
          </p>
        ) : (
          <p className="mb-4 text-xs text-slate-500">
            Ambiente seguro — os dados do cartão vão direto ao Mercado Pago.
          </p>
        )}

        {!brickMounted && !brickTimedOut ? (
          <div className="mb-3 flex items-center gap-2 py-6 text-sm text-slate-500">
            <Loader2 className="size-4 animate-spin" />
            Preparando o formulário de pagamento…
          </div>
        ) : null}
        {brickTimedOut && !brickMounted ? (
          <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-3 text-sm text-amber-950" role="alert">
            <p>O formulário do Mercado Pago demorou para abrir. Nenhuma cobrança foi feita.</p>
            <button
              type="button"
              className="mt-2 font-semibold underline"
              onClick={() => {
                setBrickTimedOut(false);
                setShowBrick(false);
                setBrickMounted(false);
                setBrickNonce((current) => current + 1);
              }}
            >
              Tentar carregar de novo
            </button>
          </div>
        ) : null}

        {showBrick ? (
          <CardPayment
            key={`${brickContainerId}-${brickNonce}`}
            id={`${brickContainerId}_${brickNonce}`}
            locale="pt-BR"
            initialization={initialization}
            customization={customization}
            onSubmit={handleSubmit}
            onError={handleBrickError}
            onReady={handleReady}
          />
        ) : null}
      </div>
    </div>
  );
}
