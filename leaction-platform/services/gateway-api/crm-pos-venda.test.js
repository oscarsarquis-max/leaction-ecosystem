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
console.log('crm-pos-venda.test.js ok');
