'use client';

import { Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import axios from 'axios';
import { AlertCircle, Loader2 } from 'lucide-react';
import { CheckoutChrome } from '@/components/CheckoutChrome';
import { resolveClientBrand } from '@/lib/client-branding';
import {
  fetchCatalogPlans,
  formatCatalogCurrency,
  startCatalogCheckout,
  type CatalogPlanPublic,
} from '@/lib/catalog-api';
import {
  documentDigits,
  formatCnpj,
  formatCpf,
  isValidCnpj,
  isValidCpf,
} from '@/lib/br-documents';

const APP_ID = 'inove4us-school';
const BRAND = resolveClientBrand(APP_ID)!;

function newInstituicaoId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (ch) => {
    const r = (Math.random() * 16) | 0;
    const v = ch === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

function ContratarContent() {
  const searchParams = useSearchParams();
  const sku = (searchParams.get('sku') || '').trim();

  const [plan, setPlan] = useState<CatalogPlanPublic | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [payerEmail, setPayerEmail] = useState('');
  const [razaoSocial, setRazaoSocial] = useState('');
  const [docType, setDocType] = useState<'cnpj' | 'cpf'>('cnpj');
  const [document, setDocument] = useState('');
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
        const match = items.find((p) => p.sku === sku) || null;
        if (!match) {
          setLoadError('Plano não encontrado. Volte à vitrine e escolha novamente.');
        }
        setPlan(match);
      } catch {
        if (!cancelled) {
          setLoadError('Não foi possível carregar o plano agora.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sku]);

  const docOk = useMemo(() => {
    return docType === 'cpf' ? isValidCpf(document) : isValidCnpj(document);
  }, [docType, document]);

  const onDocChange = (value: string) => {
    setDocument(docType === 'cpf' ? formatCpf(value) : formatCnpj(value));
  };

  const iniciarPagamento = useCallback(async () => {
    if (!plan) return;
    const email = payerEmail.trim().toLowerCase();
    const escola = razaoSocial.trim();
    if (!email.includes('@')) {
      setFormError('Informe um e-mail válido.');
      return;
    }
    if (escola.length < 2) {
      setFormError('Informe o nome da escola.');
      return;
    }
    if (!docOk) {
      setFormError(docType === 'cpf' ? 'CPF inválido. Confira os dígitos.' : 'CNPJ inválido. Confira os dígitos.');
      return;
    }

    setSubmitting(true);
    setFormError('');
    try {
      const checkoutUrl = await startCatalogCheckout({
        app_id: APP_ID,
        sku: plan.sku,
        subject_id: newInstituicaoId(),
        subject_type: 'instituicao',
        payer_email: email,
        razao_social: escola,
        payer_document: documentDigits(document),
        payer_document_type: docType,
        return_origin: typeof window !== 'undefined' ? window.location.origin : 'https://inove4us.com.br',
        return_to: '/ecossistema?pedido=ok',
      });
      window.location.assign(checkoutUrl);
    } catch (err) {
      const msg =
        axios.isAxiosError(err) && err.response?.data?.error
          ? String(err.response.data.error)
          : 'Não foi possível iniciar o pagamento.';
      setFormError(msg);
      setSubmitting(false);
    }
  }, [plan, payerEmail, razaoSocial, document, docType, docOk]);

  const fieldClass =
    'mt-1 w-full rounded-lg border border-stone-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none focus:border-emerald-700 focus:ring-2 focus:ring-emerald-700/20';

  return (
    <CheckoutChrome brand={BRAND} subtitle="Dados da escola para emitir o acesso">
      <main className="mx-auto max-w-xl px-4 py-8 pb-16 md:px-6 md:py-12">
        <Link
          href="/ecossistema"
          className="text-sm font-semibold text-emerald-800 hover:underline"
        >
          ← Voltar aos planos
        </Link>

        {loading ? (
          <div className="mt-16 flex items-center justify-center gap-3 text-slate-600">
            <Loader2 className="size-6 animate-spin" aria-hidden />
            Carregando plano…
          </div>
        ) : loadError || !plan ? (
          <div
            className="mt-8 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-red-800"
            role="alert"
          >
            <AlertCircle className="mt-0.5 size-5 shrink-0" aria-hidden />
            <p>{loadError || 'Plano indisponível.'}</p>
          </div>
        ) : (
          <>
            <div className="mt-6 rounded-2xl border border-stone-200 bg-white p-5">
              <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">
                Plano escolhido
              </p>
              <h2 className="mt-1 text-xl font-bold text-slate-900">{plan.name}</h2>
              <p className="mt-2 text-2xl font-black text-slate-900">
                {formatCatalogCurrency(plan.price, plan.currency)}
              </p>
              {plan.licenses_granted ? (
                <p className="mt-1 text-sm text-emerald-800">
                  {plan.licenses_granted} licenças de professor
                </p>
              ) : null}
            </div>

            <form
              className="mt-8 space-y-5"
              onSubmit={(e) => {
                e.preventDefault();
                void iniciarPagamento();
              }}
            >
              <label className="block text-sm font-semibold text-slate-800">
                E-mail que receberá as credenciais
                <input
                  type="email"
                  required
                  autoComplete="email"
                  className={fieldClass}
                  value={payerEmail}
                  disabled={submitting}
                  onChange={(e) => setPayerEmail(e.target.value)}
                />
              </label>

              <label className="block text-sm font-semibold text-slate-800">
                Nome da escola
                <input
                  type="text"
                  required
                  minLength={2}
                  maxLength={255}
                  className={fieldClass}
                  value={razaoSocial}
                  disabled={submitting}
                  onChange={(e) => setRazaoSocial(e.target.value)}
                />
              </label>

              <fieldset className="space-y-3">
                <legend className="text-sm font-semibold text-slate-800">Documento</legend>
                <div className="flex gap-4">
                  <label className="inline-flex items-center gap-2 text-sm">
                    <input
                      type="radio"
                      name="docType"
                      checked={docType === 'cnpj'}
                      disabled={submitting}
                      onChange={() => {
                        setDocType('cnpj');
                        setDocument('');
                      }}
                    />
                    CNPJ
                  </label>
                  <label className="inline-flex items-center gap-2 text-sm">
                    <input
                      type="radio"
                      name="docType"
                      checked={docType === 'cpf'}
                      disabled={submitting}
                      onChange={() => {
                        setDocType('cpf');
                        setDocument('');
                      }}
                    />
                    CPF
                  </label>
                </div>
                <input
                  type="text"
                  inputMode="numeric"
                  required
                  className={fieldClass}
                  placeholder={docType === 'cpf' ? '000.000.000-00' : '00.000.000/0000-00'}
                  value={document}
                  disabled={submitting}
                  onChange={(e) => onDocChange(e.target.value)}
                  aria-invalid={document.length > 0 && !docOk}
                />
              </fieldset>

              {formError ? (
                <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
                  {formError}
                </p>
              ) : null}

              <button
                type="submit"
                disabled={submitting}
                className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-emerald-800 px-4 py-3 text-sm font-bold text-white hover:bg-emerald-900 disabled:opacity-70"
              >
                {submitting ? (
                  <>
                    <Loader2 className="size-4 animate-spin" aria-hidden />
                    Redirecionando ao pagamento…
                  </>
                ) : (
                  'Ir para o pagamento'
                )}
              </button>
            </form>
          </>
        )}
      </main>
    </CheckoutChrome>
  );
}

export default function EcossistemaContratarPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-stone-100 text-stone-600">
          <Loader2 className="size-8 animate-spin" aria-hidden />
        </div>
      }
    >
      <ContratarContent />
    </Suspense>
  );
}
