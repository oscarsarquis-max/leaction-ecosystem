'use strict';

const http = require('http');
const path = require('path');
const fs = require('fs');

function loadEnvFile(filePath) {
    if (!fs.existsSync(filePath)) return;
    fs.readFileSync(filePath, 'utf8').split(/\r?\n/).forEach((line) => {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith('#')) return;
        const eq = trimmed.indexOf('=');
        if (eq <= 0) return;
        const key = trimmed.slice(0, eq).trim();
        let val = trimmed.slice(eq + 1).trim();
        if (!process.env[key]) process.env[key] = val;
    });
}

loadEnvFile(path.join(__dirname, '..', '..', 'LeAction_SysF', '.env'));

const BASE = process.env.GATEKEEPER_PROD_TEST_URL || 'http://127.0.0.1:3001';
const KEY = process.env.PRODUCTION_MASTER_KEY || 'dev-gatekeeper-test-key-2026';
const { pool } = require('../lib/postgres-pool');

function httpGet(urlPath, cookie) {
    return new Promise((resolve, reject) => {
        const url = new URL(urlPath, BASE);
        const headers = {};
        if (cookie) headers.Cookie = cookie;
        const req = http.request(
            { hostname: url.hostname, port: url.port, path: url.pathname + url.search, method: 'GET', headers },
            (res) => {
                let body = '';
                res.on('data', (c) => { body += c; });
                res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body, location: res.headers.location }));
            }
        );
        req.on('error', reject);
        req.end();
    });
}

function cookiesFrom(res) {
    const raw = res.headers['set-cookie'];
    if (!raw) return '';
    const list = Array.isArray(raw) ? raw : [raw];
    return list.map((c) => c.split(';')[0]).join('; ');
}

async function main() {
    console.log('\n=== Gatekeeper — smoke test NODE_ENV=production (porta 3001) ===');

    await pool.query(
        `INSERT INTO public.system_config (config_key, config_value)
         VALUES ('system_locked', 'true')
         ON CONFLICT (config_key) DO UPDATE SET config_value = 'true'`
    );
    await new Promise((r) => setTimeout(r, 1600));

    const blocked = await httpGet('/login');
    console.log('  locked /login ->', blocked.status, blocked.location || '');

    const bypass = await httpGet(`/gatekeeper/bypass?secret=${encodeURIComponent(KEY)}`);
    const cookie = cookiesFrom(bypass);
    console.log('  bypass ->', bypass.status, bypass.location || '', cookie ? '(cookie ok)' : '(sem cookie)');

    const testerLogin = await httpGet('/login', cookie);
    console.log('  tester /login ->', testerLogin.status, testerLogin.location || '(sem redirect)');

    const unlock = await httpGet(`/gatekeeper/unlock?secret=${encodeURIComponent(KEY)}`);
    console.log('  unlock ->', unlock.status, unlock.body.trim());

    await new Promise((r) => setTimeout(r, 1600));
    const afterUnlock = await httpGet('/login');
    console.log('  unlocked /login ->', afterUnlock.status, afterUnlock.location || '(sem redirect)');

    const lock = await httpGet(`/gatekeeper/lock?secret=${encodeURIComponent(KEY)}`);
    console.log('  lock ->', lock.status, lock.body.trim());

    await new Promise((r) => setTimeout(r, 1600));
    const afterLock = await httpGet('/login');
    console.log('  re-locked /login ->', afterLock.status, afterLock.location || '(sem redirect)');

    await pool.query(`UPDATE public.system_config SET config_value = 'false' WHERE config_key = 'system_locked'`);
    await pool.end();
    console.log('  ✅ Smoke test produção local concluído\n');
}

main().catch(async (err) => {
    console.error(err);
    try { await pool.end(); } catch (_e) { /* ignore */ }
    process.exit(1);
});
