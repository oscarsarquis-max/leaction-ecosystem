'use strict';

/**
 * BLOG-025 — helpers da enquete lúdica (sem Bedrock/DB).
 * node --test domain/cms-enquete-ludica.test.js
 */
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const {
  parseOpcoes,
  opcoesPublicas,
  resultadoDe,
  textMentionsProduct,
  normalizeVitrineItem,
  shapeEnquete,
} = require('./cms-right-now');

describe('BLOG-025 — enquete lúdica helpers', () => {
  it('parseOpcoes guarda detalhe e produto_*', () => {
    const parsed = parseOpcoes([
      {
        id: 'a',
        pt: 'Crosta quente',
        en: 'Warm crust',
        detalhe_pt: 'trigo tostado',
        detalhe_en: 'toasted wheat',
        produto_id: '1',
        produto_nome: 'Focaccia',
        produto_url: 'https://lojadepaes.com.br/paes/focaccia',
      },
      { id: 'b', pt: 'Miolo macio', en: 'Soft crumb', detalhe: 'manteiga' },
    ]);
    assert.equal(parsed.error, undefined);
    assert.equal(parsed.opcoes[0].detalhe_pt, 'trigo tostado');
    assert.equal(parsed.opcoes[0].produto_nome, 'Focaccia');
    assert.equal(parsed.opcoes[1].detalhe_pt, 'manteiga');
  });

  it('opcoesPublicas esconde produto antes do voto e shapeEnquete revela depois', () => {
    const opcoes = [
      {
        id: 'a',
        pt: 'Crosta',
        en: 'Crust',
        detalhe_pt: 'aroma',
        produto_nome: 'Segredo',
        produto_url: 'https://x',
      },
    ];
    assert.equal(opcoesPublicas(opcoes)[0].produto_nome, undefined);
    assert.equal(opcoesPublicas(opcoes)[0].detalhe_pt, 'aroma');
    assert.equal(
      opcoesPublicas(opcoes, { revelarProduto: true })[0].produto_nome,
      'Segredo'
    );

    const before = shapeEnquete(
      {
        id: 1,
        pergunta_pt: 'Q?',
        pergunta_en: 'Q?',
        opcoes,
        fecha_em: new Date(Date.now() + 86400000).toISOString(),
      },
      null,
      []
    );
    assert.equal(before.opcoes[0].produto_nome, undefined);
    assert.equal(before.opcoes[0].detalhe_pt, 'aroma');

    const after = shapeEnquete(
      {
        id: 1,
        pergunta_pt: 'Q?',
        pergunta_en: 'Q?',
        opcoes,
        fecha_em: new Date(Date.now() + 86400000).toISOString(),
      },
      { id: 9 },
      [{ opcao_id: 'a', n: 2 }]
    );
    assert.equal(after.votou, true);
    assert.equal(after.opcoes[0].produto_nome, 'Segredo');
    assert.equal(after.total, 2);
  });

  it('resultadoDe e menção a produto', () => {
    const tally = resultadoDe(
      [{ id: 'a' }, { id: 'b' }],
      [
        { opcao_id: 'a', n: 3 },
        { opcao_id: 'b', n: 1 },
      ]
    );
    assert.equal(tally.total, 4);
    assert.equal(tally.resultado.find((r) => r.id === 'a').pct, 75);

    assert.equal(
      textMentionsProduct('amo a Focaccia de domingo', [{ nome: 'Focaccia' }]),
      true
    );
    assert.equal(textMentionsProduct('crosta quente', [{ nome: 'Focaccia' }]), false);
    assert.deepEqual(normalizeVitrineItem({ id: 7, nome: 'Pão', url: 'https://x' }), {
      id: '7',
      nome: 'Pão',
      url: 'https://x',
    });
  });
});
