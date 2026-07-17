'use strict';

const { createRequireAdminAuth } = require('./auth');
const { registerAdminAppsRoutes } = require('./apps');
const { registerAdminPlansRoutes } = require('./plans');
const { registerAdminCreditsRoutes } = require('./credits');

/**
 * @param {import('express').Express} app
 * @param {import('pg').Pool} pool
 * @param {{ jwtSecret?: string }} [options]
 */
function registerAdminRoutes(app, pool, options = {}) {
  const jwtSecret = options.jwtSecret || process.env.JWT_SECRET;
  const requireAdmin = createRequireAdminAuth(jwtSecret);

  registerAdminAppsRoutes(app, pool, { requireAdmin });
  registerAdminPlansRoutes(app, pool, { requireAdmin });
  registerAdminCreditsRoutes(app, pool, { requireAdmin });

  console.log('🛠️  [admin] rotas /admin/apps, /admin/plans e /admin/credits registradas');
}

module.exports = {
  registerAdminRoutes,
  createRequireAdminAuth,
};
