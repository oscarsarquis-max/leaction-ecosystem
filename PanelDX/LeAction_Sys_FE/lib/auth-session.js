'use strict';

const { pool } = require('./postgres-pool');

const VALID_SYSTEM_ROLES = new Set(['sysadmin', 'led', 'consultor', 'executor']);

function getAdminEmail() {
    return process.env.ADMIN_EMAIL || 'sysadmin@leaction.com.br';
}

function isSessionAdmin(req) {
    const adminEmail = getAdminEmail();
    return !!(
        req.session &&
        (req.session.isTeam ||
            req.session.isAdmin ||
            (req.session.lead && req.session.lead.email === adminEmail))
    );
}

/** Papel RBAC canônico para proxy Flask (evita enviar "admin" legado). */
function resolveSessionSystemRole(req) {
    if (!req || !req.session) return 'led';

    const stored = (req.session.system_role || '').toLowerCase();
    if (VALID_SYSTEM_ROLES.has(stored)) return stored;

    const legacy = (req.session.role || '').toUpperCase();
    if (legacy === 'ADMIN' || legacy === 'SYSADMIN') return 'sysadmin';

    const leadRole = req.session.lead && req.session.lead.system_role;
    if (leadRole && VALID_SYSTEM_ROLES.has(String(leadRole).toLowerCase())) {
        return String(leadRole).toLowerCase();
    }

    if (isSessionAdmin(req)) return 'sysadmin';

    return stored || 'led';
}

/**
 * Resolve id_clie atual pelo e-mail da sessão (auto-cura após reset demo/seed).
 * Atualiza req.session.user_id e req.session.lead.id_clie quando encontra divergência.
 */
async function resolveLeadIdClie(req) {
    if (!req || !req.session) return null;

    if (isSessionAdmin(req)) {
        return req.session.user_id || req.session.lead?.id_clie || null;
    }

    const email = (
        req.session.lead?.email ||
        req.session.lead?.mail_clie ||
        req.session.user?.email ||
        ''
    ).trim().toLowerCase();

    if (!email) {
        return req.session.user_id || req.session.lead?.id_clie || null;
    }

    try {
        const { rows } = await pool.query(
            `SELECT id_clie
             FROM public.ctdi_clie
             WHERE LOWER(TRIM(mail_clie)) = $1
             LIMIT 1`,
            [email]
        );
        if (!rows.length) {
            return req.session.user_id || req.session.lead?.id_clie || null;
        }

        const idClie = rows[0].id_clie;
        const prev = req.session.user_id || req.session.lead?.id_clie;
        if (prev !== idClie) {
            req.session.user_id = idClie;
            if (req.session.lead) req.session.lead.id_clie = idClie;
        }
        return idClie;
    } catch (err) {
        console.warn('[resolveLeadIdClie] Falha ao consultar RDS:', err.message);
        return req.session.user_id || req.session.lead?.id_clie || null;
    }
}

module.exports = {
    getAdminEmail,
    isSessionAdmin,
    resolveSessionSystemRole,
    resolveLeadIdClie,
};
