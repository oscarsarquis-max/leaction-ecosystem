'use client';

import { useEffect, useState } from 'react';
import axios from 'axios';
import {
  getHubApiBase,
  MP_PUBLIC_KEY,
  type PaymentConfigResponse,
} from '@/lib/hub-api';

export type HubPaymentConfig = {
  mpEnabled: boolean;
  checkoutMode: 'card' | 'subscription';
  paymentAmount: number;
  loading: boolean;
};

export function useHubPaymentConfig(): HubPaymentConfig {
  const [loading, setLoading] = useState(true);
  const [mpEnabled, setMpEnabled] = useState(Boolean(MP_PUBLIC_KEY));
  const [checkoutMode, setCheckoutMode] = useState<'card' | 'subscription'>('card');
  const [paymentAmount, setPaymentAmount] = useState(1);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data } = await axios.get<PaymentConfigResponse>(
          `${getHubApiBase()}/config/payments`,
          { timeout: 8000 }
        );
        if (cancelled) return;
        setMpEnabled(Boolean(data.mercadopago_enabled && MP_PUBLIC_KEY));
        setCheckoutMode(data.checkout_mode === 'subscription' ? 'subscription' : 'card');
        if (typeof data.paneldx_payment_amount === 'number' && data.paneldx_payment_amount > 0) {
          setPaymentAmount(data.paneldx_payment_amount);
        } else if (typeof data.subscription?.amount === 'number' && data.subscription.amount > 0) {
          setPaymentAmount(data.subscription.amount);
        }
      } catch {
        if (!cancelled) {
          setMpEnabled(Boolean(MP_PUBLIC_KEY));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return {
    mpEnabled,
    checkoutMode,
    paymentAmount,
    loading,
  };
}
