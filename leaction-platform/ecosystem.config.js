/**
 * PM2 — Action Hub (produção EC2)
 *
 * Serviços gerenciados:
 *   - action-hub      → Next.js na porta 4000
 *   - gateway-api     → Express na porta 4001
 *   - marketplace-api → Flask plugin Marketplace na porta 4012
 *
 * Uso no servidor (após build e .env):
 *   cd /var/www/leaction-platform   # ou caminho do clone
 *   mkdir -p logs
 *   pm2 start ecosystem.config.js
 *   pm2 save
 *   pm2 startup
 */
const path = require('path');

const ROOT = __dirname;
const LOG_DIR = path.join(ROOT, 'logs');

module.exports = {
  apps: [
    {
      name: 'action-hub',
      cwd: path.join(ROOT, 'frontend/action-hub'),
      script: 'npm',
      args: 'run start',
      interpreter: 'none',
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      restart_delay: 3000,
      max_restarts: 20,
      min_uptime: '10s',
      watch: false,
      env: {
        NODE_ENV: 'production',
        PORT: 4000,
        APP_VERSION: process.env.APP_VERSION || '',
        GIT_SHA: process.env.GIT_SHA || '',
      },
      error_file: path.join(LOG_DIR, 'action-hub-error.log'),
      out_file: path.join(LOG_DIR, 'action-hub-out.log'),
      merge_logs: false,
      time: true,
    },
    {
      name: 'gateway-api',
      cwd: path.join(ROOT, 'services/gateway-api'),
      script: 'server.js',
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      restart_delay: 3000,
      max_restarts: 20,
      min_uptime: '10s',
      watch: false,
      env: {
        NODE_ENV: 'production',
        GATEWAY_PORT: 4001,
        APP_VERSION: process.env.APP_VERSION || '',
        GIT_SHA: process.env.GIT_SHA || '',
      },
      error_file: path.join(LOG_DIR, 'gateway-api-error.log'),
      out_file: path.join(LOG_DIR, 'gateway-api-out.log'),
      merge_logs: false,
      time: true,
    },
    {
      name: 'marketplace-api',
      cwd: path.join(ROOT, 'backend'),
      script: path.join(ROOT, 'backend/.venv/bin/python'),
      args: 'run.py',
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      restart_delay: 3000,
      max_restarts: 20,
      min_uptime: '10s',
      watch: false,
      env: {
        NODE_ENV: 'production',
        MARKETPLACE_PORT: 4012,
        FLASK_DEBUG: '0',
      },
      error_file: path.join(LOG_DIR, 'marketplace-api-error.log'),
      out_file: path.join(LOG_DIR, 'marketplace-api-out.log'),
      merge_logs: false,
      time: true,
    },
  ],
};
