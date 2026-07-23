'use client';

import { Suspense, useEffect, useMemo, useState, type ReactNode } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import axios from 'axios';
import {
  BookOpen,
  CheckCircle2,
  Clock3,
  CreditCard,
  LayoutDashboard,
  Link2,
  Loader2,
  Mail,
  Lock,
  UserRound
} from 'lucide-react';
import { useCart } from '@/context/CartContext';
import { useHubSession } from '@/context/HubSessionContext';
import { MercadoPagoSubscriptionBrick } from '@/components/MercadoPagoSubscriptionBrick';
import { CheckoutChrome } from '@/components/CheckoutChrome';
import { BackToHubHome } from '@/components/BackToHubHome';
import { parseClientId, resolveClientBrand, type ClientBrandTheme } from '@/lib/client-branding';
import { getHubApiBase, MP_PUBLIC_KEY, buildClientReturnUrl, parseCheckoutOrderId, parseReturnTo, parseReturnOrigin, MP_SUBSCRIPTION_AMOUNT } from '@/lib/hub-api';
import { useAdminGate } from '@/lib/require-admin';

function cartItemsToSkus(items: { id?: string | number; sku?: string }[]): string[] {
  return items
    .map((item) => {
      const sku = item.sku != null ? String(item.sku).trim() : '';
      if (sku) return sku;
      return String(item.id ?? '').trim();
    })
    .filter(Boolean);
}

type OrderStatus = 'PENDING' | 'PAID' | string;

type Order = {
  id: string;
  status: OrderStatus;
  created_at: string;
  product_name: string;
  product_type: string;
  external_resource_id?: string | null;
  product_external_resource_id?: string | null;
};

type DashboardUser = {
  id: string;
  email: string;
  name: string;
  document_id?: string | null;
  phone?: string | null;
  company?: string | null;
  address?: string | null;
  city?: string | null;
  state?: string | null;
};

type DashboardResponse = {
  user: DashboardUser;
  orders: Order[];
};

function isNonEmptyString(value: string | null | undefined): boolean {
  return typeof value === 'string' && value.trim().length > 0;
}

function isProfileComplete(user: DashboardUser | null): boolean {
  if (!user) return false;
  return (
    isNonEmptyString(user.document_id) &&
    isNonEmptyString(user.phone) &&
    isNonEmptyString(user.address)
  );
}

const PANELDX_TYPE = 'PANELDX_ASSESSMENT';

function withCheckoutChrome(
  brand: ClientBrandTheme | null,
  subtitle: string | undefined,
  content: ReactNode
) {
  if (brand) {
    return (
      <CheckoutChrome brand={brand} subtitle={subtitle}>
        {content}
      </CheckoutChrome>
    );
  }
  return content;
}

function orderNeedsReferenceLink(order: Order): boolean {
  return order.product_type === PANELDX_TYPE && !isNonEmptyString(order.external_resource_id ?? undefined);
}

function parseOrderPaymentAmount(order: Order | null): number | null {
  if (!order?.external_resource_id) return null;
  const raw = String(order.external_resource_id).trim();
  if (!raw.startsWith('{')) return null;
  try {
    const parsed = JSON.parse(raw) as { valor_negociado?: unknown; plano_nome?: string };
    const v = Number(parsed.valor_negociado);
    return Number.isFinite(v) && v > 0 ? Math.round(v * 100) / 100 : null;
  } catch {
    return null;
  }
}

function parseOrderPlanLabel(order: Order | null): string | null {
  if (!order?.external_resource_id) return null;
  const raw = String(order.external_resource_id).trim();
  if (!raw.startsWith('{')) return null;
  try {
    const parsed = JSON.parse(raw) as { plano_nome?: string };
    const name = String(parsed.plano_nome || '').trim();
    return name || null;
  } catch {
    return null;
  }
}

/** Pedidos: instante UTC → exibição America/Sao_Paulo. */
const formatDate = (dateString: string) => {
  const raw = String(dateString || '').trim();
  if (!raw) return '—';
  // ISO com Z / offset, ou "YYYY-MM-DD HH:mm:ss" sem fuso (UTC do Hub)
  const hasTz = /([zZ]|[+-]\d{2}:?\d{2})$/.test(raw);
  const normalized = hasTz
    ? raw
    : /^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}/.test(raw)
      ? `${raw.replace(' ', 'T')}Z`
      : raw;
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return raw;
  return new Intl.DateTimeFormat('pt-BR', {
    timeZone: 'America/Sao_Paulo',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
};

function DashboardContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const email = useMemo(() => searchParams.get('email')?.trim() || '', [searchParams]);
  const checkoutParam = useMemo(
    () => parseCheckoutOrderId(searchParams.get('checkout')),
    [searchParams]
  );
  const isCheckoutFlow = checkoutParam.length > 0;
  const returnTo = useMemo(() => parseReturnTo(searchParams.get('return_to')), [searchParams]);
  const returnOrigin = useMemo(() => parseReturnOrigin(searchParams.get('return_origin')), [searchParams]);
  const clientParam = useMemo(() => parseClientId(searchParams.get('client')), [searchParams]);
  const isPartnerCheckout = isCheckoutFlow || clientParam.length > 0;
  const clientReturnUrl = useMemo(
    () => buildClientReturnUrl(returnOrigin, returnTo),
    [returnOrigin, returnTo]
  );
  const apiBase = useMemo(() => getHubApiBase(), []);

  const { cartItems, setCartItems } = useCart();
  const { user: sessionUser, login: hubLogin, adoptEmail } = useHubSession();
  const { isAdmin, hydrated: adminHydrated } = useAdminGate();
  const [emailLogin, setEmailLogin] = useState('');
  const [passwordLogin, setPasswordLogin] = useState('');
  const [loginStatus, setLoginStatus] = useState<'idle' | 'syncing' | 'paying'>('idle');
  const viewParam = useMemo(() => searchParams.get('view')?.trim() || '', [searchParams]);
  const wantsCartOnly = viewParam === 'cart';

  // Admin ops: histórico global fica em /dashboard/admin/payments (não no painel do comprador)
  useEffect(() => {
    if (!adminHydrated || !isAdmin || isCheckoutFlow || wantsCartOnly) return;
    router.replace('/dashboard/admin/payments');
  }, [adminHydrated, isAdmin, isCheckoutFlow, wantsCartOnly, router]);
  const [checkoutSuccess, setCheckoutSuccess] = useState(false);
  const [checkoutError, setCheckoutError] = useState('');
  const [mpEnabled, setMpEnabled] = useState(Boolean(MP_PUBLIC_KEY));
  const [mpCheckoutMode, setMpCheckoutMode] = useState<'card' | 'subscription'>('card');
  const [mpPaymentAmount, setMpPaymentAmount] = useState(1);
  const [mpPublicKey, setMpPublicKey] = useState(MP_PUBLIC_KEY);
  const [mpSandboxPayerEmail, setMpSandboxPayerEmail] = useState('');
  const [mpSandboxMode, setMpSandboxMode] = useState(false);
  const [mpBrickPairValid, setMpBrickPairValid] = useState(true);
  const [mpBrickPairHint, setMpBrickPairHint] = useState('');
  const [mpServerTokenizeFallback, setMpServerTokenizeFallback] = useState(false);
  const [allowPaymentSimulation, setAllowPaymentSimulation] = useState(false);

  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');
  const [userName, setUserName] = useState('LeActioner');
  const [dashboardUser, setDashboardUser] = useState<DashboardUser | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [checkoutDetailOrder, setCheckoutDetailOrder] = useState<Order | null>(null);
  const [checkoutDetailAmount, setCheckoutDetailAmount] = useState<number | null>(null);
  const [checkoutDetailLoading, setCheckoutDetailLoading] = useState(false);

  const [profileDocument, setProfileDocument] = useState('');
  const [profilePhone, setProfilePhone] = useState('');
  const [profileAddress, setProfileAddress] = useState('');
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileFeedback, setProfileFeedback] = useState<{ type: 'ok' | 'err'; text: string } | null>(null);

  const [referenceDrafts, setReferenceDrafts] = useState<Record<string, string>>({});
  const [referenceDraftSuggestedFromProduct, setReferenceDraftSuggestedFromProduct] = useState<
    Record<string, boolean>
  >({});
  const [referenceSavingId, setReferenceSavingId] = useState<string | null>(null);
  const [referenceFeedback, setReferenceFeedback] = useState<Record<string, { type: 'ok' | 'err'; text: string }>>(
    {}
  );
  const [paymentProcessingId, setPaymentProcessingId] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const href = window.location.href;
    const qs = searchParams.toString();
    console.info('[ActionHub Dashboard] URL recebida:', href);
    console.info('[ActionHub Dashboard] query string:', qs || '(vazia)');
    console.info(
      '[ActionHub Dashboard] checkout=',
      checkoutParam || '(ausente)',
      '| email=',
      email || '(ausente)'
    );
    if (!checkoutParam && href.includes('/dashboard')) {
      console.warn('[ActionHub Dashboard] Parametro checkout ausente na URL de dashboard.');
    }
  }, [searchParams, checkoutParam, email]);

  useEffect(() => {
    axios
      .get<{
        mercadopago_enabled: boolean;
        checkout_mode?: 'card' | 'subscription';
        paneldx_payment_amount?: number;
        public_key?: string;
        sandbox_payer_email?: string;
        sandbox_mode?: boolean;
        brick_pair_valid?: boolean;
        brick_pair_hint?: string | null;
        server_tokenize_fallback?: boolean;
        allow_payment_simulation?: boolean;
      }>(`${apiBase}/config/payments`, { timeout: 8000 })
      .then((res) => {
        setAllowPaymentSimulation(Boolean(res.data.allow_payment_simulation));
        if (!isCheckoutFlow) return;
        const gatewayKey = String(res.data.public_key || '').trim();
        if (gatewayKey) setMpPublicKey(gatewayKey);
        const effectiveKey = gatewayKey || MP_PUBLIC_KEY;
        setMpEnabled(Boolean(res.data.mercadopago_enabled && effectiveKey));
        setMpCheckoutMode(res.data.checkout_mode === 'subscription' ? 'subscription' : 'card');
        const sandbox =
          Boolean(res.data.sandbox_mode) ||
          effectiveKey.startsWith('TEST-') ||
          Boolean(res.data.allow_payment_simulation);
        setMpSandboxMode(sandbox);
        setMpSandboxPayerEmail(
          sandbox ? String(res.data.sandbox_payer_email || '').trim() : ''
        );
        setMpBrickPairValid(res.data.brick_pair_valid !== false);
        setMpBrickPairHint(String(res.data.brick_pair_hint || '').trim());
        setMpServerTokenizeFallback(Boolean(res.data.server_tokenize_fallback));
        if (typeof res.data.paneldx_payment_amount === 'number' && res.data.paneldx_payment_amount > 0) {
          setMpPaymentAmount(res.data.paneldx_payment_amount);
        }
      })
      .catch(() => {
        if (isCheckoutFlow) {
          setMpEnabled(Boolean(MP_PUBLIC_KEY));
          setMpSandboxMode(String(MP_PUBLIC_KEY || '').startsWith('TEST-'));
        }
      });
  }, [isCheckoutFlow, apiBase]);

  useEffect(() => {
    const emailFromCheckout = searchParams.get('email')?.trim() || '';
    if (emailFromCheckout && !emailLogin) {
      setEmailLogin(emailFromCheckout);
    }
  }, [searchParams, emailLogin]);

  useEffect(() => {
    if (!dashboardUser || isProfileComplete(dashboardUser)) {
      return;
    }
    setProfileDocument((dashboardUser.document_id ?? '').trim());
    setProfilePhone((dashboardUser.phone ?? '').trim());
    setProfileAddress((dashboardUser.address ?? '').trim());
  }, [dashboardUser]);

  useEffect(() => {
    const fetchOrders = async () => {
      if (!email) {
        setLoading(false);
        setErrorMessage('');
        return;
      }

      try {
        setLoading(true);
        setErrorMessage('');
        setDashboardUser(null);

        const response = await axios.get<DashboardResponse>(
          `${apiBase}/my-orders/${encodeURIComponent(email)}`,
          { timeout: 15000 }
        );
        const u = response.data.user;
        setDashboardUser(u ?? null);
        setUserName(u?.name || 'LeActioner');
        const fetchedOrders = response.data.orders || [];
        setOrders(fetchedOrders);

        // Inicializa sugestoes de codigo de referencia a partir do produto, quando aplicavel
        const initialDrafts: Record<string, string> = {};
        const initialSuggested: Record<string, boolean> = {};
        for (const order of fetchedOrders) {
          if (
            orderNeedsReferenceLink(order) &&
            isNonEmptyString(order.product_external_resource_id ?? undefined)
          ) {
            const suggestion = (order.product_external_resource_id ?? '').trim();
            if (suggestion) {
              initialDrafts[order.id] = suggestion;
              initialSuggested[order.id] = true;
            }
          }
        }
        setReferenceDrafts(initialDrafts);
        setReferenceDraftSuggestedFromProduct(initialSuggested);
      } catch (error: any) {
        const statusCode = error?.response?.status;
        if (statusCode === 404) {
          setErrorMessage('Nao encontramos um LeActioner com este e-mail. Verifique e tente novamente.');
        } else {
          setErrorMessage('Nao foi possivel carregar seus pedidos agora. Tente novamente em instantes.');
        }
        setDashboardUser(null);
        setOrders([]);
      } finally {
        setLoading(false);
      }
    };

    fetchOrders();
  }, [email]);

  const checkoutOrder = useMemo(
    () =>
      isCheckoutFlow
        ? orders.find((order) => order.id === checkoutParam) ?? checkoutDetailOrder
        : null,
    [orders, isCheckoutFlow, checkoutParam, checkoutDetailOrder]
  );

  useEffect(() => {
    if (!isCheckoutFlow || !checkoutParam || !email) {
      setCheckoutDetailOrder(null);
      setCheckoutDetailAmount(null);
      setCheckoutDetailLoading(false);
      return;
    }

    let cancelled = false;
    setCheckoutDetailLoading(true);

    axios
      .get<{ order: Order; payment_amount?: number }>(
        `${apiBase}/orders/${checkoutParam}/checkout`,
        { timeout: 10000 }
      )
      .then((res) => {
        if (cancelled) return;
        if (res.data.order) {
          setCheckoutDetailOrder(res.data.order);
          if (res.data.order.status === 'PAID') {
            setCheckoutSuccess(true);
          }
        }
        if (typeof res.data.payment_amount === 'number' && res.data.payment_amount > 0) {
          setCheckoutDetailAmount(Math.round(res.data.payment_amount * 100) / 100);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setCheckoutDetailOrder(null);
          setCheckoutDetailAmount(null);
        }
      })
      .finally(() => {
        if (!cancelled) setCheckoutDetailLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [isCheckoutFlow, checkoutParam, email, apiBase]);

  const checkoutBrand = useMemo(() => {
    if (!isPartnerCheckout) return null;
    const byClient = resolveClientBrand(clientParam, checkoutOrder?.product_type ?? null);
    if (byClient) return byClient;
    const byProduct = resolveClientBrand(null, checkoutOrder?.product_type ?? null);
    if (byProduct) return byProduct;
    // PanelDX desvinculado do Hub — sem fallback de marca
    return null;
  }, [isPartnerCheckout, clientParam, isCheckoutFlow, checkoutOrder?.product_type]);

  const checkoutPaymentAmount = useMemo(() => {
    const fromOrder = parseOrderPaymentAmount(checkoutOrder);
    if (fromOrder != null) return fromOrder;
    if (checkoutDetailAmount != null && checkoutDetailAmount > 0) return checkoutDetailAmount;
    // Sem valor dinâmico do pedido: não cobrar fallback do .env
    return 0;
  }, [checkoutOrder, checkoutDetailAmount]);

  const checkoutBrickReady =
    Boolean(email) &&
    !loading &&
    !checkoutDetailLoading &&
    checkoutPaymentAmount > 0 &&
    checkoutOrder?.status !== 'PAID';

  // E-mail do cliente (query) — NÃO trocar pelo comprador sandbox no Brick/UI.
  // O gateway já reescreve payer_email para a conta de teste no POST /payments/card.
  const mpPayerEmail = email;

  const checkoutPlanLabel = useMemo(
    () => parseOrderPlanLabel(checkoutOrder),
    [checkoutOrder]
  );

  useEffect(() => {
    if (!isCheckoutFlow || !checkoutParam || loading) return;

    if (checkoutOrder?.status === 'PAID') {
      setCheckoutSuccess(true);
    }
  }, [isCheckoutFlow, checkoutParam, checkoutOrder, loading]);

  useEffect(() => {
    if (!checkoutSuccess) return;
    const timer = window.setTimeout(() => {
      window.location.assign(clientReturnUrl);
    }, 4000);
    return () => window.clearTimeout(timer);
  }, [checkoutSuccess, clientReturnUrl]);

  const handleSaveProfile = async () => {
    if (!email) return;
    setProfileSaving(true);
    setProfileFeedback(null);
    try {
      const { data } = await axios.patch<{ user: DashboardUser }>(
        `${apiBase}/users/${encodeURIComponent(email)}`,
        {
          document_id: profileDocument.trim(),
          phone: profilePhone.trim(),
          address: profileAddress.trim()
        }
      );
      setDashboardUser(data.user);
      setUserName(data.user?.name || 'LeActioner');
      setProfileFeedback({ type: 'ok', text: 'Perfil atualizado com sucesso.' });
    } catch (err: unknown) {
      const msg =
        axios.isAxiosError(err) && err.response?.data && typeof (err.response.data as { error?: string }).error === 'string'
          ? (err.response.data as { error: string }).error
          : 'Nao foi possivel salvar o perfil. Tente novamente.';
      setProfileFeedback({ type: 'err', text: msg });
    } finally {
      setProfileSaving(false);
    }
  };

  const setReferenceDraft = (orderId: string, value: string) => {
    setReferenceDrafts((prev) => ({ ...prev, [orderId]: value }));
    setReferenceDraftSuggestedFromProduct((prev) => {
      const next = { ...prev };
      if (value.trim().length > 0) {
        next[orderId] = false;
      } else {
        delete next[orderId];
      }
      return next;
    });
  };

  const handleLinkReference = async (order: Order) => {
    const raw = (referenceDrafts[order.id] ?? '').trim();
    if (!raw) {
      setReferenceFeedback((prev) => ({
        ...prev,
        [order.id]: { type: 'err', text: 'Informe o codigo de referencia.' }
      }));
      return;
    }
    setReferenceSavingId(order.id);
    setReferenceFeedback((prev) => {
      const next = { ...prev };
      delete next[order.id];
      return next;
    });
    try {
      const { data } = await axios.patch<{ order: { id: string; external_resource_id: string | null } }>(
        `${apiBase}/orders/${order.id}`,
        { external_resource_id: raw }
      );
      const ext = data.order?.external_resource_id ?? raw;
      setOrders((prev) =>
        prev.map((o) => (o.id === order.id ? { ...o, external_resource_id: ext } : o))
      );
      setReferenceFeedback((prev) => ({
        ...prev,
        [order.id]: { type: 'ok', text: 'Referencia vinculada.' }
      }));
    } catch (err: unknown) {
      const msg =
        axios.isAxiosError(err) && err.response?.data && typeof (err.response.data as { error?: string }).error === 'string'
          ? (err.response.data as { error: string }).error
          : 'Nao foi possivel vincular. Tente novamente.';
      setReferenceFeedback((prev) => ({
        ...prev,
        [order.id]: { type: 'err', text: msg }
      }));
    } finally {
      setReferenceSavingId(null);
    }
  };

  const handleSimulatePayment = async (order: Order) => {
    setPaymentProcessingId(order.id);
    try {
      const { data } = await axios.post<{
        success: boolean;
        order: { id: string; status: string };
      }>(`${apiBase}/simular-pagamento`, { order_id: order.id });
      const newStatus = data.order?.status ?? 'PAID';
      setOrders((prev) =>
        prev.map((o) => (o.id === order.id ? { ...o, status: newStatus } : o))
      );
      if (order.id === checkoutParam) {
        setCheckoutSuccess(true);
      }
    } catch (err: unknown) {
      const msg =
        axios.isAxiosError(err) &&
        err.response?.data &&
        typeof (err.response.data as { error?: string }).error === 'string'
          ? (err.response.data as { error: string }).error
          : 'Nao foi possivel finalizar o pagamento. Tente novamente.';
      alert(msg);
    } finally {
      setPaymentProcessingId(null);
    }
  };

  const handleCheckoutPayment = async () => {
    setCheckoutError('');

    const emailTyped = emailLogin.trim() || email;
    if (!emailTyped.includes('@')) {
      alert('Por favor, insira um e-mail valido.');
      return;
    }

    if (!checkoutParam) {
      alert('Pedido de checkout invalido ou ausente na URL.');
      return;
    }

    setLoginStatus('paying');
    try {
      const { data } = await axios.post<{
        success: boolean;
        already_paid?: boolean;
        order: { id: string; status: string };
      }>(`${apiBase}/simular-pagamento`, { order_id: checkoutParam });

      if (data.already_paid || data.order?.status === 'PAID') {
        setCheckoutSuccess(true);
        return;
      }

      setCheckoutSuccess(true);
    } catch (err: unknown) {
      const msg =
        axios.isAxiosError(err) &&
        err.response?.data &&
        typeof (err.response.data as { error?: string }).error === 'string'
          ? (err.response.data as { error: string }).error
          : 'Nao foi possivel confirmar o pagamento. Tente novamente.';
      setCheckoutError(msg);
    } finally {
      setLoginStatus('idle');
    }
  };

  const handleSandboxCardPayment = async () => {
    setCheckoutError('');

    if (!checkoutParam) {
      alert('Pedido de checkout invalido ou ausente na URL.');
      return;
    }

    setLoginStatus('paying');
    try {
      const { data } = await axios.post<{
        success: boolean;
        already_paid?: boolean;
        order: { id: string; status: string };
      }>(`${apiBase}/payments/sandbox-card`, {
        order_id: checkoutParam,
        payer_email: mpPayerEmail || emailLogin.trim() || email,
      });

      if (data.already_paid || data.order?.status === 'PAID') {
        setCheckoutSuccess(true);
        return;
      }

      setCheckoutSuccess(true);
    } catch (err: unknown) {
      const msg =
        axios.isAxiosError(err) &&
        err.response?.data &&
        typeof (err.response.data as { error?: string }).error === 'string'
          ? (err.response.data as { error: string }).error
          : 'Nao foi possivel confirmar o pagamento sandbox. Tente novamente.';
      setCheckoutError(msg);
    } finally {
      setLoginStatus('idle');
    }
  };

  // Sessão do header → URL do dashboard (histórico / checkout)
  useEffect(() => {
    if (email) {
      adoptEmail(email);
      return;
    }
    if (!sessionUser?.email || isCheckoutFlow) return;
    const params = new URLSearchParams(searchParams.toString());
    if (params.get('email') === sessionUser.email) return;
    params.set('email', sessionUser.email);
    router.replace(`/dashboard?${params.toString()}`);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- só reage a sessão/email
  }, [email, sessionUser?.email, isCheckoutFlow, adoptEmail, router]);

  const handleLogin = async (event?: React.FormEvent | React.MouseEvent) => {
    event?.preventDefault();

    const emailTyped = emailLogin.trim();
    if (!emailTyped.includes('@')) {
      alert('Por favor, insira um e-mail valido.');
      return;
    }
    if (passwordLogin.length < 4) {
      alert('Informe a senha (minimo 4 caracteres). No primeiro acesso, ela sera criada.');
      return;
    }

    setLoginStatus('syncing');
    try {
      await hubLogin(emailTyped, passwordLogin);

      if (isCheckoutFlow || clientParam) {
        const params = new URLSearchParams(searchParams.toString());
        params.set('email', emailTyped);
        router.push(`/dashboard?${params.toString()}`);
        return;
      }

      const skus = cartItemsToSkus(cartItems);
      if (skus.length > 0) {
        try {
          await axios.post(`${apiBase}/sync-cart`, {
            email: emailTyped,
            items: skus,
          });
          setCartItems([]);
        } catch (err) {
          console.error(err);
          alert(
            'Login ok, mas nao foi possivel sincronizar o carrinho. Verifique o gateway (porta 4001).'
          );
        }
      }

      router.push('/dashboard?email=' + encodeURIComponent(emailTyped));
    } catch (err) {
      const msg = axios.isAxiosError(err)
        ? String((err.response?.data as { error?: string } | undefined)?.error || err.message)
        : err instanceof Error
          ? err.message
          : 'Falha no login';
      alert(msg);
    } finally {
      setLoginStatus('idle');
    }
  };

  if (checkoutSuccess) {
    const successBody = (
      <main className="min-h-[calc(100vh-60px)] text-slate-900">
        <div className="flex min-h-[calc(100vh-60px)] flex-col items-center justify-center px-6 py-16">
          <div
            className="w-full max-w-lg rounded-3xl border bg-white p-8 text-center shadow-xl"
            style={{
              borderColor: checkoutBrand?.colors.cardBorder ?? '#e7e5e4',
              boxShadow: checkoutBrand
                ? `0 20px 40px ${
                    checkoutBrand.id === 'inove4us'
                      ? 'rgba(127, 29, 29, 0.12)'
                      : 'rgba(249, 115, 22, 0.12)'
                  }`
                : '0 20px 40px rgba(15, 23, 42, 0.08)',
            }}
          >
            <div
              className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full"
              style={{
                backgroundColor: checkoutBrand?.colors.accentMuted ?? '#f1f5f9',
                color: checkoutBrand?.colors.accent ?? '#0f172a',
              }}
            >
              <CheckCircle2 className="size-8" />
            </div>
            <h1 className="text-2xl font-black tracking-tight text-slate-900">Pagamento confirmado!</h1>
            <p className="mt-4 text-sm leading-relaxed text-slate-600">
              {checkoutBrand
                ? `Seu acesso ao ${checkoutBrand.displayName} foi liberado. Voce sera redirecionado automaticamente em alguns segundos.`
                : 'Seu acesso foi liberado. Voce sera redirecionado automaticamente em alguns segundos.'}
            </p>
            <a
              href={clientReturnUrl}
              className="mt-8 inline-flex w-full items-center justify-center rounded-xl py-3.5 text-sm font-bold text-white shadow-lg transition"
              style={{
                backgroundColor: checkoutBrand?.colors.success ?? '#059669',
              }}
              onMouseEnter={(e) => {
                if (checkoutBrand) {
                  e.currentTarget.style.backgroundColor = checkoutBrand.colors.successHover;
                }
              }}
              onMouseLeave={(e) => {
                if (checkoutBrand) {
                  e.currentTarget.style.backgroundColor = checkoutBrand.colors.success;
                }
              }}
            >
              {checkoutBrand ? `Voltar ao ${checkoutBrand.displayName} agora` : 'Voltar ao aplicativo agora'}
            </a>
          </div>
        </div>
      </main>
    );

    return withCheckoutChrome(checkoutBrand, checkoutOrder?.product_name, successBody);
  }

  if (adminHydrated && isAdmin && !isCheckoutFlow && !wantsCartOnly) {
    return (
      <main className="flex min-h-[40vh] items-center justify-center text-sm text-slate-500">
        <Loader2 className="mr-2 size-5 animate-spin" />
        Abrindo painel de pagamentos…
      </main>
    );
  }

  if (!email) {
    const loginBody = (
      <main className="min-h-[calc(100vh-60px)] text-slate-900">
        <div className="flex min-h-[calc(100vh-60px)] flex-col items-center justify-center px-6 py-16">
          <div
            className="w-full max-w-md rounded-3xl border bg-white p-8 shadow-xl"
            style={{ borderColor: checkoutBrand?.colors.cardBorder ?? '#e2e8f0' }}
          >
            <div className="mb-6 text-center">
              <div
                className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl text-white shadow-lg"
                style={{ backgroundColor: checkoutBrand?.colors.accent ?? '#dc2626' }}
              >
                {isCheckoutFlow ? <CreditCard className="size-7" /> : <LayoutDashboard className="size-7" />}
              </div>
              <h1 className="text-2xl font-black tracking-tight text-slate-900">
                {isPartnerCheckout
                  ? 'Identifique-se para pagar'
                  : wantsCartOnly
                    ? 'Finalize seu carrinho'
                    : 'Identifique-se'}
              </h1>
              <p className="mt-2 text-sm text-slate-500">
                {isPartnerCheckout
                  ? checkoutBrand
                    ? `Confirme o mesmo e-mail e senha usados no ${checkoutBrand.displayName} para concluir o pagamento.`
                    : 'Confirme o mesmo e-mail e senha do aplicativo de origem para concluir o pagamento.'
                  : wantsCartOnly
                    ? 'Você pode montar o carrinho sem login. Para comprar ou ver o histórico, entre com e-mail e senha.'
                    : 'Informe e-mail e senha para ver seu histórico. No primeiro acesso, a senha será criada.'}
              </p>
            </div>

            {isPartnerCheckout && (
              <div
                className="mb-6 rounded-2xl border px-4 py-3 text-sm"
                style={{
                  borderColor: checkoutBrand?.colors.infoBorder ?? '#fdba74',
                  backgroundColor: checkoutBrand?.colors.infoBg ?? '#fff7ed',
                  color: checkoutBrand?.colors.infoText ?? '#7c2d12',
                }}
              >
                {checkoutBrand
                  ? `Pedido ${checkoutBrand.displayName} vinculado. Na proxima tela voce vera seus pedidos e o checkout com Mercado Pago.`
                  : 'Pedido vinculado. Na próxima tela você verá seus pedidos e o checkout com Mercado Pago.'}
              </div>
            )}

            {cartItems.length > 0 && !isCheckoutFlow && (
              <div className="mb-6 rounded-2xl border border-emerald-200/80 bg-emerald-50/90 px-4 py-3">
                <p className="text-sm leading-relaxed text-emerald-950">
                  {cartItems.length === 1
                    ? 'Olá! Você tem 1 item selecionado. Informe seu e-mail para salvar esses pedidos e acessar sua área.'
                    : `Olá! Você tem ${cartItems.length} itens selecionados. Informe seu e-mail para salvar esses pedidos e acessar sua área.`}
                </p>
                <ul className="mt-3 space-y-1 border-t border-emerald-200/60 pt-3 text-sm text-emerald-900/90">
                  {cartItems.map((item) => {
                    const label =
                      typeof item.nome === 'string' && item.nome.trim()
                        ? item.nome.trim()
                        : String(item.sku ?? item.id ?? '');
                    return (
                      <li key={String(item.id ?? item.sku ?? label)} className="flex gap-2">
                        <span className="text-emerald-600" aria-hidden>
                          ·
                        </span>
                        <span>{label}</span>
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}

            <form
              onSubmit={(e) => {
                void handleLogin(e);
              }}
            >
            <label className="mb-2 block text-sm font-semibold text-slate-700">E-mail</label>
            <div className="relative mb-4">
              <Mail className="absolute left-3 top-1/2 size-5 -translate-y-1/2 text-slate-400" />
              <input
                type="email"
                autoComplete="username"
                placeholder="voce@empresa.com"
                className="w-full rounded-xl border border-slate-200 bg-slate-50/80 py-3 pl-11 pr-4 text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-red-600 focus:bg-white focus:ring-2 focus:ring-red-600/20"
                value={emailLogin}
                onChange={(e) => setEmailLogin(e.target.value)}
              />
            </div>

            <label className="mb-2 block text-sm font-semibold text-slate-700">Senha</label>
            <div className="relative mb-6">
              <Lock className="absolute left-3 top-1/2 size-5 -translate-y-1/2 text-slate-400" />
              <input
                type="password"
                autoComplete="current-password"
                placeholder="••••••••"
                className="w-full rounded-xl border border-slate-200 bg-slate-50/80 py-3 pl-11 pr-4 text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-red-600 focus:bg-white focus:ring-2 focus:ring-red-600/20"
                value={passwordLogin}
                onChange={(e) => setPasswordLogin(e.target.value)}
              />
            </div>

            <button
              type="submit"
              disabled={loginStatus === 'syncing'}
              className="flex w-full items-center justify-center gap-2 rounded-xl py-3.5 text-sm font-bold text-white shadow-lg transition disabled:cursor-not-allowed disabled:opacity-70"
              style={{
                backgroundColor: checkoutBrand?.colors.accent ?? '#450a0a',
              }}
            >
              {loginStatus === 'syncing' ? (
                <>
                  <Loader2 className="size-5 animate-spin" />
                  Entrando...
                </>
              ) : isPartnerCheckout ? (
                'Continuar para pagar'
              ) : wantsCartOnly ? (
                'Entrar e sincronizar carrinho'
              ) : (
                'Acessar Meu Painel'
              )}
            </button>
            </form>
          </div>
        </div>
      </main>
    );

    return withCheckoutChrome(checkoutBrand, checkoutBrand?.productLabel, loginBody);
  }

  const dashboardBody = (
    <main
      className="min-h-screen text-slate-900"
      style={{ backgroundColor: checkoutBrand?.colors.pageBg ?? '#f8fafc' }}
    >
      <section className="mx-auto max-w-6xl px-4 py-10 pb-16 md:px-8">
        {!checkoutBrand && (
        <div className="mb-8 rounded-3xl bg-gradient-to-r from-red-950 via-red-800 to-red-600 p-8 text-white shadow-lg">
          <BackToHubHome
            label="Voltar ao Action Hub"
            className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-orange-100/90 transition hover:text-white"
          />
          <p className="mb-2 flex items-center gap-2 text-sm/6 font-medium text-orange-100">
            <UserRound size={16} />
            Area do LeActioner
          </p>
          <h1 className="text-3xl font-black tracking-tight md:text-4xl">Bem-vindo, {userName}!</h1>
          <p className="mt-3 text-sm text-orange-100 md:text-base">
            Acompanhe seus pedidos e acesse seus conteudos assim que os pagamentos forem aprovados.
          </p>
          <Link
            href="/dashboard/crm/tracking"
            className="mt-5 inline-flex items-center gap-2 rounded-lg border border-white/25 bg-white/10 px-3 py-1.5 text-xs font-semibold text-orange-50 transition hover:bg-white/20"
          >
            Tracking &amp; Conversão (PLG)
          </Link>
        </div>
        )}

        {checkoutBrand && (
          <div className="mb-8 rounded-2xl border bg-white p-6 shadow-sm" style={{ borderColor: checkoutBrand.colors.cardBorder }}>
            <p className="text-sm font-semibold uppercase tracking-wide" style={{ color: checkoutBrand.colors.accent }}>
              {checkoutBrand.displayName}
            </p>
            <h1 className="mt-1 text-2xl font-black tracking-tight text-slate-900 md:text-3xl">
              Ola, {userName}
            </h1>
            <p className="mt-2 text-sm text-slate-600">{checkoutBrand.productLabel}</p>
          </div>
        )}

        {isCheckoutFlow && checkoutParam && (
          <section
            className="mb-8 rounded-2xl border bg-white p-5 shadow-sm md:p-6"
            style={{ borderColor: checkoutBrand?.colors.cardBorder ?? '#fed7aa' }}
          >
            <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
                  <CreditCard size={20} style={{ color: checkoutBrand?.colors.accent }} />
                  {checkoutBrand ? `Checkout ${checkoutBrand.displayName}` : 'Checkout'}
                </h2>
                <p className="mt-1 text-sm text-slate-600">
                  Pedido <span className="font-mono text-xs">{checkoutParam}</span>
                  {checkoutOrder
                    ? ` — ${checkoutPlanLabel || checkoutOrder.product_name}`
                    : ''}
                  {checkoutPaymentAmount > 0 ? (
                    <>
                      {' '}
                      ·{' '}
                      {new Intl.NumberFormat('pt-BR', {
                        style: 'currency',
                        currency: 'BRL',
                      }).format(checkoutPaymentAmount)}
                    </>
                  ) : null}
                </p>
              </div>
              {checkoutOrder?.status === 'PENDING' && (
                <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800">
                  <Clock3 size={14} />
                  Aguardando pagamento
                </span>
              )}
            </div>

            {!checkoutParam && (
              <p className="text-sm text-red-600">Pedido de checkout invalido na URL.</p>
            )}

            {checkoutOrder?.status === 'PAID' ? (
              <p className="text-sm text-emerald-700">
                Este pedido já foi pago. Você será redirecionado ao app de origem em instantes.
              </p>
            ) : (
              <>
                {checkoutError && (
                  <p className="mb-4 text-sm text-red-600" role="alert">
                    {checkoutError}
                  </p>
                )}

                {mpEnabled ? (
                  <>
                    <p
                      className="mb-3 rounded-lg border px-3 py-2 text-xs"
                      style={{
                        borderColor: checkoutBrand?.colors.infoBorder ?? '#fdba74',
                        backgroundColor: checkoutBrand?.colors.infoBg ?? '#fff7ed',
                        color: checkoutBrand?.colors.infoText ?? '#7c2d12',
                      }}
                    >
                      {mpSandboxMode ? (
                        <>
                          Sandbox Mercado Pago: cartão <strong>5031 4332 1540 6351</strong>, CVV{' '}
                          <strong>123</strong>, validade futura, titular <strong>APRO</strong> e CPF{' '}
                          <strong>123.456.789-09</strong>. Valor cobrado: R${' '}
                          {checkoutPaymentAmount.toFixed(2).replace('.', ',')}.
                          {email ? (
                            <>
                              {' '}
                              Pedido vinculado a <strong>{email}</strong>
                              {mpSandboxPayerEmail ? (
                                <>
                                  {' '}
                                  (cobrança MP sandbox usa {mpSandboxPayerEmail} só no servidor).
                                </>
                              ) : null}
                              .
                            </>
                          ) : null}
                        </>
                      ) : (
                        <>
                          Pagamento em produção. Valor: R${' '}
                          {checkoutPaymentAmount.toFixed(2).replace('.', ',')}.
                          {email ? (
                            <>
                              {' '}
                              Pedido vinculado a <strong>{email}</strong>.
                            </>
                          ) : null}{' '}
                          Use um cartão real.
                        </>
                      )}
                    </p>
                    {!checkoutBrickReady ? (
                      <div className="flex items-center justify-center gap-2 py-10 text-sm text-slate-500">
                        <Loader2 className="size-5 animate-spin" />
                        {loading || checkoutDetailLoading
                          ? 'Carregando dados do pedido...'
                          : 'Aguardando e-mail e valor do pedido para liberar o pagamento...'}
                      </div>
                    ) : (
                      <>
                        {!mpBrickPairValid && mpServerTokenizeFallback ? (
                          <div className="mb-4 space-y-3">
                            <p
                              className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
                              role="alert"
                            >
                              {mpBrickPairHint ||
                                'Não foi possível validar o par Public Key + Access Token do Mercado Pago. Confira as Credenciais de teste no painel MP (mesmo app).'}
                            </p>
                            <button
                              type="button"
                              onClick={() => void handleSandboxCardPayment()}
                              disabled={loginStatus === 'paying'}
                              className="inline-flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-3 text-sm font-bold text-white transition hover:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-70"
                            >
                              {loginStatus === 'paying' ? (
                                <>
                                  <Loader2 className="size-4 animate-spin" />
                                  Processando pagamento sandbox...
                                </>
                              ) : (
                                <>
                                  <CreditCard size={16} />
                                  Pagar sandbox (MP real, sem Brick)
                                </>
                              )}
                            </button>
                          </div>
                        ) : null}
                        <MercadoPagoSubscriptionBrick
                          payerEmail={mpPayerEmail}
                          orderId={checkoutParam}
                          amount={checkoutPaymentAmount}
                          checkoutMode={mpCheckoutMode}
                          publicKey={mpPublicKey}
                          sandboxMode={mpSandboxMode}
                          onSuccess={() => setCheckoutSuccess(true)}
                          onError={(msg) => setCheckoutError(msg)}
                        />
                      </>
                    )}
                    {allowPaymentSimulation ? (
                      <div className="mt-4 rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-3">
                        <p className="mb-2 text-xs text-slate-600">
                          {mpBrickPairValid ? (
                            <>
                              Se o Brick falhar com <strong>Card Token not found (2006)</strong>, o par de
                              credenciais TEST do painel MP está inconsistente.
                            </>
                          ) : (
                            <>
                              O Brick pode falhar com <strong>2006</strong> no sandbox MP. Use{' '}
                              <strong>Pagar sandbox (sem Brick)</strong> acima ou a simulação local abaixo.
                            </>
                          )}
                        </p>
                        <button
                          type="button"
                          onClick={() => void handleCheckoutPayment()}
                          disabled={loginStatus === 'paying'}
                          className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:border-orange-300 hover:text-orange-700 disabled:cursor-not-allowed disabled:opacity-70"
                        >
                          {loginStatus === 'paying' ? (
                            <>
                              <Loader2 className="size-3.5 animate-spin" />
                              Processando...
                            </>
                          ) : (
                            <>
                              <CreditCard size={14} />
                              Simular pagamento (dev)
                            </>
                          )}
                        </button>
                      </div>
                    ) : null}
                  </>
                ) : allowPaymentSimulation ? (
                  <div className="space-y-3">
                    <p className="text-sm text-amber-800">
                      Mercado Pago nao configurado neste ambiente. Use o botao abaixo apenas para
                      testes locais (simulacao).
                    </p>
                    <button
                      type="button"
                      onClick={() => void handleCheckoutPayment()}
                      disabled={loginStatus === 'paying'}
                      className="inline-flex items-center gap-2 rounded-xl px-4 py-3 text-sm font-bold text-white transition disabled:cursor-not-allowed disabled:opacity-70"
                      style={{ backgroundColor: checkoutBrand?.colors.accent ?? '#dc2626' }}
                    >
                      {loginStatus === 'paying' ? (
                        <>
                          <Loader2 className="size-4 animate-spin" />
                          Processando...
                        </>
                      ) : (
                        <>
                          <CreditCard size={16} />
                          Simular pagamento (dev)
                        </>
                      )}
                    </button>
                  </div>
                ) : (
                  <p className="text-sm text-amber-800">
                    Mercado Pago nao configurado neste ambiente. Em producao, configure as chaves
                    APP_USR no gateway.
                  </p>
                )}
              </>
            )}
          </section>
        )}

        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm md:p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900 md:text-xl">
              <BookOpen size={20} />
              Meus Pedidos
            </h2>
          </div>

          {!loading &&
            !errorMessage &&
            dashboardUser &&
            !isAdmin &&
            !isProfileComplete(dashboardUser) && (
            <div className="mb-8 rounded-2xl border border-orange-200/80 bg-orange-50/50 p-5 md:p-6">
              <h3 className="text-base font-bold text-slate-900 md:text-lg">Conclusão de Perfil</h3>
              <p className="mt-1 text-sm text-slate-600">
                Preencha os dados abaixo para concluir seu cadastro e liberar o acompanhamento completo dos seus pedidos.
              </p>
              <div className="mt-5 grid gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-slate-600">
                    Documento
                  </label>
                  <input
                    type="text"
                    autoComplete="off"
                    className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-red-600 focus:ring-2 focus:ring-red-600/20"
                    value={profileDocument}
                    onChange={(e) => setProfileDocument(e.target.value)}
                    placeholder="CPF ou documento"
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-slate-600">
                    Telefone
                  </label>
                  <input
                    type="tel"
                    autoComplete="tel"
                    className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-red-600 focus:ring-2 focus:ring-red-600/20"
                    value={profilePhone}
                    onChange={(e) => setProfilePhone(e.target.value)}
                    placeholder="Com DDD"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-slate-600">
                    Endereço
                  </label>
                  <input
                    type="text"
                    autoComplete="street-address"
                    className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-red-600 focus:ring-2 focus:ring-red-600/20"
                    value={profileAddress}
                    onChange={(e) => setProfileAddress(e.target.value)}
                    placeholder="Logradouro, numero, complemento"
                  />
                </div>
              </div>
              {profileFeedback && (
                <p
                  className={`mt-3 text-sm ${profileFeedback.type === 'ok' ? 'text-emerald-700' : 'text-red-600'}`}
                  role="status"
                >
                  {profileFeedback.text}
                </p>
              )}
              <div className="mt-4">
                <button
                  type="button"
                  onClick={() => void handleSaveProfile()}
                  disabled={profileSaving}
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-red-600 px-4 py-2.5 text-sm font-bold text-white shadow-md shadow-red-600/20 transition hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  {profileSaving ? (
                    <>
                      <Loader2 className="size-4 animate-spin" />
                      Salvando...
                    </>
                  ) : (
                    'Salvar perfil'
                  )}
                </button>
              </div>
            </div>
          )}

          {loading && (
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-6 text-center text-slate-600">
              Carregando...
            </div>
          )}

          {!loading && errorMessage && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-center text-amber-700">
              {errorMessage}
            </div>
          )}

          {!loading && !errorMessage && orders.length === 0 && (
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-6 text-center text-slate-600">
              Voce ainda nao possui pedidos. Assim que realizar uma compra, ela aparecera aqui.
            </div>
          )}

          {!loading && !errorMessage && orders.length > 0 && (
            <div className="overflow-x-auto">
              <table className="min-w-full border-separate border-spacing-y-2">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                    <th className="px-3 py-2">Nome do Produto</th>
                    <th className="px-3 py-2">Data</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="min-w-[220px] px-3 py-2">Código de Referência do Serviço</th>
                    <th className="px-3 py-2">Acao</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map((order) => {
                    const isPending = order.status === 'PENDING';
                    const isPaid = order.status === 'PAID';
                    const isSuggestedReference = !!referenceDraftSuggestedFromProduct[order.id];

                    return (
                      <tr key={order.id} className="rounded-xl bg-slate-50 text-sm">
                        <td className="rounded-l-xl px-3 py-3 font-semibold text-slate-800">
                          {order.product_name}
                        </td>
                        <td className="px-3 py-3 text-slate-600">{formatDate(order.created_at)}</td>
                        <td className="px-3 py-3">
                          {isPending && (
                            <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800">
                              <Clock3 size={14} />
                              Pendente
                            </span>
                          )}
                          {isPaid && (
                            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">
                              <CheckCircle2 size={14} />
                              Aprovado
                            </span>
                          )}
                          {!isPending && !isPaid && (
                            <span className="inline-flex items-center rounded-full bg-slate-200 px-3 py-1 text-xs font-semibold text-slate-700">
                              {order.status}
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-3 align-top">
                          {order.product_type === PANELDX_TYPE ? (
                            orderNeedsReferenceLink(order) ? (
                              <div className="flex min-w-[200px] flex-col gap-2">
                                <div className="flex flex-wrap items-end gap-2">
                                  <input
                                    type="text"
                                    className={`min-w-0 flex-1 rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs outline-none focus:border-red-600 focus:ring-1 focus:ring-red-600/30 ${
                                      isSuggestedReference ? 'text-slate-400' : 'text-slate-900'
                                    }`}
                                    placeholder="Codigo do assessment"
                                    value={referenceDrafts[order.id] ?? ''}
                                    onChange={(e) => setReferenceDraft(order.id, e.target.value)}
                                    disabled={referenceSavingId === order.id}
                                  />
                                  <button
                                    type="button"
                                    onClick={() => void handleLinkReference(order)}
                                    disabled={referenceSavingId === order.id}
                                    className="inline-flex shrink-0 items-center gap-1 rounded-lg bg-red-600 px-2.5 py-1.5 text-xs font-bold text-white transition hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-70"
                                  >
                                    {referenceSavingId === order.id ? (
                                      <Loader2 className="size-3.5 animate-spin" />
                                    ) : (
                                      <Link2 className="size-3.5" />
                                    )}
                                    Vincular
                                  </button>
                                </div>
                                {referenceFeedback[order.id] && (
                                  <p
                                    className={`text-xs ${
                                      referenceFeedback[order.id].type === 'ok'
                                        ? 'text-emerald-700'
                                        : 'text-red-600'
                                    }`}
                                  >
                                    {referenceFeedback[order.id].text}
                                  </p>
                                )}
                              </div>
                            ) : (
                              <span className="text-xs font-medium text-slate-700">
                                {String(order.external_resource_id ?? '').trim() || '—'}
                              </span>
                            )
                          ) : (
                            <span className="text-xs text-slate-400">—</span>
                          )}
                        </td>
                        <td className="rounded-r-xl px-3 py-3">
                          {isPending && allowPaymentSimulation && (
                            <button
                              type="button"
                              onClick={() => void handleSimulatePayment(order)}
                              disabled={paymentProcessingId === order.id}
                              className="inline-flex items-center gap-2 rounded-lg bg-red-600 px-3 py-2 text-xs font-bold text-white transition hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-70"
                            >
                              {paymentProcessingId === order.id ? (
                                <Loader2 className="size-3.5 animate-spin" />
                              ) : (
                                <CreditCard size={14} />
                              )}
                              Finalizar Pagamento
                            </button>
                          )}
                          {isPending && !allowPaymentSimulation && (
                            <span className="text-xs text-slate-500">Aguardando MP</span>
                          )}
                          {isPaid && (
                            <button
                              type="button"
                              className="inline-flex items-center gap-2 rounded-lg bg-slate-200 px-3 py-2 text-xs font-bold text-slate-700 transition hover:bg-slate-300"
                            >
                              <BookOpen size={14} />
                              Acessar Conteudo
                            </button>
                          )}
                          {!isPending && !isPaid && (
                            <button
                              type="button"
                              className="inline-flex items-center gap-2 rounded-lg bg-slate-200 px-3 py-2 text-xs font-bold text-slate-700"
                            >
                              Ver Detalhes
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </section>
    </main>
  );

  return withCheckoutChrome(checkoutBrand, checkoutOrder?.product_name, dashboardBody);
}

export default function DashboardPage() {
  return (
    <Suspense
      fallback={
        <main className="flex min-h-[calc(100vh-60px)] items-center justify-center bg-slate-50 text-slate-600">
          <div className="flex items-center gap-2">
            <Loader2 className="size-5 animate-spin" />
            Carregando painel...
          </div>
        </main>
      }
    >
      <DashboardContent />
    </Suspense>
  );
}
