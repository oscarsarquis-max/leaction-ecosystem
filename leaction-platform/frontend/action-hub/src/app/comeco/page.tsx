'use client';

import { useEffect, useRef, useState, type ReactNode, type RefObject } from 'react';
import Link from 'next/link';

const WA_URL = 'https://wa.me/5585999031861';
const INOVE_ACESSO = 'https://inove4us.com.br/acesso';
const SCHOOL_ACESSO = 'https://school.inove4us.com.br/acesso';

const NOVIDADES = [
  {
    date: '14 ago 2026',
    iso: '2026-08-14',
    title: 'Um começo comum para o ecossistema',
    body: 'Esta página reúne os caminhos de professor e escola: entender o produto, treinar o fluxo e entrar no app certo — sem misturar os dois públicos.',
  },
  {
    date: '13 ago 2026',
    iso: '2026-08-13',
    title: 'Escolas contratam na vitrine',
    body: 'Planos do inove4us school (vitrine e checkout) ficam em /ecossistema. O começo aponta para lá quando o visitante é gestor escolar.',
  },
  {
    date: '13 ago 2026',
    iso: '2026-08-13',
    title: 'Professor: Mesa do Inovador',
    body: 'Cadastro freemium e execução de aula no Inove; quem já tem vínculo com escola entra pelo mesmo acesso do professor.',
  },
] as const;

type Passo = { titulo: string; itens: string[] };
type BlocoTreino = { id: string; titulo: string; intro: string; passos: Passo[] };

/** Versão pública estática — espelha o Roteiro Guiado do School (sem checkboxes / feedback / notas internas). */
const TREINO_ESCOLA: BlocoTreino[] = [
  {
    id: 'A',
    titulo: 'Na escola — Torre de Controle',
    intro:
      'Papel da coordenação: organizar a estrutura acadêmica e o método antes da aula existir.',
    passos: [
      {
        titulo: 'Entrar',
        itens: [
          'Acesse a Escola e faça login com as credenciais recebidas.',
          'O menu disponível depende do perfil de acesso (zonas).',
        ],
      },
      {
        titulo: 'Secretaria Acadêmica',
        itens: [
          'Confira unidade, período letivo, cursos, turmas e disciplinas.',
          'Veja os alunos da turma (ou importe por planilha, se precisar).',
          'A aba Situação por período mostra uma fotografia do agora — não um histórico longo.',
        ],
      },
      {
        titulo: 'Minha Equipe',
        itens: [
          'Convide o(a) professor(a) pelo e-mail.',
          'Copie o link de convite gerado na tela para compartilhar (o fluxo atual entrega o link na interface).',
        ],
      },
      {
        titulo: 'Alocação',
        itens: [
          'Na Secretaria, aloque o professor em turma e disciplina.',
          'Opcional: publique um aviso simples para a turma.',
        ],
      },
      {
        titulo: 'Editor Pedagógico',
        itens: [
          'Explore o catálogo de metodologias e os passos de cada uma.',
          'Conheça o pilar de inclusão / PEI — é onde a escola governa o método.',
        ],
      },
      {
        titulo: 'Radar Pedagógico',
        itens: [
          'Abra o Radar (pode estar vazio antes da primeira aula).',
          'Entenda grafo, listas e agenda — depois da aula do professor, a ponte aparece aqui.',
        ],
      },
    ],
  },
  {
    id: 'C',
    titulo: 'A ponte — o que a escola enxerga depois',
    intro: 'Depois que o professor executa a aula no Inove, a escola vê o espelho na Torre.',
    passos: [
      {
        titulo: 'Radar de novo',
        itens: [
          'Confira se a aula aparece refletida.',
          'Abra o mesmo cartão que o professor viu na mesa.',
          'Se houve sugestão de curadoria no fechamento, veja a fila de revisão.',
        ],
      },
      {
        titulo: 'Equipe — acompanhamento',
        itens: [
          'Abra o professor em Minha Equipe.',
          'Veja a linha do tempo: convite → aceite → entrega.',
        ],
      },
    ],
  },
];

const TREINO_PROFESSOR: BlocoTreino[] = [
  {
    id: 'B',
    titulo: 'No Inove — Mesa do Inovador',
    intro:
      'Papel do professor: receber o vínculo da escola (ou usar o freemium solo) e executar a aula com o mínimo de burocracia.',
    passos: [
      {
        titulo: 'Aceitar o convite (quando vier da escola)',
        itens: [
          'Abra o link de convite recebido.',
          'Faça login ou crie a conta no Inove.',
          'Confirme o vínculo com a escola, se for pedido.',
          'Você deve cair na Mesa do Inovador.',
        ],
      },
      {
        titulo: 'Preparar a aula',
        itens: [
          'Veja o cartão da turma/aula alocada (ou o planejamento disponível).',
          'Abra o roteiro da aula — texto pronto, com os passos da metodologia.',
          'Se houver aviso fixado no cartão, note.',
        ],
      },
      {
        titulo: 'Dar a aula',
        itens: [
          'Entre na execução / desafio.',
          'Mova os cartões no quadro — o rastro alimenta o diário.',
          'Feche com o Diário de bordo.',
          'Opcional: envie uma sugestão de melhoria no fechamento (vai para a curadoria da escola).',
        ],
      },
    ],
  },
];

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

function renderItem(text: string): ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return <span key={i}>{part}</span>;
  });
}

function TreinoPainel({ blocos }: { blocos: BlocoTreino[] }) {
  return (
    <div>
      {blocos.map((bloco) => (
        <div key={bloco.id} className="comeco-treino-bloco reveal">
          <h3>{bloco.titulo}</h3>
          <p className="intro">{bloco.intro}</p>
          {bloco.passos.map((passo) => (
            <article key={passo.titulo} className="comeco-passo">
              <h4>{passo.titulo}</h4>
              <ul>
                {passo.itens.map((item) => (
                  <li key={item}>{renderItem(item)}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      ))}
    </div>
  );
}

export default function ComecoPage() {
  const rootRef = useRef<HTMLElement>(null);
  const [treinoTab, setTreinoTab] = useState<'escola' | 'professor'>('escola');
  useRevealOnScroll(rootRef, true);

  return (
    <main className="ecossistema-page comeco-page" ref={rootRef}>
      <section className="eco-hero">
        <div className="eco-container">
          <p className="eyebrow reveal">ecossistema inove4us</p>
          <h1 className="reveal">
            Um começo claro: <em>professor</em>, <em>escola</em> ou só entender o caminho.
          </h1>
          <p className="lead reveal">
            Dois produtos, um ecossistema. Escolha o seu perfil — ou veja como cada lado funciona
            antes de entrar.
          </p>

          <div className="comeco-fork">
            <article className="comeco-fork-card reveal">
              <h3>Sou professor(a)</h3>
              <p>
                A Mesa do Inovador (Inove) tira burocracia da ponta: roteiro pronto, execução e
                diário no fluxo da aula — freemium para começar sozinho(a).
              </p>
              <a className="comeco-btn comeco-btn-primary" href={INOVE_ACESSO}>
                Ir para o cadastro / acesso
              </a>
            </article>

            <article className="comeco-fork-card reveal">
              <h3>Sou gestor(a) escolar</h3>
              <p>
                O inove4us school é a Torre de Controle da escola: governança, equipe, método e
                visão do que acontece em sala — sem misturar com o app do professor.
              </p>
              <Link className="comeco-btn comeco-btn-primary" href="/ecossistema">
                Ver planos e contratar
              </Link>
            </article>

            <article className="comeco-fork-card reveal">
              <h3>Quero entender antes</h3>
              <p>
                Percorra o treinamento público: o que a escola monta, o que o professor faz na mesa
                e como os dois se encontram.
              </p>
              <a className="comeco-btn comeco-btn-ghost" href="#treinamentos">
                Ver treinamentos
              </a>
            </article>
          </div>
        </div>
      </section>

      <section className="eco-block eco-wash" id="novidades">
        <div className="eco-container">
          <div className="head reveal">
            <p className="kicker">Atualizações</p>
            <h2>Novidades</h2>
            <p>O que muda no ecossistema — não só no School.</p>
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

      <section className="eco-block" id="treinamentos">
        <div className="eco-container">
          <div className="head reveal">
            <p className="kicker">Treinamentos</p>
            <h2>Como o ecossistema funciona</h2>
            <p>
              Versão pública e estática do roteiro — sem login e sem gravar progresso. Escolha a
              persona.
            </p>
          </div>

          <div className="comeco-tabs reveal" role="tablist" aria-label="Persona do treinamento">
            <button
              type="button"
              role="tab"
              className="comeco-tab"
              aria-selected={treinoTab === 'escola'}
              onClick={() => setTreinoTab('escola')}
            >
              Como funciona para a escola
            </button>
            <button
              type="button"
              role="tab"
              className="comeco-tab"
              aria-selected={treinoTab === 'professor'}
              onClick={() => setTreinoTab('professor')}
            >
              Como funciona para o professor
            </button>
          </div>

          {treinoTab === 'escola' ? (
            <TreinoPainel blocos={TREINO_ESCOLA} />
          ) : (
            <TreinoPainel blocos={TREINO_PROFESSOR} />
          )}
        </div>
      </section>

      <section className="eco-block eco-wash" id="acessos">
        <div className="eco-container">
          <div className="head reveal">
            <p className="kicker">Clientes</p>
            <h2>Links de acesso</h2>
            <p>Já faz parte do ecossistema? Entre pelo app certo.</p>
          </div>
          <div className="comeco-access reveal">
            <a href={SCHOOL_ACESSO}>Já sou escola, quero entrar</a>
            <a href={INOVE_ACESSO}>Já sou professor(a), quero entrar</a>
          </div>
        </div>
      </section>

      <section className="eco-closing" id="comercial">
        <div className="eco-container">
          <h2 className="reveal">Fale com a área comercial</h2>
          <p className="reveal" style={{ maxWidth: 520, margin: '0 auto 28px', opacity: 0.9 }}>
            Dúvidas de contratação ou para entender o que cabe na sua escola — WhatsApp. Canal só
            para quem ainda não é cliente; suporte e reclamações ficam dentro do app logado.
          </p>
          <a className="cta reveal comeco-btn-wa" href={WA_URL} target="_blank" rel="noreferrer">
            Conversar no WhatsApp
          </a>
        </div>
      </section>
    </main>
  );
}
