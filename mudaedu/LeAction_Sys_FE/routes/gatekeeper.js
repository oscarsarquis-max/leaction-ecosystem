'use strict';

const express = require('express');
const crypto = require('crypto');

const { unlockSystem, lockSystem } = require('../lib/system-config');

const router = express.Router();

function getProductionMasterKey() {
    return String(process.env.PRODUCTION_MASTER_KEY || '').trim();
}

/** Bypass/unlock: sempre em production; em dev só com GATEKEEPER_ALLOW_DEV=true. */
function isGatekeeperAdminRouteEnabled() {
    if ((process.env.NODE_ENV || 'development') === 'production') {
        return true;
    }
    return String(process.env.GATEKEEPER_ALLOW_DEV || '').toLowerCase() === 'true';
}

function gatekeeperDevOnlyResponse(res) {
    return res.status(403).send(
        'Rotas de homologação disponíveis apenas em produção. '
        + 'Em dev, defina GATEKEEPER_ALLOW_DEV=true no .env.development para testar localmente.'
    );
}

function isValidMasterSecret(providedSecret) {
    const expected = getProductionMasterKey();
    const provided = String(providedSecret || '').trim();

    if (!expected || !provided) {
        return false;
    }

    try {
        const expectedBuf = Buffer.from(expected, 'utf8');
        const providedBuf = Buffer.from(provided, 'utf8');
        if (expectedBuf.length !== providedBuf.length) {
            return false;
        }
        return crypto.timingSafeEqual(expectedBuf, providedBuf);
    } catch (_err) {
        return false;
    }
}

function gatekeeperDisabledResponse(res) {
    return res.status(403).send('Acesso negado.');
}

router.get('/gatekeeper/bypass', (req, res) => {
    if (!isGatekeeperAdminRouteEnabled()) {
        return gatekeeperDevOnlyResponse(res);
    }

    if (!getProductionMasterKey()) {
        console.error('[Gatekeeper] PRODUCTION_MASTER_KEY não configurada.');
        return gatekeeperDisabledResponse(res);
    }

    if (!isValidMasterSecret(req.query.secret)) {
        return gatekeeperDisabledResponse(res);
    }

    req.session.is_admin_tester = true;
    req.session.save((err) => {
        if (err) {
            console.error('[Gatekeeper] Falha ao persistir sessão de homologação:', err.message);
            return res.status(500).send('Falha ao registrar sessão de homologação.');
        }
        return res.redirect('/');
    });
});

router.get('/gatekeeper/unlock', async (req, res) => {
    if (!isGatekeeperAdminRouteEnabled()) {
        return gatekeeperDevOnlyResponse(res);
    }

    if (!getProductionMasterKey()) {
        console.error('[Gatekeeper] PRODUCTION_MASTER_KEY não configurada.');
        return gatekeeperDisabledResponse(res);
    }

    if (!isValidMasterSecret(req.query.secret)) {
        return gatekeeperDisabledResponse(res);
    }

    try {
        await unlockSystem();
        return res.status(200).send('Sistema liberado para uso geral!');
    } catch (err) {
        console.error('[Gatekeeper] Falha ao liberar system_locked:', err.message);
        return res.status(500).send('Falha ao liberar o sistema. Verifique a conexão com o banco.');
    }
});

router.get('/gatekeeper/lock', async (req, res) => {
    if (!isGatekeeperAdminRouteEnabled()) {
        return gatekeeperDevOnlyResponse(res);
    }

    if (!getProductionMasterKey()) {
        console.error('[Gatekeeper] PRODUCTION_MASTER_KEY não configurada.');
        return gatekeeperDisabledResponse(res);
    }

    if (!isValidMasterSecret(req.query.secret)) {
        return gatekeeperDisabledResponse(res);
    }

    try {
        await lockSystem();
        return res.status(200).send('Sistema BLOQUEADO. Tela de manutenção ativada para o público.');
    } catch (err) {
        console.error('[Gatekeeper] Falha ao bloquear system_locked:', err.message);
        return res.status(500).send('Falha ao bloquear o sistema. Verifique a conexão com o banco.');
    }
});

router.get('/manutencao', (_req, res) => {
    res.render('manutencao', {
        layout: false,
        title: 'MudaEdu — Em preparação',
    });
});

module.exports = router;
