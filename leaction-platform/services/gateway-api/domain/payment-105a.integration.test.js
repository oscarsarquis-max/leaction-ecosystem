'use strict';
const {test, before, after, beforeEach} = require('node:test');
const assert = require('node:assert/strict');
const {randomUUID} = require('crypto');
const {Pool} = require('pg');
const {fulfillVerifiedCardPayment} = require('./mp-webhooks');
const url = process.env.PAY105A_TEST_DATABASE_URL;
if (url && !/^postgresql:\/\/[^@]+@127\.0\.0\.1:5438\/hub_pay105a$/.test(url)) {
  throw new Error('A dedicated local hub_pay105a database is required');
}
const pool = url ? new Pool({connectionString:url}) : null;
const dbtest = url ? test : test.skip;
before(async () => {
  if (!pool) return;
  await pool.query(`CREATE TABLE IF NOT EXISTS products(id uuid primary key,type text,external_resource_id text);
    ALTER TABLE products ADD COLUMN IF NOT EXISTS external_resource_id text;
    CREATE TABLE IF NOT EXISTS users(id uuid primary key,email text,full_name text);
    CREATE TABLE IF NOT EXISTS orders(id uuid primary key,status text,payment_status text,paid_at timestamptz,
      created_at timestamptz default now(),updated_at timestamptz default now(),external_resource_id text,
      gateway_reference text,gateway_ref text,payment_url text,product_id uuid,user_id uuid);
    CREATE TABLE IF NOT EXISTS webhook_outbox(id uuid primary key default gen_random_uuid(),app_id text,
      event_type text,payload_json jsonb,idempotency_key text unique,status text,attempts int,
      next_retry_at timestamptz,created_at timestamptz default now());`);
});
beforeEach(async () => {
  if (!pool) return;
  await pool.query('DROP TRIGGER IF EXISTS fail_outbox ON webhook_outbox');
  await pool.query('TRUNCATE orders,products,users,webhook_outbox');
});
after(async () => {if (pool) await pool.end();});
async function fixture() {
  const product=randomUUID(), id=randomUUID();
  await pool.query("INSERT INTO products(id,type) VALUES($1,'AMOUNT_CHECKOUT')",[product]);
  const payload={source:'amount_checkout',app_id:'lojadepaes',amount_cents:7000,currency:'BRL',method:'card',order_reference:'LP-TEST-'+id,payment_request_id:randomUUID()};
  await pool.query("INSERT INTO orders(id,status,product_id,external_resource_id) VALUES($1,'PENDING',$2,$3)",[id,product,JSON.stringify(payload)]);
  return {order:{id,product_type:'AMOUNT_CHECKOUT',external_resource_id:JSON.stringify(payload)},payment:{
    id:'test-'+id,external_reference:id,status:'approved',status_detail:'accredited',captured:true,currency_id:'BRL',
    transaction_amount:70,transaction_amount_refunded:0,date_approved:'2026-10-27T20:10:26Z',date_last_updated:'2026-10-27T20:10:27Z',live_mode:false,
  }};
}
dbtest('synchronous card approval durably queues exactly one Loja event and records method/value',async()=>{
  const f=await fixture();
  const first=await fulfillVerifiedCardPayment(pool,f.order,f.payment,'test-secret');
  assert.equal(first.order.status,'PAID');
  const second=await fulfillVerifiedCardPayment(pool,f.order,f.payment,'test-secret');
  assert.equal(second.alreadyPaid,true);
  const {rows:[row]}=await pool.query('SELECT status,external_resource_id FROM orders WHERE id=$1',[f.order.id]);
  assert.equal(row.status,'PAID');
  const stored=JSON.parse(row.external_resource_id);
  assert.equal(stored.paid_amount_cents,7000);
  assert.equal(stored.mp_payment_id,f.payment.id);
  const {rows}=await pool.query('SELECT payload_json FROM webhook_outbox');
  assert.equal(rows.length,1);
  assert.equal(rows[0].payload_json.financial_status,'paid');
  assert.equal(rows[0].payload_json.method,'card');
  assert.equal(rows[0].payload_json.paid_amount_cents,7000);
});
dbtest('outbox failure cannot commit paid without the event; retry recovers both',async()=>{
  const f=await fixture();
  await pool.query(`CREATE OR REPLACE FUNCTION fail_105a_event() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'outbox unavailable'; END $$;
    CREATE TRIGGER fail_outbox BEFORE INSERT ON webhook_outbox FOR EACH ROW EXECUTE FUNCTION fail_105a_event();`);
  await assert.rejects(fulfillVerifiedCardPayment(pool,f.order,f.payment,'test-secret'),/outbox unavailable/);
  assert.equal((await pool.query('SELECT status FROM orders WHERE id=$1',[f.order.id])).rows[0].status,'PENDING');
  assert.equal((await pool.query('SELECT count(*)::int n FROM webhook_outbox')).rows[0].n,0);
  await pool.query('DROP TRIGGER fail_outbox ON webhook_outbox');
  await fulfillVerifiedCardPayment(pool,f.order,f.payment,'test-secret');
  assert.equal((await pool.query('SELECT status FROM orders WHERE id=$1',[f.order.id])).rows[0].status,'PAID');
  assert.equal((await pool.query('SELECT count(*)::int n FROM webhook_outbox')).rows[0].n,1);
});
dbtest('unpaid authorization, wrong reference and wrong currency never mark paid',async()=>{
  for(const override of [{status:'authorized'},{captured:false},{currency_id:'USD'},{external_reference:randomUUID()}]) {
    const f=await fixture();
    await assert.rejects(fulfillVerifiedCardPayment(pool,f.order,{...f.payment,...override},'test-secret'));
    assert.equal((await pool.query('SELECT status FROM orders WHERE id=$1',[f.order.id])).rows[0].status,'PENDING');
  }
  assert.equal((await pool.query('SELECT count(*)::int n FROM webhook_outbox')).rows[0].n,0);
});
dbtest('two orders of the same value retain separate provider IDs and events',async()=>{
  const a=await fixture(),b=await fixture();
  await fulfillVerifiedCardPayment(pool,a.order,a.payment,'test-secret');
  await fulfillVerifiedCardPayment(pool,b.order,b.payment,'test-secret');
  const {rows}=await pool.query('SELECT payload_json FROM webhook_outbox');
  const links=new Map(rows.map(x=>[x.payload_json.order_id,x.payload_json.mp_payment_id]));
  assert.equal(links.size,2);
  assert.equal(links.get(a.order.id),a.payment.id);
  assert.equal(links.get(b.order.id),b.payment.id);
});
