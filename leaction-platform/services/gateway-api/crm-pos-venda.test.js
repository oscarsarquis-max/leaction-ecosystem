'use strict';

const assert = require('assert');
const { avaliarAlertas, LIMIARES, montarEtapas, daysSinceSp } = require('./crm-pos-venda');

function daysAgo(n) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d;
}

const now = new Date();
const fake = {
  instituicao_id: '00000000-0000-4000-8000-000000000099',
  contratou_em: daysAgo(20),
  login_gestor: null,
  senha_alterar: null,
  turma_criar: null,
  aluno_matricular: null,
  n_convidar: 0,
  n_aceitar: 1,
  n_prof_usando: 0,
  dias_uso_7d: 0,
  seats: 50,
  snap_school: {
    turmas: 0,
    alunos: 0,
    professores_vinculo: { pendente: 0, ativo: 1 },
    licencas: { em_uso: 1, total_assentos: 50 },
  },
};

const built = montarEtapas(fake, now);
assert.strictEqual(built.etapas.contratou.feito, true);
assert.strictEqual(built.etapas.gestor_login.feito, false);
assert.ok(built.licencas.em_uso / built.licencas.total < 0.2);

const { alertas } = avaliarAlertas(
  {
    etapas: built.etapas,
    professoresCounts: built.professores,
    licencas: built.licencas,
    teveUsoProf: false,
  },
  now
);
assert.ok(alertas.some((a) => a.chave === 'pagou_nao_logou'), 'pagou_nao_logou');
assert.ok(alertas.some((a) => a.chave === 'licenca_ociosa'), 'licenca_ociosa');

const limZero = JSON.parse(JSON.stringify(LIMIARES));
limZero.pagou_nao_logou.dias = 0;
const hoje = montarEtapas({ ...fake, contratou_em: now, snap_school: { ...fake.snap_school, licencas: { em_uso: 40, total_assentos: 50 }, professores_vinculo: { pendente: 0, ativo: 40 } } }, now);
const withDefault = avaliarAlertas({ etapas: hoje.etapas, professoresCounts: hoje.professores, licencas: hoje.licencas, teveUsoProf: false }, now, LIMIARES);
const withZero = avaliarAlertas({ etapas: hoje.etapas, professoresCounts: hoje.professores, licencas: hoje.licencas, teveUsoProf: false }, now, limZero);
assert.ok(!withDefault.alertas.some((a) => a.chave === 'pagou_nao_logou'));
assert.ok(withZero.alertas.some((a) => a.chave === 'pagou_nao_logou'));
assert.ok(daysSinceSp(now, now) === 0);

const helenita = montarEtapas(
  {
    instituicao_id: 'e9aeac41-55aa-4eab-b223-f9f03be2fea0',
    contratou_em: daysAgo(0),
    login_gestor: daysAgo(0),
    senha_alterar: null,
    turma_criar: null,
    aluno_matricular: null,
    n_convidar: 0,
    n_aceitar: 0,
    n_prof_usando: 0,
    dias_uso_7d: 0,
    seats: 50,
    snap_school: {
      turmas: 6,
      alunos: 0,
      professores_vinculo: { pendente: 6, ativo: 0 },
      licencas: { em_uso: 0, total_assentos: 50 },
    },
  },
  now
);
assert.strictEqual(helenita.etapas.contratou.quantidade, null);
assert.strictEqual(helenita.etapas.contratou.quantidade_rotulo, null);
assert.strictEqual(helenita.etapas.criou_turmas.quantidade, 6);
assert.strictEqual(helenita.etapas.criou_turmas.quantidade_rotulo, '6 turmas');
assert.strictEqual(helenita.etapas.cadastrou_alunos.quantidade, 0);
assert.strictEqual(helenita.etapas.cadastrou_alunos.quantidade_rotulo, '0 alunos');
assert.strictEqual(helenita.etapas.convidou_professores.quantidade, 6);
assert.strictEqual(helenita.etapas.convidou_professores.quantidade_rotulo, '6 convidados');
assert.strictEqual(helenita.etapas.professores_aceitaram.quantidade, 0);
assert.strictEqual(
  helenita.etapas.professores_aceitaram.quantidade_rotulo,
  '0 de 6 aceitaram · licenças 0/50'
);
assert.strictEqual(helenita.etapas.professores_usaram.quantidade, 0);
assert.strictEqual(helenita.etapas.professores_usaram.quantidade_rotulo, '0 de 6 usando');
assert.strictEqual(helenita.etapas.uso_recorrente.quantidade, 0);
assert.strictEqual(helenita.etapas.uso_recorrente.quantidade_rotulo, '0 dias ativos em 7');

const escolaTeste = montarEtapas(
  {
    ...fake,
    snap_school: {
      turmas: 3,
      alunos: 18,
      professores_vinculo: { pendente: 0, ativo: 4 },
      licencas: { em_uso: 4, total_assentos: 50 },
    },
  },
  now
);
assert.strictEqual(escolaTeste.etapas.criou_turmas.quantidade_rotulo, '3 turmas');
assert.strictEqual(escolaTeste.etapas.cadastrou_alunos.quantidade_rotulo, '18 alunos');

const semSnap = montarEtapas({ ...fake, snap_school: null, n_aceitar: 0 }, now);
assert.strictEqual(semSnap.etapas.criou_turmas.quantidade, null);
assert.strictEqual(semSnap.etapas.criou_turmas.quantidade_rotulo, 'sem snapshot ainda');
assert.strictEqual(semSnap.etapas.cadastrou_alunos.quantidade, null);
assert.strictEqual(semSnap.etapas.cadastrou_alunos.quantidade_rotulo, 'sem snapshot ainda');
assert.notStrictEqual(semSnap.etapas.criou_turmas.quantidade_rotulo, 'undefined');

console.log('crm-pos-venda.test.js ok');
