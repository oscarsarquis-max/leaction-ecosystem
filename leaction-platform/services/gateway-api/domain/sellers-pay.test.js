'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('crypto');
const fs = require('node:fs');
const path = require('node:path');
const {
  encryptSellerSecret,
  decryptSellerSecret,
} = require('../lib/seller-crypto');
const {
  signState,
  verifyState,
  signChargeToken,
  verifyChargeToken,
  returnToAllowed,
  sellerPaymentsEnabled,
  isSellerAppAllowed,
  upsertSellerAccount,
  ensureSellerAccessToken,
  STATE_TTL_MS,
} = require('./sellers-oauth');
const {
  mapMpToChargeStatus,
  applyPaymentObservation,
  createPixWithSellerToken,
  createCardWithSellerToken,
} = require('./seller-charges');

const KEY = Buffer.alloc(32, 7).toString('base64');
const STATE = 'seller-state-secret-for-tests-32b';

async function withEnv(map, fn) {
  const prev = {};
  for (const [k, v] of Object.entries(map)) {
    prev[k] = process.env[k];
    if (v == null) delete process.env[k];
    else process.env[k] = v;
  }
  try {
    return await fn();
  } finally {
    for (const [k, v] of Object.entries(prev)) {
      if (v === undefined) delete process.env[k];
      else process.env[k] = v;
    }
  }
}

function memoryPool(seed = {}) {
  const tables = {
    seller_accounts: [...(seed.seller_accounts || [])],
    seller_charges: [...(seed.seller_charges || [])],
    app_registry: [
      {
        app_id: 'lojadepaes',
        name: 'Loja',
        active: true,
        webhook_secret: 'secret-loja',
        return_origins: ['https://lojadepaes.com.br'],
      },
    ],
  };
  return {
    tables,
    async query(sql, params = []) {
      const text = String(sql).replace(/\s+/g, ' ').trim();
      if (text.startsWith('SELECT app_id, name, active')) {
        const row = tables.app_registry.find((r) => r.app_id === params[0]);
        return { rows: row ? [row] : [] };
      }
      if (text.includes('FROM seller_accounts WHERE app_id') && text.includes('seller_ref')) {
        const row = tables.seller_accounts.find(
          (r) => r.app_id === params[0] && r.seller_ref === params[1]
        );
        return { rows: row ? [{ ...row }] : [] };
      }
      if (text.includes('FROM seller_accounts WHERE app_id') && text.includes('LIMIT 1') && params.length === 2) {
        const row = tables.seller_accounts.find(
          (r) => r.app_id === params[0] && r.seller_ref === params[1]
        );
        return { rows: row ? [{ id: row.id }] : [] };
      }
      if (text.startsWith('INSERT INTO seller_accounts')) {
        const row = {
          id: crypto.randomUUID(),
          app_id: params[0],
          seller_ref: params[1],
          mp_user_id: params[2],
          mp_nickname: params[3],
          access_token_enc: params[4],
          refresh_token_enc: params[5],
          public_key: params[6],
          expires_at: params[7],
          status: 'connected',
          last_error: null,
          connected_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        tables.seller_accounts.push(row);
        return { rows: [{ ...row }] };
      }
      if (text.startsWith('UPDATE seller_accounts SET') && text.includes("status = 'connected'")) {
        const row = tables.seller_accounts.find((r) => r.id === params[0]);
        Object.assign(row, {
          mp_user_id: params[1],
          mp_nickname: params[2] ?? row.mp_nickname,
          access_token_enc: params[3],
          refresh_token_enc: params[4],
          public_key: params[5],
          expires_at: params[6],
          status: 'connected',
          last_error: null,
          connected_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        });
        return { rows: [{ ...row }] };
      }
      if (text.startsWith('UPDATE seller_accounts SET') && text.includes("status = 'error'")) {
        const row = tables.seller_accounts.find((r) => r.id === params[0]);
        row.status = 'error';
        row.last_error = params[1];
        return { rows: [{ ...row }] };
      }
      if (text.startsWith('UPDATE seller_charges SET')) {
        const row = tables.seller_charges.find((r) => r.id === params[0]);
        if (!row) return { rows: [] };
        row.mp_payment_id = params[1] ?? row.mp_payment_id;
        row.status = params[2];
        row.mp_status = params[3];
        row.mp_status_detail = params[4];
        if (params[5]) row.method = params[5];
        row.pix_qr_code = params[6] ?? row.pix_qr_code;
        row.pix_qr_code_base64 = params[7] ?? row.pix_qr_code_base64;
        row.pix_ticket_url = params[8] ?? row.pix_ticket_url;
        row.pix_expires_at = params[9] ?? row.pix_expires_at;
        if (params[2] === 'PAID') {
          row.paid_amount_cents = params[10];
          row.paid_at = row.paid_at || new Date().toISOString();
        }
        row.refunded_amount_cents = params[11] ?? row.refunded_amount_cents;
        row.mismatch_reason = params[12];
        row.last_observed_at = new Date().toISOString();
        row.updated_at = new Date().toISOString();
        return { rows: [{ ...row }] };
      }
      throw new Error(`SQL não simulado: ${text.slice(0, 120)}`);
    },
  };
}

test('cifra AES-256-GCM roundtrip e rejeita chave curta', async () => {
  await withEnv({ SELLER_TOKEN_KEY: KEY }, () => {
    const enc = encryptSellerSecret('APP_USR-token-secreto');
    assert.notEqual(enc, 'APP_USR-token-secreto');
    assert.equal(decryptSellerSecret(enc), 'APP_USR-token-secreto');
  });
  assert.throws(() => encryptSellerSecret('x', Buffer.alloc(8).toString('base64')));
});

test('state OAuth: inválido e expirado são recusados', async () => {
  await withEnv({ SELLER_STATE_SECRET: STATE }, () => {
    const ok = signState({
      app_id: 'lojadepaes',
      seller_ref: 'p1',
      return_to: 'https://lojadepaes.com.br/parceiro',
      exp: Date.now() + STATE_TTL_MS,
    });
    assert.equal(verifyState(ok).ok, true);
    assert.equal(verifyState('abc.def').ok, false);
    const expired = signState({
      app_id: 'lojadepaes',
      seller_ref: 'p1',
      return_to: 'https://lojadepaes.com.br/parceiro',
      exp: Date.now() - 1000,
    });
    assert.equal(verifyState(expired).error, 'state expirado');
  });
});

test('token do link de checkout HMAC', async () => {
  await withEnv({ SELLER_STATE_SECRET: STATE }, () => {
    const id = crypto.randomUUID();
    const t = signChargeToken(id);
    assert.equal(verifyChargeToken(id, t), true);
    assert.equal(verifyChargeToken(id, t + 'x'), false);
  });
});

test('return_to só aceita origem cadastrada', () => {
  const allowed = ['https://lojadepaes.com.br'];
  assert.equal(returnToAllowed('https://lojadepaes.com.br/parceiro?x=1', allowed).ok, true);
  assert.equal(returnToAllowed('https://evil.example/x', allowed).ok, false);
});

test('chave desligada e app fora da lista', async () => {
  await withEnv({ SELLER_PAYMENTS_ENABLED: 'false', SELLER_APP_IDS: 'lojadepaes' }, () => {
    assert.equal(sellerPaymentsEnabled(), false);
    assert.equal(isSellerAppAllowed('lojadepaes'), true);
    assert.equal(isSellerAppAllowed('inove4us'), false);
  });
});

test('token fica cifrado no banco e cobrança Pix usa só o token do parceiro', async () => {
  await withEnv(
    {
      SELLER_TOKEN_KEY: KEY,
      SELLER_STATE_SECRET: STATE,
      SELLER_PAYMENTS_ENABLED: 'true',
      SELLER_APP_IDS: 'lojadepaes',
      MP_CLIENT_ID: 'client',
      MP_CLIENT_SECRET: 'secret',
    },
    async () => {
      const pool = memoryPool();
      const account = await upsertSellerAccount(pool, {
        appId: 'lojadepaes',
        sellerRef: 'partner-1',
        tokenPayload: {
          access_token: 'APP_USR-parceiro',
          refresh_token: 'TG-refresh',
          public_key: 'APP_USR-pub-parceiro',
          user_id: 12345,
          nickname: 'Queijaria',
          expires_in: 60 * 60 * 24 * 30,
        },
      });
      assert.match(account.access_token_enc, /^[A-Za-z0-9+/=]+$/);
      assert.notEqual(account.access_token_enc, 'APP_USR-parceiro');
      assert.equal(decryptSellerSecret(account.access_token_enc), 'APP_USR-parceiro');

      let usedAuth = null;
      const payment = await createPixWithSellerToken(
        'APP_USR-parceiro',
        {
          id: '11111111-1111-1111-1111-111111111111',
          amount_cents: 5800,
          description: 'Queijo + frete',
          payer_email: 'ana@example.test',
        },
        {
          http: async (opts) => {
            usedAuth = opts.headers.Authorization;
            assert.equal(usedAuth, 'Bearer APP_USR-parceiro');
            assert.doesNotMatch(JSON.stringify(opts), /MP_ACCESS_TOKEN|APP_USR-global/);
            assert.equal(opts.data.payment_method_id, 'pix');
            assert.equal(opts.data.notification_url.includes('/webhook/sellers'), true);
            return {
              data: {
                id: 9001,
                status: 'pending',
                status_detail: 'pending_waiting_transfer',
                payment_method_id: 'pix',
                transaction_amount: 58,
                point_of_interaction: {
                  transaction_data: {
                    qr_code: 'pix-copia-cola',
                    qr_code_base64: 'base64',
                    ticket_url: 'https://mp/ticket',
                  },
                },
                date_of_expiration: '2026-11-25T20:00:00.000Z',
              },
            };
          },
        }
      );
      assert.equal(payment.id, 9001);
      assert.equal(usedAuth, 'Bearer APP_USR-parceiro');
    }
  );
});

test('cartão (corpo P3) e webhook conferem valor', async () => {
  await withEnv({ SELLER_TOKEN_KEY: KEY }, async () => {
    const charge = {
      id: '22222222-2222-2222-2222-222222222222',
      amount_cents: 5800,
      description: 'Queijo',
      payer_email: 'ana@example.test',
      status: 'PENDING',
    };
    const pool = memoryPool({
      seller_charges: [{ ...charge }],
    });

    const paid = await createCardWithSellerToken(
      'APP_USR-parceiro',
      charge,
      {
        token: 'card-tok',
        payment_method_id: 'visa',
        issuer_id: '24',
        installments: 1,
        payer: { email: 'ana@example.test', identification: { type: 'CPF', number: '39053344705' } },
      },
      {
        http: async (opts) => {
          assert.equal(opts.headers.Authorization, 'Bearer APP_USR-parceiro');
          assert.equal(opts.data.payer.identification.type, 'CPF');
          assert.equal(opts.data.transaction_amount, 58);
          return {
            data: {
              id: 9002,
              status: 'approved',
              status_detail: 'accredited',
              payment_type_id: 'credit_card',
              payment_method_id: 'visa',
              transaction_amount: 58,
            },
          };
        },
      }
    );
    assert.equal(mapMpToChargeStatus(paid.status), 'PAID');

    const ok = await applyPaymentObservation(pool, charge, paid);
    assert.equal(ok.status, 'PAID');
    assert.equal(ok.paid_amount_cents, 5800);

    const mismatch = await applyPaymentObservation(pool, charge, {
      ...paid,
      id: 9003,
      transaction_amount: 10,
    });
    assert.equal(mismatch.status, 'PENDING');
    assert.equal(mismatch.mismatch_reason, 'amount_mismatch');
  });
});

test('renovação de token quando faltam menos de 15 dias', async () => {
  await withEnv(
    {
      SELLER_TOKEN_KEY: KEY,
      MP_CLIENT_ID: 'cid',
      MP_CLIENT_SECRET: 'csec',
    },
    async () => {
      const pool = memoryPool();
      const soon = new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString();
      const account = {
        id: crypto.randomUUID(),
        app_id: 'lojadepaes',
        seller_ref: 'p1',
        access_token_enc: encryptSellerSecret('old-access'),
        refresh_token_enc: encryptSellerSecret('old-refresh'),
        public_key: 'pub',
        expires_at: soon,
        status: 'connected',
        mp_nickname: 'X',
        mp_user_id: 1,
      };
      pool.tables.seller_accounts.push(account);

      const token = await ensureSellerAccessToken(pool, account, {
        postOauthToken: async (body) => {
          assert.equal(body.grant_type, 'refresh_token');
          assert.equal(body.refresh_token, 'old-refresh');
          return {
            data: {
              access_token: 'new-access',
              refresh_token: 'new-refresh',
              public_key: 'pub',
              expires_in: 60 * 60 * 24 * 90,
              user_id: 1,
            },
          };
        },
      });
      assert.equal(token, 'new-access');
      assert.equal(decryptSellerSecret(pool.tables.seller_accounts[0].access_token_enc), 'new-access');
    }
  );
});

test('arquivos do Pay legado e /checkout/direct não mudaram', () => {
  const root = path.join(__dirname, '..', '..', '..');
  const expected = {
    'services/gateway-api/mercadopago.js':
      'B4C7C10CF8CAE12222254308D4144E22DDAFAABDEDB249B6AD24CF581F585C73',
    'services/gateway-api/domain/amount-checkout.js':
      'CAAD9B468514341106D7C2C21DEE530DDAA02188BE8EA23F5628B01406AE2F4F',
    'services/gateway-api/domain/checkout-sessions.js':
      'C46B75002F222B074647CBE912901505AA708606BA47DCA75EDC13DBB7C7F1D6',
    'services/gateway-api/domain/mp-webhooks.js':
      '3983720D936E7BBD46D102587D46C8D455EFE6016EF79EBD61221E26FBD6AC1D',
    'frontend/action-hub/src/app/checkout/direct/page.tsx':
      '0BFD5B5F5B5B4B2447529069D74D48952EB5A4ABE33D7D2D250E56E0FA72CEE2',
  };
  for (const [rel, want] of Object.entries(expected)) {
    const buf = fs.readFileSync(path.join(root, rel));
    const got = crypto.createHash('sha256').update(buf).digest('hex').toUpperCase();
    assert.equal(got, want, `${rel} mudou — P1-Pay não pode alterar este arquivo`);
  }
});
