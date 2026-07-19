'use strict';

const { isSessionAdmin } = require('../lib/auth-session');
const {
    fetchContractStatusForClie,
    isContractAccessAllowed,
    resolveIdClieForContract,
} = require('../lib/contract-access');
const { buildActionHubCheckoutUrl } = require('../lib/actionhub-checkout');

const CONTRACT_EXEMPT_PATHS = new Set([
    '/',
    '/cadastro',
    '/login',
    '/logout',
    '/termos-de-uso',
    '/instrucoes-de-uso',
    '/versao-aplicacao',
    '/verificar-email',
    '/consultor-leaction',
    '/portal-consultor',
    '/manutencao',
    '/gatekeeper/bypass',
    '/gatekeeper/unlock',
    '/gatekeeper/lock',
]);

const CONTRACT_EXEMPT_PREFIXES = [
    '/css/',
    '/js/',
    '/images/',
    '/img/',
    '/gatekeeper/',
    '/gatekeeper',
    '/api/public/',
    '/api/admin/crm',
    '/bff/admin/crm',
    '/bff/admin/consultores',
    '/bff/consultor',
    '/admin/crm',
    '/admin',
    '/admin-cms',
    '/admin/cms',
    '/admin/esim',
    '/admin/usuarios',
    '/admin/mesas-inovacao',
];

function isContractExempt(pathname) {
    if (CONTRACT_EXEMPT_PATHS.has(pathname)) return true;
    return CONTRACT_EXEMPT_PREFIXES.some(
        (prefix) => pathname === prefix || pathname.startsWith(prefix)
    );
}

function isElbHealthCheck(req) {
    const ua = String(req.headers['user-agent'] || '');
    return ua.includes('ELB-HealthChecker');
}

/**
 * Bloqueia navegação quando contrato do cliente está inadimplente ou cancelado.
 * Consulta o banco a cada requisição (reflete alterações imediatamente).
 */
async function contractAccessMiddleware(req, res, next) {
    if (isContractExempt(req.path) || isElbHealthCheck(req)) {
        return next();
    }

    if (!req.session || (!req.session.lead && !req.session.isTeam && !req.session.user_id)) {
        return next();
    }

    if (isSessionAdmin(req)) {
        return next();
    }

    let idClie;
    try {
        idClie = await resolveIdClieForContract(req);
    } catch (err) {
        console.warn('[ContractAccess] Falha ao resolver id_clie:', err.message);
        return next();
    }

    if (!idClie) {
        return next();
    }

    let status;
    try {
        status = await fetchContractStatusForClie(idClie);
    } catch (err) {
        const missingTable = /dx_contratos|relation.*does not exist/i.test(err.message || '');
        if (missingTable) {
            return next();
        }
        console.error('[ContractAccess] Falha ao consultar contrato:', err.message);
        return next();
    }

    if (isContractAccessAllowed(status)) {
        return next();
    }

    const wantsJson =
        req.xhr ||
        (req.headers.accept && req.headers.accept.indexOf('json') > -1) ||
        req.path.startsWith('/api/') ||
        req.path.startsWith('/bff/');

    const payload = {
        success: false,
        error: 'Acesso suspenso: contrato inadimplente ou cancelado.',
        contract_status: status,
        code: 'CONTRACT_BLOCKED',
    };

    if (wantsJson) {
        return res.status(403).json(payload);
    }

    return res.status(403).render('error', {
        title: 'Acesso suspenso',
        message: 'O contrato da sua empresa está inadimplente ou cancelado. Renove ou faça upgrade para continuar usando o MudaEdu.',
        contractStatus: status,
        checkoutUpgradeUrl: buildActionHubCheckoutUrl(req, idClie, {
            returnTo: req.path || '/projeto',
        }),
        statusCode: 403,
    });
}

module.exports = {
    contractAccessMiddleware,
    isContractExempt,
};
