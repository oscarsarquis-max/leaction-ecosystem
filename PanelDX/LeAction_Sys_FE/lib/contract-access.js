'use strict';

const { pool } = require('./postgres-pool');
const { isSessionAdmin, resolveLeadIdClie } = require('./auth-session');

const CONTRACT_ACCESS_ALLOWED = new Set(['ativo', 'trial']);
const CONTRACT_ACCESS_BLOCKED = new Set(['inadimplente', 'cancelado']);

/**
 * Status do contrato vigente do cliente — consulta direta ao RDS (sem cache).
 * @param {number} idClie
 * @returns {Promise<string|null>}
 */
async function fetchContractStatusForClie(idClie) {
    if (!idClie) return null;
    const { rows } = await pool.query(
        `SELECT status
         FROM public.dx_contratos
         WHERE id_clie = $1
         ORDER BY
             CASE status
                 WHEN 'ativo' THEN 0
                 WHEN 'trial' THEN 1
                 WHEN 'inadimplente' THEN 2
                 WHEN 'cancelado' THEN 3
                 ELSE 4
             END,
             data_inicio DESC,
             id DESC
         LIMIT 1`,
        [idClie]
    );
    return rows.length ? rows[0].status : null;
}

function isContractAccessAllowed(status) {
    if (!status) return true;
    const normalized = String(status).trim().toLowerCase();
    if (CONTRACT_ACCESS_BLOCKED.has(normalized)) return false;
    if (CONTRACT_ACCESS_ALLOWED.has(normalized)) return true;
    return true;
}

/**
 * Resolve id_clie da sessão para checagem de contrato.
 */
async function resolveIdClieForContract(req) {
    if (!req || !req.session) return null;
    if (isSessionAdmin(req)) return null;

    const fromSession =
        req.session.user_id ||
        req.session.lead?.id_clie ||
        req.session.id_clie ||
        null;

    const resolved = await resolveLeadIdClie(req);
    return resolved || fromSession;
}

module.exports = {
    fetchContractStatusForClie,
    isContractAccessAllowed,
    resolveIdClieForContract,
};
