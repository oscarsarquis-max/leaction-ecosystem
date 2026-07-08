'use strict';

const { Pool } = require('pg');

const sslMode = (process.env.DB_SSLMODE || 'disable').toLowerCase();
const useSsl = sslMode === 'require' || sslMode === 'verify-full' || sslMode === 'verify-ca';

const pool = new Pool({
    host: process.env.DB_HOST || '127.0.0.1',
    port: Number(process.env.DB_PORT || 5432),
    database: process.env.DB_NAME || 'LeAction_SysF',
    user: process.env.DB_USER || process.env.DB_USERNAME || 'postgres',
    password: process.env.DB_PASS || process.env.DB_PASSWORD || '',
    ssl: useSsl ? { rejectUnauthorized: false } : false,
    max: Number(process.env.DB_POOL_MAX || 5),
    idleTimeoutMillis: 30_000,
    connectionTimeoutMillis: 10_000,
});

pool.on('error', (err) => {
    console.error('[PostgreSQL Pool] Erro inesperado no cliente idle:', err.message);
});

module.exports = { pool };
