'use strict';

/**
 * Smoke da API de identidade (sem HTTP — chama o domínio direto).
 * Garante upsert, validação de função, união de permissões e update admin.
 */

const path = require('path');
const { Pool } = require('pg');
const {
  upsertUsuario,
  getUsuarioPerfil,
  updateUsuarioAdmin,
  upsertFuncao,
  createPermissao,
} = require('../domain/identidade-api');

require('dotenv').config({
  path: path.join(__dirname, '../../../.env'),
  override: true,
});

const APP_ID = 'identidade.smoke';
const EMAIL = 'identidade.smoke@test.local';

function parseDatabaseUrl(url) {
  if (!url) return null;
  try {
    const u = new URL(url);
    return {
      host: u.hostname,
      port: Number(u.port || 5432),
      database: decodeURIComponent(u.pathname.replace(/^\//, '')),
      user: decodeURIComponent(u.username),
      password: decodeURIComponent(u.password),
    };
  } catch {
    return null;
  }
}

const db = parseDatabaseUrl(process.env.DATABASE_URL) || {
  host: process.env.DB_HOST || '127.0.0.1',
  port: Number(process.env.DB_PORT || 5434),
  database: process.env.DB_NAME || 'leaction_hub',
  user: process.env.DB_USER || 'admin',
  password: process.env.DB_PASS || 'password123',
};

const pool = new Pool(db);

(async () => {
  await pool.query(
    `INSERT INTO app_registry (app_id, name, webhook_secret, return_origins, active)
     VALUES ($1, 'Identidade smoke', $2, ARRAY[]::TEXT[], TRUE)
     ON CONFLICT (app_id) DO UPDATE
       SET active = TRUE`,
    [APP_ID, 'dev-identidade-smoke-secret']
  );

  await pool.query(`DELETE FROM identidade_usuarios WHERE sistema = $1`, [APP_ID]);
  await pool.query(`DELETE FROM identidade_funcoes WHERE sistema = $1`, [APP_ID]);
  await pool.query(`DELETE FROM identidade_permissoes WHERE sistema = $1`, [APP_ID]);

  const missingFuncao = await upsertUsuario(pool, {
    sistema: APP_ID,
    email: EMAIL,
    nome: 'Smoke User',
    nivel: 'usuario_executor',
    funcao: 'professor',
  });
  if (missingFuncao.ok || missingFuncao.status !== 400) {
    throw new Error('deveria recusar função inexistente');
  }
  if (!String(missingFuncao.error || '').includes('não existe')) {
    throw new Error(`erro de função deveria ser específico: ${missingFuncao.error}`);
  }
  console.log('funcao_missing', missingFuncao.error);

  const badNivel = await upsertUsuario(pool, {
    sistema: APP_ID,
    email: EMAIL,
    nome: 'Smoke User',
    nivel: 'superuser',
  });
  if (badNivel.ok || badNivel.status !== 400) {
    throw new Error('deveria recusar nivel inválido');
  }
  console.log('nivel_invalid', badNivel.error);

  const permA = await createPermissao(pool, {
    sistema: APP_ID,
    chave: 'criar_aula',
    descricao: 'Criar aula',
  });
  const permB = await createPermissao(pool, {
    sistema: APP_ID,
    chave: 'editar_perfil_proprio',
    descricao: 'Editar perfil próprio',
  });
  if (!permA.ok || !permB.ok) {
    throw new Error('falha ao criar permissões de smoke');
  }

  const dup = await createPermissao(pool, {
    sistema: APP_ID,
    chave: 'criar_aula',
    descricao: 'duplicada',
  });
  if (dup.ok || dup.status !== 409) {
    throw new Error('chave duplicada deveria ser 409');
  }

  const fn = await upsertFuncao(pool, {
    sistema: APP_ID,
    nome: 'professor',
    nivel_associado: 'usuario_executor',
    permissoes: ['criar_aula', 'editar_perfil_proprio'],
  });
  if (!fn.ok || fn.funcao.nome !== 'professor') {
    throw new Error('falha ao upsert função');
  }

  const created = await upsertUsuario(pool, {
    sistema: APP_ID,
    email: EMAIL,
    nome: 'Smoke User',
    nivel: 'usuario_executor',
    funcao: 'professor',
  });
  if (!created.ok || created.usuario.nivel !== 'usuario_executor') {
    throw new Error('falha no upsert inicial');
  }
  console.log('upsert_create', created.usuario.id);

  const executor = await getUsuarioPerfil(pool, { sistema: APP_ID, email: EMAIL });
  if (!executor.ok) throw new Error(executor.error);
  if (executor.perfil.permissoes.sort().join(',') !== 'criar_aula,editar_perfil_proprio') {
    throw new Error(`executor permissoes inesperadas: ${executor.perfil.permissoes}`);
  }
  console.log('executor_perfil', executor.perfil);

  const promoted = await upsertUsuario(pool, {
    sistema: APP_ID,
    email: EMAIL,
    nome: 'Smoke Admin',
    nivel: 'admin',
    funcao: 'professor',
  });
  if (!promoted.ok || promoted.usuario.nome !== 'Smoke Admin') {
    throw new Error('upsert deveria atualizar nome/nivel');
  }

  const adminPerfil = await getUsuarioPerfil(pool, { sistema: APP_ID, email: EMAIL });
  if (!adminPerfil.ok) throw new Error(adminPerfil.error);
  if (adminPerfil.perfil.permissoes.sort().join(',') !== 'criar_aula,editar_perfil_proprio') {
    throw new Error(`admin deveria herdar todas as chaves: ${adminPerfil.perfil.permissoes}`);
  }
  console.log('admin_perfil', adminPerfil.perfil);

  const missing = await getUsuarioPerfil(pool, {
    sistema: APP_ID,
    email: 'nobody@test.local',
  });
  if (missing.ok || missing.status !== 404) {
    throw new Error('usuário ausente deveria ser 404');
  }

  const updated = await updateUsuarioAdmin(pool, created.usuario.id, {
    nivel: 'gestor_produtivo',
    funcao: null,
    status: 'inativo',
  });
  if (!updated.ok || updated.usuario.status !== 'inativo') {
    throw new Error('update admin falhou');
  }
  const gestor = await getUsuarioPerfil(pool, { sistema: APP_ID, email: EMAIL });
  if (!gestor.ok || gestor.perfil.permissoes.length !== 0) {
    throw new Error('gestor sem função não deve ter permissões extras');
  }
  console.log('gestor_sem_funcao', gestor.perfil);

  await pool.query(`DELETE FROM identidade_usuarios WHERE sistema = $1`, [APP_ID]);
  await pool.query(`DELETE FROM identidade_funcoes WHERE sistema = $1`, [APP_ID]);
  await pool.query(`DELETE FROM identidade_permissoes WHERE sistema = $1`, [APP_ID]);
  await pool.query(`DELETE FROM app_registry WHERE app_id = $1`, [APP_ID]);

  console.log('SMOKE_OK');
  await pool.end();
})().catch(async (e) => {
  console.error(e);
  try {
    await pool.end();
  } catch {
    /* ignore */
  }
  process.exit(1);
});
