'use client';

import { Suspense, useEffect, useMemo, useRef, useState, type RefObject } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { AlertCircle, Loader2, Mail } from 'lucide-react';
import { CatalogPricingCards } from '@/components/CatalogPricingCards';
import { CheckoutChrome } from '@/components/CheckoutChrome';
import { resolveClientBrand } from '@/lib/client-branding';
import { fetchCatalogPlans, type CatalogPlanPublic } from '@/lib/catalog-api';

const APP_ID = 'inove4us-school';
const BRAND = resolveClientBrand(APP_ID)!;

const PRINCIPIOS = [
  {
    kicker: 'Governança',
    title: 'Compliance jurídico por design',
    body: 'Separação formal AEE/PEI, histórico imutável com assinatura e timestamp — blinda a escola de passivo legal e atende exigência do MEC.',
  },
  {
    kicker: 'Visão de exceção',
    title: 'Gestão pelo que importa',
    body: 'A escola enxerga exatamente onde a atenção é necessária, não um volume de dados pra garimpar.',
  },
  {
    kicker: 'Evolução viva',
    title: 'O currículo da escola nunca para no tempo',
    body: 'Curadoria da coordenação vira padrão novo pros professores no dia seguinte, não fica arquivada.',
  },
] as const;

const DIFERENCIAIS = [
  {
    title: 'Espelho fiel',
    body: 'A coordenação vê exatamente o mesmo cartão de aula que o professor vê na mesa dele.',
  },
  {
    title: 'Inclusão de verdade',
    body: 'O PEI cruza a metodologia oficial da escola com a condição de cada aluno, e chega pronto pro professor usar — não é papel guardado em gaveta.',
  },
  {
    title: 'Onboarding sem fricção',
    body: 'O professor entra, aceita o convite, e já está pronto pra dar aula no mesmo dia.',
  },
] as const;

/** Placeholder estático — editar aqui, sem lógica. */
const NOVIDADES = [
  {
    date: '13 ago 2026',
    iso: '2026-08-13',
    title: 'A Torre de Controle abre a vitrine',
    body: 'Escolas contratam o inove4us school por aqui: escolha o plano, informe os dados e receba as credenciais no e-mail do cadastro.',
  },
  {
    date: '13 ago 2026',
    iso: '2026-08-13',
    title: 'Inclusão deixa a gaveta',
    body: 'O PEI cruza a metodologia oficial da escola com a condição de cada aluno e chega no cartão de aula, pronto para o professor usar.',
  },
  {
    date: '01 set 2026',
    iso: '2026-09-01',
    title: 'Próximas entregas da Torre',
    body: 'Radar pedagógico, curadoria viva e onboarding de professores seguem o roteiro de evolução — texto placeholder, a atualizar.',
  },
] as const;

function useRevealOnScroll(rootRef: RefObject<HTMLElement | null>, enabled: boolean) {
  useEffect(() => {
    if (!enabled || !rootRef.current) return undefined;
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const els = rootRef.current.querySelectorAll('.reveal');
    if (reduce) {
      els.forEach((el) => el.classList.add('in'));
      return undefined;
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('in');
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12 }
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, [enabled, rootRef]);
}

function PedidoRecebido() {
  return (
    <main className="mx-auto max-w-2xl px-4 py-16 md:px-6">
      <div className="rounded-2xl border border-emerald-200 bg-white p-8 text-center shadow-sm">
        <Mail className="mx-auto mb-4 size-10 text-emerald-700" aria-hidden />
        <h2 className="text-2xl font-bold text-slate-900">Pedido recebido</h2>
        <p className="mt-3 text-slate-600">
          Pagamento em processamento. As credenciais de acesso à Torre de Controle serão enviadas
          para o e-mail informado no cadastro. Confira também a caixa de spam.
        </p>
        <p className="mt-4 text-sm text-slate-500">
          Ainda não existe sessão nesta página — o primeiro acesso é pelo link do e-mail.
        </p>
        <Link
          href="/ecossistema"
          className="mt-8 inline-flex rounded-xl bg-emerald-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-emerald-900"
        >
          Voltar à vitrine
        </Link>
      </div>
    </main>
  );
}

function EcossistemaHome() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const pedidoOk = searchParams.get('pedido') === 'ok';
  const rootRef = useRef<HTMLElement>(null);

  const [plans, setPlans] = useState<CatalogPlanPublic[]>([]);
  const [loadingPlans, setLoadingPlans] = useState(true);
  const [loadError, setLoadError] = useState('');

  useRevealOnScroll(rootRef, !pedidoOk);

  useEffect(() => {
    if (pedidoOk) return undefined;
    let cancelled = false;
    (async () => {
      setLoadingPlans(true);
      setLoadError('');
      try {
        const items = await fetchCatalogPlans(APP_ID);
        if (cancelled) return;
        if (!items.length) {
          setLoadError(
            'Não há planos disponíveis no momento. Tente novamente em alguns minutos ou fale com o suporte.'
          );
        }
        setPlans(items);
      } catch {
        if (!cancelled) {
          setLoadError(
            'Não foi possível carregar os planos agora. Verifique sua conexão e tente novamente.'
          );
        }
      } finally {
        if (!cancelled) setLoadingPlans(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [pedidoOk]);

  const subtitle = useMemo(
    () =>
      pedidoOk ? 'Confirme o e-mail de acesso' : 'Torre de Controle para a sua escola',
    [pedidoOk]
  );

  return (
    <CheckoutChrome brand={BRAND} subtitle={subtitle} className={pedidoOk ? '' : 'pb-0'}>
      {pedidoOk ? (
        <PedidoRecebido />
      ) : (
        <main className="ecossistema-page" ref={rootRef}>
          <section className="eco-hero">
            <div className="eco-container">
              <p className="eyebrow reveal">inove4us school</p>
              <h1 className="reveal">
                A <em>torre de controle</em> da sua escola sobre o que acontece em cada sala de
                aula.
              </h1>
              <p className="lead reveal">
                Governança pedagógica, compliance de inclusão e visão real da execução — sem
                burocratizar o professor.
              </p>
            </div>
          </section>

          <section className="eco-block eco-wash" id="principios">
            <div className="eco-container">
              <div className="head reveal">
                <h2>Por que o inove4us school</h2>
              </div>
              <div className="eco-grid3">
                {PRINCIPIOS.map((item) => (
                  <article key={item.kicker} className="eco-card reveal">
                    <span className="num">{item.kicker}</span>
                    <h3>{item.title}</h3>
                    <p>{item.body}</p>
                  </article>
                ))}
              </div>
            </div>
          </section>

          <section className="eco-block" id="dia-a-dia">
            <div className="eco-container">
              <div className="head reveal">
                <h2>O que muda no dia a dia</h2>
              </div>
              <div className="eco-grid3">
                {DIFERENCIAIS.map((item) => (
                  <article key={item.title} className="eco-card reveal">
                    <h3>{item.title}</h3>
                    <p>{item.body}</p>
                  </article>
                ))}
              </div>
            </div>
          </section>

          <section className="eco-block eco-wash" id="planos">
            <div className="eco-container">
              <div className="head reveal">
                <h2>Planos</h2>
                <p>
                  Não é preciso criar conta nesta página: escolha o plano, informe os dados da
                  escola no passo seguinte e conclua o pagamento. As credenciais chegam no e-mail
                  do cadastro.
                </p>
              </div>

              {loadingPlans ? (
                <div className="flex items-center justify-center gap-3 py-20 text-slate-600">
                  <Loader2 className="size-6 animate-spin" aria-hidden />
                  Carregando planos…
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
                  ctaLabel="Contratar"
                  onSelect={(plan) => {
                    router.push(`/ecossistema/contratar?sku=${encodeURIComponent(plan.sku)}`);
                  }}
                />
              )}
            </div>
          </section>

          <section className="eco-block" id="novidades">
            <div className="eco-container">
              <div className="head reveal">
                <h2>Novidades</h2>
              </div>
              <div className="eco-news">
                {NOVIDADES.map((item) => (
                  <article key={item.title} className="eco-news-item reveal">
                    <time dateTime={item.iso}>{item.date}</time>
                    <h3>{item.title}</h3>
                    <p>{item.body}</p>
                  </article>
                ))}
              </div>
            </div>
          </section>

          <section className="eco-closing">
            <div className="eco-container">
              <h2 className="reveal">Pronto pra ver isso na sua escola?</h2>
              <a className="cta reveal" href="#planos">
                Ver planos
              </a>
            </div>
          </section>
        </main>
      )}
    </CheckoutChrome>
  );
}

export default function EcossistemaPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-stone-100 text-stone-600">
          <Loader2 className="size-8 animate-spin" aria-hidden />
        </div>
      }
    >
      <EcossistemaHome />
    </Suspense>
  );
}
