/**
 * Aplica migration + seed (rascunho e publicado) do assistente comercial_publico.
 *
 * Uso (na raiz leaction-platform, com gateway .env DATABASE_URL):
 *   node scripts/seed-cms-assistente-comercial-publico.js
 */
const fs = require('fs');
const path = require('path');
const { Client } = require('pg');

function loadEnv(filePath) {
  const out = {};
  if (!fs.existsSync(filePath)) return out;
  const raw = fs.readFileSync(filePath, 'utf8').replace(/^\uFEFF/, '');
  for (const line of raw.split(/\r?\n/)) {
    const m = line.match(/^([A-Z0-9_]+)=(.*)$/);
    if (!m) continue;
    let v = m[2].trim();
    if (
      (v.startsWith('"') && v.endsWith('"')) ||
      (v.startsWith("'") && v.endsWith("'"))
    ) {
      v = v.slice(1, -1);
    }
    out[m[1]] = v;
  }
  return out;
}

const TREE = {
  avatar_name: 'Comercial',
  avatar_tagline: 'Contratação e primeiros passos',
  avatar_candidates: ['Comercial'],
  root_id: 'inicio',
  nodes: {
    inicio: {
      message:
        'Olá! Posso ajudar na contratação — inove4us school, Inove4Us (professor) ou serviços do ActionHub. Escolha uma opção:',
      options: [
        {
          label: 'Sou escola, quero conhecer o inove4us school',
          next: 'escola',
        },
        {
          label: 'Sou professor(a), quero conhecer o Inove4Us',
          next: 'professor',
        },
        {
          label: 'Quero saber sobre os serviços do Hub',
          next: 'hub',
        },
        {
          label: 'Quero falar direto com alguém',
          href: 'https://wa.me/5585999031861',
        },
      ],
    },
    escola: {
      message:
        'O inove4us school é a Torre de Controle da escola: governança, equipe, método e visão do que acontece em sala — sem misturar com o app do professor. Planos e checkout ficam na vitrine /ecossistema.',
      options: [
        { label: 'Ver planos e contratar', href: '/ecossistema' },
        { label: 'Falar no WhatsApp', href: 'https://wa.me/5585999031861' },
        { label: 'Voltar', next: 'inicio' },
      ],
    },
    professor: {
      message:
        'O Inove4Us é a ferramenta do professor (Mesa do Inovador): roteiro pronto, execução e diário no fluxo da aula — freemium para começar. Cadastro e acesso ficam em inove4us.com.br.',
      options: [
        { label: 'Ir para o cadastro / acesso', href: 'https://inove4us.com.br/acesso' },
        { label: 'Falar no WhatsApp', href: 'https://wa.me/5585999031861' },
        { label: 'Voltar', next: 'inicio' },
      ],
    },
    hub: {
      message:
        'O ActionHub concentra marketplace B2B, planos, CMS e a ponte com os satélites do ecossistema. Para entender o que cabe na sua operação, o canal comercial é o WhatsApp.',
      options: [
        { label: 'Conversar no WhatsApp', href: 'https://wa.me/5585999031861' },
        { label: 'Voltar', next: 'inicio' },
      ],
    },
  },
};

async function main() {
  const root = path.resolve(__dirname, '..');
  const e = loadEnv(path.join(root, '.env'));
  if (!e.DATABASE_URL) throw new Error('DATABASE_URL ausente em .env');

  const u = new URL(e.DATABASE_URL);
  const client = new Client({
    host: u.hostname,
    port: Number(u.port || 5432),
    user: decodeURIComponent(u.username),
    password: decodeURIComponent(u.password),
    database: u.pathname.replace(/^\//, ''),
  });
  await client.connect();

  const patch = fs.readFileSync(
    path.join(root, 'shared/database/patch_cms_assistente_comercial_publico.sql'),
    'utf8'
  );
  await client.query(patch);
  console.log('OK migration comercial_publico');

  for (const status of ['rascunho', 'publicado']) {
    const publicadoEm = status === 'publicado';
    await client.query(
      `INSERT INTO cms_assistente_chat
         (sistema_destino, status, tree, publicado_em, atualizado_em, atualizado_por)
       VALUES ($1::varchar, $2::varchar, $3::jsonb,
               CASE WHEN $2::varchar = 'publicado' THEN NOW() ELSE NULL END,
               NOW(), $4::text)
       ON CONFLICT (sistema_destino, status) DO UPDATE SET
         tree = EXCLUDED.tree,
         atualizado_em = NOW(),
         atualizado_por = EXCLUDED.atualizado_por,
         publicado_em = CASE
           WHEN EXCLUDED.status = 'publicado' THEN NOW()
           ELSE cms_assistente_chat.publicado_em
         END`,
      ['comercial_publico', status, JSON.stringify(TREE), 'seed-script']
    );
    console.log('OK upsert', status, publicadoEm ? '(publicado)' : '(rascunho)');
  }

  await client.end();
  console.log('Seed comercial_publico concluído.');
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
