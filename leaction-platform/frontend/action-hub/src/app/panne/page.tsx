'use client';

import { Fragment, useEffect, useId, useState } from 'react';
import {
  PanneAssistenteComercial,
  openPanneAssistenteComercial,
} from './PanneAssistenteComercial';

const DEMO_URL = 'https://demo.panne.ia.br';

const NAV = [
  { href: '#fluxo', label: 'Como funciona' },
  { href: '#organiza', label: 'O que a Panne organiza' },
  { href: '#para-quem', label: 'Para quem é' },
  { href: '#demonstracao', label: 'Demonstração' },
] as const;

const FLOW = [
  { title: 'Compras e entradas', text: 'A mercadoria só entra depois de conferida.' },
  { title: 'Estoque e insumos', text: 'O saldo reflete o que foi realmente aceito.' },
  { title: 'Produtos', text: 'Cada item carrega identidade, modalidade e prontidão.' },
  { title: 'Receitas técnicas', text: 'A fórmula vigente orienta o que se produz.' },
  { title: 'Planejamento e ordens', text: 'O dia ganha sequência, quantidade e prazo.' },
  { title: 'Preparo e execução', text: 'A ordem vira trabalho visível no chão.' },
  { title: 'Acabamento e conformidade', text: 'O produto só segue se estiver de acordo.' },
  { title: 'Custos e preços', text: 'A decisão econômica usa o que está documentado — e o que falta permanece visível.' },
] as const;

const PRODUCT_NODES = [
  { title: 'Produto', detail: 'identidade' },
  { title: 'Receita técnica', detail: 'versão vigente' },
  { title: 'Componentes', detail: 'insumos e partes' },
  { title: 'Preparo', detail: 'modo de fazer' },
  { title: 'Rotulagem', detail: 'prévia' },
  { title: 'Produção', detail: 'prontidão' },
] as const;

const ENTRY_WAYS = [
  { title: 'Registro manual', text: 'Quando o documento chega fora do padrão digital.' },
  { title: 'XML', text: 'Leitura do arquivo fiscal para conferência.' },
  { title: 'PDF ou fotografia', text: 'Captura do documento para revisão humana.' },
  { title: 'Fazenda', text: 'Integração futura, com certificado A1.' },
] as const;

const COST_ITEMS = [
  { title: 'Formação do custo', text: 'O que entra na composição do produto ou do lote.' },
  { title: 'Custo de aquisição', text: 'O valor conferido na entrada da mercadoria.' },
  { title: 'Previsto e realizado', text: 'O planejado e o que de fato ocorreu na ordem.' },
  { title: 'Políticas de markup', text: 'A regra de formação, quando houver política definida.' },
  { title: 'Preço praticado', text: 'O valor em vigor — distinto de margem e de markup.' },
  { title: 'Margem e histórico', text: 'O resultado e o rastro de alterações para auditoria.' },
] as const;

const PRINCIPLES = [
  {
    title: 'Processo visível',
    text: 'Cada pessoa entende onde está, o que falta e qual é a próxima ação.',
  },
  {
    title: 'Decisão humana',
    text: 'O sistema orienta e registra; decisões importantes permanecem sob responsabilidade da equipe.',
  },
  {
    title: 'Memória operacional',
    text: 'Versões, movimentos, conferências e alterações permanecem rastreáveis.',
  },
] as const;

const PROFILES = [
  {
    id: 'proprietario',
    label: 'Proprietário',
    acompanha: 'O pulso do dia: planejado e realizado, prioridades, custos e lacunas.',
    decide: 'Onde investir atenção, o que pode esperar e o que precisa de exceção.',
    fluxo: 'Painel executivo, prioridades e o fechamento da jornada.',
  },
  {
    id: 'producao',
    label: 'Produção',
    acompanha: 'Ordens do dia, andamento e o que trava o preparo.',
    decide: 'Sequência, ajustes no chão e o encerramento da ordem.',
    fluxo: 'Planejamento, preparo, execução e acabamento.',
  },
  {
    id: 'formulador',
    label: 'Formulador',
    acompanha: 'Receitas, versões, componentes e a prévia de rotulagem.',
    decide: 'Qual fórmula vale, o que muda na próxima versão e se o produto está pronto.',
    fluxo: 'Produto, receita técnica, componentes e rotulagem.',
  },
  {
    id: 'compras',
    label: 'Compras',
    acompanha: 'Entradas em conferência, divergências e estoque crítico.',
    decide: 'O que confirmar, o que devolver à conferência e o que ainda não move o saldo.',
    fluxo: 'Compras, entradas e estoque.',
  },
  {
    id: 'regulatorio',
    label: 'Regulatório',
    acompanha: 'Conformidade, rotulagem e o que impede a liberação.',
    decide: 'Se o produto pode seguir depois das checagens.',
    fluxo: 'Acabamento, conformidade e rotulagem.',
  },
  {
    id: 'comercial',
    label: 'Comercial',
    acompanha: 'Custo com base, preço praticado e onde a informação ainda falta.',
    decide: 'Preço somente quando a base está visível — nunca no escuro.',
    fluxo: 'Custos, preços, margem e o histórico da decisão.',
  },
] as const;

export default function PannePage() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [profileId, setProfileId] = useState<(typeof PROFILES)[number]['id']>('proprietario');
  const menuId = useId();
  const profile = PROFILES.find((item) => item.id === profileId) ?? PROFILES[0];

  useEffect(() => {
    if (!menuOpen) return undefined;
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setMenuOpen(false);
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [menuOpen]);

  function goTo(href: string) {
    setMenuOpen(false);
    if (href.startsWith('#')) {
      const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      document
        .getElementById(href.slice(1))
        ?.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
    }
  }

  return (
    <div className="panne-page" lang="pt-BR">
      <a className="panne-skip" href="#conteudo">
        Ir para o conteúdo
      </a>

      <header className="panne-header">
        <div className="panne-wrap panne-header-inner">
          <a className="panne-brand" href="#conteudo" onClick={() => setMenuOpen(false)}>
            <img src="/brands/panne.png" alt="Panne" width={180} height={40} />
          </a>

          <nav className="panne-nav" aria-label="Seções da página">
            {NAV.map((item) => (
              <a key={item.href} href={item.href}>
                {item.label}
              </a>
            ))}
          </nav>

          <a
            className="panne-btn panne-btn-primary panne-header-cta"
            href={DEMO_URL}
            rel="noopener noreferrer"
          >
            Entrar na demonstração
          </a>

          <button
            type="button"
            className="panne-menu-btn"
            aria-expanded={menuOpen}
            aria-controls={menuId}
            aria-label={menuOpen ? 'Fechar menu' : 'Abrir menu'}
            onClick={() => setMenuOpen((open) => !open)}
          >
            {menuOpen ? 'Fechar' : 'Menu'}
          </button>
        </div>

        <div className={`panne-menu-panel${menuOpen ? ' is-open' : ''}`} id={menuId}>
          <div className="panne-wrap">
            <nav aria-label="Menu móvel">
              {NAV.map((item) => (
                <a
                  key={item.href}
                  href={item.href}
                  onClick={(e) => {
                    e.preventDefault();
                    goTo(item.href);
                  }}
                >
                  {item.label}
                </a>
              ))}
            </nav>
            <a
              className="panne-btn panne-btn-primary"
              href={DEMO_URL}
              rel="noopener noreferrer"
              onClick={() => setMenuOpen(false)}
            >
              Entrar na demonstração
            </a>
          </div>
        </div>
      </header>

      <main id="conteudo">
        <section className="panne-hero">
          <div className="panne-wrap panne-hero-grid">
            <div>
              <p className="panne-kicker">Panne — produção com método</p>
              <h1>Da entrada da mercadoria ao produto vendido, toda a operação faz sentido.</h1>
              <p className="panne-lead">
                A Panne conecta compras, estoque, produtos, receitas, produção, conformidade, custos
                e preços em um único fluxo — sem abandonar a técnica exigida pela indústria.
              </p>
              <div className="panne-actions">
                <a className="panne-btn panne-btn-primary" href={DEMO_URL} rel="noopener noreferrer">
                  Explorar a demonstração
                </a>
                <a className="panne-btn panne-btn-secondary" href="#fluxo">
                  Conhecer o fluxo
                </a>
              </div>
            </div>

            <aside className="panne-atelier" aria-label="Representação ilustrativa do fluxo produtivo">
              <p className="panne-atelier-label">Exemplo visual — não é a aplicação</p>
              <p className="panne-atelier-product">Pão de fermentação natural</p>
              <div className="panne-atelier-meta">
                <span className="panne-chip">Produzido</span>
                <span className="panne-chip">Receita v3</span>
                <span className="panne-chip">Ordem 1048</span>
              </div>
              <p className="panne-atelier-flow">
                <strong>Farinha</strong>
                <span className="panne-atelier-arrow" aria-hidden>
                  →
                </span>
                <strong>Massa</strong>
                <span className="panne-atelier-arrow" aria-hidden>
                  →
                </span>
                <strong>Forno</strong>
                <span className="panne-atelier-arrow" aria-hidden>
                  →
                </span>
                <strong>Rótulo</strong>
                <span className="panne-atelier-arrow" aria-hidden>
                  →
                </span>
                <strong>Pronto</strong>
              </p>
              <div className="panne-atelier-pulse">
                <p>
                  <strong>Planejado</strong>
                  40 unidades
                </p>
                <p>
                  <strong>Realizado</strong>
                  36 unidades
                </p>
                <p>
                  <strong>Estoque</strong>
                  fermento — atenção
                </p>
                <p>
                  <strong>Custo</strong>
                  parcial
                </p>
              </div>
            </aside>
          </div>
        </section>

        <section className="panne-section" id="fluxo" aria-labelledby="fluxo-title">
          <div className="panne-wrap">
            <p className="panne-kicker">Uma operação, um percurso</p>
            <h2 id="fluxo-title">A operação inteira em uma só jornada</h2>
            <p className="panne-section-intro">
              O caminho crítico não é uma lista de módulos. Cada etapa entrega a seguinte.
            </p>

            <ol className="panne-path">
              {FLOW.map((step, index) => (
                <li key={step.title}>
                  <span className="panne-path-num">{index + 1}</span>
                  <h3>{step.title}</h3>
                  <p>{step.text}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <div className="panne-band">
          <section className="panne-section" id="organiza" aria-labelledby="organiza-title">
            <div className="panne-wrap">
              <p className="panne-kicker">O negócio pulsando</p>
              <h2 id="organiza-title">Saiba o que aconteceu, o que está acontecendo e onde agir.</h2>
              <p className="panne-section-intro">
                O painel executivo reúne o dia em um recorte só — números abaixo são demonstrativos.
              </p>

              <div className="panne-pulse">
                <p className="panne-pulse-note">Exemplo visual</p>
                <div className="panne-pulse-card">
                  <h3>Produção e movimento</h3>
                  <p className="panne-metric">
                    Planejada <span>12 ordens</span>
                  </p>
                  <p className="panne-metric">
                    Realizada <span>9 ordens</span>
                  </p>
                  <p className="panne-metric">
                    Entradas conferidas <span>3</span>
                  </p>
                  <p className="panne-metric">
                    Saídas do dia <span>5</span>
                  </p>
                </div>
                <div className="panne-pulse-card">
                  <h3>Agenda do dia</h3>
                  <p className="panne-agenda">
                    <time dateTime="2026-09-02T14:00">14h00</time>
                    Ordem 1048 — pão de fermentação
                  </p>
                  <p className="panne-agenda" style={{ marginTop: '0.85rem' }}>
                    <time dateTime="2026-09-02T16:30">16h30</time>
                    Acabamento — lote 22
                  </p>
                </div>
                <div className="panne-pulse-card">
                  <h3>Prioridades</h3>
                  <ul className="panne-priorities">
                    <li>Duas ordens atrasam o forno da tarde.</li>
                    <li>Fermento abaixo do ponto de atenção.</li>
                  </ul>
                </div>
                <div className="panne-pulse-card">
                  <h3>Economia visível</h3>
                  <p className="panne-metric">
                    Custos completos <span>4 produtos</span>
                  </p>
                  <p className="panne-metric">
                    Custos parciais <span>2 produtos</span>
                  </p>
                  <p className="panne-metric">
                    Preços sem base comercial <span>1 produto</span>
                  </p>
                </div>
              </div>
            </div>
          </section>
        </div>

        <section className="panne-section" id="produto" aria-labelledby="produto-title">
          <div className="panne-wrap">
            <p className="panne-kicker">Produto no centro</p>
            <h2 id="produto-title">O produto reúne a história técnica e operacional.</h2>
            <p className="panne-section-intro">
              Não é uma ficha isolada: o produto aponta para a receita, os componentes e o que a
              produção precisa para executar.
            </p>

            <div className="panne-graph" aria-label="Relação do produto até a produção">
              {PRODUCT_NODES.map((node, index) => (
                <Fragment key={node.title}>
                  <div className="panne-graph-node">
                    <strong>{node.title}</strong>
                    <span>{node.detail}</span>
                  </div>
                  {index < PRODUCT_NODES.length - 1 ? (
                    <span className="panne-graph-join" aria-hidden>
                      →
                    </span>
                  ) : null}
                </Fragment>
              ))}
            </div>

            <dl className="panne-facts">
              <div>
                <dt>Identidade do produto</dt>
                <dd>Nome, família e o que o distingue na operação.</dd>
              </div>
              <div>
                <dt>Modalidade</dt>
                <dd>Produzido internamente ou comprado pronto para revenda.</dd>
              </div>
              <div>
                <dt>Receita e versão</dt>
                <dd>A fórmula que vale agora — e o rastro das versões anteriores.</dd>
              </div>
              <div>
                <dt>Ingredientes e componentes</dt>
                <dd>O que entra, em que quantidade, e de onde vem o saldo.</dd>
              </div>
              <div>
                <dt>Modo de preparo</dt>
                <dd>A instrução que a produção segue na ordem.</dd>
              </div>
              <div>
                <dt>Rotulagem e prontidão</dt>
                <dd>A prévia do rótulo e se o produto pode ir para o chão.</dd>
              </div>
            </dl>
          </div>
        </section>

        <div className="panne-band">
          <section className="panne-section" id="entrada" aria-labelledby="entrada-title">
            <div className="panne-wrap">
              <p className="panne-kicker">Entrada e rastreabilidade</p>
              <h2 id="entrada-title">O estoque começa com uma entrada conferida.</h2>
              <p className="panne-section-intro">
                Há mais de um caminho para registrar o documento. O destino é o mesmo: conferir
                antes de mover o saldo.
              </p>

              <ol className="panne-entry-ways">
                {ENTRY_WAYS.map((way) => (
                  <li key={way.title}>
                    <h3>{way.title}</h3>
                    <p>{way.text}</p>
                  </li>
                ))}
              </ol>

              <div className="panne-gate">
                <p>
                  A confirmação humana precede a movimentação. Divergências permanecem visíveis.
                  O estoque só muda depois da confirmação.
                </p>
                <p>
                  A conexão real com a Fazenda depende de certificado A1. A demonstração utiliza
                  apenas documentos sintéticos.
                </p>
              </div>
            </div>
          </section>
        </div>

        <section className="panne-section" id="custos" aria-labelledby="custos-title">
          <div className="panne-wrap">
            <p className="panne-kicker">Custos, preço e margem</p>
            <h2 id="custos-title">Decisões econômicas precisam de uma base confiável.</h2>
            <p className="panne-quote">Informação ausente não é tratada como zero.</p>
            <div className="panne-cost-states" aria-label="Estados da informação">
              <span className="panne-state panne-state--ok">completo</span>
              <span className="panne-state panne-state--partial">parcial</span>
              <span className="panne-state panne-state--empty">sem informação</span>
            </div>
            <div className="panne-cost-list">
              {COST_ITEMS.map((item) => (
                <div key={item.title}>
                  <h3>{item.title}</h3>
                  <p>{item.text}</p>
                </div>
              ))}
            </div>
            <p className="panne-note">
              Markup não é margem. Onde a base ainda está incompleta, a Panne mostra a lacuna em
              vez de inventar um número. A formação de preço continua a evoluir — o princípio já
              vale: sem base, sem sugerido definitivo.
            </p>
          </div>
        </section>

        <div className="panne-band">
          <section className="panne-section" id="tecnica" aria-labelledby="tecnica-title">
            <div className="panne-wrap">
              <p className="panne-kicker">Técnica sem complexidade desnecessária</p>
              <h2 id="tecnica-title">Simplificar a operação não significa esconder a técnica.</h2>
              <div className="panne-principles">
                {PRINCIPLES.map((item) => (
                  <div key={item.title}>
                    <h3>{item.title}</h3>
                    <p>{item.text}</p>
                  </div>
                ))}
              </div>
            </div>
          </section>
        </div>

        <section className="panne-section" id="para-quem" aria-labelledby="para-quem-title">
          <div className="panne-wrap">
            <p className="panne-kicker">Para quem é</p>
            <h2 id="para-quem-title">O mesmo fluxo, recortes diferentes.</h2>
            <p className="panne-section-intro">
              Escolha um perfil. A Panne não pede que todos vejam a mesma tela o tempo todo.
            </p>

            <div className="panne-profiles" role="tablist" aria-label="Perfis">
              {PROFILES.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  role="tab"
                  className="panne-profile-btn"
                  aria-selected={profileId === item.id}
                  onClick={() => setProfileId(item.id)}
                >
                  {item.label}
                </button>
              ))}
            </div>

            <div className="panne-profile-panel" role="tabpanel" aria-label={profile.label}>
              <div>
                <h3>Acompanha</h3>
                <p>{profile.acompanha}</p>
              </div>
              <div>
                <h3>Decide</h3>
                <p>{profile.decide}</p>
              </div>
              <div>
                <h3>No fluxo</h3>
                <p>{profile.fluxo}</p>
              </div>
            </div>
          </div>
        </section>

        <section className="panne-close" id="demonstracao" aria-labelledby="close-title">
          <div className="panne-wrap">
            <h2 id="close-title">
              Sua produção já possui um fluxo. A Panne torna esse fluxo visível, controlável e
              melhorável.
            </h2>
            <p>Conheça a Panne com dados demonstrativos e percorra a jornada completa antes de decidir.</p>
            <div className="panne-actions">
              <a className="panne-btn panne-btn-invert" href={DEMO_URL} rel="noopener noreferrer">
                Entrar na demonstração
              </a>
              <button
                type="button"
                className="panne-btn panne-btn-ghost"
                onClick={() => openPanneAssistenteComercial()}
              >
                Falar com o comercial
              </button>
            </div>
          </div>
        </section>
      </main>

      <footer className="panne-footer">
        <div className="panne-wrap panne-footer-grid">
          <div>
            <h2>Panne</h2>
            <p>
              Produção com método: da entrada conferida ao produto vendido, com a técnica que a
              indústria exige e a clareza que a gestão precisa.
            </p>
          </div>
          <div>
            <p>
              <a href={DEMO_URL} rel="noopener noreferrer">
                Acessar a demonstração
              </a>
            </p>
            <p style={{ marginTop: '0.65rem' }}>
              <a href="/">Action Hub</a>
            </p>
          </div>
        </div>
        <div className="panne-wrap">
          <p className="panne-hub">Produto do ecossistema Action Hub.</p>
        </div>
      </footer>

      <PanneAssistenteComercial />
    </div>
  );
}
