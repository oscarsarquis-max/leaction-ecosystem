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
 * paneldx.com.br público fica só com aviso de desativação (sem redirecionar/mencionar outro produto).
 * Override: PANELDX_PUBLIC_DEACTIVATED=0|false libera; =1|true força em qualquer host.
 */
function isPublicSiteDeactivated(req) {
    const flag = String(process.env.PANELDX_PUBLIC_DEACTIVATED || '')
        .trim()
        .toLowerCase();
    if (flag === '0' || flag === 'false' || flag === 'off') return false;
    if (flag === '1' || flag === 'true' || flag === 'on' || flag === 'yes') return true;

    const host = String(req.headers['x-forwarded-host'] || req.headers.host || '')
        .split(',')[0]
        .trim()
        .split(':')[0]
        .toLowerCase();
    return host === 'paneldx.com.br' || host === 'www.paneldx.com.br';
}

/**
 * Middleware global — bloqueia navegação quando system_locked=true no PostgreSQL
 * ou quando o host público PanelDX está desativado.
 * Passam sem bloqueio: rotas CMS, sysadmin logado e testers (bypass).
 */
async function gatekeeperMiddleware(req, res, next) {
    if (isGatekeeperExempt(req.path)) {
        return next();
    }

    if (isElbHealthCheck(req)) {
        return next();
    }

    let locked = isPublicSiteDeactivated(req);
    if (!locked) {
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
            error: 'PanelDX desativado. Este serviço não está mais disponível.',
            maintenance: true,
            deactivated: true,
        });
    }

    return res.redirect('/manutencao');
}

module.exports = {
    gatekeeperMiddleware,
    isGatekeeperExempt,
};
