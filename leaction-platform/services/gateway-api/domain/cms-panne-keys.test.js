'use strict';

/**
 * Smoke unitário — allowlist e defaults Panne (sem Postgres).
 * node --test services/gateway-api/domain/cms-panne-keys.test.js
 */
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const {
  defaultsForConfigKey,
  defaultPanneLanding,
} = require('./cms-landing');

describe('CMS keys Panne', () => {
  it('defaults distintos para panne-demo e panne', () => {
    const demo = defaultsForConfigKey('panne-demo');
    const prod = defaultsForConfigKey('panne');
    assert.ok(demo.landing.coluna1?.title);
    assert.ok(prod.landing.coluna1?.title);
    assert.notEqual(demo.instructions, prod.instructions);
    assert.match(demo.instructions, /panne-demo/);
    assert.match(prod.instructions, /preparat/);
    assert.equal(demo.landing.hero_cta?.visible, false);
    assert.equal(prod.landing.hero_cta?.visible, false);
  });

  it('defaultPanneLanding demo vs prod não compartilham título idêntico', () => {
    const a = defaultPanneLanding('demo');
    const b = defaultPanneLanding('prod');
    assert.notEqual(a.coluna1.title, b.coluna1.title);
  });

  it('inove4us e default permanecem intactos', () => {
    const inv = defaultsForConfigKey('inove4us');
    const def = defaultsForConfigKey('default');
    assert.match(String(inv.landing.hero?.leaction_title || ''), /inove4us/i);
    assert.ok(def.landing);
  });
});
