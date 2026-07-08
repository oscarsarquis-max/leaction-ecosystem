'use strict';

const { isSystemLocked } = require('../lib/system-config');
const { isSessionAdmin } = require('../lib/auth-session');

/** Rotas que nunca devem ser bloqueadas (evita loop de redirect). */
const GATEKEEPER_EXEMPT_PATHS = new Set([
    '/manutencao',
]);

/** Prefixos liberados: estáticos públicos + rotas administrativas do gatekeeper. */
const GATEKEEPER_EXEMPT_PREFIXES = [
    '/css/',
    '/js/',
    '/images/',
    '/img/',
    '/gatekeeper/',
    '/gatekeeper',
];

/** CMS — conteúdo público e painel sysadmin devem funcionar mesmo com system_locked. */
const GATEKEEPER_CMS_PATHS = [
    '/admin-cms',
    '/admin/cms',
    '/admin/esim',
    '/admin/usuarios',
    '/admin/mesas-inovacao',
    '/esim',
    '/api/admin/cms',
    '/api/admin/esim',
    '/api/admin/usuarios',
    '/api/admin/crm',
    '/bff/admin/usuarios',
    '/bff/admin/crm',
    '/admin/crm',
    '/api/admin/mesas-inovacao',
    '/api/public/cms',
    '/admin/cms/upload',
    '/node/admin/cms/upload',
];

function isGatekeeperExempt(pathname) {
    if (GATEKEEPER_EXEMPT_PATHS.has(pathname)) {
        return true;
    }
    if (GATEKEEPER_CMS_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`))) {
        return true;
    }
    return GATEKEEPER_EXEMPT_PREFIXES.some(
        (prefix) => pathname === prefix || pathname.startsWith(prefix)
    );
}

function isElbHealthCheck(req) {
    const ua = String(req.headers['user-agent'] || '');
    return ua.includes('ELB-HealthChecker');
}

/**
 * Middleware global — bloqueia navegação quando system_locked=true no PostgreSQL.
 * Passam sem bloqueio: rotas CMS, sysadmin logado e testers (bypass).
 */
async function gatekeeperMiddleware(req, res, next) {
    if (isGatekeeperExempt(req.path)) {
        return next();
    }

    if (isElbHealthCheck(req)) {
        return next();
    }

    let locked = false;
    try {
        locked = await isSystemLocked();
    } catch (err) {
        const isProd = (process.env.NODE_ENV || 'development') === 'production';
        console.error('[Gatekeeper] Falha ao consultar system_locked:', err.message);
        if (isProd) {
            return res.redirect('/manutencao');
        }
        return next();
    }

    if (!locked) {
        return next();
    }

    if (req.session && req.session.is_admin_tester === true) {
        return next();
    }

    if (isSessionAdmin(req)) {
        return next();
    }

    const wantsJson =
        req.xhr ||
        (req.headers.accept && req.headers.accept.indexOf('json') > -1) ||
        req.path.startsWith('/api/');

    if (wantsJson) {
        return res.status(503).json({
            error: 'Sistema em preparação para homologação produtiva.',
            maintenance: true,
        });
    }

    return res.redirect('/manutencao');
}

module.exports = {
    gatekeeperMiddleware,
    isGatekeeperExempt,
};
