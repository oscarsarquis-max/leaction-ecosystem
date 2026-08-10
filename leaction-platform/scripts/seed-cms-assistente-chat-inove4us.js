'use strict';

/**
 * Seed — árvore Nina (assistente-chat) para sistema_destino=inove4us.
 * Fonte canônica: inove4us/backend/assistente_chat_fallback.py
 * Limites freemium: placeholders {{FREEMIUM_AULAS}} / {{FREEMIUM_DESAFIOS}}
 * (substituídos pelo BFF do inove4us no consumo).
 *
 * Uso:
 *   $env:DATABASE_URL = "<connection string leaction_hub>"
 *   node scripts/seed-cms-assistente-chat-inove4us.js
 */

const fs = require('fs');
const path = require('path');

function loadPg() {
  try {
    return require('pg');
  } catch {
    return require(path.join(
      __dirname,
      '..',
      'services',
      'gateway-api',
      'node_modules',
      'pg'
    ));
  }
}

const { Client } = loadPg();
const { validateTree } = require(path.join(
  __dirname,
  '..',
  'services',
  'gateway-api',
  'domain',
  'cms-assistente-chat'
));

/** Árvore publicada — ids e textos alinhados ao fallback do inove4us. */
const TREE = {
  avatar_name: 'Nina',
  avatar_tagline: 'Guia do inovador',
  avatar_candidates: ['Nina'],
  root_id: 'inicio',
  nodes: {
    inicio: {
      message:
        'Olá! Sou a Nina, sua guia no inove4us. ' +
        'Escolha um tema abaixo — ou deixe uma sugestão no campo acima.',
      options: [
        { label: 'Aulas do Dia a Dia (rápido)', next: 'dia_a_dia' },
        { label: 'Desafios e Projetos', next: 'desafios' },
        { label: 'Como usar o Kanban', next: 'kanban' },
        { label: 'Planos, pagamentos e conta', next: 'planos' },
      ],
    },
    dia_a_dia: {
      message:
        'O Dia a Dia é o ciclo rápido (~50 min) para planejar e executar ' +
        'uma aula. Você preenche as 4 estações e move o trabalho no Kanban ' +
        '(Para Fazer → Fazendo → Pronto).',
      options: [
        { label: 'O que são as 4 estações?', next: 'dia_estacoes' },
        { label: 'Como escolher a atividade em campo?', next: 'dia_dinamica' },
        { label: 'Abrir o Dia a Dia', next: 'dia_a_dia', href: '/dia-a-dia' },
        { label: 'Voltar ao início', next: 'inicio' },
      ],
    },
    dia_estacoes: {
      message:
        'As 4 estações do ciclo são:\n' +
        '1 · Alinhamento (abertura)\n' +
        '2 · Entrega do dia\n' +
        '3 · Atividade em campo (dinâmica ativa)\n' +
        '4 · Retro do ciclo (fechamento)\n\n' +
        'Isso aparece exatamente assim na tela de planejar aula.',
      options: [
        { label: 'Como escolher a atividade em campo?', next: 'dia_dinamica' },
        { label: 'Ir para nova aula', next: 'dia_estacoes', href: '/dia-a-dia/nova' },
        { label: 'Voltar ao Dia a Dia', next: 'dia_a_dia' },
        { label: 'Voltar ao início', next: 'inicio' },
      ],
    },
    dia_dinamica: {
      message:
        'Na estação 3 · Atividade em campo você pode escolher uma dinâmica ' +
        'sugerida do catálogo ou descrever a sua. A sugestão é um atalho — ' +
        'não substitui o seu julgamento pedagógico.',
      options: [
        { label: 'Abrir nova aula', next: 'dia_dinamica', href: '/dia-a-dia/nova' },
        { label: 'Voltar ao Dia a Dia', next: 'dia_a_dia' },
        { label: 'Voltar ao início', next: 'inicio' },
      ],
    },
    desafios: {
      message:
        'Em Desafios você descreve a dor real da turma; a inove4us estrutura ' +
        'causas e caminhos metodológicos e gera um plano EduScrum com Kanban. ' +
        'Cada geração bem-sucedida consome 1 crédito de desafio.',
      options: [
        { label: 'Como escrever um bom desafio?', next: 'desafio_escrever' },
        { label: 'A geração consome crédito?', next: 'desafio_credito' },
        { label: 'Abrir Desafio', next: 'desafios', href: '/desafio' },
        { label: 'Voltar ao início', next: 'inicio' },
      ],
    },
    desafio_escrever: {
      message:
        'Seja específico: turma, tema e a dor real (o que trava a aprendizagem). ' +
        'Cite nomes concretos (projeto, prazo, hipóteses dos alunos). ' +
        'Evite só dizer “a turma está dispersa” — quanto mais contexto, ' +
        'melhor a hipótese e o plano.',
      options: [
        { label: 'Ir para Desafio', next: 'desafio_escrever', href: '/desafio' },
        { label: 'Voltar a Desafios', next: 'desafios' },
        { label: 'Voltar ao início', next: 'inicio' },
      ],
    },
    desafio_credito: {
      message:
        'Sim. Cada estruturação com IA consome 1 crédito de desafio. ' +
        'No plano gratuito você começa com {{FREEMIUM_DESAFIOS}} desafio (crédito de IA). ' +
        'No gratuito, o Dia a Dia é só navegação — o registro de aulas exige plano ou pacote avulso.',
      options: [
        { label: 'Ver planos e créditos', next: 'planos' },
        { label: 'Voltar a Desafios', next: 'desafios' },
        { label: 'Voltar ao início', next: 'inicio' },
      ],
    },
    kanban: {
      message:
        'O Kanban acompanha a execução da aula ou do plano EduScrum. ' +
        'As colunas são: Para Fazer → Fazendo → Pronto. ' +
        'Ao mover um card, você registra uma observação curta do que mudou.',
      options: [
        { label: 'Como mover os cards?', next: 'kanban_mover' },
        { label: 'Onde vejo o Kanban?', next: 'kanban_onde' },
        { label: 'Voltar ao início', next: 'inicio' },
      ],
    },
    kanban_mover: {
      message:
        'Clique no card e escolha a coluna de destino (Para Fazer, Fazendo ou Pronto). ' +
        'É pedido um registro breve do que foi feito — isso alimenta o histórico ' +
        'da aula. Não usamos o termo “Sprint” aqui: o ciclo é a própria aula ' +
        'ou a continuidade/reinício no EduScrum.',
      options: [
        {
          label: 'Abrir Mesa (agenda e mapa)',
          next: 'kanban_mover',
          href: '/mesa-do-inovador',
        },
        { label: 'Voltar ao Kanban', next: 'kanban' },
        { label: 'Voltar ao início', next: 'inicio' },
      ],
    },
    kanban_onde: {
      message:
        'No Dia a Dia, o Kanban fica ao lado do planejamento do ciclo. ' +
        'Nos Desafios, depois de gerar o plano EduScrum, o quadro aparece ' +
        'na etapa de execução da aula registrada na agenda.',
      options: [
        { label: 'Ir ao Dia a Dia', next: 'kanban_onde', href: '/dia-a-dia' },
        { label: 'Ir a Desafios', next: 'kanban_onde', href: '/desafio' },
        { label: 'Voltar ao Kanban', next: 'kanban' },
        { label: 'Voltar ao início', next: 'inicio' },
      ],
    },
    planos: {
      message:
        'No plano gratuito você começa com {{FREEMIUM_DESAFIOS}} desafio (crédito de IA). ' +
        'O Dia a Dia fica liberado para navegação; o registro de aulas exige ' +
        'plano Profissional, Mentor ou pacote avulso.',
      options: [
        { label: 'Limites do plano grátis', next: 'planos_limites' },
        { label: 'Como assinar / comprar créditos?', next: 'planos_assinar' },
        { label: 'Renovação e cancelamento', next: 'planos_cancelar' },
        { label: 'Voltar ao início', next: 'inicio' },
      ],
    },
    planos_limites: {
      message:
        'Gratuito: {{FREEMIUM_DESAFIOS}} crédito de desafio. ' +
        'Registro no Dia a Dia não está incluso — só navegação. ' +
        'Quando o crédito acaba, a estruturação com IA fica bloqueada até ' +
        'você escolher um plano ou pacote.',
      options: [
        { label: 'Como assinar?', next: 'planos_assinar' },
        { label: 'Voltar a Planos', next: 'planos' },
        { label: 'Voltar ao início', next: 'inicio' },
      ],
    },
    planos_assinar: {
      message:
        'Use o botão Ver planos (no topo ou quando os créditos acabam). ' +
        'Você escolhe o plano no Action Hub e paga com Mercado Pago ' +
        '(cartão e demais meios disponíveis no checkout). ' +
        'Profissional R$ 24,90 · Mentor R$ 49,90 · pacote avulso de 3 desafios.',
      options: [
        {
          label: 'Abrir planos (upgrade)',
          next: 'planos_assinar',
          action: 'open_upgrade',
        },
        { label: 'Voltar a Planos', next: 'planos' },
        { label: 'Voltar ao início', next: 'inicio' },
      ],
    },
    planos_cancelar: {
      message:
        'Assinaturas e cobranças ficam no Action Hub / Mercado Pago. ' +
        'Para alterar ou cancelar, use o fluxo de planos/conta do Hub ' +
        'ou o suporte indicado na página de pagamento. ' +
        'Pacotes avulsos de créditos não renovam automaticamente.',
      options: [
        { label: 'Voltar a Planos', next: 'planos' },
        { label: 'Voltar ao início', next: 'inicio' },
      ],
    },
  },
};

const EXPECTED_NODE_IDS = [
  'inicio',
  'dia_a_dia',
  'dia_estacoes',
  'dia_dinamica',
  'desafios',
  'desafio_escrever',
  'desafio_credito',
  'kanban',
  'kanban_mover',
  'kanban_onde',
  'planos',
  'planos_limites',
  'planos_assinar',
  'planos_cancelar',
];

const DATABASE_URL =
  process.env.DATABASE_URL ||
  'postgresql://admin:password123@localhost:5433/leaction_hub';

function pgClientConfig(databaseUrl) {
  const forceSsl =
    /sslmode=(require|verify-full|verify-ca|no-verify)/i.test(databaseUrl) ||
    databaseUrl.includes('rds.amazonaws.com');
  const connectionString = databaseUrl
    .replace(/([?&])sslmode=[^&]*/gi, '$1')
    .replace(/[?&]$/, '')
    .replace(/\?&/, '?');
  return {
    connectionString,
    ssl: forceSsl ? { rejectUnauthorized: false } : false,
  };
}

(async () => {
  const missing = EXPECTED_NODE_IDS.filter((id) => !(id in TREE.nodes));
  if (missing.length) {
    console.error('Nós faltando na árvore seed:', missing.join(', '));
    process.exit(1);
  }
  const extra = Object.keys(TREE.nodes).filter((id) => !EXPECTED_NODE_IDS.includes(id));
  if (extra.length) {
    console.error('Nós extras (não esperados):', extra.join(', '));
    process.exit(1);
  }

  const errors = validateTree(TREE);
  if (errors.length) {
    console.error('Árvore inválida:');
    for (const e of errors) console.error(' -', e);
    process.exit(1);
  }

  const client = new Client(pgClientConfig(DATABASE_URL));
  await client.connect();

  const table = await client.query(
    `SELECT COUNT(*)::int AS n FROM information_schema.tables
     WHERE table_schema = 'public' AND table_name = 'cms_assistente_chat'`
  );
  if (table.rows[0].n !== 1) {
    console.error(
      'Tabela cms_assistente_chat não existe. Rode antes:\n' +
        '  node scripts/apply-cms-assistente-chat-patch.js'
    );
    await client.end();
    process.exit(1);
  }

  const result = await client.query(
    `INSERT INTO cms_assistente_chat
       (sistema_destino, status, tree, publicado_em, atualizado_em, atualizado_por)
     VALUES ('inove4us', 'publicado', $1::jsonb, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'seed')
     ON CONFLICT (sistema_destino, status) DO UPDATE SET
       tree = EXCLUDED.tree,
       publicado_em = CURRENT_TIMESTAMP,
       atualizado_em = CURRENT_TIMESTAMP,
       atualizado_por = EXCLUDED.atualizado_por
     RETURNING id, sistema_destino, status, publicado_em`,
    [JSON.stringify(TREE)]
  );

  const row = result.rows[0];
  console.log('Seed OK:', {
    id: row.id,
    sistema_destino: row.sistema_destino,
    status: row.status,
    publicado_em: row.publicado_em,
    nodes: Object.keys(TREE.nodes).length,
  });

  // Sanity: mesma query do GET público
  const pub = await client.query(
    `SELECT tree FROM cms_assistente_chat
     WHERE status = 'publicado' AND sistema_destino = 'inove4us'
     LIMIT 1`
  );
  const tree = pub.rows[0]?.tree;
  const recheck = validateTree(tree);
  if (recheck.length) {
    console.error('Falha na revalidação pós-insert:', recheck);
    await client.end();
    process.exit(1);
  }
  console.log('GET equivalente OK — root_id=', tree.root_id, 'avatar=', tree.avatar_name);

  await client.end();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
