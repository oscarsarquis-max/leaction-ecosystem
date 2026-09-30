'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { FUNIS, resolveFunil, montarFunilLoja } = require('./crm-funis');
const { classificarEvento } = require('./crm-funcionalidades');
const {
  parseDisplayNome,
  parseUsuarioOrigem,
  sanitizarIngestaoLoja,
} = require('./crm-tracking');

function sha(text) {
  return crypto.createHash('sha256').update(text).digest('hex');
}

const SQL_HASH = {
  inove: 'e903b224379f',
  school: '0daec8e4c5c6',
  paneldx: '3e6ec6a0539e',
};

test('funis de inove, school e paneldx permanecem o SQL transcrito', () => {
  const pairs = [
    ['inove', 'inove4us', 'eng_inove'],
    ['school', 'inove4us-school', 'eng_school'],
    ['paneldx', 'paneldx', 'eng_paneldx'],
  ];
  for (const [file, sistema, engFile] of pairs) {
    const funilPath = path.join(__dirname, `_sql_${file}.txt`);
    const engPath = path.join(__dirname, `_sql_${engFile}.txt`);
    assert.equal(sha(FUNIS[sistema].funilSql).slice(0, 12), SQL_HASH[file]);
    if (fs.existsSync(funilPath)) {
      assert.equal(FUNIS[sistema].funilSql, fs.readFileSync(funilPath, 'utf8'));
      assert.equal(FUNIS[sistema].engagementSql, fs.readFileSync(engPath, 'utf8'));
    }
    assert.equal(FUNIS[sistema].ramos.length, 0);
  }
  assert.equal(FUNIS.inove4us.modelo, 'inove4us_desafio_plano_pagamento');
  assert.equal(FUNIS['inove4us-school'].modelo, 'inove4us_school_b2b');
  assert.equal(FUNIS.paneldx.modelo, 'paneldx_freemium');
  assert.equal(FUNIS.paneldx.fallback, true);
  assert.deepEqual(
    FUNIS.inove4us.etapas.map((e) => e.rotulo),
    ['Acesso / Mesa', 'Criou desafio', 'Elaborou plano', 'Pagou / assinou']
  );
  assert.deepEqual(
    FUNIS['inove4us-school'].etapas.map((e) => e.rotulo),
    ['Acesso', 'Login', 'Checkout', 'Pagou']
  );
  assert.deepEqual(
    FUNIS.paneldx.etapas.map((e) => e.rotulo),
    ['Home', 'Interesse (Clique)', 'Uso Real']
  );
});

test('origem desconhecida cai no fallback nomeado paneldx', () => {
  const funil = resolveFunil('origem-que-nao-existe');
  assert.equal(funil.fallbackDe, 'paneldx');
  assert.equal(funil.modelo, 'paneldx_freemium');
  assert.equal(funil.funilSql, FUNIS.paneldx.funilSql);
  assert.equal(funil.solicitado, 'origem-que-nao-existe');
  assert.match(funil.funilSql, /s\.sistema_origem = \$1/);
});

test('funil da loja conta sessao e o ramo nao entra na cadeia', () => {
  const cheio = montarFunilLoja({
    visitas_home: 1,
    etapa_escolha: 1,
    etapa_pedido: 1,
    etapa_aceite: 1,
    etapa_pagamento: 1,
    ramo_outra_data: 0,
  });
  assert.deepEqual(
    cheio.etapas.map((e) => e.rotulo),
    ['Visita', 'Escolha', 'Pedido enviado', 'Aceite da padaria', 'Pagamento']
  );
  assert.deepEqual(
    cheio.etapas.map((e) => e.sessoes),
    [1, 1, 1, 1, 1]
  );
  assert.deepEqual(
    cheio.etapas.slice(1).map((e) => e.conv_anterior_pct),
    [100, 100, 100, 100]
  );
  assert.equal(cheio.conversao_visita_aceite_pct, 100);
  assert.match(cheio.nota, /aceite da padaria/);

  const ramo = montarFunilLoja({
    visitas_home: 1,
    etapa_escolha: 1,
    etapa_pedido: 0,
    etapa_aceite: 0,
    etapa_pagamento: 0,
    ramo_outra_data: 1,
  });
  assert.deepEqual(
    ramo.etapas.map((e) => e.sessoes),
    [1, 1, 0, 0, 0]
  );
  assert.equal(ramo.ramos[0].sessoes, 1);
  assert.equal(ramo.ramos[0].pct, 100);
  assert.equal(ramo.ramos[0].sobre, 'escolha');
  assert.equal(ramo.conversao_visita_aceite_pct, 0);
});

test('prompt 137 rejeita @ e CPF so em nome de exibicao', () => {
  assert.equal(parseDisplayNome('ana@escola.com'), null);
  assert.equal(parseDisplayNome('123.456.789-09'), null);
  assert.equal(parseDisplayNome('Ana Gestora'), 'Ana Gestora');
  const email = parseUsuarioOrigem('ana@escola.com');
  assert.equal(email.ref, 'ana@escola.com');
  assert.equal(email.intId, null);
});

test('lojadepaes nao grava instituicao nem dado pessoal; as outras origens seguem iguais', () => {
  const hash = 'a'.repeat(64);
  const loja = sanitizarIngestaoLoja('lojadepaes', {
    usuario: parseUsuarioOrigem('cliente@padaria.com'),
    instituicaoId: '11111111-1111-4111-8111-111111111111',
    usuarioNome: 'Cliente',
    instituicaoNome: 'Padaria',
    dados: { email: 'cliente@padaria.com', fornada: '2026-09-23', cpf: '123.456.789-09' },
  });
  assert.equal(loja.usuario.ref, null);
  assert.equal(loja.instituicaoId, null);
  assert.equal(loja.usuarioNome, null);
  assert.equal(loja.instituicaoNome, null);
  assert.equal(loja.dados.email, null);
  assert.equal(loja.dados.cpf, null);
  assert.equal(loja.dados.fornada, '2026-09-23');

  const interno = sanitizarIngestaoLoja('lojadepaes', {
    usuario: parseUsuarioOrigem(hash),
    instituicaoId: '11111111-1111-4111-8111-111111111111',
    usuarioNome: null,
    instituicaoNome: null,
    dados: { pedido: 'p1' },
  });
  assert.equal(interno.usuario.ref, hash);
  assert.equal(interno.instituicaoId, null);

  const inove = sanitizarIngestaoLoja('inove4us', {
    usuario: parseUsuarioOrigem('gestor@escola.com'),
    instituicaoId: '11111111-1111-4111-8111-111111111111',
    usuarioNome: 'Ana Gestora',
    instituicaoNome: 'Escola',
    dados: { email: 'gestor@escola.com' },
  });
  assert.equal(inove.usuario.ref, 'gestor@escola.com');
  assert.equal(inove.instituicaoId, '11111111-1111-4111-8111-111111111111');
  assert.equal(inove.usuarioNome, 'Ana Gestora');
  assert.equal(inove.dados.email, 'gestor@escola.com');
});

test('taxonomia da loja nao cai em Nao mapeado e nao move o inove', () => {
  const cls = (sistema, tipo, url) =>
    classificarEvento({ sistema_origem: sistema, tipo_evento: tipo, url_pagina: url });
  assert.equal(cls('lojadepaes', 'pageview', '/').chave, 'vitrine');
  assert.equal(cls('lojadepaes', 'fornada_escolher', '/').chave, 'vitrine');
  assert.equal(cls('lojadepaes', 'data_solicitar', '/').chave, 'vitrine');
  assert.equal(cls('lojadepaes', 'pedido_enviar', '/').chave, 'pedido');
  assert.equal(cls('lojadepaes', 'pedido_aceitar', '/').chave, 'pedido');
  assert.equal(cls('lojadepaes', 'pagamento_registrar', '/').chave, 'financeiro');
  assert.equal(cls('lojadepaes', 'evento_novo', '/').chave, 'outros');
  assert.equal(cls('inove4us', 'pageview', '/').chave, 'acesso');
  assert.equal(cls('inove4us', 'pageview', '/desafio').chave, 'desafio');
  assert.equal(cls('inove4us-school', 'pageview', '/').chave, 'acesso');
  assert.equal(cls('inove4us', 'pagamento_aprovado', '/pagamento').chave, 'comercial');
});
