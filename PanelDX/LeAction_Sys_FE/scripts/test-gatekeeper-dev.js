'use strict';

/**
 * Testes locais do Gatekeeper (dev).
 * Uso: node scripts/test-gatekeeper-dev.js
 * Requer: PostgreSQL acessível + servidor Node em http://localhost:3000
 */

const fs = require('fs');
const path = require('path');
const http = require('http');

function loadEnvFile(filePath) {
    if (!fs.existsSync(filePath)) return;
    const raw = fs.readFileSync(filePath, 'utf8');
    raw.split(/\r?\n/).forEach((line) => {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith('#')) return;
        const eq = trimmed.indexOf('=');
        if (eq <= 0) return;
        const key = trimmed.slice(0, eq).trim();
        let val = trimmed.slice(eq + 1).trim();
        if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
            val = val.slice(1, -1);
        }
        if (!process.env[key]) process.env[key] = val;
    });
}

loadEnvFile(path.join(__dirname, '..', '.env.development'));
loadEnvFile(path.join(__dirname, '..', '..', 'LeAction_SysF', '.env'));

// Placeholder legado — herda senha real do backend
if (process.env.DB_PASS === 'sua_senha') {
    const backendPath = path.join(__dirname, '..', '..', 'LeAction_SysF', '.env');
    if (fs.existsSync(backendPath)) {
        const raw = fs.readFileSync(backendPath, 'utf8');
        raw.split(/\r?\n/).forEach((line) => {
            const trimmed = line.trim();
            if (!trimmed || trimmed.startsWith('#')) return;
            const eq = trimmed.indexOf('=');
            if (eq <= 0) return;
            const key = trimmed.slice(0, eq).trim();
            let val = trimmed.slice(eq + 1).trim();
            if (key === 'DB_PASS' && val) process.env.DB_PASS = val;
        });
    }
}

const BASE_URL = process.env.GATEKEEPER_TEST_URL || 'http://127.0.0.1:3000';
const MASTER_KEY = process.env.PRODUCTION_MASTER_KEY || 'dev-gatekeeper-test-key-2026';

process.env.PRODUCTION_MASTER_KEY = MASTER_KEY;
process.env.SYSTEM_CONFIG_CACHE_MS = '1000';

const { pool } = require('../lib/postgres-pool');
const { setSystemLockedCache } = require('../lib/system-config');

function httpGet(urlPath, opts = {}) {
    return new Promise((resolve, reject) => {
        const url = new URL(urlPath, BASE_URL);
        const headers = { ...(opts.headers || {}) };
        if (opts.cookie) headers.Cookie = opts.cookie;

        const req = http.request(
            {
                hostname: url.hostname,
                port: url.port,
                path: url.pathname + url.search,
                method: opts.method || 'GET',
                headers,
            },
            (res) => {
                let body = '';
                res.on('data', (chunk) => { body += chunk; });
                res.on('end', () => {
                    resolve({
                        status: res.statusCode,
                        headers: res.headers,
                        body,
                        location: res.headers.location,
                    });
                });
            }
        );
        req.on('error', reject);
        req.end();
    });
}

function extractCookie(setCookieHeader) {
    if (!setCookieHeader) return '';
    const list = Array.isArray(setCookieHeader) ? setCookieHeader : [setCookieHeader];
    return list.map((c) => c.split(';')[0]).join('; ');
}

async function ensureSchema() {
    const sqlPath = path.join(__dirname, '..', '..', 'migrations', '009_system_config.sql');
    const sql = fs.readFileSync(sqlPath, 'utf8');
    await pool.query(sql);
}

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

async function setLocked(locked) {
    await pool.query(
        `INSERT INTO public.system_config (config_key, config_value)
         VALUES ('system_locked', $1)
         ON CONFLICT (config_key) DO UPDATE SET config_value = EXCLUDED.config_value`,
        [locked ? 'true' : 'false']
    );
    setSystemLockedCache(locked);
    // Aguarda TTL do servidor (processo separado) propagar a mudança
    await sleep(Number(process.env.GATEKEEPER_TEST_CACHE_WAIT_MS || 1600));
}

function assert(name, condition, detail) {
    if (condition) {
        console.log(`  ✅ ${name}`);
        return true;
    }
    console.log(`  ❌ ${name}${detail ? ` — ${detail}` : ''}`);
    return false;
}

async function run() {
    console.log('\n=== Gatekeeper — testes em dev ===');
    console.log(`Base URL: ${BASE_URL}`);
    console.log(`DB: ${process.env.DB_HOST}:${process.env.DB_PORT}/${process.env.DB_NAME}`);

    let passed = 0;
    let failed = 0;

    function check(name, ok, detail) {
        if (assert(name, ok, detail)) passed += 1;
        else failed += 1;
    }

    await ensureSchema();

    // --- Cenário A: sistema bloqueado ---
    console.log('\n[A] system_locked=true');
    await setLocked(true);

    const manutencao = await httpGet('/manutencao');
    check('/manutencao retorna 200', manutencao.status === 200);
    check('/manutencao contém texto esperado', /desativad|PanelDX/i.test(manutencao.body));

    const loginBlocked = await httpGet('/login', { method: 'GET' });
    check('/login redireciona para /manutencao', loginBlocked.status === 302 && loginBlocked.location === '/manutencao');

    const css = await httpGet('/css/mesa-inovacao.css');
    check('/css/* liberado (200 ou 404 sem redirect)', css.status !== 302 || !String(css.location || '').includes('manutencao'));

    const bypassWrong = await httpGet('/gatekeeper/bypass?secret=chave-invalida');
    check('/gatekeeper/bypass secret inválido → 403', bypassWrong.status === 403);

    // --- Cenário B: bypass em dev (habilitado com GATEKEEPER_ALLOW_DEV=true) ---
    console.log('\n[B] bypass/unlock (NODE_ENV=development + GATEKEEPER_ALLOW_DEV)');
    const bypassDev = await httpGet(`/gatekeeper/bypass?secret=${encodeURIComponent(MASTER_KEY)}`);
    const allowDev = String(process.env.GATEKEEPER_ALLOW_DEV || '').toLowerCase() === 'true';
    if (allowDev) {
        check('/gatekeeper/bypass em dev → redirect /', bypassDev.status === 302 && bypassDev.location === '/');
    } else {
        check('/gatekeeper/bypass em dev → 403 (proteção)', bypassDev.status === 403);
    }

    // --- Cenário C: sistema desbloqueado ---
    console.log('\n[C] system_locked=false');
    await setLocked(false);

    const home = await httpGet('/');
    check('/ acessível após unlock (200)', home.status === 200);
    check('home não redireciona para manutencao', !String(home.location || '').includes('manutencao'));

    // --- Cenário D: unlock e lock endpoints em dev ---
    await setLocked(true);
    const unlockDev = await httpGet(`/gatekeeper/unlock?secret=${encodeURIComponent(MASTER_KEY)}`);
    if (allowDev) {
        check('/gatekeeper/unlock em dev → 200', unlockDev.status === 200);
    } else {
        check('/gatekeeper/unlock em dev → 403 (proteção)', unlockDev.status === 403);
    }

    const lockDev = await httpGet(`/gatekeeper/lock?secret=${encodeURIComponent(MASTER_KEY)}`);
    if (allowDev) {
        check('/gatekeeper/lock em dev → 200', lockDev.status === 200);
        check('/gatekeeper/lock mensagem de bloqueio', /BLOQUEADO/i.test(lockDev.body));
    } else {
        check('/gatekeeper/lock em dev → 403 (proteção)', lockDev.status === 403);
    }
    await setLocked(false);

    console.log('\n--- Resultado ---');
    console.log(`Passou: ${passed} | Falhou: ${failed}`);

    if (failed > 0) {
        process.exitCode = 1;
    } else {
        console.log('Todos os testes de dev passaram.\n');
        console.log('Nota: bypass/unlock/lock completos exigem NODE_ENV=production.');
        console.log('Para homologar bypass/unlock/lock localmente:');
        console.log('  $env:NODE_ENV="production"; $env:PRODUCTION_MASTER_KEY="..."; node server.js');
    }

    await pool.end();
}

run().catch(async (err) => {
    console.error('\n❌ Erro fatal nos testes:', err.message);
    try { await pool.end(); } catch (_e) { /* ignore */ }
    process.exit(1);
});
