'use strict';

const crypto = require('crypto');

const HUB_PUBLIC_URL = (process.env.HUB_PUBLIC_URL || '').replace(/\/$/, '');
const HUB_ACTION_HUB_PORT = process.env.HUB_ACTION_HUB_PORT || '4000';
const CHECKOUT_HANDOFF_SECRET =
    process.env.CHECKOUT_HANDOFF_SECRET ||
    process.env.SESSION_SECRET ||
    'paneldx-dev-checkout-handoff';

/**
 * Token opcional de handoff PanelDX → ActionHub (HMAC, válido por 1h).
 */
function createCheckoutHandoffToken(idClie) {
    const exp = Date.now() + 60 * 60 * 1000;
    const payload = `${idClie}:${exp}`;
    const sig = crypto.createHmac('sha256', CHECKOUT_HANDOFF_SECRET).update(payload).digest('hex');
    return Buffer.from(`${payload}:${sig}`).toString('base64url');
}

function resolveHubPublicUrl(req) {
    if (HUB_PUBLIC_URL) return HUB_PUBLIC_URL;
    const protocol = req?.protocol || 'http';
    const host = req?.hostname || 'localhost';
    return `${protocol}://${host}:${HUB_ACTION_HUB_PORT}`;
}

/**
 * URL white-label do ActionHub para contratação/upgrade de plano PanelDX.
 */
function buildActionHubCheckoutUrl(req, idClie, options = {}) {
    const hubBase = resolveHubPublicUrl(req);
    const params = new URLSearchParams();
    params.set('client_id', String(idClie));

    const email =
        options.email ||
        req?.session?.lead?.email ||
        req?.session?.lead?.mail_clie ||
        req?.session?.user?.email ||
        '';
    if (email) params.set('email', email.trim());

    if (options.includeToken !== false) {
        params.set('token', createCheckoutHandoffToken(idClie));
    }

    const returnOrigin = options.returnOrigin || (req ? `${req.protocol}://${req.get('host')}` : '');
    if (returnOrigin) params.set('return_origin', returnOrigin);

    const returnTo = options.returnTo || '/projeto';
    if (returnTo) params.set('return_to', returnTo);

    if (options.planId) params.set('plan_id', String(options.planId));

    if (options.idMatu) params.set('id_matu', String(options.idMatu));

    return `${hubBase}/checkout/paneldx?${params.toString()}`;
}

/**
 * Checkout expresso — pacote add-on de licenças (sem vitrine).
 */
function buildActionHubAddonCheckoutUrl(req, idClie, addonId, options = {}) {
    const hubBase = resolveHubPublicUrl(req);
    const params = new URLSearchParams();
    params.set('client_id', String(idClie));
    params.set('addon_id', String(addonId));

    const email =
        options.email ||
        req?.session?.lead?.email ||
        req?.session?.lead?.mail_clie ||
        req?.session?.user?.email ||
        '';
    if (email) params.set('email', email.trim());

    if (options.includeToken !== false) {
        params.set('token', createCheckoutHandoffToken(idClie));
    }

    const returnOrigin = options.returnOrigin || (req ? `${req.protocol}://${req.get('host')}` : '');
    if (returnOrigin) params.set('return_origin', returnOrigin);

    const returnTo = options.returnTo || '/teams';
    if (returnTo) params.set('return_to', returnTo);

    return `${hubBase}/checkout/direct?${params.toString()}`;
}

module.exports = {
    buildActionHubCheckoutUrl,
    buildActionHubAddonCheckoutUrl,
    createCheckoutHandoffToken,
    resolveHubPublicUrl,
};
