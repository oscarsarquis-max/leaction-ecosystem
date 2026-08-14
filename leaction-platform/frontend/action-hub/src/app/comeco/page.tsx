'use client';

import { useEffect, useRef, useState, type ReactNode, type RefObject } from 'react';
import Link from 'next/link';
import type { LucideIcon } from 'lucide-react';
import {
  Activity,
  BookOpen,
  Building2,
  Link2,
  LogIn,
  Mail,
  PenLine,
  PlayCircle,
  Users,
} from 'lucide-react';
import {
  ComecoAssistenteComercial,
  openComecoAssistenteComercial,
} from './ComecoAssistenteComercial';

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

type Passo = { titulo: string; itens: string[]; icon: LucideIcon };
type BlocoTreino = {
  id: string;
  titulo: string;
  intro: string;
  /** Cor do cabeçalho de bloco — mesma linguagem do /roteiro-guiado (School). */
  cor: string;
  passos: Passo[];
};

type TreinoPersona = 'escola' | 'professor';

/** Versão pública estática — espelha o Roteiro Guiado do School (sem checkboxes / feedback / notas internas). */
const TREINO_ESCOLA: BlocoTreino[] = [
  {
    id: 'A',
    titulo: 'A · Escola — a Torre de Controle',
    cor: '#1f6f4a',
    intro:
      'Papel da coordenação: organizar a estrutura acadêmica e o método antes da aula existir.',
    passos: [
      {
        titulo: 'Entrar',
        icon: LogIn,
        itens: [
          'Acesse a Escola e faça login com as credenciais recebidas.',
          'O menu disponível depende do perfil de acesso (zonas).',
        ],
      },
      {
        titulo: 'Secretaria Acadêmica',
        icon: Building2,
        itens: [
          'Confira unidade, período letivo, cursos, turmas e disciplinas.',
          'Veja os alunos da turma (ou importe por planilha, se precisar).',
          'A aba Situação por período mostra uma fotografia do agora — não um histórico longo.',
        ],
      },
      {
        titulo: 'Minha Equipe',
        icon: Users,
        itens: [
          'Convide o(a) professor(a) pelo e-mail.',
          'Copie o link de convite gerado na tela para compartilhar (o fluxo atual entrega o link na interface).',
        ],
      },
      {
        titulo: 'Alocação',
        icon: Link2,
        itens: [
          'Na Secretaria, aloque o professor em turma e disciplina.',
          'Opcional: publique um aviso simples para a turma.',
        ],
      },
      {
        titulo: 'Editor Pedagógico',
        icon: PenLine,
        itens: [
          'Explore o catálogo de metodologias e os passos de cada uma.',
          'Conheça o pilar de inclusão / PEI — é onde a escola governa o método.',
        ],
      },
      {
        titulo: 'Radar Pedagógico',
        icon: Activity,
        itens: [
          'Abra o Radar (pode estar vazio antes da primeira aula).',
          'Entenda grafo, listas e agenda — depois da aula do professor, a ponte aparece aqui.',
        ],
      },
    ],
  },
  {
    id: 'C',
    titulo: 'C · A ponte — o que a escola enxerga depois',
    cor: '#4a3a7a',
    intro: 'Depois que o professor executa a aula no Inove, a escola vê o espelho na Torre.',
    passos: [
      {
        titulo: 'Radar de novo',
        icon: Activity,
        itens: [
          'Confira se a aula aparece refletida.',
          'Abra o mesmo cartão que o professor viu na mesa.',
          'Se houve sugestão de curadoria no fechamento, veja a fila de revisão.',
        ],
      },
      {
        titulo: 'Equipe — acompanhamento',
        icon: Users,
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
    titulo: 'B · Professor — a Mesa do Inovador',
    /** No roteiro autenticado o bloco B usa marrom; em /comeco alinhamos ao bordo da Posicionamento (Inove4Us). */
    cor: '#7a2331',
    intro:
      'Papel do professor: receber o vínculo da escola (ou usar o freemium solo) e executar a aula com o mínimo de burocracia.',
    passos: [
      {
        titulo: 'Aceitar o convite (quando vier da escola)',
        icon: Mail,
        itens: [
          'Abra o link de convite recebido.',
          'Faça login ou crie a conta no Inove.',
          'Confirme o vínculo com a escola, se for pedido.',
          'Você deve cair na Mesa do Inovador.',
        ],
      },
      {
        titulo: 'Preparar a aula',
        icon: BookOpen,
        itens: [
          'Veja o cartão da turma/aula alocada (ou o planejamento disponível).',
          'Abra o roteiro da aula — texto pronto, com os passos da metodologia.',
          'Se houver aviso fixado no cartão, note.',
        ],
      },
      {
        titulo: 'Dar a aula',
        icon: PlayCircle,
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
    const els = Array.from(rootRef.current.querySelectorAll('.reveal'));
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduce) {
      els.forEach((el) => el.classList.add('in'));
      return undefined;
    }
    // Acima da dobra: mostra na hora (evita página “só fundo” se o IO atrasar).
    els.forEach((el) => {
      const rect = el.getBoundingClientRect();
      if (rect.top < window.innerHeight * 0.92) {
        el.classList.add('in');
      }
    });
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('in');
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.08, rootMargin: '0px 0px -8% 0px' }
    );
    els.forEach((el) => {
      if (!el.classList.contains('in')) io.observe(el);
    });
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

function TreinoPainel({
  blocos,
  persona,
}: {
  blocos: BlocoTreino[];
  persona: TreinoPersona;
}) {
  let stepNo = 0;

  return (
    <div className={`comeco-treino comeco-treino--${persona}`} data-persona={persona}>
      {blocos.map((bloco) => (
        <div key={bloco.id} className="comeco-treino-bloco reveal">
          <div className="comeco-treino-bloco-head" style={{ background: bloco.cor }}>
            {bloco.titulo}
          </div>
          <p className="intro">{bloco.intro}</p>
          <ol className="comeco-treino-timeline">
            {bloco.passos.map((passo) => {
              stepNo += 1;
              const Icon = passo.icon;
              return (
                <li key={passo.titulo} className="comeco-passo">
                  <div className="comeco-passo-rail" aria-hidden>
                    <span className="comeco-passo-marker">
                      <span className="comeco-passo-num">{stepNo}</span>
                      <Icon className="comeco-passo-icon" strokeWidth={2} />
                    </span>
                  </div>
                  <div className="comeco-passo-body">
                    <h4>{passo.titulo}</h4>
                    <ul>
                      {passo.itens.map((item) => (
                        <li key={item}>{renderItem(item)}</li>
                      ))}
                    </ul>
                  </div>
                </li>
              );
            })}
          </ol>
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
            Uma <em>trincheira</em> para o professor. Uma <em>torre de controle</em> para a escola —
            e um começo claro para os dois.
          </h1>
          <p className="lead reveal">
            Dois produtos, uma só verdade pedagógica. Escolha o seu perfil — ou veja como cada lado
            funciona antes de entrar.
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

      <section className="eco-block" id="posicionamento">
        <div className="eco-container">
          <div className="head reveal">
            <p className="kicker">Posicionamento</p>
            <h2>Dois produtos, uma só verdade pedagógica</h2>
            <p>
              O que o professor executa na ponta é exatamente o que a gestão enxerga, audita e
              evolui no centro.
            </p>
          </div>

          <div className="comeco-pos-split reveal">
            <article className="comeco-pos-side comeco-pos-b2c">
              <img
                className="comeco-pos-logo"
                src="/brands/inove4us.png"
                alt="Inove4Us — ferramenta do professor"
              />
              <p className="comeco-pos-kicker">01 — B2C</p>
              <h3>Inove4Us</h3>
              <p>
                A ferramenta do professor. Remove a carga burocrática das costas do docente para
                que ele foque exclusivamente na execução da aula e na observação dos alunos.
              </p>
            </article>
            <article className="comeco-pos-side comeco-pos-b2b">
              <img
                className="comeco-pos-logo"
                src="/brands/inove4us-school.png"
                alt="inove4us school — ferramenta da escola"
              />
              <p className="comeco-pos-kicker">02 — B2B</p>
              <h3>inove4us school</h3>
              <p>
                A ferramenta da escola. Governança, compliance jurídico e visão de exceção sobre
                tudo o que acontece em sala — sem tirar autonomia do professor.
              </p>
            </article>
          </div>

          <div className="comeco-pos-sub comeco-pos-b2c-tone">
            <div className="head reveal">
              <p className="comeco-pos-kicker">Inove4Us — a ferramenta do professor</p>
              <h2>A Trincheira e a Mesa de Operação</h2>
              <p>
                O objetivo é um só: tirar a burocracia do caminho para que o professor foque na
                aula e nos alunos — nunca no preenchimento de formulário.
              </p>
            </div>

            <p className="comeco-pos-subhead reveal">Princípios norteadores</p>
            <div className="comeco-pos-grid">
              <article className="comeco-pos-card reveal">
                <span className="comeco-pos-num">Fricção zero</span>
                <h4>Operação invisível</h4>
                <p>
                  A simples movimentação dos cards no Kanban gera o &quot;Diário de Bordo&quot;
                  automaticamente. Documentar não é uma tarefa extra — é consequência de
                  executar.
                </p>
              </article>
              <article className="comeco-pos-card reveal">
                <span className="comeco-pos-num">Empatia visual</span>
                <h4>Proteção do espaço do professor</h4>
                <p>
                  O ambiente — a &quot;Mesa&quot; — é dele. O design protege esse espaço de
                  qualquer sensação de vigilância ou cobrança externa.
                </p>
              </article>
              <article className="comeco-pos-card reveal">
                <span className="comeco-pos-num">Protagonismo</span>
                <h4>Voz no momento certo</h4>
                <p>
                  O professor pode sugerir mudanças na metodologia (Curadoria) exatamente no
                  instante em que a aula termina — quando a percepção ainda está viva.
                </p>
              </article>
            </div>

            <p className="comeco-pos-subhead reveal">Diferenciais para o professor</p>
            <div className="comeco-pos-diff-row">
              <article className="comeco-pos-diff reveal">
                <span className="comeco-pos-tag">IA</span>
                <h4>Roteiro &quot;mastigado&quot; por IA</h4>
                <p>Um roteiro único, em Markdown, pronto para dar aula — sem montagem manual.</p>
              </article>
              <article className="comeco-pos-diff reveal">
                <span className="comeco-pos-tag">Inclusão</span>
                <h4>Amparo direto no card</h4>
                <p>
                  Adaptações de PEI chegam junto da aula, no próprio card — não em um documento
                  separado que ninguém abre.
                </p>
              </article>
              <article className="comeco-pos-diff reveal">
                <span className="comeco-pos-tag">Comunicação</span>
                <h4>Avisos pinados na mesa</h4>
                <p>
                  Comunicação direta da escola, fixada no topo da mesa de trabalho — visível sem
                  precisar procurar.
                </p>
              </article>
            </div>
          </div>

          <div className="comeco-pos-sub comeco-pos-b2b-tone">
            <div className="head reveal">
              <p className="comeco-pos-kicker">inove4us school — a ferramenta da escola</p>
              <h2>A Torre de Controle e o Radar Pedagógico</h2>
              <p>
                Governança sobre o que acontece em cada sala de aula, sem burocratizar o professor
                — visão de exceção, não vigilância linha a linha.
              </p>
            </div>

            <p className="comeco-pos-subhead reveal">Princípios norteadores</p>
            <div className="comeco-pos-grid">
              <article className="comeco-pos-card reveal">
                <span className="comeco-pos-num">Governança</span>
                <h4>Compliance jurídico by design</h4>
                <p>
                  Separação formal AEE/PEI e uma &quot;Máquina do Tempo&quot; — histórico imutável,
                  assinaturas com timestamp — que blinda a escola de passivos legais e atende
                  exigências do MEC.
                </p>
              </article>
              <article className="comeco-pos-card reveal">
                <span className="comeco-pos-num">Exceção</span>
                <h4>Gestão pelo que importa</h4>
                <p>
                  O Grafo destaca em lilás exatamente as sugestões de curadoria que pedem atenção
                  — a gestão vê o desvio, não o volume.
                </p>
              </article>
              <article className="comeco-pos-card reveal">
                <span className="comeco-pos-num">Disclosure</span>
                <h4>Complexidade sob demanda</h4>
                <p>
                  Acordeões colapsados, pílulas de status, filtros poderosos: a informação densa
                  fica disponível, mas nunca despejada de uma vez.
                </p>
              </article>
            </div>

            <p className="comeco-pos-subhead reveal">Diferenciais para a escola e a gestão</p>
            <div className="comeco-pos-diff-row">
              <article className="comeco-pos-diff reveal">
                <span className="comeco-pos-tag">Espelho</span>
                <h4>Espelhamento absoluto</h4>
                <p>
                  O Radar mostra exatamente o mesmo card que o professor vê na mesa — o mesmo{' '}
                  <em>TeacherCardPreview</em>, sem tradução nem perda de contexto.
                </p>
              </article>
              <article className="comeco-pos-diff reveal">
                <span className="comeco-pos-tag">Curadoria</span>
                <h4>Evolução curricular viva</h4>
                <p>
                  Curadoria da escola → IA reescreve → novo padrão já disponível no dia seguinte. A
                  metodologia da escola nunca fica parada no tempo.
                </p>
              </article>
              <article className="comeco-pos-diff reveal">
                <span className="comeco-pos-tag">Onboarding</span>
                <h4>Funil financeiro automático</h4>
                <p>
                  Webhook Action-Sponge conduz onboarding e cobrança ponta a ponta, sem intervenção
                  manual da equipe.
                </p>
              </article>
            </div>
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
              className="comeco-tab comeco-tab--escola"
              aria-selected={treinoTab === 'escola'}
              onClick={() => setTreinoTab('escola')}
            >
              Como funciona para a escola
            </button>
            <button
              type="button"
              role="tab"
              className="comeco-tab comeco-tab--professor"
              aria-selected={treinoTab === 'professor'}
              onClick={() => setTreinoTab('professor')}
            >
              Como funciona para o professor
            </button>
          </div>

          {treinoTab === 'escola' ? (
            <TreinoPainel blocos={TREINO_ESCOLA} persona="escola" />
          ) : (
            <TreinoPainel blocos={TREINO_PROFESSOR} persona="professor" />
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
            Dúvidas de contratação do Hub ou do inove4us — use o guia comercial (botões) ou o
            WhatsApp. Canal só para quem ainda não é cliente; suporte e reclamações ficam no app
            logado.
          </p>
          <div
            className="reveal"
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: 12,
              justifyContent: 'center',
              alignItems: 'center',
            }}
          >
            <button
              type="button"
              className="cta comeco-btn-wa"
              onClick={() => openComecoAssistenteComercial()}
            >
              Abrir guia comercial
            </button>
            <a className="comeco-btn comeco-btn-ghost" href={WA_URL} target="_blank" rel="noreferrer">
              WhatsApp direto
            </a>
          </div>
        </div>
      </section>

      <ComecoAssistenteComercial />
    </main>
  );
}
