'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { initMercadoPago, CardPayment } from '@mercadopago/sdk-react';
import axios from 'axios';
import { Loader2 } from 'lucide-react';
import { getHubApiBase, MP_PUBLIC_KEY } from '@/lib/hub-api';

type MercadoPagoSubscriptionBrickProps = {
  payerEmail: string;
  orderId: string;
  amount?: number;
  checkoutMode?: 'card' | 'subscription';
  /** Preferir a public_key do gateway (/config/payments) — evita mismatch com NEXT_PUBLIC. */
  publicKey?: string;
  onSuccess: () => void;
  onError: (message: string) => void;
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

function formatBrickError(err: unknown): string {
  if (axios.isAxiosError(err) && err.response?.data) {
    const body = err.response.data as {
      error?: string;
      mp_status_detail?: string;
      hint?: string;
    };
    if (body.error) {
      let msg = body.mp_status_detail ? `${body.error} (${body.mp_status_detail})` : body.error;
      if (body.hint) msg += ` — ${body.hint}`;
      return msg;
    }
  }
  if (err instanceof Error && err.message) return err.message;
  return 'Não foi possível processar o pagamento. Verifique os dados do cartão.';
}

export function MercadoPagoSubscriptionBrick({
  payerEmail,
  orderId,
  amount = 1,
  checkoutMode = 'card',
  publicKey: publicKeyProp,
  onSuccess,
  onError,
}: MercadoPagoSubscriptionBrickProps) {
  const [ready, setReady] = useState(false);
  const [showBrick, setShowBrick] = useState(false);
  const [brickMounted, setBrickMounted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [brickIssue, setBrickIssue] = useState('');
  const onErrorRef = useRef(onError);
  const onSuccessRef = useRef(onSuccess);

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
  }, [onError, onSuccess]);

  useEffect(() => {
    if (!publicKey) {
      onErrorRef.current('Chave pública do Mercado Pago não configurada (NEXT_PUBLIC_MP_PUBLIC_KEY).');
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
  }, [ready, emailReady, orderId]);

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

      setSubmitting(true);
      setBrickIssue('');
      try {
        if (isCardMode) {
          const { data } = await axios.post(
            `${getHubApiBase()}/payments/card`,
            {
              card_token_id: token,
              payment_method_id: paymentMethodId,
              payer_email: stableEmail,
              order_id: orderId,
              installments: formData.installments || 1,
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
        const msg = formatBrickError(err);
        setBrickIssue(msg);
        onErrorRef.current(msg);
        throw err instanceof Error ? err : new Error(msg);
      } finally {
        setSubmitting(false);
      }
    },
    [isCardMode, orderId, stableEmail]
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
      if (ignoredWhileTyping.has(message)) {
        return;
      }
      const msg =
        message.includes('Secure Fields') || message.includes('secure_fields')
          ? 'O Brick do Mercado Pago não carregou (Public Key desatualizada). Use o botão "Pagar sandbox (sem Brick)" abaixo.'
          : message || 'Erro ao carregar o formulário Mercado Pago. Recarregue a página e tente novamente.';
      setBrickIssue(msg);
      onErrorRef.current(msg);
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
          Processando pagamento...
        </div>
      ) : null}

      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
          {isCardMode
            ? `Pagamento — R$ ${brickAmount.toFixed(2).replace('.', ',')}`
            : `Assinatura mensal — R$ ${brickAmount.toFixed(2).replace('.', ',')}`}
        </p>
        <p className="mb-4 text-xs text-slate-500">
          Sandbox: cartão <strong>5031 4332 1540 6351</strong>, CVV <strong>123</strong>, validade futura,
          titular <strong>APRO</strong>, CPF <strong>123.456.789-09</strong>.
        </p>
        {brickIssue ? (
          <p className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
            {brickIssue}
          </p>
        ) : null}

        {!brickMounted ? (
          <div className="mb-3 flex items-center gap-2 py-6 text-sm text-slate-500">
            <Loader2 className="size-4 animate-spin" />
            Montando formulário Mercado Pago...
          </div>
        ) : null}

        {showBrick ? (
          <CardPayment
            id={brickContainerId}
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
