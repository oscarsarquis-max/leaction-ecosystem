#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const { Client } = require("pg");

const IDS = [
  "759bcd79-e238-4bf9-b379-7e0f08548692",
  "d79861f6-65a6-48b9-be3f-d2aa1729dcd0",
  "ac3ffaa6-eef0-4ef2-b3e2-99b40e5c17ec",
  "97de3e93-a7b4-45ef-8716-0c411c23eec4",
];
const REFS = ["LPA8FC361791", "LP91E9C35D1B"];
const MP = ["186394563492", "186395690348"];

function envFromPid(pid) {
  const raw = fs.readFileSync(`/proc/${pid}/environ`);
  const out = {};
  for (const part of raw.toString("utf8").split("\0")) {
    const i = part.indexOf("=");
    if (i > 0) out[part.slice(0, i)] = part.slice(i + 1);
  }
  return out;
}

function gatewayPid() {
  const root = "/proc";
  for (const name of fs.readdirSync(root)) {
    if (!/^\d+$/.test(name)) continue;
    let cmd = "";
    try {
      cmd = fs.readFileSync(path.join(root, name, "cmdline")).toString("utf8");
    } catch {
      continue;
    }
    if (cmd.includes("gateway-api/serve")) return name;
  }
  throw new Error("gateway_pid_missing");
}

function pick(payload) {
  const pix = payload && payload.pix && typeof payload.pix === "object" ? payload.pix : {};
  return {
    order_reference: payload.order_reference || null,
    method: payload.method || null,
    amount_cents: payload.amount_cents ?? null,
    currency: payload.currency || null,
    mp_payment_id: payload.mp_payment_id || pix.mp_payment_id || null,
    provider_status: payload.provider_status || pix.status || null,
    status_detail: payload.status_detail || pix.status_detail || null,
    cancelled: payload.cancelled === true,
    paid_amount_cents: payload.paid_amount_cents ?? null,
    paid_amount_confirmed: payload.paid_amount_confirmed === true,
    observed_amount_cents: payload.observed_amount_cents ?? null,
    live_mode: payload.live_mode === true ? true : payload.live_mode === false ? false : null,
    provider_observed_at: payload.provider_observed_at || null,
  };
}

async function main() {
  const pid = gatewayPid();
  const env = envFromPid(pid);
  if (!env.DATABASE_URL) throw new Error("database_url_missing");
  const connectionString = env.DATABASE_URL.replace(/([?&])sslmode=[^&]*/gi, "$1")
    .replace(/\?&/, "?")
    .replace(/[?&]$/, "");
  const client = new Client({
    connectionString,
    ssl: /localhost|127\.0\.0\.1/i.test(env.DATABASE_URL) ? undefined : { rejectUnauthorized: false },
  });
  await client.connect();
  const orders = await client.query(
    `SELECT id::text, status, payment_status, paid_at, created_at, updated_at,
            gateway_reference, external_resource_id
     FROM orders WHERE id = ANY($1::uuid[]) ORDER BY created_at`,
    [IDS]
  );
  console.log("hub_orders", orders.rowCount);
  for (const row of orders.rows) {
    let payload = {};
    try {
      payload = typeof row.external_resource_id === "string"
        ? JSON.parse(row.external_resource_id)
        : row.external_resource_id || {};
    } catch {
      payload = {};
    }
    console.log(JSON.stringify({
      id: row.id,
      status: row.status,
      payment_status: row.payment_status,
      paid_at: row.paid_at,
      gateway_reference: /^\d+$/.test(String(row.gateway_reference || "")) ? row.gateway_reference : null,
      created_at: row.created_at,
      updated_at: row.updated_at,
      ...pick(payload),
    }));
  }

  const outbox = await client.query(
    `SELECT id::text, event_type, status, attempts, created_at, next_retry_at, left(coalesce(last_error,''), 160) AS err,
            payload_json->>'order_id' AS order_id,
            payload_json->>'order_reference' AS order_reference,
            payload_json->>'financial_status' AS financial_status,
            payload_json->>'mp_status' AS mp_status,
            payload_json->>'mp_payment_id' AS mp_payment_id
     FROM webhook_outbox
     WHERE app_id = 'lojadepaes'
       AND (
         payload_json->>'order_id' = ANY($1::text[])
         OR payload_json->>'order_reference' = ANY($2::text[])
         OR payload_json->>'mp_payment_id' = ANY($3::text[])
       )
     ORDER BY created_at`,
    [IDS, REFS, MP]
  );
  console.log("hub_outbox", outbox.rowCount);
  for (const row of outbox.rows) console.log(JSON.stringify(row));
  await client.end();

  process.chdir("/var/www/leaction-platform/services/gateway-api");
  require("dotenv").config({ path: "/var/www/leaction-platform/.env", override: true });
  const { fetchMercadoPagoPayment, getMercadoPagoAccessToken } = require("/var/www/leaction-platform/services/gateway-api/mercadopago");
  const axios = require("axios");
  const mpIds = new Set(MP);
  for (const row of orders.rows) {
    let payload = {};
    try {
      payload = typeof row.external_resource_id === "string"
        ? JSON.parse(row.external_resource_id)
        : row.external_resource_id || {};
    } catch {
      payload = {};
    }
    const pix = payload.pix && typeof payload.pix === "object" ? payload.pix : {};
    const id = payload.mp_payment_id || pix.mp_payment_id;
    if (id) mpIds.add(String(id));
    if (/^\d+$/.test(String(row.gateway_reference || ""))) mpIds.add(String(row.gateway_reference));
  }
  for (const id of mpIds) {
    try {
      const payment = await fetchMercadoPagoPayment(id);
      console.log(JSON.stringify({
        source: "mercadopago",
        id: payment.id,
        status: payment.status,
        status_detail: payment.status_detail,
        currency_id: payment.currency_id,
        transaction_amount: payment.transaction_amount,
        transaction_amount_refunded: payment.transaction_amount_refunded,
        payment_type_id: payment.payment_type_id,
        payment_method_id: payment.payment_method_id,
        external_reference: payment.external_reference,
        live_mode: payment.live_mode,
        date_created: payment.date_created,
        date_approved: payment.date_approved,
        date_last_updated: payment.date_last_updated,
      }));
    } catch (err) {
      console.log(JSON.stringify({ source: "mercadopago", id, error: err.message, statusCode: err.statusCode || null }));
    }
  }
  const token = getMercadoPagoAccessToken();
  for (const id of IDS) {
    try {
      const found = await axios.get("https://api.mercadopago.com/v1/payments/search", {
        params: { external_reference: id, limit: 10 },
        headers: { Authorization: `Bearer ${token}` },
        timeout: 15000,
      });
      const results = (found.data && found.data.results) || [];
      console.log(JSON.stringify({
        source: "mercadopago_search",
        external_reference: id,
        count: results.length,
        results: results.map((payment) => ({
          id: payment.id,
          status: payment.status,
          status_detail: payment.status_detail,
          currency_id: payment.currency_id,
          transaction_amount: payment.transaction_amount,
          transaction_amount_refunded: payment.transaction_amount_refunded,
          payment_type_id: payment.payment_type_id,
          payment_method_id: payment.payment_method_id,
          live_mode: payment.live_mode,
          date_approved: payment.date_approved,
          date_created: payment.date_created,
        })),
      }));
    } catch (err) {
      console.log(JSON.stringify({
        source: "mercadopago_search",
        external_reference: id,
        error: err.message,
        statusCode: err.response && err.response.status,
      }));
    }
  }
}

main().catch((err) => {
  console.error("hub_read_failed", err.message);
  process.exit(1);
});
