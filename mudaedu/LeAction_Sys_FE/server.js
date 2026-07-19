const path = require('path');
const fs = require('fs');

// --- DEVOPS: CONFIGURAÇÃO DE AMBIENTE (antes de postgres-pool / gatekeeper) ---
const env = process.env.NODE_ENV || 'development';
require('dotenv').config({ path: path.join(__dirname, `.env.${env}`) });
require('dotenv').config({ path: path.join(__dirname, '../LeAction_SysF/.env'), override: false });
require('dotenv').config({ path: path.join(__dirname, '../.env'), override: false });
if (process.env.DB_PASS === 'sua_senha' && process.env.DB_PASSWORD) {
    process.env.DB_PASS = process.env.DB_PASSWORD;
}
if (!process.env.DB_USER && process.env.DB_USERNAME) {
    process.env.DB_USER = process.env.DB_USERNAME;
}
if (!process.env.DB_PASS && process.env.DB_PASSWORD) {
    process.env.DB_PASS = process.env.DB_PASSWORD;
}
// Placeholder legado no .env.development — herda senha real do LeAction_SysF/.env
if (process.env.DB_PASS === 'sua_senha') {
    const backendEnvPath = path.join(__dirname, '../LeAction_SysF/.env');
    if (fs.existsSync(backendEnvPath)) {
        const backendVars = require('dotenv').parse(fs.readFileSync(backendEnvPath));
        if (backendVars.DB_PASS) {
            process.env.DB_PASS = backendVars.DB_PASS;
        }
        if (!process.env.DB_HOST && backendVars.DB_HOST) process.env.DB_HOST = backendVars.DB_HOST;
        if (!process.env.DB_NAME && backendVars.DB_NAME) process.env.DB_NAME = backendVars.DB_NAME;
        if (!process.env.DB_USER && backendVars.DB_USER) process.env.DB_USER = backendVars.DB_USER;
    }
}

const axios = require('axios');
const express = require('express');
const expressLayouts = require('express-ejs-layouts');
const session = require('express-session');
const multer = require('multer');
const gatekeeperRoutes = require('./routes/gatekeeper');
const { gatekeeperMiddleware } = require('./middleware/gatekeeper');
const { contractAccessMiddleware } = require('./middleware/contract-access');
const { isSessionAdmin, resolveSessionSystemRole, getAdminEmail, resolveLeadIdClie } = require('./lib/auth-session');
const { buildActionHubCheckoutUrl, buildActionHubAddonCheckoutUrl, resolveHubPublicUrl } = require('./lib/actionhub-checkout');
const cmsS3 = require('./lib/cms-s3-storage');

const app = express();
const PORT = process.env.PORT || 3001;

// --- CONFIGURAÇÕES BÁSICAS ---
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, 'public')));

// Fallback S3 para imagens CMS legadas (/images/...) após deploy ECS
app.get('/images/:filename', async (req, res, next) => {
    const filename = path.basename(req.params.filename || '');
    if (!filename || filename.includes('..')) {
        return res.status(400).send('Nome de arquivo inválido.');
    }
    const localPath = path.join(__dirname, 'public', 'images', filename);
    if (fs.existsSync(localPath)) {
        return res.sendFile(localPath);
    }
    if (!cmsS3.isCmsS3Enabled()) {
        return next();
    }
    try {
        const exists = await cmsS3.cmsObjectExists(filename);
        if (!exists) {
            return next();
        }
        return res.redirect(302, cmsS3.getPublicUrlForFilename(filename));
    } catch (err) {
        console.error('[CMS S3] Falha ao resolver imagem:', filename, err.message);
        return next();
    }
});

app.use(expressLayouts);
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

// --- CONSTANTES ---
// Desenvolvimento: BACKEND_URL (.env.development, ex.: :5002) tem prioridade.
// Produção/Docker: FLASK_API_URL (rede interna do container) tem prioridade.
function resolveBackendUrl() {
    const nodeEnv = process.env.NODE_ENV || 'development';
    const flaskPort = process.env.FLASK_PORT || '5002';
    if (nodeEnv !== 'production') {
        return (
            process.env.BACKEND_URL ||
            process.env.FLASK_API_URL ||
            `http://127.0.0.1:${flaskPort}`
        );
    }
    return (
        process.env.FLASK_API_URL ||
        process.env.BACKEND_URL ||
        'http://127.0.0.1:5000'
    );
}

const BACKEND_URL = resolveBackendUrl();
const API_BASE_URL = `${BACKEND_URL}/api`;
const ADMIN_EMAIL = process.env.ADMIN_EMAIL || 'sysadmin@leaction.com.br'; // Ajuste conforme seu uso

/** Headers RBAC repassados ao Flask (escopo por papel). */
function flaskRbacHeaders(req) {
    const sr = resolveSessionSystemRole(req);
    const sessionEmail =
        (req.session.lead && req.session.lead.email) ||
        (isSessionAdmin(req) ? getAdminEmail() : '');
    return {
        'X-PanelDX-System-Role': sr,
        'X-PanelDX-Id-Usuario': req.session.id_usuario != null ? String(req.session.id_usuario) : '',
        'X-PanelDX-Id-Member': req.session.id_member != null ? String(req.session.id_member) : '',
        'X-PanelDX-Id-Clie': req.session.user_id != null ? String(req.session.user_id) : '',
        'X-PanelDX-Id-Proj': req.session.id_proj != null ? String(req.session.id_proj) : '',
        'X-PanelDX-Id-Squad': req.session.id_squad != null ? String(req.session.id_squad) : '',
        'X-PanelDX-Email': sessionEmail,
        'X-PanelDX-Position': req.session.position || '',
        'X-PanelDX-Auth-Type': req.session.auth_type || 'lead',
    };
}

async function proxyFlaskRbac(req, res, method, path, body) {
    try {
        const url = `${BACKEND_URL}${path}`;
        const config = {
            timeout: FLASK_HTTP_TIMEOUT_MS,
            headers: { 'Content-Type': 'application/json', ...flaskRbacHeaders(req) },
        };
        let response;
        if (method === 'GET') {
            response = await axios.get(url, { ...config, params: req.query });
        } else if (method === 'PUT') {
            response = await axios.put(url, body || req.body, config);
        } else if (method === 'DELETE') {
            response = await axios.delete(url, config);
        } else {
            response = await axios.post(url, body || req.body, config);
        }
        return res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            return res.status(error.response.status).json(error.response.data);
        }
        return res.status(502).json({ status: 'error', message: 'Falha ao comunicar com o backend.' });
    }
}

const FLASK_HTTP_TIMEOUT_MS = Number(process.env.FLASK_HTTP_TIMEOUT_MS || 60000);

/** GET ao Flask com retry para falhas transitórias (ex.: ECONNRESET durante reload do debug). */
async function axiosGetWithRetry(url, options = {}, retries = 3) {
    const config = { timeout: FLASK_HTTP_TIMEOUT_MS, ...options };
    let lastError;
    for (let attempt = 0; attempt < retries; attempt++) {
        try {
            return await axios.get(url, config);
        } catch (err) {
            lastError = err;
            const code = err?.code || '';
            const msg = String(err?.message || '');
            const retryable =
                code === 'ECONNRESET' ||
                code === 'ECONNREFUSED' ||
                code === 'ETIMEDOUT' ||
                msg.includes('ECONNRESET') ||
                msg.includes('socket hang up');
            if (!retryable || attempt === retries - 1) {
                throw err;
            }
            await new Promise((resolve) => setTimeout(resolve, 400 * (attempt + 1)));
        }
    }
    throw lastError;
}

async function fetchCmsPublic() {
    try {
        const response = await axios.get(`${API_BASE_URL}/public/cms`, { timeout: 8000 });
        return response.data;
    } catch (error) {
        console.warn('⚠️ CMS público indisponível:', error.message);
        return null;
    }
}

/** Relatório completo (162 questões) — só após AVALIACAO OK ou CONCLUIDO. */
function isRelatorioCompletoDisponivel(statusIa) {
    const s = String(statusIa || '').trim().toUpperCase();
    return s === 'AVALIACAO OK' || s.includes('CONCLU');
}

/** Cliente empresarial com avaliação inicial (exclui inovador solo). */
function isClienteEmpresarialAvaliacao(record) {
    if (!record) return false;
    const initRole = String(record.init_role || 'GENERAL').toUpperCase().trim();
    const statusIa = String(record.status_ia || '').toUpperCase().trim();
    const justificativa = String(record.justificativa_solo || '').trim();
    if (initRole === 'SOLO') return false;
    if (statusIa === 'SANDBOX') return false;
    if (justificativa) return false;
    return true;
}

/** Href do menu Análise de Contexto / diagnóstico conforme estágio da jornada. */
function getDiagnosticoHref(idMatu, statusIa) {
    const s = String(statusIa || '').trim().toUpperCase();
    if (!s || s === 'AGUARDANDO CONTEXTO') {
        return `/avaliacoes/${idMatu}`;
    }
    return isRelatorioCompletoDisponivel(s)
        ? `/diagnostico/${idMatu}`
        : `/diagnostico-inicial/${idMatu}`;
}

// --- Upload de imagens do CMS (local dev ou S3 em produção) ---
const CMS_IMAGES_DIR = path.join(__dirname, 'public', 'images');
fs.mkdirSync(CMS_IMAGES_DIR, { recursive: true });

const cmsImageStorage = cmsS3.isCmsS3Enabled()
    ? multer.memoryStorage()
    : multer.diskStorage({
        destination: (req, file, cb) => cb(null, CMS_IMAGES_DIR),
        filename: (req, file, cb) => {
            cb(null, cmsS3.buildCmsFilename(file.originalname));
        },
    });

const cmsImageUpload = multer({
    storage: cmsImageStorage,
    limits: { fileSize: 5 * 1024 * 1024 },
    fileFilter: (req, file, cb) => {
        if (file.mimetype && file.mimetype.startsWith('image/')) {
            cb(null, true);
            return;
        }
        cb(new Error('Apenas arquivos de imagem são permitidos.'));
    },
});

// --- Upload de comprovação documental das métricas da Sprint ---
const METRICAS_UPLOAD_DIR = path.join(__dirname, 'public', 'uploads', 'metricas');
fs.mkdirSync(METRICAS_UPLOAD_DIR, { recursive: true });

const METRICA_DOC_EXTS = new Set([
    '.pdf', '.png', '.jpg', '.jpeg', '.webp', '.gif',
    '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt',
]);

function isMetricaDocumentoPermitido(file) {
    const ext = path.extname(file.originalname || '').toLowerCase();
    if (METRICAS_DOC_EXTS.has(ext)) return true;
    const mime = String(file.mimetype || '').toLowerCase();
    return (
        mime.startsWith('image/') ||
        mime === 'application/pdf' ||
        mime === 'text/plain' ||
        mime.includes('msword') ||
        mime.includes('officedocument') ||
        mime.includes('ms-excel') ||
        mime.includes('ms-powerpoint')
    );
}

const metricasDocStorage = cmsS3.isCmsS3Enabled()
    ? multer.memoryStorage()
    : multer.diskStorage({
        destination: (req, file, cb) => cb(null, METRICAS_UPLOAD_DIR),
        filename: (req, file, cb) => {
            cb(null, cmsS3.buildCmsFilename(file.originalname));
        },
    });

const metricasDocUpload = multer({
    storage: metricasDocStorage,
    limits: { fileSize: 15 * 1024 * 1024 },
    fileFilter: (req, file, cb) => {
        if (isMetricaDocumentoPermitido(file)) {
            cb(null, true);
            return;
        }
        cb(new Error('Tipo de arquivo não permitido. Use PDF, imagem ou Office.'));
    },
});

// --- Integração Action Hub (URLs dinâmicas — não dependem de IP fixo na LAN) ---
const HUB_GATEWAY_INTERNAL = (process.env.HUB_GATEWAY_INTERNAL_URL || 'http://127.0.0.1:4001').replace(/\/$/, '');
const HUB_PUBLIC_URL = (process.env.HUB_PUBLIC_URL || '').replace(/\/$/, '');
const HUB_ACTION_HUB_PORT = String(process.env.HUB_ACTION_HUB_PORT || '4000');

function resolveClientHost(req) {
    const forwarded = req.get('x-forwarded-host');
    const hostHeader = forwarded || req.get('host') || 'localhost:3000';
    const hostname = hostHeader.split(':')[0];
    const protocol = req.get('x-forwarded-proto') || req.protocol || 'http';
    return { hostname, protocol };
}

function attachCoachLocals(req, res, context, extra = {}) {
    res.locals.coachContext = context;
    res.locals.coachData = extra.coachData || {};
}

// --- MIDDLEWARE GLOBAL: VARIÁVEIS PARA AS VIEWS ---
app.use((req, res, next) => {
    const { hostname, protocol } = resolveClientHost(req);
    res.locals.API_BASE_URL = API_BASE_URL;
    // Browser usa proxy same-origin; servidor monta URL do Hub no mesmo hostname
    res.locals.hubApiUrl = '/hub-api';
    res.locals.hubPublicUrl = HUB_PUBLIC_URL || `${protocol}://${hostname}:${HUB_ACTION_HUB_PORT}`;
    res.locals.hubWebhookUrl =
        process.env.HUB_WEBHOOK_URL || `${BACKEND_URL}/api/hub/payment-webhook`;
    res.locals.whatsappCommunityUrl =
        process.env.WHATSAPP_COMMUNITY_URL || 'https://chat.whatsapp.com/placeholder-mudaedu-comunidade';
    next();
});

// Proxy same-origin → gateway local (evita IP fixo e CORS no browser)
app.use('/hub-api', async (req, res) => {
    const targetUrl = `${HUB_GATEWAY_INTERNAL}${req.url}`;
    try {
        const response = await axios({
            method: req.method,
            url: targetUrl,
            data: ['GET', 'HEAD'].includes(req.method.toUpperCase()) ? undefined : req.body,
            headers: {
                'content-type': req.get('content-type') || 'application/json',
            },
            validateStatus: () => true,
            timeout: 60000,
        });
        if (response.headers['content-type']) {
            res.set('content-type', response.headers['content-type']);
        }
        res.status(response.status).send(response.data);
    } catch (err) {
        console.error('[Hub Proxy]', err.message);
        res.status(502).json({
            error: 'Gateway Action Hub indisponível. Verifique se o serviço na porta 4001 está ativo.',
        });
    }
});

// ==================================================================
// 1. GERENCIAMENTO DE SESSÃO (CORRIGIDO E PERMISSIVO)
// ==================================================================
app.use(session({
    secret: process.env.SESSION_SECRET || 'leaction_dev_secret_troque_em_producao',
    resave: false,              // FORÇA salvar a sessão
    saveUninitialized: true,   // FORÇA criar cookie para anônimos
    cookie: {
        secure: false,         // OBRIGATÓRIO FALSE para localhost
        httpOnly: true,        // Protege contra JS
        sameSite: 'lax',         // Permite que o cookie sobreviva ao redirect para /projeto
        maxAge: 1000 * 60 * 60 * 24 // 24 horas
    }
}));

// ==================================================================
// GATEKEEPER — homologação produtiva (system_locked + bypass)
// Ordem: sessão → rotas /gatekeeper + /manutencao → middleware global
// ==================================================================
app.use(gatekeeperRoutes);
app.use(gatekeeperMiddleware);
app.use(contractAccessMiddleware);

// Upload de imagens do CMS — antes do authMiddleware (validação de sysadmin no handler).
// Em produção, /api/* vai para o Flask; use /node/admin/cms/upload ou /admin/cms/upload.
function handleCmsImageUpload(req, res) {
    if (!isSessionAdmin(req)) {
        return res.status(403).json({ success: false, error: 'Acesso restrito ao Sysadmin.' });
    }

    cmsImageUpload.single('imagem')(req, res, async (err) => {
        if (err) {
            const message = err.code === 'LIMIT_FILE_SIZE'
                ? 'Imagem muito grande. Limite: 5 MB.'
                : (err.message || 'Falha no upload.');
            return res.status(400).json({ success: false, error: message });
        }
        if (!req.file) {
            return res.status(400).json({ success: false, error: 'Nenhum arquivo enviado.' });
        }

        try {
            if (cmsS3.isCmsS3Enabled()) {
                const uploaded = await cmsS3.uploadCmsImage(
                    req.file.buffer,
                    req.file.mimetype,
                    req.file.originalname
                );
                console.log(
                    `📤 [CMS Upload S3] ${req.file.originalname} -> ${uploaded.publicUrl}`
                );
                return res.json({
                    success: true,
                    url: uploaded.persistedUrl,
                    public_url: uploaded.publicUrl,
                    storage: 's3',
                });
            }

            const url = cmsS3.getCmsPersistedUrl(req.file.filename);
            console.log(`📤 [CMS Upload local] ${req.file.originalname} -> ${url}`);
            return res.json({ success: true, url, storage: 'local' });
        } catch (uploadErr) {
            console.error('[CMS Upload] Erro:', uploadErr.message);
            return res.status(500).json({
                success: false,
                error: 'Falha ao persistir imagem do CMS.',
            });
        }
    });
}

app.post('/node/admin/cms/upload', handleCmsImageUpload);
app.post('/admin/cms/upload', handleCmsImageUpload);
app.post('/api/admin/upload', handleCmsImageUpload);

// ==================================================================
// 2. LISTAS DE PERMISSÃO
// ==================================================================
const publicPaths = ['/', '/cadastro', '/login', '/logout', '/termos-de-uso', '/instrucoes-de-uso', '/versao-aplicacao', '/verificar-email', '/consultor-leaction', '/mesa-do-inovador', '/solucionador-de-problemas', '/manutencao', '/gatekeeper/bypass', '/gatekeeper/unlock', '/gatekeeper/lock'];
const restrictedPaths = ['/clientes', '/dimensoes', '/fases', '/blocos', '/questoes', '/sprints', '/rodadas', '/maturidades', '/surveys', '/entregaveis', '/movimentos', '/dominios', '/admin', '/teams', '/inteligencia-negocio'];
const leadPaths = ['/avaliacoes', '/diagnostico'];

/** Páginas públicas com layout — precisam do mesmo lead enriquecido da sidebar. */
const PUBLIC_LAYOUT_PATHS = new Set(['/instrucoes-de-uso', '/versao-aplicacao', '/termos-de-uso']);

/** Monta objeto lead a partir da sessão (IDs soltos + lead parcial). */
function buildLeadFromSession(req) {
    const raw = req.session.lead || null;
    const idMatu = raw?.id_matu || req.session.id_matu || null;
    const idClie = raw?.id_clie || req.session.user_id || null;
    if (!raw && !idMatu && !idClie && !req.session.user_name) return null;

    const hasActive = raw?.hasActiveProject === true
        || raw?.hasActiveProject === 1
        || raw?.hasActiveProject === 'true'
        || raw?.has_active_project === true
        || req.session.hasActiveProject === true;

    return {
        ...(raw || {}),
        id_matu: idMatu,
        id_clie: idClie,
        nome: raw?.nome || req.session.user_name || null,
        email: raw?.email || null,
        hasActiveProject: hasActive,
        has_active_project: hasActive,
        plano_ia_concluido: !!(raw?.plano_ia_concluido),
        status_ia: raw?.status_ia || null,
        clima_organizacional: raw?.clima_organizacional || null,
        init_role: raw?.init_role || req.session.init_role || null,
        perfil_lead: raw?.perfil_lead || null,
        system_role: raw?.system_role || req.session.system_role || null,
    };
}

/** Injeta sessão no EJS (necessário em rotas públicas que usam layout com sidebar). */
function injectSessionLocals(req, res) {
    const isTeam = !!req.session.isTeam;
    const lead = buildLeadFromSession(req);
    const isLoggedIn = !!(lead || isTeam || req.session.user_id);
    res.locals.isLoggedIn = isLoggedIn;
    res.locals.isAdmin = isSessionAdmin(req) || isTeam || !!(lead && lead.email === ADMIN_EMAIL);
    res.locals.isHolding = !!req.session.is_holding;
    res.locals.system_role = resolveSessionSystemRole(req);
    res.locals.isExecutor = req.session.system_role === 'executor';
    res.locals.isConsultor = req.session.system_role === 'consultor';
    res.locals.user = lead || (isTeam
        ? { nome: req.session.user_name || 'Admin', role: 'ADMIN' }
        : null);
    res.locals.lead = res.locals.user;
    res.locals.isRelatorioCompletoDisponivel = isRelatorioCompletoDisponivel;
    res.locals.getDiagnosticoHref = getDiagnosticoHref;
}

/**
 * Enriquece lead na sessão/locals (status IA, plano, contrato) para a sidebar
 * ficar igual à do /projeto mesmo em páginas que não montam o commonContext.
 */
async function hydrateLeadSidebarContext(req, res) {
    injectSessionLocals(req, res);
    if (res.locals.isAdmin || res.locals.isHolding || res.locals.isConsultor || res.locals.isExecutor) {
        return;
    }

    const idMatu = req.session.id_matu || req.session.lead?.id_matu || null;
    const idClie = req.session.user_id || req.session.lead?.id_clie || null;
    if (!idMatu && !idClie) return;

    const merged = buildLeadFromSession(req) || {};

    const tasks = [];
    if (idMatu) {
        tasks.push(
            axios.get(`${API_BASE_URL}/client/genese-status/${idMatu}`, { timeout: 4000 })
                .then((r) => ({ kind: 'genese', data: r.data }))
                .catch(() => ({ kind: 'genese', data: null }))
        );
        tasks.push(
            axios.get(`${API_BASE_URL}/ctdi_matu/${idMatu}`, { timeout: 4000 })
                .then((r) => ({ kind: 'matu', data: r.data }))
                .catch(() => ({ kind: 'matu', data: null }))
        );
    }
    if (idClie) {
        tasks.push(
            axios.get(`${API_BASE_URL}/ctdi_clie/${idClie}`, { timeout: 4000 })
                .then((r) => ({ kind: 'clie', data: r.data }))
                .catch(() => ({ kind: 'clie', data: null }))
        );
    }

    const results = await Promise.all(tasks);
    for (const item of results) {
        if (!item || !item.data) continue;
        if (item.kind === 'genese') {
            if (item.data.status_ia) merged.status_ia = item.data.status_ia;
            if (item.data.plano_pronto != null) {
                merged.plano_ia_concluido = !!item.data.plano_pronto;
            }
        }
        if (item.kind === 'matu') {
            if (item.data.status_ia) merged.status_ia = item.data.status_ia;
            if (item.data.data_geracao_plano) {
                merged.data_geracao_plano = item.data.data_geracao_plano;
            }
            const st = String(item.data.status_ia || merged.status_ia || '').toUpperCase();
            if (st.indexOf('CONCLU') !== -1) merged.plano_ia_concluido = true;
        }
        if (item.kind === 'clie') {
            if (item.data.clima_organizacional) {
                merged.clima_organizacional = item.data.clima_organizacional;
            }
            if (item.data.empresa_clie) merged.empresa_clie = item.data.empresa_clie;
            if (item.data.nome_clie && !merged.nome) merged.nome = item.data.nome_clie;
            if (item.data.has_active_project) {
                merged.hasActiveProject = true;
                merged.has_active_project = true;
            }
            if (item.data.perfil_lead) merged.perfil_lead = item.data.perfil_lead;
            if (item.data.init_role) merged.init_role = item.data.init_role;
        }
    }

    merged.id_matu = idMatu || merged.id_matu;
    merged.id_clie = idClie || merged.id_clie;
    if (merged.hasActiveProject) req.session.hasActiveProject = true;

    req.session.lead = { ...(req.session.lead || {}), ...merged };
    if (idMatu) req.session.id_matu = idMatu;

    res.locals.lead = req.session.lead;
    res.locals.user = req.session.lead;
}

async function syncLeadGeneseStatus(req, res) {
    await hydrateLeadSidebarContext(req, res);
}

// ==================================================================
// 3. MIDDLEWARE DE AUTENTICAÇÃO (O PORTEIRO INTELIGENTE)
// ==================================================================
const authMiddleware = async (req, res, next) => {
    const currentPath = req.path;

    console.log(`\n[DEBUG ACESSO] ---------------------------------`);
    console.log(`| Rota: ${currentPath}`);
    console.log(`| Sessão ID: ${req.sessionID}`); // <--- CORRIGIDO AQUI
    console.log(`| Lead no Objeto Session: ${req.session.lead ? 'IDENTIFICADO' : 'VAZIO'}`);
    console.log(`| User ID direto: ${req.session.user_id || 'NULO'}`);
    console.log(`------------------------------------------------\n`);

    // A. O "FURA-FILA" (VIP) - Libera estáticos e APIs públicas
    // Páginas públicas com layout ainda precisam da sessão na sidebar.
    if (publicPaths.includes(currentPath) ||
        currentPath.startsWith('/hub-api') ||
        currentPath.startsWith('/bff/') ||
        currentPath.startsWith('/api/') ||
        currentPath.startsWith('/css/') ||
        currentPath.startsWith('/js/') ||
        currentPath.startsWith('/img/') ||
        currentPath.startsWith('/images/')) {
        if (PUBLIC_LAYOUT_PATHS.has(currentPath)) {
            await hydrateLeadSidebarContext(req, res);
        } else if (publicPaths.includes(currentPath)) {
            injectSessionLocals(req, res);
        }
        return next();
    }

    const isDev = (process.env.NODE_ENV || 'development') !== 'production';

    // Preview do Cockpit Holding em desenvolvimento (sem exigir login)
    if (isDev && currentPath === '/cockpit-rede') {
        res.locals.isLoggedIn = true;
        res.locals.isAdmin = true;
        res.locals.user = req.session.lead || (req.session.isTeam
            ? { nome: req.session.user_name || 'Admin', role: 'ADMIN' }
            : { nome: 'Preview Dev', role: 'ADMIN' });
        res.locals.lead = res.locals.user;
        return next();
    }

    // B. RECUPERA SESSÃO
    injectSessionLocals(req, res);
    const lead = req.session.lead;
    const isTeam = req.session.isTeam;
    const isHolding = !!req.session.is_holding;
    const isLoggedIn = !!(lead || isTeam);
    const isAdmin = !!res.locals.isAdmin;

    // C. REGRAS DE BLOQUEIO

    // 1. Visitante
    if (!isLoggedIn) {
        if (req.xhr || req.headers.accept?.indexOf('json') > -1) {
            return res.status(401).json({ error: 'Sessão expirada' });
        }
        return res.redirect('/');
    }

    // 1b. Gestor de Rede (Holding) — acesso somente leitura ao Cockpit
    const holdingAllowed = ['/cockpit-rede', '/logout'];
    if (isHolding) {
        if (!holdingAllowed.some(p => currentPath === p || currentPath.startsWith(p + '/'))) {
            return res.redirect('/cockpit-rede');
        }
        return next();
    }

    // 2. Admin (God Mode)
    if (isAdmin) {
        return next();
    }

    // 2b. Consultor — Portal do Parceiro
    if (req.session.system_role === 'consultor') {
        if (currentPath.startsWith('/portal-consultor') || currentPath === '/logout') {
            return next();
        }
        return res.redirect('/portal-consultor');
    }

    // --- AJUSTE AQUI: LIBERAR /teams PARA O LEAD ---
    if (currentPath.startsWith('/teams')) {
        return next(); // Deixa o Lead passar para a página de equipes
    }

    // 3. Cliente em área restrita (Outros caminhos como /admin, /config, etc)
    if (restrictedPaths.some(path => currentPath.startsWith(path))) {
        return res.redirect('/projeto');
    }

    await syncLeadGeneseStatus(req, res);

    next();
};

app.use(authMiddleware);

// ==================================================================
// 📝 MICRO-CMS — Gestão de Conteúdo (Sysadmin) — rotas prioritárias
// ==================================================================
app.get('/admin-cms', (req, res) => {
    if (!isSessionAdmin(req)) {
        return res.status(403).render('error', {
            title: 'Acesso negado',
            message: 'A Gestão de Conteúdo (CMS) é restrita ao Sysadmin. Faça login com uma conta administrativa.'
        });
    }
    res.render('admin-cms', {
        title: 'Gestão de Conteúdo (CMS)',
        isLoggedIn: true,
        isAdmin: true,
        user: req.session.lead || { nome: req.session.user_name || 'Admin', role: 'ADMIN' },
        lead: req.session.lead || { nome: req.session.user_name || 'Admin', role: 'ADMIN' }
    });
});

app.get('/admin/cms', (req, res) => res.redirect(301, '/admin-cms'));
app.get('/esim', (req, res) => res.redirect(301, '/admin/esim'));

// ==================================================================
// 📡 Gestão eSIM (Sysadmin)
// ==================================================================
app.get('/admin/esim', (req, res) => {
    if (!isSessionAdmin(req)) {
        return res.status(403).render('error', {
            title: 'Acesso negado',
            message: 'A Gestão eSIM é restrita ao Sysadmin. Faça login com uma conta administrativa.'
        });
    }
    res.render('admin-esim', {
        title: 'Gestão eSIM',
        pageStylesheet: '/css/admin-esim.css?v=3',
        pageScript: '/js/admin-esim.js?v=3',
        id_clie: req.session.user_id || req.session.lead?.id_clie || '',
        isLoggedIn: true,
        isAdmin: true,
        user: req.session.lead || { nome: req.session.user_name || 'Admin', role: 'ADMIN' },
        lead: req.session.lead || { nome: req.session.user_name || 'Admin', role: 'ADMIN' }
    });
});

// ==================================================================
// 👥 Gestão Global de Usuários (Sysadmin)
// ==================================================================
function isSessionSysadmin(req) {
    return resolveSessionSystemRole(req) === 'sysadmin';
}

app.get('/admin/usuarios', (req, res) => {
    if (!isSessionSysadmin(req)) {
        return res.status(403).render('error', {
            title: 'Acesso negado',
            message: 'A Gestão Global de Usuários é restrita ao Sysadmin.'
        });
    }
    res.render('admin-usuarios', {
        title: 'Gestão Global de Usuários',
        pageStylesheet: '/css/admin-usuarios.css?v=8',
        pageScript: '/js/admin-usuarios.js?v=9',
        isLoggedIn: true,
        isAdmin: true,
        system_role: 'sysadmin',
        user: req.session.lead || { nome: req.session.user_name || 'Admin', role: 'ADMIN' },
        lead: req.session.lead || { nome: req.session.user_name || 'Admin', role: 'ADMIN' }
    });
});

// ==================================================================
// 🤝 Portal do Parceiro (Consultor)
// ==================================================================
app.get('/portal-consultor', (req, res) => {
    const sr = resolveSessionSystemRole(req);
    if (sr !== 'consultor' && !isSessionAdmin(req)) {
        return res.status(403).render('error', {
            title: 'Acesso negado',
            message: 'O Portal do Parceiro é restrito a consultores credenciados.'
        });
    }
    res.render('portal-consultor', {
        title: 'Portal do Parceiro',
        pageStylesheets: [
            '/css/mesa-inovacao.css?v=7',
            '/css/admin-esim.css?v=3',
            '/css/portal-consultor.css?v=2',
        ],
        pageScript: '/js/portal-consultor.js?v=2',
        isLoggedIn: true,
        isConsultor: sr === 'consultor',
        system_role: sr,
        user: req.session.lead || { nome: req.session.user_name || 'Consultor', role: 'CONSULTOR' },
        lead: req.session.lead || { nome: req.session.user_name || 'Consultor', role: 'CONSULTOR' }
    });
});

// ==================================================================
// 🤝 CRM & Contratos (Sysadmin)
// ==================================================================
app.get('/admin/crm', (req, res) => {
    if (!isSessionSysadmin(req)) {
        return res.status(403).render('error', {
            title: 'Acesso negado',
            message: 'O CRM & Gestão de Contratos é restrito ao Sysadmin.'
        });
    }
    res.render('admin-crm', {
        title: 'CRM & Contratos',
        pageStylesheet: '/css/admin-crm.css?v=5',
        pageScript: '/js/crm-admin.js?v=8',
        pageVendorScripts: ['https://cdn.jsdelivr.net/npm/apexcharts@3.45.2/dist/apexcharts.min.js'],
        isLoggedIn: true,
        isAdmin: true,
        system_role: 'sysadmin',
        user: req.session.lead || { nome: req.session.user_name || 'Admin', role: 'ADMIN' },
        lead: req.session.lead || { nome: req.session.user_name || 'Admin', role: 'ADMIN' }
    });
});

async function proxyAdminUsuarios(req, res, method, flaskPath) {
    if (!isSessionSysadmin(req)) {
        return res.status(403).json({ status: 'error', error: 'Acesso restrito ao Sysadmin.' });
    }
    try {
        const url = `${BACKEND_URL}${flaskPath}`;
        const config = {
            timeout: FLASK_HTTP_TIMEOUT_MS,
            headers: { 'Content-Type': 'application/json', ...flaskRbacHeaders(req) }
        };
        let response;
        if (method === 'GET') {
            response = await axios.get(url, { ...config, params: req.query });
        } else if (method === 'POST') {
            response = await axios.post(url, req.body, config);
        } else if (method === 'PUT') {
            response = await axios.put(url, req.body, config);
        } else if (method === 'DELETE') {
            response = await axios.delete(url, config);
        } else {
            return res.status(405).json({ status: 'error', error: 'Método não suportado.' });
        }
        return res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            return res.status(error.response.status).json(error.response.data);
        }
        console.error(`❌ Erro proxy admin usuários ${method} ${flaskPath}:`, error.message);
        return res.status(502).json({ status: 'error', error: 'Falha ao comunicar com o backend.' });
    }
}

// BFF — em produção o ALB envia /api* ao Flask; o browser deve usar /bff/* (sessão Node + headers RBAC).
const BFF_ADMIN_USUARIOS = '/bff/admin/usuarios';
app.get(BFF_ADMIN_USUARIOS, (req, res) => proxyAdminUsuarios(req, res, 'GET', '/api/admin/usuarios'));
app.get(`${BFF_ADMIN_USUARIOS}/opcoes-empresa`, (req, res) => proxyAdminUsuarios(req, res, 'GET', '/api/admin/usuarios/opcoes-empresa'));
app.get(`${BFF_ADMIN_USUARIOS}/:id/acesso`, (req, res) => proxyAdminUsuarios(req, res, 'GET', `/api/admin/usuarios/${req.params.id}/acesso`));
app.post(BFF_ADMIN_USUARIOS, (req, res) => proxyAdminUsuarios(req, res, 'POST', '/api/admin/usuarios'));
app.put(`${BFF_ADMIN_USUARIOS}/:id`, (req, res) => proxyAdminUsuarios(req, res, 'PUT', `/api/admin/usuarios/${req.params.id}`));
app.delete(`${BFF_ADMIN_USUARIOS}/:id`, (req, res) => proxyAdminUsuarios(req, res, 'DELETE', `/api/admin/usuarios/${req.params.id}`));

// BFF — CRM / Contratos (Sysadmin)
const BFF_ADMIN_CRM = '/bff/admin/crm';
async function proxyAdminCrm(req, res, method, flaskPath) {
    if (!isSessionAdmin(req)) {
        return res.status(403).json({ status: 'error', message: 'Acesso restrito ao Sysadmin.' });
    }
    return proxyFlaskRbac(req, res, method, flaskPath);
}
app.get(`${BFF_ADMIN_CRM}/dashboard`, (req, res) => proxyAdminCrm(req, res, 'GET', '/api/admin/crm/dashboard'));
app.get(`${BFF_ADMIN_CRM}/planos`, (req, res) => proxyAdminCrm(req, res, 'GET', '/api/admin/crm/planos'));
app.post(`${BFF_ADMIN_CRM}/planos`, (req, res) => proxyAdminCrm(req, res, 'POST', '/api/admin/crm/planos'));
app.put(`${BFF_ADMIN_CRM}/planos/:id`, (req, res) => proxyAdminCrm(req, res, 'PUT', `/api/admin/crm/planos/${req.params.id}`));
app.get(`${BFF_ADMIN_CRM}/contratos`, (req, res) => proxyAdminCrm(req, res, 'GET', '/api/admin/crm/contratos'));
app.get(`${BFF_ADMIN_CRM}/contratos/:id`, (req, res) => proxyAdminCrm(req, res, 'GET', `/api/admin/crm/contratos/${req.params.id}`));
app.post(`${BFF_ADMIN_CRM}/contratos`, (req, res) => proxyAdminCrm(req, res, 'POST', '/api/admin/crm/contratos'));
app.put(`${BFF_ADMIN_CRM}/contratos/:id`, (req, res) => proxyAdminCrm(req, res, 'PUT', `/api/admin/crm/contratos/${req.params.id}`));
app.get(`${BFF_ADMIN_CRM}/contratos/:id/addons`, (req, res) => proxyAdminCrm(req, res, 'GET', `/api/admin/crm/contratos/${req.params.id}/addons`));
app.post(`${BFF_ADMIN_CRM}/contratos/:id/addons`, (req, res) => proxyAdminCrm(req, res, 'POST', `/api/admin/crm/contratos/${req.params.id}/addons`));
app.delete(`${BFF_ADMIN_CRM}/contratos/:id/addons/:addonId`, (req, res) => proxyAdminCrm(req, res, 'DELETE', `/api/admin/crm/contratos/${req.params.id}/addons/${req.params.addonId}`));
app.post(`${BFF_ADMIN_CRM}/vitrine/publicar`, (req, res) => proxyAdminCrm(req, res, 'POST', '/api/admin/crm/vitrine/publicar'));
app.get(`${BFF_ADMIN_CRM}/vitrine/ultima-publicacao`, (req, res) => proxyAdminCrm(req, res, 'GET', '/api/admin/crm/vitrine/ultima-publicacao'));
app.get(`${BFF_ADMIN_CRM}/consultores`, (req, res) => proxyAdminCrm(req, res, 'GET', '/api/admin/crm/consultores'));
app.get(`${BFF_ADMIN_CRM}/consultores/usuarios-sem-perfil`, (req, res) => proxyAdminCrm(req, res, 'GET', '/api/admin/crm/consultores/usuarios-sem-perfil'));
app.get(`${BFF_ADMIN_CRM}/consultores/:id`, (req, res) => proxyAdminCrm(req, res, 'GET', `/api/admin/crm/consultores/${req.params.id}`));
app.post(`${BFF_ADMIN_CRM}/consultores`, (req, res) => proxyAdminCrm(req, res, 'POST', '/api/admin/crm/consultores'));
app.put(`${BFF_ADMIN_CRM}/consultores/:id`, (req, res) => proxyAdminCrm(req, res, 'PUT', `/api/admin/crm/consultores/${req.params.id}`));
app.delete(`${BFF_ADMIN_CRM}/consultores/:id`, (req, res) => proxyAdminCrm(req, res, 'DELETE', `/api/admin/crm/consultores/${req.params.id}`));
app.get('/bff/admin/consultores', (req, res) => proxyAdminCrm(req, res, 'GET', '/api/admin/crm/consultores'));
app.get(`${BFF_ADMIN_CRM}/funil`, (req, res) => {
    const qs = req.url.includes('?') ? req.url.slice(req.url.indexOf('?')) : '';
    return proxyAdminCrm(req, res, 'GET', `/api/admin/crm/funil${qs}`);
});
app.post(`${BFF_ADMIN_CRM}/funil/:id/atribuir`, (req, res) =>
    proxyAdminCrm(req, res, 'POST', `/api/admin/crm/funil/${req.params.id}/atribuir`));
app.put(`${BFF_ADMIN_CRM}/funil/:id/atribuir`, (req, res) =>
    proxyAdminCrm(req, res, 'PUT', `/api/admin/crm/funil/${req.params.id}/atribuir`));

// BFF — Portal do Parceiro (Consultor)
const BFF_CONSULTOR = '/bff/consultor';
async function proxyConsultor(req, res, method, flaskPath) {
    const sr = resolveSessionSystemRole(req);
    if (sr !== 'consultor' && !isSessionAdmin(req)) {
        return res.status(403).json({ status: 'error', message: 'Acesso restrito ao Consultor.' });
    }
    return proxyFlaskRbac(req, res, method, flaskPath);
}
app.get(`${BFF_CONSULTOR}/dashboard`, (req, res) => proxyConsultor(req, res, 'GET', '/api/bff/consultor/dashboard'));
app.get(`${BFF_CONSULTOR}/clientes`, (req, res) => proxyConsultor(req, res, 'GET', '/api/bff/consultor/clientes'));
app.get(`${BFF_CONSULTOR}/sprints`, (req, res) => proxyConsultor(req, res, 'GET', '/api/bff/consultor/sprints'));
app.get(`${BFF_CONSULTOR}/demandas`, (req, res) => proxyConsultor(req, res, 'GET', '/api/bff/consultor/demandas'));
app.post(`${BFF_CONSULTOR}/demandas`, (req, res) => proxyConsultor(req, res, 'POST', '/api/bff/consultor/demandas'));
app.put(`${BFF_CONSULTOR}/demandas/:id`, (req, res) => proxyConsultor(req, res, 'PUT', `/api/bff/consultor/demandas/${req.params.id}`));
app.post(`${BFF_CONSULTOR}/vincular-lead`, (req, res) => proxyConsultor(req, res, 'POST', '/api/bff/consultor/vincular-lead'));
app.get(`${BFF_CONSULTOR}/prospectos`, (req, res) => proxyConsultor(req, res, 'GET', '/api/bff/consultor/prospectos'));
app.post(`${BFF_CONSULTOR}/prospectos`, (req, res) => proxyConsultor(req, res, 'POST', '/api/bff/consultor/prospectos'));

app.get('/bff/public/vitrine/planos', async (req, res) => {
    try {
        const response = await axios.get(`${BACKEND_URL}/api/public/vitrine/planos`, {
            timeout: FLASK_HTTP_TIMEOUT_MS,
        });
        return res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            return res.status(error.response.status).json(error.response.data);
        }
        return res.status(502).json({ status: 'error', error: 'Falha ao carregar vitrine de planos.' });
    }
});

app.get('/api/led/usuarios-disponiveis', (req, res) => proxyFlaskRbac(req, res, 'GET', '/api/led/usuarios-disponiveis'));
app.post('/bff/led/usuarios', (req, res) => proxyFlaskRbac(req, res, 'POST', '/api/led/usuarios'));
app.get('/bff/led/cota-usuarios', (req, res) => proxyFlaskRbac(req, res, 'GET', '/api/led/cota-usuarios'));
app.get('/bff/led/meu-contrato', (req, res) => proxyFlaskRbac(req, res, 'GET', '/api/led/meu-contrato'));

app.get('/meu-contrato', async (req, res) => {
    const dadosUsuario = req.session.user || req.session.lead;
    if (!dadosUsuario) {
        return res.redirect('/');
    }

    const idClie = await resolveLeadIdClie(req);
    const checkoutUpgradeUrl = idClie
        ? buildActionHubCheckoutUrl(req, idClie, { returnTo: '/meu-contrato' })
        : '';
    const checkoutAddonUrlTemplate = idClie
        ? buildActionHubAddonCheckoutUrl(req, idClie, '{addon_id}', { returnTo: '/meu-contrato' })
        : '';
    const hubDashboardUrl = `${resolveHubPublicUrl(req)}/dashboard`;

    res.render('meu-contrato', {
        title: 'Meu Contrato',
        pageStylesheets: [
            '/css/mesa-inovacao.css?v=7',
            '/css/admin-esim.css?v=3',
            '/css/meu-contrato.css?v=1',
        ],
        pageScript: '/js/meu-contrato.js?v=1',
        user: dadosUsuario,
        lead: dadosUsuario,
        isLoggedIn: true,
        isAdmin: isSessionAdmin(req),
        idClie: idClie || '',
        checkoutUpgradeUrl,
        checkoutAddonUrlTemplate,
        hubDashboardUrl,
        API_BASE_URL: process.env.API_BASE_URL || 'http://localhost:3000/api',
    });
});

app.post('/api/webhooks/ativar-addon', async (req, res) => {
    try {
        const response = await axios.post(`${BACKEND_URL}/api/webhooks/ativar-addon`, req.body, {
            timeout: FLASK_HTTP_TIMEOUT_MS,
            headers: { 'Content-Type': 'application/json' },
        });
        return res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            return res.status(error.response.status).json(error.response.data);
        }
        return res.status(502).json({ error: 'Falha ao processar webhook de add-on.' });
    }
});

app.get('/bff/meus-projetos', async (req, res) => {
    const dadosUsuario = req.session.user || req.session.lead;
    if (!dadosUsuario) {
        return res.status(401).json([]);
    }
    try {
        const email = (dadosUsuario.email || req.session.lead?.email || '').trim();
        const idClie = await resolveLeadIdClie(req);
        const userRole = isSessionAdmin(req) ? 'ADMIN' : 'LEAD';
        const response = await axios.get(`${BACKEND_URL}/api/meus-projetos`, {
            params: { role: userRole, id_clie: idClie, email },
            timeout: FLASK_HTTP_TIMEOUT_MS,
        });
        const projetos = response.data || [];
        if (projetos.length && req.session.lead && projetos[0].id_clie) {
            req.session.user_id = projetos[0].id_clie;
            req.session.lead.id_clie = projetos[0].id_clie;
        }
        return res.json(projetos);
    } catch (error) {
        console.error('>>> [ERRO] BFF meus-projetos:', error.message);
        return res.status(502).json([]);
    }
});

async function proxyEsimAdmin(req, res, method, flaskPath) {
    if (!isSessionAdmin(req)) {
        return res.status(403).json({ status: 'error', message: 'Acesso restrito ao Sysadmin.' });
    }
    try {
        const url = `${BACKEND_URL}${flaskPath}`;
        const config = {
            timeout: FLASK_HTTP_TIMEOUT_MS,
            headers: { 'Content-Type': 'application/json' }
        };
        let response;
        if (method === 'GET') {
            response = await axios.get(url, { ...config, params: req.query });
        } else if (method === 'POST') {
            response = await axios.post(url, req.body, config);
        } else if (method === 'PUT') {
            response = await axios.put(url, req.body, config);
        } else if (method === 'DELETE') {
            response = await axios.delete(url, config);
        } else {
            return res.status(405).json({ status: 'error', message: 'Método não suportado.' });
        }
        return res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            return res.status(error.response.status).json(error.response.data);
        }
        console.error(`❌ Erro proxy admin eSIM ${method} ${flaskPath}:`, error.message);
        return res.status(502).json({ status: 'error', message: 'Falha ao comunicar com o backend eSIM.' });
    }
}

app.get('/api/admin/esim/catalog', (req, res) => proxyEsimAdmin(req, res, 'GET', '/api/admin/esim/catalog'));
app.post('/api/admin/esim/catalog', (req, res) => proxyEsimAdmin(req, res, 'POST', '/api/admin/esim/catalog'));
app.put('/api/admin/esim/catalog/:id', (req, res) => proxyEsimAdmin(req, res, 'PUT', `/api/admin/esim/catalog/${req.params.id}`));
app.delete('/api/admin/esim/catalog/:id', (req, res) => proxyEsimAdmin(req, res, 'DELETE', `/api/admin/esim/catalog/${req.params.id}`));
app.post('/api/admin/esim/catalog/:id/disparar-mesa', (req, res) => proxyEsimAdmin(
    req,
    res,
    'POST',
    `/api/admin/esim/catalog/${req.params.id}/disparar-mesa`
));

app.get('/api/admin/esim/provedores', (req, res) => proxyEsimAdmin(req, res, 'GET', '/api/admin/esim/provedores'));
app.post('/api/admin/esim/provedores', (req, res) => proxyEsimAdmin(req, res, 'POST', '/api/admin/esim/provedores'));
app.put('/api/admin/esim/provedores/:id', (req, res) => proxyEsimAdmin(req, res, 'PUT', `/api/admin/esim/provedores/${req.params.id}`));
app.delete('/api/admin/esim/provedores/:id', (req, res) => proxyEsimAdmin(req, res, 'DELETE', `/api/admin/esim/provedores/${req.params.id}`));

app.get('/api/admin/esim/framework-options', (req, res) => proxyEsimAdmin(req, res, 'GET', '/api/admin/esim/framework-options'));
app.get('/api/admin/esim/blocos', (req, res) => proxyEsimAdmin(req, res, 'GET', '/api/admin/esim/blocos'));

app.get('/api/admin/mesas-inovacao', (req, res) => proxyEsimAdmin(req, res, 'GET', '/api/admin/mesas-inovacao'));

// ==================================================================
// 🎯 RBAC — Sala de Execução e Notificações
// ==================================================================
app.get('/execucao', (req, res) => {
    if (!req.session.user_id && !req.session.id_member) {
        return res.redirect('/?error=acesso_execucao');
    }
    const sr = (req.session.system_role || '').toLowerCase();
    if (sr !== 'executor' && !req.session.isAdmin) {
        return res.status(403).render('error', {
            title: 'Acesso negado',
            message: 'A Sala de Execução é restrita ao perfil Executor (e SysAdmin para suporte).'
        });
    }
    res.render('execucao', {
        title: 'Sala de Execução',
        pageStylesheet: '/css/execucao.css?v=2',
        pageScript: '/js/execucao.js?v=2',
        isLoggedIn: true,
        isAdmin: !!req.session.isAdmin,
        isExecutor: true,
        system_role: sr,
        user: req.session.lead || { nome: req.session.user_name, role: sr },
        lead: req.session.lead || { nome: req.session.user_name, role: sr },
        id_member: req.session.id_member,
        position: req.session.position || ''
    });
});

app.get('/api/execucao/tarefas', (req, res) => proxyFlaskRbac(req, res, 'GET', '/api/execucao/tarefas'));
app.get('/api/notificacoes', (req, res) => proxyFlaskRbac(req, res, 'GET', '/api/notificacoes'));
app.put('/api/notificacoes/:id/ler', (req, res) => proxyFlaskRbac(req, res, 'PUT', `/api/notificacoes/${req.params.id}/ler`));
app.get('/api/rbac/capacidade', (req, res) => proxyFlaskRbac(req, res, 'GET', '/api/rbac/capacidade'));

app.get('/api/public/cms', async (req, res) => {
    try {
        const response = await axios.get(`${API_BASE_URL}/public/cms`, { timeout: 8000 });
        return res.status(response.status).json(response.data);
    } catch (error) {
        console.error('[CMS] Erro GET /api/public/cms:', error.message);
        return res.status(error.response?.status || 500).json(
            error.response?.data || { success: false, error: 'Falha ao carregar CMS público.' }
        );
    }
});

app.get('/api/admin/cms', async (req, res) => {
    if (!isSessionAdmin(req)) {
        return res.status(403).json({ success: false, error: 'Acesso restrito ao Sysadmin.' });
    }
    try {
        const response = await axios.get(`${API_BASE_URL}/admin/cms`);
        return res.status(response.status).json(response.data);
    } catch (error) {
        console.error('❌ Erro GET /api/admin/cms:', error.message);
        return res.status(error.response?.status || 500).json(
            error.response?.data || { success: false, error: 'Falha ao carregar CMS.' }
        );
    }
});

app.put('/api/admin/cms', async (req, res) => {
    if (!isSessionAdmin(req)) {
        return res.status(403).json({ success: false, error: 'Acesso restrito ao Sysadmin.' });
    }
    try {
        const response = await axios.put(`${API_BASE_URL}/admin/cms`, req.body, {
            headers: { 'Content-Type': 'application/json' }
        });
        return res.status(response.status).json(response.data);
    } catch (error) {
        console.error('❌ Erro PUT /api/admin/cms:', error.message);
        return res.status(error.response?.status || 500).json(
            error.response?.data || { success: false, error: 'Falha ao salvar CMS.' }
        );
    }
});

// ==================================================================
// NOVAS ROTAS DO PRESURVEY (DEVE FICAR ACIMA DAS ROTAS GENÉRICAS)
// ==================================================================

// Alterado o prefixo de /api/ para /node/ para contornar o desvio do Nginx na AWS
app.post('/node/client/processar-presurvey', async (req, res) => {
    console.log("[SERVER] Tentando processar presurvey para ID:", req.body.id_matu);
    const { id_matu } = req.body;

    try {
        // Usamos o axios para bater no Flask (porta 5000)
        // BACKEND_URL vem do .env.development (padrão local: porta 5002)
        const response = await axios.post(`${BACKEND_URL}/api/calculate-presurvey`, {
            id_matu: id_matu
        });

        console.log("[SERVER] Resposta do Flask recebida com sucesso!");
        res.json({ success: true });

    } catch (error) {
        console.error("❌ [SERVER ERROR] Falha no processamento:");

        if (error.response) {
            // O Flask respondeu, mas com erro (ex: 404, 500 do Python)
            console.error("Dados do Python:", error.response.data);
            res.status(error.response.status).json({ error: error.response.data });
        } else {
            // Erro de rede (Flask desligado) ou erro de sintaxe no Node
            console.error("Mensagem de erro:", error.message);
            res.status(500).json({ error: "Erro de conexão com o motor de cálculo (Flask)." });
        }
    }
});

// Rota para renderizar o relatório vistoso
app.get('/diagnostico-inicial/:id_matu', async (req, res) => {
    const { id_matu } = req.params;
    console.log("[NODE] Solicitando relatório para ID:", id_matu);

    try {
        const flaskResponse = await axios.get(`${BACKEND_URL}/api/get-presurvey-results/${id_matu}`);

        // Debug: Veja se os dados chegaram
        console.log("[NODE] Dados recebidos do Flask:", flaskResponse.data);

        const flaskData = flaskResponse.data;
        const leadData = flaskData.lead || {};
        const statusIaReport = String(leadData.status_ia || '').trim().toUpperCase();
        const temProjetoAtivo = req.session.hasActiveProject === true
            || leadData.hasActiveProject === true
            || leadData.has_active_project === true
            || statusIaReport === 'PROJETO OK'
            || statusIaReport === 'CONTEXTO OK'
            || statusIaReport === 'AVALIACAO OK'
            || statusIaReport === 'PENDENTE'
            || statusIaReport === 'PROCESSANDO'
            || statusIaReport === 'CONCLUIDO';

        attachCoachLocals(req, res, 'presurvey');

        const idClieResolved =
            leadData.id_clie ||
            req.session.lead?.id_clie ||
            req.session.user_id ||
            null;
        const hubEmail =
            leadData.mail_clie ||
            req.session.lead?.email ||
            req.session.lead?.mail_clie ||
            '';
        const checkoutPlanUrl =
            idClieResolved && hubEmail
                ? buildActionHubCheckoutUrl(req, idClieResolved, {
                      email: hubEmail,
                      returnTo: '/avaliacoes',
                      idMatu: leadData.id_matu || id_matu,
                  })
                : null;

        res.render('presurvey', {
            title: 'Diagnóstico Preliminar',
            lead: { ...leadData, hasActiveProject: temProjetoAtivo },
            preData: flaskData.preData || {},
            refSetor: flaskData.refSetor || {},
            insights_ia: flaskData.insights_ia || {},
            statusIA: leadData.status_ia,
            temProjetoAtivo,
            hubCustomerEmail: hubEmail,
            checkoutPlanUrl,
            pageVendorScripts: ['/js/presurvey-radar-lib.js?v=2'],
            pageScript: '/js/presurvey-charts.js?v=4',
        });

    } catch (err) {
        console.error("❌ ERRO NO NODE AO BUSCAR RELATÓRIO:", err.message);
        // Se der erro, mande uma mensagem clara para a tela em vez de ficar em branco
        res.status(500).send(`Erro ao carregar relatório: ${err.message}. Verifique se o Flask está rodando.`);
    }
});

// ==================================================================
// 4. ROTAS DE AUTENTICAÇÃO (LOGIN E EMAIL)
// ==================================================================

// PASSO 1: Verificar Email
app.post('/verificar-email', async (req, res) => {
    try {
        const response = await axios.post(`${API_BASE_URL}/check-email`, req.body);
        res.json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            res.status(500).json({ error: 'Erro de comunicação.' });
        }
    }
});

// ==================================================================
// 4. ROTAS DE AUTENTICAÇÃO (LOGIN E EMAIL) - VERSÃO DE DIAGNÓSTICO
// ==================================================================

app.post('/login', async (req, res) => {
    const { email, codigo } = req.body;
    const credential = codigo || req.body.credential;

    console.log(`\n--- [INÍCIO TENTATIVA DE LOGIN] ---`);
    console.log(`Email: ${email}`);
    console.log(`Endpoint Python: ${API_BASE_URL}/login`);

    try {
        // 1. Chamada ao Backend Python
        const response = await axios.post(`${API_BASE_URL}/login`, {
            email: email,
            credential: credential,
            codigo: credential,
            type: 'LEAD'
        });

        // 2. INSPEÇÃO DOS DADOS (O ponto crítico)
        const data = response.data;
        console.log(">>> [RESPOSTA INTEGRAL DO PYTHON]:", JSON.stringify(data, null, 2));

        const isAdminEmail = (data.email || email) === ADMIN_EMAIL;
        const systemRole = (data.system_role || (isAdminEmail ? 'sysadmin' : 'led')).toLowerCase();

        if (!data.id_clie) {
            console.error("⚠️ [ALERTA] id_clie ausente no retorno do Python!");
        }
        if (!data.id_matu && systemRole === 'led') {
            console.error("⚠️ [ALERTA] id_matu ausente para perfil Gestor (led)!");
        }

        // 3. GRAVAÇÃO NA SESSÃO (RBAC + mapeamento legado)
        req.session.user_id = data.id_clie;
        req.session.user_name = data.nome_clie;
        req.session.id_matu = data.id_matu;
        req.session.system_role = systemRole;
        req.session.id_usuario = data.id_usuario || null;
        req.session.id_member = data.id_member || null;
        req.session.id_squad = data.id_squad || null;
        req.session.id_proj = data.id_proj || null;
        req.session.position = data.position || null;
        req.session.auth_type = data.auth_type || 'lead';

        req.session.isTeam = systemRole === 'sysadmin' || isAdminEmail;
        req.session.role = systemRole === 'sysadmin' ? 'ADMIN' : systemRole.toUpperCase();
        req.session.isAdmin = req.session.isTeam;
        req.session.isExecutor = systemRole === 'executor';
        req.session.isConsultor = systemRole === 'consultor';

        req.session.init_role = data.init_role || 'GENERAL';
        req.session.is_holding = !!data.is_holding;
        req.session.id_rede = data.id_rede ? String(data.id_rede).trim().toUpperCase() : null;

        req.session.lead = {
            id_clie: data.id_clie,
            id_matu: data.id_matu,
            email: data.email || email,
            nome: data.nome_clie,
            hasActiveProject: data.hasActiveProject,
            faseAtual: data.faseAtual,
            role: req.session.role,
            system_role: systemRole,
            id_usuario: data.id_usuario || null,
            id_member: data.id_member || null,
            position: data.position || null,
            init_role: data.init_role || 'GENERAL',
            data_geracao_plano: data.data_geracao_plano,
            perfil_lead: data.perfil_lead,
            is_holding: !!data.is_holding,
            id_rede: data.id_rede ? String(data.id_rede).trim().toUpperCase() : null
        };

        // Flags de estado
        req.session.hasActiveProject = data.hasActiveProject;
        req.session.faseAtual = data.faseAtual;

        // 4. PERSISTÊNCIA E REDIRECIONAMENTO (Modificado para integração com o Flask)
        req.session.save((err) => {
            if (err) {
                console.error('❌ [ERRO] Falha ao gravar sessão no Storage:', err);
                return res.status(500).json({ success: false, message: 'Erro interno de sessão' });
            }

            let destino = data.redirect || (
                systemRole === 'sysadmin' ? '/admin'
                    : systemRole === 'executor' ? '/execucao'
                    : systemRole === 'consultor' ? '/portal-consultor'
                    : '/projeto'
            );

            if (data.is_holding) {
                destino = '/cockpit-rede';
            } else if (!data.redirect && systemRole === 'led') {
                const papelInicial = String(data.init_role || '').toUpperCase().trim();
                const perfilLead = String(data.perfil_lead || '').toUpperCase().trim();

                if (perfilLead === 'INOVADOR' || papelInicial === 'SOLO') {
                    destino = `${BACKEND_URL}/inovador/?id_clie=${data.id_clie}`;
                }
            }

            console.log(`✅ [LOGIN SUCESSO] IDs Gravados: Clie=${req.session.user_id}, Matu=${req.session.id_matu}`);
            console.log(`Redirecionando para: ${destino}`);

            res.json({ success: true, redirect: destino });
        });

    } catch (error) {
        console.error('❌ [FALHA NO LOGIN]');
        if (error.response) {
            console.error('Status Python:', error.response.status);
            console.error('Mensagem Python:', error.response.data);
        } else {
            console.error('Erro de Rede/Conexão:', error.message);
        }

        const msg = error.response?.data?.error || 'Credenciais inválidas ou erro de conexão';
        res.status(401).json({ success: false, message: msg });
    }
});

app.get('/logout', (req, res) => {
    // Destrói a sessão e redireciona para a raiz (Home)
    req.session.destroy(() => res.redirect('/'));
});

// ==================================================================
// 5. ROTAS DE NAVEGAÇÃO E SISTEMA
// ==================================================================

// ==================================================================
// ROTA HOME (Inteligente)
// ==================================================================
app.get('/', async (req, res) => {
    // 1. Se já tem sessão, manda pro painel (não perde tempo carregando iframe)
    if (req.session.user_id) {
        if (req.session.is_holding) {
            return res.redirect('/cockpit-rede');
        }
        if (req.session.system_role === 'executor') {
            return res.redirect('/execucao');
        }
        if (String(req.session.init_role).toUpperCase() === 'SOLO') {
            return res.redirect('/inovador/dashboard');
        }
        return res.redirect(req.session.isTeam ? '/admin' : '/projeto');
    }

    const cms = await fetchCmsPublic();

    res.render('index', {
        title: 'Transformação Digital Educacional | Diagnóstico Gratuito MudaEdu',
        metaDescription: 'Avalie a maturidade tecnológica da sua instituição de ensino. Faça o diagnóstico gratuito As-Is da LeAction e receba um roadmap de tecnologia educacional e agilidade.',
        metaKeywords: 'transformação digital educacional, tecnologia educacional na gestão, maturidade digital em escolas, plano de inovação para instituições de ensino, agilidade na educação, framework para educação digital',
        isLoggedIn: false,
        isAdmin: false,
        lead: null,
        user: null,
        cms
    });
});

// PÁGINAS ESTÁTICAS
app.get('/cadastro', (req, res) => res.render('lead-capture', { title: 'Inscrição' }));

// Consultor LeAction — página pública standalone (lead magnet)
app.get('/consultor-leaction', (req, res) => {
    attachCoachLocals(req, res, 'consultor');
    res.render('consultor-leaction', { title: 'Consultor LeAction', layout: false });
});

// Freemium PLG — aliases canônicos para tracking/funil no Action Hub
app.get('/solucionador-de-problemas', (req, res) => {
    attachCoachLocals(req, res, 'consultor');
    res.render('consultor-leaction', {
        title: 'Solucionador de Problemas — Consultor LeAction',
        layout: false,
    });
});

app.get('/mesa-do-inovador', (req, res) => {
    res.render('mesa-do-inovador', {
        title: 'Mesa do Inovador | MudaEdu',
        layout: false,
    });
});

// Proxy sensor → Flask → Action Hub (fire-and-forget no cliente)
app.post('/api/tracking/enviar', async (req, res) => {
    try {
        const response = await axios.post(`${BACKEND_URL}/api/tracking/enviar`, req.body, {
            timeout: 6000,
            headers: {
                'Content-Type': 'application/json',
                'X-Forwarded-For':
                    req.headers['x-forwarded-for'] ||
                    req.socket?.remoteAddress ||
                    '',
                'User-Agent': req.headers['user-agent'] || '',
            },
            validateStatus: () => true,
        });
        return res.status(response.status).json(response.data);
    } catch (error) {
        console.warn('⚠️ [tracking/enviar] proxy falhou (UX não bloqueada):', error.message);
        return res.status(202).json({ ok: true, forwarded: false, error: 'proxy_unavailable' });
    }
});

// Ponte pública para o agente de IA do Consultor (não exige autenticação)
app.post('/api/public/consultor-ia', async (req, res) => {
    try {
        const response = await axios.post(`${BACKEND_URL}/api/public/consultor-ia`, req.body);
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            console.error("❌ Erro na ponte do Consultor IA:", error.message);
            res.status(500).json({ status: 'error', message: 'Erro de comunicação com o motor de IA.' });
        }
    }
});
app.get('/termos-de-uso', (req, res) => res.render('termos-de-uso', { title: 'Termos de Uso' }));
app.get('/instrucoes-de-uso', async (req, res) => {
    const cms = await fetchCmsPublic();
    // Sessão/sidebar já injetadas no authMiddleware (rota pública).
    res.render('instrucoes-de-uso', {
        title: 'Guia MVP',
        cms
    });
});

app.get('/versao-aplicacao', async (req, res) => {
    const cms = await fetchCmsPublic();
    res.render('versao-aplicacao', {
        title: 'Versão da Aplicação',
        cms
    });
});

// --- ROTA ADMIN (Painel Roxo) ---
app.get('/admin', async (req, res) => {
    const cms = await fetchCmsPublic();
    res.render('index', {
        title: 'Painel Admin',
        isLoggedIn: true,
        isAdmin: true,
        lead: null,
        user: {
            id: req.session.user_id,
            nome: req.session.user_name,
            role: 'ADMIN'
        },
        cms
    });
});

// ==================================================================
// 🏛️ COCKPIT DA REDE — Padrão Holding (somente leitura, VIP)
// Declarado no bloco principal de navegação (evita 404 por ordem/carga)
// ==================================================================
function normIdRede(val) {
    if (!val) return '';
    return String(val).trim().toUpperCase();
}

function renderCockpitRede(req, res) {
    const isHolding = !!req.session.is_holding;
    const isAdmin = res.locals.isAdmin;
    const isDev = (process.env.NODE_ENV || 'development') !== 'production';
    const idRede = normIdRede(req.session.id_rede || req.query.rede || req.query.id_rede || '');

    if (!isHolding && !isAdmin && !isDev) {
        return res.redirect('/projeto');
    }

    return res.render('cockpit-rede', {
        title: 'Cockpit da Rede',
        isLoggedIn: true,
        isHolding: isHolding,
        isAdmin: isAdmin && !isHolding,
        id_rede: idRede,
        lead: res.locals.user || { nome: req.session.user_name, id_rede: idRede },
        user: res.locals.user || { nome: req.session.user_name || 'Gestor da Rede' }
    });
}

app.get('/cockpit-rede', renderCockpitRede);

// Lista redes cadastradas (Holding)
app.get('/api/holding/redes', async (req, res) => {
    try {
        const response = await axios.get(`${BACKEND_URL}/api/holding/redes`);
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            console.error('❌ Erro na ponte Holding Redes:', error.message);
            res.status(500).json({ success: false, error: 'Erro de comunicação com o backend.' });
        }
    }
});

// Ponte do Panorama Holding — consolidação Multi-Tier BI (dados reais do Postgres)
app.get('/api/holding/panorama', async (req, res) => {
    try {
        const isAdmin = req.session.isTeam || req.session.isAdmin ||
            (req.session.lead && req.session.lead.email === ADMIN_EMAIL);

        const normRede = (val) => {
            if (val == null || val === '') return null;
            const s = String(val).trim().toUpperCase();
            return s || null;
        };

        // Gestor: rede fixa na sessão. Admin: query ?rede= ou ?id_rede=
        let idRede = null;
        if (isAdmin) {
            idRede = normRede(req.query.rede || req.query.id_rede) || normRede(req.session.id_rede);
        } else {
            idRede = normRede(req.session.id_rede);
        }

        const params = {};
        if (idRede) params.id_rede = idRede;
        if (!idRede && req.session.user_id) params.id_clie = req.session.user_id;
        if (isAdmin && req.query.mock) params.mock = req.query.mock;

        const response = await axios.get(`${BACKEND_URL}/api/holding/panorama`, { params });
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            console.error('❌ Erro na ponte Holding Panorama:', error.message);
            res.status(500).json({ success: false, error: 'Erro de comunicação com o motor Python no Holding.' });
        }
    }
});

// ==================================================================
// 🏛️ ADMIN: Vincular cliente à rede (Holding) — PRIORIDADE ALTA (antes dos catch-alls)
// ==================================================================
app.put('/api/admin/clientes/:id/rede', async (req, res) => {
    const isAdmin = req.session.isTeam || req.session.isAdmin ||
        (req.session.lead && req.session.lead.email === ADMIN_EMAIL);

    if (!isAdmin) {
        return res.status(403).json({ success: false, error: 'Acesso restrito ao Sysadmin.' });
    }

    const { id } = req.params;
    const id_rede = req.body?.id_rede != null ? String(req.body.id_rede).trim().toUpperCase() || null : null;
    const is_holding = !!req.body?.is_holding;

    try {
        const response = await axios.put(
            `${API_BASE_URL}/admin/clientes/${id}/rede`,
            { id_rede, is_holding },
            { headers: { 'Content-Type': 'application/json' } }
        );
        return res.status(response.status).json({
            success: true,
            message: 'Atualizado com sucesso',
            ...response.data
        });
    } catch (error) {
        console.error('❌ Erro PUT /api/admin/clientes/:id/rede:', error.message);
        if (error.response) {
            const data = error.response.data;
            if (data && typeof data === 'object') {
                return res.status(error.response.status).json({
                    success: false,
                    error: data.error || data.message || 'Falha ao atualizar rede.'
                });
            }
            return res.status(error.response.status).json({
                success: false,
                error: `Backend retornou HTTP ${error.response.status}. Verifique se o Flask foi reiniciado.`
            });
        }
        return res.status(500).json({ success: false, error: 'Erro de comunicação com o backend.' });
    }
});

// --- ROTA PROJETO (Painel Verde - Home Dinâmica) ---
app.get('/projeto', async (req, res) => {

    // --- DEBUG DE IDENTIDADE START ---
    console.log("\n--- [INSPEÇÃO DE CHEGADA EM /PROJETO] ---");
    console.log("Timestamp:", new Date().toISOString());
    console.log("ID da Sessão (req.sessionID):", req.sessionID);
    console.log("Existe objeto req.session?", !!req.session);

    const id_matu = req.session.id_matu || (req.session.lead ? req.session.lead.id_matu : null);
    const id_clie = req.session.user_id;

    console.log(`[CHECK FINAL] ID Matu: ${id_matu}, ID Clie: ${id_clie}`);

    if (!id_clie) {
        console.log("⚠️ [REDIRECIONAMENTO DEFENSIVO] ID do Cliente ausente em /projeto. Ejetando para a Home.");
        return res.redirect('/');
    }

    try {
        let journeyData = [];
        let dadosCompletosCliente = {};
        let dadosMaturidade = {};
        let hasProject = false;

        // 1. Buscamos os dados cadastrais do cliente (dependem estritamente do id_clie, que existe!)
        const clientRes = await axios.get(`${API_BASE_URL}/ctdi_clie/${id_clie}`);
        dadosCompletosCliente = clientRes.data || {};

        // =========================================================================
        // 🎯 🌟 O TESTE CONDICIONAL DO DESVIO: INSERIDO NO CIRCUITO DO GET 🌟
        // =========================================================================
        const papelInicial = String(dadosCompletosCliente.init_role || req.session.init_role || '').toUpperCase().trim();
        const perfilLead = String(dadosCompletosCliente.perfil_lead || req.session.perfil_lead || req.session.lead?.perfil_lead || '').toUpperCase().trim();

        console.log(`[DEBUG DESVIO GET] Analisando Papel: "${papelInicial}" | Perfil: "${perfilLead}"`);

        if (perfilLead === 'INOVADOR' || papelInicial === 'SOLO' || id_clie === 8) {
            console.log(`🎯 [DESVIO ATIVADO] Utilizador Solo detectado no GET. Redirecionando para a Oficina Flask...`);
            return res.redirect(`${BACKEND_URL}/inovador/?id_clie=${id_clie}`);
        }
        // =========================================================================

        // 2. Só batemos nas APIs de jornada e maturidade se o id_matu já existir no banco!
        if (id_matu) {
            const [journeyRes, matuRes] = await Promise.all([
                axios.get(`${API_BASE_URL}/client/journey`, { params: { id_matu } }),
                axios.get(`${API_BASE_URL}/ctdi_matu/${id_matu}`)
            ]);

            journeyData = journeyRes.data || [];
            dadosMaturidade = matuRes.data || {};
            const statusIaUpper = String(dadosMaturidade.status_ia || '').trim().toUpperCase();
            const temSprintsKanban = journeyData.some(
                (onda) => Array.isArray(onda.sprints) && onda.sprints.length > 0
            );
            const planoIaConcluido = statusIaUpper === 'CONCLUIDO' && temSprintsKanban;

            hasProject = journeyData.length > 0
                || !!dadosCompletosCliente.has_active_project
                || statusIaUpper === 'PROJETO OK';

            console.log(">>> [DB CHECK] Status IA recuperado:", dadosMaturidade.status_ia);
            console.log(">>> [DB CHECK] Plano IA concluído (Kanban):", planoIaConcluido);
        } else {
            console.log("ℹ️ [INFO] Utilizador sem id_matu (Avaliação Inicial pendente). Ignorando barramento de APIs.");
        }

        // --- UNIFICAÇÃO DE CONTEXTO ---
        const statusIaCtx = String(dadosMaturidade.status_ia || req.session.lead?.status_ia || '').trim().toUpperCase();
        const temSprintsCtx = journeyData.some(
            (onda) => Array.isArray(onda.sprints) && onda.sprints.length > 0
        );
        const planoIaConcluidoCtx = statusIaCtx === 'CONCLUIDO' && temSprintsCtx;

        let diagnosticoReport = null;
        const statusesComMatriz = ['AVALIACAO OK', 'PENDENTE', 'CONCLUIDO'];
        if (id_matu && statusesComMatriz.includes(statusIaCtx)) {
            try {
                const diagRes = await axios.get(`${API_BASE_URL}/diagnostico/${id_matu}`);
                diagnosticoReport = diagRes.data;
            } catch (diagErr) {
                console.warn('⚠️ Diagnóstico indisponível para matriz no dashboard:', diagErr.message);
            }
        }

        let presurveyDashboard = null;
        const statusesComPresurvey = ['PRESURVEY OK', 'PROJETO OK', 'CONTEXTO OK'];
        if (id_matu && statusesComPresurvey.includes(statusIaCtx)) {
            try {
                const presRes = await axios.get(`${BACKEND_URL}/api/get-presurvey-results/${id_matu}`);
                presurveyDashboard = presRes.data || null;
            } catch (presErr) {
                console.warn('⚠️ Pré-survey indisponível para hub central:', presErr.message);
            }
        }

        const commonContext = {
            ...req.session.lead,
            ...dadosCompletosCliente,
            ...dadosMaturidade,
            id_matu: id_matu,
            id_clie: id_clie,
            nome: req.session.user_name || dadosCompletosCliente.nome_clie,
            role: 'LEAD',
            hasActiveProject: hasProject,
            plano_ia_concluido: planoIaConcluidoCtx,
            // Só sinaliza plano gerado após IA Master concluir e popular o Kanban
            data_geracao_plano: planoIaConcluidoCtx
                ? (dadosMaturidade.data_geracao_plano || req.session.lead?.data_geracao_plano || new Date().toISOString())
                : null,
            tipo_ensino: dadosCompletosCliente.tipo_ensino || null,
            qtd_alunos: dadosCompletosCliente.qtd_alunos || null,
        };

        // --- ATUALIZAÇÃO DA SESSÃO ---
        req.session.lead = commonContext;
        req.session.hasActiveProject = hasProject;

        // ✨ PERSISTÊNCIA SEGURA: Aguarda a gravação física antes de renderizar para evitar colisões no Chrome
        req.session.save((err) => {
            if (err) {
                console.error("❌ Erro ao salvar sessão em /projeto:", err);
            }

            const sprintsAtivas = journeyData.flatMap(onda =>
                (onda.sprints || []).filter(s => s.stat_sprn === 'ativa')
            );

            const leadEmail =
                commonContext.email ||
                commonContext.mail_clie ||
                req.session.lead?.email ||
                '';
            const checkoutPlanUrl =
                id_clie && leadEmail
                    ? buildActionHubCheckoutUrl(req, id_clie, {
                          email: leadEmail,
                          returnTo: '/avaliacoes',
                          idMatu: id_matu,
                      })
                    : null;

            res.render('index', {
                title: hasProject ? 'Meu Projeto' : 'Diagnóstico',
                isLoggedIn: true,
                isAdmin: false,
                lead: commonContext,
                user: commonContext,
                journey: journeyData,
                sprintsAtivas: sprintsAtivas,
                diagnosticoReport,
                presurveyDashboard,
                checkoutPlanUrl,
            });
        });

    } catch (error) {
        console.error("❌ Erro no Dashboard (Lead):", error.message);
        res.render('index', {
            title: 'Painel LeAction',
            isLoggedIn: true,
            isAdmin: false,
            lead: { ...req.session.lead, id_matu, id_clie, hasActiveProject: false },
            user: { ...req.session.lead, id_matu, id_clie, hasActiveProject: false },
            journey: [],
            sprintsAtivas: []
        });
    }
});

// ==================================================================
// 6. ROTAS ESPECÍFICAS DO LEAD (Restauradas!)
// ==================================================================

/** Extrai os Top 5 blocos prioritários do relatório de maturidade (mesma lógica do diagnóstico). */
function buildTopMaturityGaps(report) {
    const dimNameById = {
        1: 'Visão Compartilhada (SV)', 2: 'Coração e Conexão (HC)', 3: 'Estrutura Fluida (FS)',
        4: 'Aprendizagem em Ação (LA)', 5: 'Arquitetura Digital (DA)'
    };
    const allBlocks = [];
    (report.suggestions || []).forEach((sug) => {
        (sug.blocos_sugeridos || []).forEach((block) => {
            allBlocks.push({
                id_bloc: block.id_bloc || null,
                id_doma: block.id_doma || sug.id_doma || null,
                id_dime: block.id_dime || null,
                nome: block.nome || 'Bloco sem nome',
                desc: block.desc || 'Sem descrição disponível.',
                gap: parseFloat(sug.gap_dom) || 0,
                score_pres: parseFloat(sug.score_dom_pres) || 0,
                score_fut: parseFloat(sug.score_dom_fut) || 0,
                dominio: sug.dominio_nome || 'Domínio',
                dimensao: dimNameById[block.id_dime] || 'Dimensão'
            });
        });
    });
    allBlocks.sort((a, b) => {
        if (b.gap !== a.gap) return b.gap - a.gap;
        return a.nome.localeCompare(b.nome, 'pt-BR');
    });
    return allBlocks.slice(0, 5);
}

/** Catálogo fixo de direcionadores (espelha PANORAMA_DIRECIONADORES_FIXOS no Flask). */
const DIRECIONADORES_CATALOGO_FIXO = [
    { slug: 'digitalizacao_organizacional', nome: 'Digitalização Organizacional', meta_label: 'Redução de Custo' },
    { slug: 'engajamento_comunidade', nome: 'Engajamento da Comunidade', meta_label: 'Aumento de Receita' },
    { slug: 'capacitacao_docente', nome: 'Capacitação Docente', meta_label: 'Redução de Custo' },
    { slug: 'prontidao_tecnologica', nome: 'Prontidão Tecnológica', meta_label: 'Redução de Custo' },
    { slug: 'novos_modelos_negocio', nome: 'Novos Modelos de Negócio', meta_label: 'Aumento de Receita' }
];

async function loadDirecionadoresEstrategicos(idClie) {
    if (idClie) {
        try {
            const res = await axios.get(`${API_BASE_URL}/okr/consolidado`, { params: { id_clie: idClie } });
            const rows = res.data || [];
            const map = new Map();
            rows.forEach((row) => {
                if (!row.id_direc || map.has(row.id_direc)) return;
                map.set(row.id_direc, {
                    id_direc: row.id_direc,
                    nome: row.nome_direc,
                    desc: row.desc_direc || row.direc_kpi || '',
                    slug: row.slug_catalogo || '',
                    meta_label: row.meta_financeira || ''
                });
            });
            if (map.size > 0) return Array.from(map.values());
        } catch (err) {
            console.warn('⚠️ Direcionadores OKR indisponíveis, usando catálogo fixo:', err.message);
        }
    }
    return DIRECIONADORES_CATALOGO_FIXO.map((d) => ({
        id_direc: `cat_${d.slug}`,
        nome: d.nome,
        desc: `Diretriz estratégica — ${d.meta_label}`,
        slug: d.slug,
        meta_label: d.meta_label
    }));
}

// Mesa de Inovação Organizacional — lead com relatório ou equipe interna
app.get('/admin/mesas-inovacao', (req, res) => {
    if (!isSessionAdmin(req)) {
        return res.status(403).render('error', {
            title: 'Acesso negado',
            message: 'O painel de Mesas de Inovação é restrito ao administrador.'
        });
    }
    res.render('admin-mesas-inovacao', {
        title: 'Mesas de Inovação',
        pageStylesheet: '/css/admin-mesas-inovacao.css?v=1',
        pageScript: '/js/admin-mesas-inovacao.js?v=1',
        isLoggedIn: true,
        isAdmin: true,
        user: req.session.lead || { nome: req.session.user_name || 'Admin', role: 'ADMIN' },
        lead: req.session.lead || { nome: req.session.user_name || 'Admin', role: 'ADMIN' }
    });
});

app.get('/projeto/mesa-inovacao', async (req, res) => {
    if (!req.session.lead && !req.session.isTeam) {
        return res.redirect('/?error=acesso_mesa_inovacao');
    }

    const isAdmin = isSessionAdmin(req);
    let id_matu = req.session.id_matu || req.session.lead?.id_matu;
    let id_clie = req.session.lead?.id_clie || null;

    if (isAdmin && req.query.id_matu) {
        const qMatu = parseInt(req.query.id_matu, 10);
        if (!Number.isNaN(qMatu) && qMatu > 0) {
            id_matu = qMatu;
        }
        if (req.query.id_clie) {
            const qClie = parseInt(req.query.id_clie, 10);
            if (!Number.isNaN(qClie) && qClie > 0) {
                id_clie = qClie;
            }
        }
    }

    if (!id_matu) {
        if (isAdmin) {
            return res.redirect('/admin/mesas-inovacao');
        }
        return res.redirect('/avaliacoes');
    }

    try {
        const response = await axios.get(`${API_BASE_URL}/diagnostico/${id_matu}`);
        const report = response.data || {};
        const topGaps = buildTopMaturityGaps(report);
        if (!id_clie) {
            id_clie = report.id_clie || null;
        }
        const direcionadores = await loadDirecionadoresEstrategicos(id_clie);

        attachCoachLocals(req, res, 'execucao');

        res.render('mesa-inovacao', {
            title: 'Mesa de Inovação Organizacional',
            pageStylesheet: '/css/mesa-inovacao.css?v=5',
            pageScript: '/js/mesa-inovacao.js?v=9',
            isLoggedIn: true,
            isAdmin: !!req.session.isTeam,
            lead: req.session.lead,
            user: req.session.lead || { nome: req.session.user_name, role: 'ADMIN' },
            id_matu,
            id_clie,
            topGaps,
            direcionadores,
            clienteNome: report.cliente || req.session.lead?.nome || 'Organização',
            blocoPrefill: req.query.bloco || ''
        });
    } catch (error) {
        console.error('❌ Erro ao carregar Mesa de Inovação:', error.message);
        res.status(500).render('error', {
            title: 'Erro',
            message: 'Não foi possível carregar os gaps do Relatório de Maturidade.'
        });
    }
});

// A. SPRINT (Kanban de Visão Total)
app.get('/projeto/sprint-atual', async (req, res) => {
    if (!req.session.lead) return res.redirect('/');

    try {
        const id_matu = req.session.id_matu || req.session.lead.id_matu;

        // 1. Busca a jornada completa (todas as ondas e sprints)
        const response = await axios.get(`${API_BASE_URL}/client/journey`, {
            params: { id_matu: id_matu }
        });

        const journeyData = response.data || [];

        // 2. VERIFICAÇÃO SIMPLES: Só checa se existe algum dado
        if (!journeyData || journeyData.length === 0) {
            console.log("⚠️ Nenhuma jornada encontrada.");
            return res.redirect('/meu-plano?error=sem_dados');
        }

        // 3. Renderiza passando TUDO.
        // O EJS agora tem o "journey" completo para filtrar as 3 colunas (Backlog, Ativa, Concluída)
        injectSessionLocals(req, res);
        attachCoachLocals(req, res, 'execucao');

        const systemRole = String(res.locals.system_role || req.session.system_role || '').toLowerCase();
        const isModerator = systemRole === 'consultor' || systemRole === 'sysadmin';

        res.render('sprint-atual', {
            title: 'Quadro Kanban',
            isLoggedIn: true,
            isAdmin: !!res.locals.isAdmin,
            isConsultor: !!res.locals.isConsultor,
            system_role: systemRole || 'led',
            // Moderador = consultor | sysadmin (pontua qualidade)
            podeAvaliarMetricas: isModerator,
            // Cliente executa, marca DoD e encerra
            podeEncerrarSprint: !isModerator,
            lead: req.session.lead,
            user: { nome: req.session.user_name, role: isModerator ? 'MODERADOR' : 'LEAD' },
            journey: journeyData // Enviamos a estrutura completa
        });

    } catch (error) {
        console.error("❌ Erro ao carregar Kanban:", error.message);
        res.redirect('/meu-plano');
    }
});

// Status da Gênese IA (polling da máquina de estados)
app.get('/api/client/genese-status/:id_matu', async (req, res) => {
    try {
        const response = await axios.get(`${API_BASE_URL}/client/genese-status/${req.params.id_matu}`);
        res.json(response.data);
    } catch (error) {
        const status = error.response?.status || 500;
        res.status(status).json(error.response?.data || { error: error.message });
    }
});

// B. DIAGNÓSTICO — JSON para dashboard (matriz embutida)
app.get('/api/diagnostico/:id_matu', async (req, res) => {
    try {
        const response = await axios.get(`${API_BASE_URL}/diagnostico/${req.params.id_matu}`);
        res.json(response.data);
    } catch (error) {
        const status = error.response?.status || 500;
        const message = error.response?.data?.error || error.message || 'Erro ao buscar diagnóstico.';
        console.error('❌ [/api/diagnostico] Falha:', message);
        res.status(status).json({ error: message });
    }
});

// B. DIAGNÓSTICO (Relatório PDF)
app.get('/diagnostico/:id_matu', async (req, res) => {
    try {
        const id_matu = req.params.id_matu;
        let statusIa = String(req.session.lead?.status_ia || '').trim().toUpperCase();

        if (!statusIa) {
            try {
                const stRes = await axios.get(`${API_BASE_URL}/client/genese-status/${id_matu}`, { timeout: 5000 });
                statusIa = String(stRes.data?.status_ia || '').trim().toUpperCase();
            } catch (_) { /* usa sessão */ }
        }

        if (!isRelatorioCompletoDisponivel(statusIa)) {
            console.log(`[NODE] Redirecionando para preliminar (status=${statusIa || '—'}) id=${id_matu}`);
            return res.redirect(`/diagnostico-inicial/${id_matu}`);
        }

        const response = await axios.get(`${API_BASE_URL}/diagnostico/${id_matu}`);

        const leadData = req.session.lead || {
            nome: req.session.user_name,
            id_matu: req.params.id_matu
        };

        res.render('diagnosticos', {
            title: 'Diagnóstico',
            pageStylesheet: '/css/diagnostico-sprint.css?v=17',
            isLoggedIn: true,
            isAdmin: false,
            report: response.data,
            lead: leadData,
            user: { nome: req.session.user_name, role: 'LEAD' }
        });
    } catch (error) {
        res.status(500).render('error', { title: 'Erro', message: 'Erro ao gerar relatório.' });
    }
});

// Novo menu de INTELIGÊNCIA do sistema----------------------------------------------------------
// 1. Rota de Avaliações Iniciais (Antiga "Todas Avaliações")
// O link na sidebar aponta para /avaliacoes, que já está configurada para renderizar 'avaliacoes-list'
app.get('/avaliacoes', async (req, res) => {
    const isAdmin = res.locals.isAdmin;
    try {
        if (isAdmin) {
            const response = await axios.get(`${API_BASE_URL}/all_maturities`);
            const maturidades = (response.data || []).filter(isClienteEmpresarialAvaliacao);
            return res.render('avaliacoes-list', { title: 'Avaliações Iniciais', maturidades });
        } else if (req.session.lead) {
            const initRole = String(req.session.lead.init_role || req.session.init_role || '').toUpperCase().trim();
            const perfilLead = String(req.session.lead.perfil_lead || '').toUpperCase().trim();
            if (initRole === 'SOLO' || perfilLead === 'INOVADOR') {
                return res.redirect(`${BACKEND_URL}/inovador/?id_clie=${req.session.lead.id_clie}`);
            }
            return res.redirect(`/avaliacoes/${req.session.lead.id_matu}`);
        } else {
            return res.redirect('/');
        }
    } catch (error) {
        res.status(500).render('error', { title: 'Erro', message: error.message });
    }
});

// 2. Nova Rota: Inteligência de Negócio (IA)
// Aqui você centralizará as análises de todos os projetos para o SysAdmin
app.get('/inteligencia-negocio', async (req, res) => {
    // 1. Pega o status de Admin do res.locals (setado pelo seu authMiddleware)
    const isAdmin = res.locals.isAdmin;

    try {
        if (isAdmin) {
            // PADRÃO ADMIN: Busca todos os status no Python
            console.log(">>> [SERVER] Buscando Pulso IA para SysAdmin...");
            const response = await axios.get(`${API_BASE_URL}/admin/ia-status`);

            return res.render('inteligencia-negocio', {
                title: 'Inteligência de Negócio',
                isAdmin: true,
                projetos: response.data,
                user: res.locals.user // Injeta o objeto user que seu layout.ejs espera
            });

        } else if (req.session.lead) {
            // PADRÃO LEAD: Busca apenas o status do Lead logado
            const idClie = req.session.lead.id_clie;
            console.log(`>>> [SERVER] Buscando Pulso IA para Lead ${idClie}...`);

            // Aqui chamamos a rota de cliente (que você deve ter no Python)
            const response = await axios.get(`${API_BASE_URL}/cliente/ia-status/${idClie}`);

            return res.render('inteligencia-negocio', {
                title: 'Minha Inteligência',
                isAdmin: false,
                projetos: response.data, // Vem como array de 1 item
                lead: req.session.lead,
                user: res.locals.user
            });
        } else {
            return res.redirect('/');
        }
    } catch (error) {
        console.error("❌ Erro no padrão Inteligência:", error.message);
        res.status(500).render('error', { title: 'Erro', message: error.message });
    }
});

app.get('/insights-ia/:id_matu', async (req, res) => {
    const { id_matu } = req.params;

    try {
        // 1. Chamada ao Python para buscar os dados do projeto real (ID 71/Cliente 70)
        const response = await axios.get(`${API_BASE_URL}/admin/ia-status-detalhado/${id_matu}`);
        const dadosProjeto = response.data;

        if (!dadosProjeto || dadosProjeto.error) {
            return res.status(404).send("Projeto não encontrado.");
        }

        console.log(`>>> [INSIGHTS] Visualizando projeto de: ${dadosProjeto.nome_clie} (ID Cliente: ${dadosProjeto.id_clie || 'N/A'})`);

        // 2. Renderização
        res.render('insights-ia', {
            title: 'Insights Estratégicos IA',
            plano: dadosProjeto,       // <--- ESTE é o dono do projeto (Ex: Cliente 70)
            isAdmin: res.locals.isAdmin,
            user: res.locals.user,     // <--- ESTE é você logado (Admin ID 1) para a sidebar não quebrar
            lead: res.locals.lead
        });

    } catch (error) {
        console.error("❌ Erro na Rota Insights:", error.message);
        res.status(500).render('error', {
            title: 'Erro',
            message: 'Erro ao carregar dados do projeto ' + id_matu
        });
    }
});

// ✨ TRATAMENTO OPERACIONAL PARA FORMULÁRIOS DE ONBOARDING (SEM ID_MATU INICIAL)
app.get('/avaliacoes/:id_matu', async (req, res) => {
    try {
        const { id_matu } = req.params;
        const id_clie = req.session.user_id;

        // 🎯 DETECTOR DE NOVO USUÁRIO: Se id_matu for nulo, indefinido ou string 'null', tratamos como onboarding zerado
        const ehNovaAvaliacao = (!id_matu || id_matu === 'null' || id_matu === 'undefined');

        // A árvore estrutural de questões sempre precisa ser buscada para montar a UI do formulário
        const questRes = await axiosGetWithRetry(`${API_BASE_URL}/questions_by_dimension`);
        const questions = questRes.data;

        // Modelos contextuais de fallback para novos usuários
        let maturityData = { id_clie: id_clie, status_ia: 'AGUARDANDO CONTEXTO' };
        let savedAnswers = {};

        // 🎯 INTELIGÊNCIA PERMISSIVA: Só batemos nas tabelas ctdi_matu e ctdi_surv se o registro físico já existir no banco!
        if (!ehNovaAvaliacao) {
            const [matuRes, ansRes] = await Promise.all([
                axiosGetWithRetry(`${API_BASE_URL}/ctdi_matu/${id_matu}`),
                axiosGetWithRetry(`${API_BASE_URL}/ctdi_surv/by_maturity/${id_matu}`)
            ]);

            maturityData = matuRes.data || {};

            const idClieMatu = maturityData.id_clie;
            if (idClieMatu) {
                const clieRes = await axiosGetWithRetry(`${API_BASE_URL}/ctdi_clie/${idClieMatu}`);
                const perfil = { ...maturityData, ...(clieRes.data || {}) };
                if (!isClienteEmpresarialAvaliacao(perfil)) {
                    if (res.locals.isAdmin) {
                        return res.redirect('/avaliacoes');
                    }
                    return res.redirect(`${BACKEND_URL}/inovador/?id_clie=${idClieMatu}`);
                }
            }

            savedAnswers = ansRes.data.reduce((acc, ans) => {
                acc[ans.id_ques] = {
                    grad: ans.grad_ques,
                    text: ans.quali_ques || '',
                    hasAnswer: true
                };
                return acc;
            }, {});
        } else {
            console.log(`📝 [ESTADO SOBERANO ZERO] Inicializando questionário limpo de Onboarding para o Cliente ID: ${id_clie}`);
        }

        attachCoachLocals(req, res, 'assessment');

        res.render('avaliacoes', {
            title: 'Avaliação',
            isLoggedIn: true,
            isAdmin: res.locals.isAdmin,
            maturityData: maturityData,
            questions: questions,
            savedAnswers,
            lead: req.session.lead,
            user: { nome: req.session.user_name }
        });

    } catch (error) {
        console.error("❌ Erro crítico ao renderizar questionário de avaliações:", error.message);
        res.status(500).render('error', { title: 'Erro', message: 'Erro ao carregar o questionário: ' + error.message });
    }
});

// ==================================================================
// 7. ROTAS DE ADMINISTRAÇÃO E API (PONTES)
// ==================================================================

// Rotas CRUD
const crudPages = ['clientes', 'dimensoes', 'fases', 'blocos', 'questoes', 'sprints', 'rodadas', 'maturidades', 'surveys', 'entregaveis', 'movimentos', 'dominios'];
crudPages.forEach(page => {
    app.get(`/${page}`, (req, res) => {
        const renderOpts = {
            title: page.charAt(0).toUpperCase() + page.slice(1),
        };
        if (page === 'dimensoes' || page === 'dominios') {
            renderOpts.pageStylesheet = '/css/engine-crud-modal.css?v=3';
        }
        res.render(page, renderOpts);
    });
});

app.get('/teams', async (req, res) => {
    const dadosUsuario = req.session.user || req.session.lead;

    if (!dadosUsuario) {
        console.log('>>> [BLOQUEIO] Sessão ausente no Teams.');
        return res.redirect('/');
    }

    const userRole = isSessionAdmin(req) ? 'ADMIN' : 'LEAD';
    const leadEmail = (dadosUsuario.email || req.session.lead?.email || '').trim();
    const teamsRenderBase = {
        title: 'Gestão de Time',
        pageStylesheets: [
            '/css/mesa-inovacao.css?v=7',
            '/css/admin-esim.css?v=3',
            '/css/teams.css?v=10',
        ],
        pageScript: '/js/teams.js?v=10',
        user: dadosUsuario,
        lead: dadosUsuario,
        isLoggedIn: true,
        isAdmin: isSessionAdmin(req),
        API_BASE_URL: process.env.API_BASE_URL || 'http://localhost:3000/api',
    };

    try {
        const idClie = await resolveLeadIdClie(req);
        console.log(`>>> [INFO] Teams: ${leadEmail} | id_clie=${idClie} | role=${userRole}`);

        const response = await axios.get(`${BACKEND_URL}/api/meus-projetos`, {
            params: { role: userRole, id_clie: idClie, email: leadEmail },
            timeout: FLASK_HTTP_TIMEOUT_MS,
        });
        const projetos = response.data || [];
        if (projetos.length && req.session.lead && projetos[0].id_clie) {
            req.session.user_id = projetos[0].id_clie;
            req.session.lead.id_clie = projetos[0].id_clie;
        }

        const idClieResolved = (projetos[0] && projetos[0].id_clie) || idClie || '';
        const checkoutUpgradeUrl = idClieResolved
            ? buildActionHubCheckoutUrl(req, idClieResolved, { returnTo: '/teams' })
            : '';
        const checkoutAddonUrlTemplate = idClieResolved
            ? buildActionHubAddonCheckoutUrl(req, idClieResolved, '{addon_id}', { returnTo: '/teams' })
            : '';

        res.render('teams', {
            ...teamsRenderBase,
            projetos,
            idClie: idClieResolved,
            userRole,
            checkoutUpgradeUrl,
            checkoutAddonUrlTemplate,
        });
    } catch (error) {
        console.error('>>> [ERRO] Falha no backend Teams:', error.message);
        const idClie = await resolveLeadIdClie(req);
        const checkoutUpgradeUrl = idClie
            ? buildActionHubCheckoutUrl(req, idClie, { returnTo: '/teams' })
            : '';
        const checkoutAddonUrlTemplate = idClie
            ? buildActionHubAddonCheckoutUrl(req, idClie, '{addon_id}', { returnTo: '/teams' })
            : '';
        res.render('teams', {
            ...teamsRenderBase,
            projetos: [],
            idClie: idClie || '',
            userRole,
            checkoutUpgradeUrl,
            checkoutAddonUrlTemplate,
        });
    }
});

// APIs Pontes
app.get('/api/admin/clientes-search', async (req, res) => {
    try {
        const response = await axios.get(`${API_BASE_URL}/admin/clientes-search`, { params: req.query });
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ error: 'Erro API Python' });
    }
});

// ==================================================================
// ROTA: PONTE PARA O TOGGLE (COM DEBUG DETALHADO)
// ==================================================================
app.post('/api/admin/toggle-project', async (req, res) => {
    try {
        // 1. TENTATIVA DE DESCOBRIR QUEM É O ADMIN LOGADO
        // Dependendo de como você salva o login, o ID pode estar em lugares diferentes.
        // Vamos tentar todos os lugares comuns:
        let adminId = null;

        if (req.session.user) {
            // Se o objeto user existe, tenta pegar id_team ou id
            adminId = req.session.user.id_team || req.session.user.id || req.session.user.id_clie;
        } else if (req.session.id_team) {
            adminId = req.session.id_team;
        } else if (req.session.user_id) {
            adminId = req.session.user_id;
        }

        console.log(`[NODE DEBUG] Admin ID detectado na sessão: ${adminId}`);

        // 2. MONTA O PACOTE NOVO
        // Pega o que veio do front (id_clie, status) e ADICIONA o id_team
        const payload = {
            ...req.body,
            id_team: adminId
        };

        console.log(`[NODE] Enviando payload completo para Python:`, payload);

        // 3. ENVIA PARA O PYTHON
        const response = await axios.post(`${API_BASE_URL}/admin/toggle-project`, payload);

        console.log(`[NODE] Sucesso:`, response.data);
        res.json(response.data);

    } catch (error) {
        console.error('❌ ERRO NA PONTE DO TOGGLE:');
        if (error.response) {
            console.error('🐍 RESPOSTA DO PYTHON:', JSON.stringify(error.response.data, null, 2));
            res.status(error.response.status).json(error.response.data);
        } else {
            console.error('❌ Erro interno:', error.message);
            res.status(500).json({ error: error.message });
        }
    }
});

// ===================================================================================
// ROTA: GERAÇÃO DO PLANO IA (Gênese Integral - Botão Dourado)
// ===================================================================================
app.post('/client/generate-ai-plan', async (req, res) => {
    console.log('⚡ [DEBUG] Rota /client/generate-ai-plan ACIONADA!');

    if (!req.session.lead) {
        console.log('⛔ [DEBUG] Sessão expirada.');
        return res.status(401).json({ success: false, error: 'Sessão expirada' });
    }

    // Recupera os IDs necessários da sessão
    const id_clie = req.session.lead.id_clie;
    const id_matu = req.session.lead.id_matu || req.session.id_matu;

    console.log(`[NODE] Cliente ${id_clie} disparando Gênese IA via Worker Python...`);

    try {
        // --- 1. COMUNICAÇÃO COM O BACKEND PYTHON ---
        // O Python vai setar 'PENDENTE' no banco de dados (ctdi_matu)
        const response = await axios.post(`${API_BASE_URL}/client/generate-ai-plan`, {
            id_matu: id_matu
        });

        // --- 2. ATUALIZAÇÃO CRÍTICA DA SESSÃO ---
        // Atualizamos o status_ia para 'PENDENTE' na memória do Node.
        // Assim, quando o res.json disparar o reload no front, o EJS já lerá o status novo.
        if (req.session.lead) {
            req.session.lead.status_ia = 'PENDENTE';
            req.session.lead.hasActiveProject = true;
            req.session.lead.data_geracao_plano = null;
            req.session.lead.plano_ia_concluido = false;
        }

        req.session.hasActiveProject = true;
        req.session.id_matu = id_matu;

        // --- 3. PERSISTÊNCIA DA SESSÃO E RESPOSTA ---
        req.session.save((err) => {
            if (err) {
                console.error('❌ Erro ao salvar sessão:', err);
                return res.status(500).json({ success: false, error: 'Erro ao salvar sessão' });
            }
            console.log(`✅ [SUCESSO] Gênese iniciada. Status na sessão: PENDENTE.`);

            // Retornamos sucesso para o fetch no front-end fazer o location.reload()
            res.json({ success: true });
        });

    } catch (error) {
        console.error('❌ Erro na Gênese IA (Ponte Node->Python):', error.message);
        const msg = error.response?.data?.error || "Erro na comunicação com o motor de IA.";
        res.status(500).json({ success: false, error: msg });
    }
});

// ROTA: MEU PLANO (A Jornada Horizontal)
app.get('/meu-plano', async (req, res) => {
  // 1. Segurança: Só entra se estiver logado
  if (!req.session.lead) return res.redirect('/');

  try {
        const id_matu = req.session.id_matu || req.session.lead.id_matu;
        const idClie = await resolveLeadIdClie(req);
        const checkoutUpgradeUrl = idClie ? buildActionHubCheckoutUrl(req, idClie, { returnTo: '/meu-plano' }) : null;

        // 2. Busca a jornada completa no Python
        const response = await axios.get(`${API_BASE_URL}/client/journey`, {
            params: { id_matu: id_matu }
        });

        // 3. Renderiza o arquivo views/client_journey.ejs
        res.render('client_journey', {
            title: 'Meu Plano Estratégico',
            isLoggedIn: true,
            isAdmin: false,
            lead: req.session.lead,
            user: { nome: req.session.user_name, role: 'LEAD' },
            journey: response.data || [],
            checkoutUpgradeUrl,
            pageStylesheet: '/css/meu-plano-pipeline.css?v=1'
        });

    } catch (error) {
        console.error("Erro ao carregar a jornada:", error.message);
        const idClie = await resolveLeadIdClie(req).catch(() => null);
        const checkoutUpgradeUrl = idClie ? buildActionHubCheckoutUrl(req, idClie, { returnTo: '/meu-plano' }) : null;
        // Em caso de erro, volta para o projeto com uma mensagem
        res.render('client_journey', {
            title: 'Meu Plano',
            isLoggedIn: true,
            isAdmin: false,
            lead: req.session.lead,
            user: { nome: req.session.user_name },
            journey: [],
            checkoutUpgradeUrl
        });
    }
});

app.get('/resultados', (req, res) => {
    if (!req.session.lead) return res.redirect('/');
    res.render('resultados', {
        title: 'Meus Resultados',
        lead: req.session.lead,
        user: { nome: req.session.user_name }
    });
});

//Cálculo das datas das sprints no planejamento
// --- ROTA DE AGENDAMENTO (PONTE PARA O BACKEND PYTHON) ---
app.post('/client/update-sprint-date', async (req, res) => {
    const { id_sprn, data_inicio } = req.body;

    // Recupera o ID do cliente da sessão para garantir segurança
    const id_clie = req.session.lead ? req.session.lead.id_clie : null;

    if (!id_clie) {
        return res.status(401).json({ success: false, error: "Sessão expirada." });
    }

    try {
        console.log(`[NODE] Solicitando agendamento da Sprint ${id_sprn} para o Backend...`);

        // 1. O Node apenas repassa os dados para o Python (API_BASE_URL)
        const response = await axios.post(`${API_BASE_URL}/client/update-sprint-date`, {
            id_sprn: id_sprn,
            data_inicio: data_inicio,
            id_clie: id_clie
        });

        // 2. Retorna a resposta vinda do Python para o Front-end
        res.json(response.data);

    } catch (err) {
        console.error("❌ Erro na ponte Node->Python:", err.message);
        const errorMsg = err.response?.data?.error || "Erro ao processar agendamento no servidor de dados.";
        res.status(500).json({ success: false, error: errorMsg });
    }
});

app.put('/api/ctdi_sprn/update-strategic', async (req, res) => {
    try {
        console.log("Encaminhando para o Python:", req.body.id_sprn);

        const response = await axios.put(`${BACKEND_URL}/api/ctdi_sprn/update-strategic`, req.body, {
            timeout: 15000,
            headers: { 'Content-Type': 'application/json', ...flaskRbacHeaders(req) },
        });

        res.json(response.data);
    } catch (error) {
        if (error.response) {
            console.error("O PYTHON RESPONDEU ERRO:", error.response.data);
            res.status(error.response.status || 500).json(error.response.data);
        } else {
            console.error("ERRO DE CONEXÃO COM PYTHON:", error.message);
            res.status(500).json({ error: "O Python está desligado ou inacessível." });
        }
    }
});

// Upload local/S3 do documento de comprovação de métrica (substitui colar URL).
app.post('/api/sprints/metricas/upload', (req, res) => {
    const loggedIn = !!(
        req.session.lead ||
        req.session.isTeam ||
        req.session.user_id ||
        req.session.id_member
    );
    if (!loggedIn) {
        return res.status(401).json({ success: false, error: 'Sessão expirada.' });
    }

    metricasDocUpload.single('documento')(req, res, async (err) => {
        if (err) {
            const message = err.code === 'LIMIT_FILE_SIZE'
                ? 'Arquivo muito grande. Limite: 15 MB.'
                : (err.message || 'Falha no upload.');
            return res.status(400).json({ success: false, error: message });
        }
        if (!req.file) {
            return res.status(400).json({ success: false, error: 'Nenhum arquivo enviado.' });
        }

        try {
            if (cmsS3.isCmsS3Enabled()) {
                const uploaded = await cmsS3.uploadCmsImage(
                    req.file.buffer,
                    req.file.mimetype,
                    req.file.originalname
                );
                return res.json({
                    success: true,
                    url: uploaded.publicUrl,
                    filename: req.file.originalname,
                    storage: 's3',
                });
            }

            const filename = req.file.filename;
            const url = `/uploads/metricas/${filename}`;
            return res.json({
                success: true,
                url,
                filename: req.file.originalname || filename,
                storage: 'local',
            });
        } catch (uploadErr) {
            console.error('[Métrica Upload] Erro:', uploadErr.message);
            return res.status(500).json({
                success: false,
                error: 'Falha ao persistir o documento.',
            });
        }
    });
});

// Governança Vetor 1 — comprovação e avaliação de métricas + DoD
app.post('/api/sprints/metricas/comprovar', async (req, res) => {
    try {
        const response = await axios.post(`${BACKEND_URL}/api/sprints/metricas/comprovar`, req.body, {
            headers: { 'Content-Type': 'application/json', ...flaskRbacHeaders(req) },
            timeout: 15000,
        });
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            console.error('Erro comprovar métrica:', error.message);
            res.status(500).json({ error: 'Erro ao conectar com o motor Python.' });
        }
    }
});

app.post('/api/sprints/metricas/submeter-analise', async (req, res) => {
    try {
        const response = await axios.post(`${BACKEND_URL}/api/sprints/metricas/submeter-analise`, req.body, {
            headers: { 'Content-Type': 'application/json', ...flaskRbacHeaders(req) },
            timeout: 90000,
        });
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            console.error('Erro submeter-analise métrica:', error.message);
            res.status(500).json({ error: 'Erro ao conectar com o motor Python.' });
        }
    }
});

app.post('/api/sprints/metricas/avaliar', async (req, res) => {
    try {
        const response = await axios.post(`${BACKEND_URL}/api/sprints/metricas/avaliar`, req.body, {
            headers: { 'Content-Type': 'application/json', ...flaskRbacHeaders(req) },
            timeout: 15000,
        });
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            console.error('Erro avaliar métrica:', error.message);
            res.status(500).json({ error: 'Erro ao conectar com o motor Python.' });
        }
    }
});

app.post('/api/sprints/dod/atualizar', async (req, res) => {
    try {
        const response = await axios.post(`${BACKEND_URL}/api/sprints/dod/atualizar`, req.body, {
            headers: { 'Content-Type': 'application/json', ...flaskRbacHeaders(req) },
            timeout: 15000,
        });
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            console.error('Erro atualizar DoD:', error.message);
            res.status(500).json({ error: 'Erro ao conectar com o motor Python.' });
        }
    }
});

app.post('/api/sprints/fechar', async (req, res) => {
    try {
        const response = await axios.post(`${BACKEND_URL}/api/sprints/fechar`, req.body, {
            headers: { 'Content-Type': 'application/json', ...flaskRbacHeaders(req) },
            timeout: 15000,
        });
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            console.error('Erro fechar sprint:', error.message);
            res.status(500).json({ error: 'Erro ao conectar com o motor Python.' });
        }
    }
});

app.post('/api/sprints/revisao-consultor/solicitar', async (req, res) => {
    try {
        const response = await axios.post(`${BACKEND_URL}/api/sprints/revisao-consultor/solicitar`, req.body, {
            headers: { 'Content-Type': 'application/json', ...flaskRbacHeaders(req) },
            timeout: 15000,
        });
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            res.status(500).json({ error: 'Erro ao conectar com o motor Python.' });
        }
    }
});

app.post('/api/sprints/revisao-consultor/finalizar', async (req, res) => {
    try {
        const response = await axios.post(`${BACKEND_URL}/api/sprints/revisao-consultor/finalizar`, req.body, {
            headers: { 'Content-Type': 'application/json', ...flaskRbacHeaders(req) },
            timeout: 15000,
        });
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            res.status(500).json({ error: 'Erro ao conectar com o motor Python.' });
        }
    }
});

// --- ROTA DE TELEMETRIA DO ECOSSISTEMA (PONTE PARA O PYTHON) ---
app.get('/api/admin/monitor-genese-data', async (req, res) => {
    // 1. Segurança: Somente Admin acessa
    if (!req.session.isAdmin) {
        return res.status(403).json({ error: 'Acesso negado' });
    }

    try {
        console.log(`[NODE] Solicitando Pulso do Ecossistema ao Backend Python...`);

        // 2. Chama o Python (API_BASE_URL) que tem a chave do banco
        const response = await axios.get(`${API_BASE_URL}/admin/monitor-genese-data`);

        // 3. Devolve o JSON vindo do Python para o seu Frontend EJS
        res.json(response.data);

    } catch (err) {
        console.error("❌ Erro na ponte de telemetria:", err.message);
        res.status(500).json({ error: "Erro ao conectar com o motor de dados." });
    }
});

// Ponte NOC Multi-Agentes (SysAdmin): métricas operacionais dos 4 agentes de IA
app.get('/api/admin/agentes/metricas', async (req, res) => {
    if (!req.session.isAdmin) {
        return res.status(403).json({ success: false, error: 'Acesso negado' });
    }
    try {
        const response = await axios.get(`${API_BASE_URL}/admin/agentes/metricas`);
        res.status(response.status).json(response.data);
    } catch (err) {
        if (err.response) {
            res.status(err.response.status).json(err.response.data);
        } else {
            console.error("❌ Erro na ponte do NOC de Agentes:", err.message);
            res.status(500).json({ success: false, error: "Erro ao conectar com o motor de métricas dos agentes." });
        }
    }
});

// Rota de ponte para os detalhes da Sprint
app.get('/api/sprint_details/:id', async (req, res) => {
    try {
        const id = req.params.id.replace(':', ''); // Limpeza de segurança
        const response = await axios.get(`${BACKEND_URL}/api/sprint_details/${id}`, {
            headers: { ...flaskRbacHeaders(req) },
            timeout: 15000,
        });
        res.json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            res.status(500).json({ error: "Erro ao conectar com o motor Python" });
        }
    }
});

// Contexto institucional atualizado do banco (inclui moderações da IA)
app.get('/api/client/context/:id_clie', async (req, res) => {
    try {
        const idClie = parseInt(req.params.id_clie, 10);
        if (!idClie) {
            return res.status(400).json({ error: 'id_clie inválido.' });
        }

        const isAdmin = req.session.isTeam || req.session.isAdmin;
        const idSessao = req.session.user_id || req.session.lead?.id_clie;
        if (!isAdmin && String(idSessao) !== String(idClie)) {
            return res.status(403).json({ error: 'Acesso negado.' });
        }

        const response = await axios.get(`${API_BASE_URL}/ctdi_clie/${idClie}`);
        return res.json(response.data || {});
    } catch (error) {
        const statusCode = error.response?.status || 500;
        const errorData = error.response?.data || { error: 'Erro ao buscar contexto do cliente.' };
        return res.status(statusCode).json(errorData);
    }
});

// Rota gravação modal clientes (dados de contexto) - INTEGRADA À MÁQUINA DE ESTADOS
app.post('/api/client/update-context', async (req, res) => {
    try {
        console.log(">>> [NODE] Recebido dados do Lead. Repassando para o Python...");

        const payload = { ...(req.body || {}) };
        if (!payload.id_clie) {
            payload.id_clie = req.session.lead?.id_clie || req.session.user_id || null;
        }

        // 1. Repassa o payload para o endpoint do Python
        const response = await axios.post(`${API_BASE_URL}/client/update-context`, payload);

        // 🎯 EVOLUÇÃO DA MÁQUINA DE ESTADOS:
        // Se quem estiver salvando for o cliente logado (LEAD), avançamos o ponteiro de status
        if (req.session && req.session.lead) {
            const statusAtual = String(req.session.lead.status_ia || '').toUpperCase().trim();

            // Só avançamos se o status for o inicial de projeto liberado ou pendente
            if (statusAtual === 'PROJETO OK' || statusAtual === 'AGUARDANDO CONTEXTO' || statusAtual === '') {
                const id_matu = req.session.id_matu || req.session.lead.id_matu;

                console.log(`⚡ [MÁQUINA DE ESTADOS] Evoluindo ID_MATU ${id_matu} para CONTEXTO OK no Postgres...`);

                // Atualiza fisicamente a tabela ctdi_matu no Python usando o endpoint genérico de CRUD
                await axios.put(`${API_BASE_URL}/ctdi_matu/${id_matu}`, {
                    status_ia: 'CONTEXTO OK'
                });

                // Atualiza a memória da sessão do Node para o EJS ler o status novo no reload
                req.session.lead.status_ia = 'CONTEXTO OK';
            }

            const ctxKeys = [
                'dados_mercado', 'dados_etnograficos', 'clima_organizacional',
                'moderacao_dados_mercado', 'moderacao_dados_etnograficos', 'moderacao_clima_organizacional',
                'bairro_clie', 'cidade_clie', 'estado_clie', 'tipo_ensino', 'qtd_alunos',
                'localizacao_sede', 'rede_ensino',
            ];
            ctxKeys.forEach((key) => {
                const val = req.body[key];
                if (val === undefined || val === null) return;
                if (key.startsWith('moderacao_') && !String(val).trim()) return;
                req.session.lead[key] = val;
            });
        }

        // 💾 PERSISTÊNCIA DA SESSÃO: Garante a gravação física dos dados antes de responder a UI
        req.session.save((err) => {
            if (err) {
                console.error("❌ [NODE] Erro ao salvar sessão após update-context:", err);
            }
            // Devolve o status 200 original com os dados do Python
            res.status(200).json(response.data);
        });

    } catch (error) {
        console.error("❌ [NODE] Falha ao comunicar com o Python:", error.message);

        const statusCode = error.response ? error.response.status : 500;
        const errorData = error.response ? error.response.data : { error: "Erro de conexão com o Backend Python." };

        res.status(statusCode).json(errorData);
    }
});

// Ponte para BUSCAR o histórico de cerimônias
app.get('/api/cerimonias/:id', async (req, res) => {
    try {
        const id = req.params.id;
        const response = await axios.get(`${BACKEND_URL}/api/cerimonias/${id}`);
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ error: "Erro ao buscar ritos no motor Python" });
    }
});

// Ponte para REGISTRAR uma nova cerimônia
app.post('/api/cerimonias/registrar', async (req, res) => {
    try {
        const response = await axios.post(`${BACKEND_URL}/api/cerimonias/registrar`, req.body);
        res.status(response.status).json(response.data);
    } catch (error) {
        res.status(500).json({ error: "Erro ao registrar rito no motor Python" });
    }
});

app.post('/api/evidencias/vincular', async (req, res) => {
    const finalUrl = `${API_BASE_URL}/evidencias/vincular`;

    try {
        const response = await axios.post(finalUrl, req.body);
        // Retorna exatamente o que o Python mandou (201 Sucesso)
        res.status(response.status).json(response.data);
    } catch (error) {
        const statusCode = error.response ? error.response.status : 500;
        const errorData = error.response ? error.response.data : { error: "Erro de conexão" };

        console.error("❌ Erro na ponte:", errorData);
        res.status(statusCode).json(errorData);
    }
});

app.get('/api/evidencias/:id_sprn', async (req, res) => {
    try {
        const id_sprn = req.params.id_sprn;
        // Repassa a chamada para o Python na porta 5000
        const response = await axios.get(`${BACKEND_URL}/api/evidencias/${id_sprn}`);
        res.json(response.data);
    } catch (error) {
        console.error("❌ Erro na ponte GET evidências:", error.message);
        res.status(500).json({ error: "Erro ao buscar evidências no motor Python" });
    }
});

app.delete('/api/evidencias/:id', async (req, res) => {
    try {
        const response = await axios.delete(`${API_BASE_URL}/evidencias/${req.params.id}`);
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ error: "Erro ao deletar" });
    }
});

// Pontes do subsistema DX (blueprint Flask em /inovador) — DEVEM ficar ANTES do proxy genérico
app.post('/api/mesa-inovacao/gerar-preview', async (req, res) => {
    try {
        const payload = { ...(req.body || {}), tipo_mesa: 'organizacional' };
        const response = await axios.post(`${BACKEND_URL}/inovador/api/acoes/gerar-preview`, payload);
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            console.error('❌ Erro na ponte Mesa Org IA:', error.message);
            res.status(500).json({ status: 'error', message: 'Erro de comunicação com o motor de IA.' });
        }
    }
});

const proxyMesaOrgNotas = async (req, res, method, pathSuffix, body) => {
    try {
        const url = `${BACKEND_URL}/inovador/api/mesa-org/notas${pathSuffix || ''}`;
        const config = { params: req.query };
        let response;
        if (method === 'GET') {
            response = await axios.get(url, config);
        } else if (method === 'POST') {
            response = await axios.post(url, body !== undefined ? body : req.body, config);
        } else if (method === 'DELETE') {
            response = await axios.delete(url, config);
        } else {
            return res.status(405).json({ status: 'error', message: 'Método não suportado.' });
        }
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            console.error('❌ Erro na ponte Mesa Org notas:', error.message);
            res.status(500).json({ status: 'error', message: 'Erro de comunicação com o backend.' });
        }
    }
};

app.get('/api/mesa-inovacao/notas', (req, res) => proxyMesaOrgNotas(req, res, 'GET'));
app.post('/api/mesa-inovacao/notas', (req, res) => proxyMesaOrgNotas(req, res, 'POST'));
app.delete('/api/mesa-inovacao/notas', (req, res) => proxyMesaOrgNotas(req, res, 'DELETE'));
app.post('/api/mesa-inovacao/notas/incubar', (req, res) => proxyMesaOrgNotas(req, res, 'POST', '/incubar'));

async function proxyEsimMesaBacklog(req, res, method, pathSuffix = '') {
    const backendPath = `/api/esim/mesa-backlog${pathSuffix}`;
    try {
        const config = { timeout: FLASK_HTTP_TIMEOUT_MS };
        const response = method === 'GET'
            ? await axios.get(`${BACKEND_URL}${backendPath}`, { ...config, params: req.query })
            : await axios.post(`${BACKEND_URL}${backendPath}`, req.body, config);
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            const action = method === 'GET' ? 'consultar' : 'marcar';
            console.error(`❌ Erro ao ${action} backlog eSIM:`, error.message);
            res.status(502).json({ status: 'error', message: `Falha ao ${action} backlog eSIM no backend.` });
        }
    }
}

app.get('/api/esim/mesa-backlog', (req, res) => proxyEsimMesaBacklog(req, res, 'GET'));
app.post('/api/esim/mesa-backlog/consumir', (req, res) => proxyEsimMesaBacklog(req, res, 'POST', '/consumir'));

// Aliases legados — Base Mobile
app.get('/api/basemobile/mesa-backlog', (req, res) => proxyEsimMesaBacklog(req, res, 'GET'));
app.post('/api/basemobile/mesa-backlog/consumir', (req, res) => proxyEsimMesaBacklog(req, res, 'POST', '/consumir'));

app.post('/api/sprints/importar', async (req, res) => {
    try {
        const response = await axios.post(`${BACKEND_URL}/inovador/api/sprints/importar`, req.body);
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            console.error("❌ Erro na ponte de importação DX:", error.message);
            res.status(500).json({ success: false, error: "Erro de comunicação com o motor Python na importação DX." });
        }
    }
});

app.put('/api/sprints/planejar-dx', async (req, res) => {
    try {
        const response = await axios.put(`${BACKEND_URL}/inovador/api/sprints/planejar-dx`, req.body);
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            console.error("❌ Erro na ponte de planejamento DX:", error.message);
            res.status(500).json({ success: false, error: "Erro de comunicação com o motor Python no planejamento DX." });
        }
    }
});

app.get('/api/sprints/blocos-pipeline', async (req, res) => {
    try {
        const response = await axios.get(`${BACKEND_URL}/inovador/api/sprints/blocos-pipeline`, {
            params: req.query
        });
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            res.status(500).json({ keys: [], error: 'Erro ao consultar pipeline de blocos.' });
        }
    }
});

app.post('/api/sprints/devolver-relatorio', async (req, res) => {
    try {
        const response = await axios.post(`${BACKEND_URL}/inovador/api/sprints/devolver-relatorio`, req.body);
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            res.status(500).json({ success: false, error: 'Erro ao devolver sprint ao backlog do relatório.' });
        }
    }
});

app.get('/api/squads/cliente', async (req, res) => {
    try {
        const response = await axios.get(`${BACKEND_URL}/inovador/api/squads/cliente`, {
            params: req.query
        });
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            res.status(500).json({ status: 'error', message: 'Erro ao buscar squads do cliente.' });
        }
    }
});

app.get('/api/blocos/buscar', async (req, res) => {
    try {
        const response = await axios.get(`${BACKEND_URL}/inovador/api/blocos/buscar`, {
            params: req.query
        });
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            res.status(500).json({ status: 'error', message: 'Erro ao buscar blocos metodológicos.' });
        }
    }
});

app.put('/api/sprints/status-dnd', async (req, res) => {
    try {
        const response = await axios.put(`${BACKEND_URL}/inovador/api/sprints/status-dnd`, req.body);
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            console.error("❌ Erro na ponte de status DnD:", error.message);
            res.status(500).json({ success: false, error: "Erro de comunicação com o motor Python no status DnD." });
        }
    }
});

// Ponte do Cockpit de Gestão — dados consolidados para os gráficos do Panorama Executivo
app.get('/api/dashboard/consolidado', async (req, res) => {
    try {
        const response = await axios.get(`${BACKEND_URL}/api/dashboard/consolidado`, {
            params: req.query
        });
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            console.error("❌ Erro na ponte do Dashboard Consolidado:", error.message);
            res.status(500).json({ success: false, error: "Erro de comunicação com o motor Python no Dashboard." });
        }
    }
});

// Ponte da Agenda Executiva — eventos e bloco de notas
app.get('/api/agenda-eventos', async (req, res) => {
    try {
        const response = await axios.get(`${BACKEND_URL}/api/agenda-eventos`, { params: req.query });
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            console.error('❌ Erro na ponte agenda-eventos GET:', error.message);
            res.status(500).json({ success: false, error: 'Erro de comunicação com o motor Python na Agenda.' });
        }
    }
});

app.post('/api/agenda-eventos', async (req, res) => {
    try {
        const response = await axios.post(`${BACKEND_URL}/api/agenda-eventos`, req.body);
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            console.error('❌ Erro na ponte agenda-eventos POST:', error.message);
            res.status(500).json({ success: false, error: 'Erro de comunicação com o motor Python na Agenda.' });
        }
    }
});

app.get('/api/agenda-eventos/:id', async (req, res) => {
    try {
        const response = await axios.get(`${BACKEND_URL}/api/agenda-eventos/${req.params.id}`);
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            res.status(500).json({ success: false, error: 'Erro de comunicação com o motor Python na Agenda.' });
        }
    }
});

app.put('/api/agenda-eventos/:id', async (req, res) => {
    try {
        const response = await axios.put(`${BACKEND_URL}/api/agenda-eventos/${req.params.id}`, req.body);
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            res.status(500).json({ success: false, error: 'Erro de comunicação com o motor Python na Agenda.' });
        }
    }
});

app.delete('/api/agenda-eventos/:id', async (req, res) => {
    try {
        const response = await axios.delete(`${BACKEND_URL}/api/agenda-eventos/${req.params.id}`);
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            res.status(500).json({ success: false, error: 'Erro de comunicação com o motor Python na Agenda.' });
        }
    }
});

// Ponte do Consultor Interno (Fast Track) — gera Sprint avulsa via IA
app.post('/api/consultor-interno/gerar-sprint-avulsa', async (req, res) => {
    try {
        const response = await axios.post(`${BACKEND_URL}/api/consultor-interno/gerar-sprint-avulsa`, req.body);
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            console.error("❌ Erro na ponte do Consultor Interno:", error.message);
            res.status(500).json({ success: false, error: "Erro de comunicação com o motor de IA." });
        }
    }
});

// Ponte IA Master — assessment conversacional (antes do proxy genérico)
app.post('/api/assessment/ia-master/turn', async (req, res) => {
    try {
        const response = await axios.post(`${BACKEND_URL}/api/assessment/ia-master/turn`, req.body, {
            timeout: 60000,
        });
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            console.error('❌ Erro na ponte IA Master turn:', error.message);
            res.status(503).json({
                status: 'error',
                message: 'Motor IA Master indisponível. Reinicie o backend Flask.',
            });
        }
    }
});

app.get('/api/assessment/ia-master/coverage/:id_matu', async (req, res) => {
    try {
        const response = await axios.get(
            `${BACKEND_URL}/api/assessment/ia-master/coverage/${req.params.id_matu}`,
            { params: req.query, timeout: 15000 }
        );
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            console.error('❌ Erro na ponte IA Master coverage:', error.message);
            res.status(503).json({ status: 'error', message: error.message });
        }
    }
});

// Ponte do Agente Moderador de Contexto (Bloco 2 — ecossistema)
app.post('/api/ai/moderator/contexto', async (req, res) => {
    try {
        const response = await axios.post(`${BACKEND_URL}/api/ai/moderator/contexto`, req.body, {
            timeout: 35000,
        });
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            console.error('❌ Erro na ponte do Moderador de Contexto:', error.message);
            res.status(500).json({ error: 'Erro de comunicação com o agente moderador de IA.' });
        }
    }
});

// Ponte do Modulador IA (O Juiz) — avaliação síncrona de evidência vs. DoD.
// DEVE ficar ANTES do proxy genérico /api/:entity/:id para não ser capturada por ele.
app.post('/api/modulador/avaliar', async (req, res) => {
    try {
        const response = await axios.post(`${BACKEND_URL}/api/modulador/avaliar`, req.body);
        res.status(response.status).json(response.data);
    } catch (error) {
        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            console.error("❌ Erro na ponte do Modulador IA:", error.message);
            res.status(500).json({ success: false, error: "Erro de comunicação com o motor de IA (Modulador)." });
        }
    }
});

// ==================================================================
// 8. PONTE GENÉRICA PARA CRUD (CORRIGIDA PARA NODE v24+)
// ==================================================================
const proxyToBackend = async (req, res, targetUrl) => {
    // 🔍 INSPEÇÃO DA PONTE DE REDE
    console.log(`\n==================================================`);
    console.log(`🎛️ [PONTE CRUD DISPARADA]`);
    console.log(`| Método: ${req.method}`);
    console.log(`| Redirecionando para o Python em: ${targetUrl}`);
    console.log(`| Dados originais recebidos no req.body:`);
    console.log(JSON.stringify(req.body, null, 2));
    console.log(`==================================================\n`);

    try {
        const response = await axios({
            method: req.method,
            url: targetUrl,
            data: req.body,
            params: req.query,
            headers: { 'Content-Type': 'application/json' }
        });

        console.log(`🟢 [PYTHON SUCESSO] Resposta devolvida pelo Flask: Status ${response.status}`);
        res.status(response.status).json(response.data);
    } catch (error) {
        console.log(`🔴 [PYTHON ERRO] O motor Flask rejeitou a requisição.`);
        if (error.response) {
            console.error('Dados do Erro Python:', JSON.stringify(error.response.data, null, 2));
            res.status(error.response.status).json(error.response.data);
        } else {
            console.error('Mensagem de Falha de Conexão:', error.message);
            res.status(500).json({ error: 'Erro de comunicação com o backend Python.' });
        }
    }
};

// Rota para Listagem e Criação (sem ID)
app.all('/api/:entity', async (req, res) => {
    const targetUrl = `${API_BASE_URL}/${req.params.entity}`;
    await proxyToBackend(req, res, targetUrl);
});

app.all('/api/:entity/:id', async (req, res) => {
    // Se a requisição chegou aqui, é porque não bateu em nenhuma rota acima
    console.log(`[SERVER] Rota GENÉRICA capturou: /api/${req.params.entity}/${req.params.id}`);
    const targetUrl = `${API_BASE_URL}/${req.params.entity}/${req.params.id}`;
    await proxyToBackend(req, res, targetUrl);
});

/////////////Pontes para as ROTINAS ESTRATÉGICAS//////////////////////////////////////////////
// Matriz canônica global OKR (baseline MudaEdu)
app.get('/api/estrategia/matriz-okr', async (req, res) => {
    try {
        const response = await axios.get(`${BACKEND_URL}/api/estrategia/matriz-okr`);
        res.json(response.data);
    } catch (error) {
        console.error('❌ Erro na ponte matriz OKR:', error.message);
        res.status(500).json({ error: 'Erro ao buscar matriz canônica OKR.' });
    }
});

app.get('/api/estrategia/objetivo/:objetivo_id', async (req, res) => {
    try {
        const response = await axios.get(`${BACKEND_URL}/api/estrategia/objetivo/${req.params.objetivo_id}`);
        res.status(response.status).json(response.data);
    } catch (error) {
        res.status(error.response?.status || 500).json(error.response?.data || { error: error.message });
    }
});

app.get('/api/estrategia/resumo-okr', async (req, res) => {
    try {
        const response = await axios.get(`${BACKEND_URL}/api/estrategia/resumo-okr`, { params: req.query });
        res.status(response.status).json(response.data);
    } catch (error) {
        res.status(error.response?.status || 500).json(error.response?.data || { error: error.message });
    }
});

app.get('/api/estrategia/objetivo-cliente/:id_obj_dt', async (req, res) => {
    try {
        const response = await axios.get(`${BACKEND_URL}/api/estrategia/objetivo-cliente/${req.params.id_obj_dt}`);
        res.status(response.status).json(response.data);
    } catch (error) {
        res.status(error.response?.status || 500).json(error.response?.data || { error: error.message });
    }
});

app.patch('/api/estrategia/objetivo-cliente/:id_obj_dt', async (req, res) => {
    try {
        const response = await axios.patch(
            `${BACKEND_URL}/api/estrategia/objetivo-cliente/${req.params.id_obj_dt}`,
            req.body
        );
        res.status(response.status).json(response.data);
    } catch (error) {
        res.status(error.response?.status || 500).json(error.response?.data || { error: error.message });
    }
});

app.patch('/api/estrategia/kr-cliente/:id_kr', async (req, res) => {
    try {
        const response = await axios.patch(
            `${BACKEND_URL}/api/estrategia/kr-cliente/${req.params.id_kr}`,
            req.body
        );
        res.status(response.status).json(response.data);
    } catch (error) {
        res.status(error.response?.status || 500).json(error.response?.data || { error: error.message });
    }
});

app.get('/api/estrategia/niveis-implementacao', async (req, res) => {
    try {
        const response = await axios.get(`${BACKEND_URL}/api/estrategia/niveis-implementacao`);
        res.status(response.status).json(response.data);
    } catch (error) {
        res.status(error.response?.status || 500).json(error.response?.data || { error: error.message });
    }
});

app.get('/api/estrategia/krs-por-sprint', async (req, res) => {
    try {
        const response = await axios.get(`${BACKEND_URL}/api/estrategia/krs-por-sprint`, { params: req.query });
        res.status(response.status).json(response.data);
    } catch (error) {
        res.status(error.response?.status || 500).json(error.response?.data || { error: error.message });
    }
});

app.get('/api/estrategia/cascata-okr-atividade', async (req, res) => {
    try {
        const response = await axios.get(`${BACKEND_URL}/api/estrategia/cascata-okr-atividade`, { params: req.query });
        res.status(response.status).json(response.data);
    } catch (error) {
        res.status(error.response?.status || 500).json(error.response?.data || { error: error.message });
    }
});

// Ponte para buscar a árvore completa de OKR estruturada do Cliente
app.get('/api/okr/consolidado/:id_clie', async (req, res) => {
    try {
        const id_clie = req.params.id_clie;
        const response = await axios.get(`${BACKEND_URL}/api/okr/consolidado?id_clie=${id_clie}`);
        res.json(response.data);
    } catch (error) {
        console.error("❌ Erro na ponte de consolidação OKR:", error.message);
        res.status(500).json({ error: "Erro ao buscar dados de planejamento estratégico no motor Python." });
    }
});

// Ponte para registrar novos Direcionadores (Nível 1)
app.post('/api/okr/direcionadores', async (req, res) => {
    try {
        const response = await axios.post(`${BACKEND_URL}/api/okr/direcionadores`, req.body);
        res.status(response.status).json(response.data);
    } catch (error) {
        res.status(500).json({ error: "Erro ao registrar direcionador no motor Python." });
    }
});

// Ponte para registrar novos Objetivos de TD (Nível 2)
app.post('/api/okr/objetivos', async (req, res) => {
    try {
        const response = await axios.post(`${BACKEND_URL}/api/okr/objetivos`, req.body);
        res.status(response.status).json(response.data);
    } catch (error) {
        res.status(500).json({ error: "Erro ao vincular objetivo no motor Python." });
    }
});

// Ponte para registrar novos Key Results (Nível 3)
app.post('/api/okr/krs', async (req, res) => {
    try {
        const response = await axios.post(`${BACKEND_URL}/api/okr/krs`, req.body);
        res.status(response.status).json(response.data);
    } catch (error) {
        res.status(500).json({ error: "Erro ao estabelecer KR no motor Python." });
    }
});

// Ponte para salvar as Atividades da Sprint (Nível 4)
app.post('/api/okr/atividades', async (req, res) => {
    try {
        const response = await axios.post(`${BACKEND_URL}/api/okr/atividades`, req.body);
        res.status(response.status).json(response.data);
    } catch (error) {
        res.status(500).json({ error: "Erro ao registrar atividade de sprint no motor Python." });
    }
});

// Ponte para ATUALIZAR (PUT) qualquer entidade do bloco estratégico (Níveis 1, 2, 3 e 4)
app.put('/api/okr/:entity/:id', async (req, res) => {
    try {
        const { entity, id } = req.params;
        const response = await axios.put(`${BACKEND_URL}/api/okr/${entity}/${id}`, req.body);
        res.status(response.status).json(response.data);
    } catch (error) {
        console.error("❌ Erro na ponte PUT de manutenção OKR:", error.message);
        const status = error.response?.status || 500;
        const payload = error.response?.data || { error: "Erro ao atualizar dados no motor Python." };
        res.status(status).json(payload);
    }
});

// Ponte para DELETAR (DELETE) qualquer entidade do bloco estratégico em cascata
app.delete('/api/okr/:entity/:id', async (req, res) => {
    try {
        const { entity, id } = req.params;
        const response = await axios.delete(`${BACKEND_URL}/api/okr/${entity}/${id}`);
        res.status(response.status).json(response.data);
    } catch (error) {
        console.error("❌ Erro na ponte DELETE de manutenção OKR:", error.message);
        res.status(500).json({ error: "Erro ao deletar dados no motor Python." });
    }
});


// Ponte corrigida para buscar os membros do time filtrados por Squad (com RBAC)
app.get('/api/ctdi_team', (req, res) => proxyFlaskRbac(req, res, 'GET', '/api/ctdi_team'));

app.post('/api/ctdi_team', (req, res) => proxyFlaskRbac(req, res, 'POST', '/api/ctdi_team'));
app.put('/api/ctdi_team/:id', (req, res) => proxyFlaskRbac(req, res, 'PUT', `/api/ctdi_team/${req.params.id}`));
app.delete('/api/ctdi_team/:id', (req, res) => proxyFlaskRbac(req, res, 'DELETE', `/api/ctdi_team/${req.params.id}`));

// Comentários do gestor na árvore OKR
app.get('/api/okr/comentarios', async (req, res) => {
    try {
        const response = await axios.get(`${BACKEND_URL}/api/okr/comentarios`, { params: req.query });
        res.status(response.status).json(response.data);
    } catch (error) {
        res.status(error.response?.status || 500).json(error.response?.data || { error: 'Erro ao buscar comentários.' });
    }
});

app.post('/api/okr/comentarios', async (req, res) => {
    try {
        const response = await axios.post(`${BACKEND_URL}/api/okr/comentarios`, req.body);
        res.status(response.status).json(response.data);
    } catch (error) {
        res.status(error.response?.status || 500).json(error.response?.data || { error: 'Erro ao salvar comentário.' });
    }
});

const CATALOGO_DIRECIONADORES_OKR = [
    { slug: 'digitalizacao_organizacional', nome: 'Digitalização Organizacional', meta_financeira: 'reducao_custo', meta_label: 'Redução de Custo', icone: '📉', ordem: 0 },
    { slug: 'engajamento_comunidade', nome: 'Engajamento da Comunidade', meta_financeira: 'aumento_receita', meta_label: 'Aumento de Receita', icone: '💰', ordem: 1 },
    { slug: 'capacitacao_docente', nome: 'Capacitação Docente', meta_financeira: 'reducao_custo', meta_label: 'Redução de Custo', icone: '📉', ordem: 2 },
    { slug: 'prontidao_tecnologica', nome: 'Prontidão Tecnológica', meta_financeira: 'reducao_custo', meta_label: 'Redução de Custo', icone: '📉', ordem: 3 },
    { slug: 'novos_modelos_negocio', nome: 'Novos Modelos de Negócio', meta_financeira: 'aumento_receita', meta_label: 'Aumento de Receita', icone: '💰', ordem: 4 },
];

function enrichDirecionadorOkr(direc) {
    const catalog = CATALOGO_DIRECIONADORES_OKR.find((c) => c.slug === direc.slug_catalogo)
        || CATALOGO_DIRECIONADORES_OKR.find((c) => c.nome === direc.nome_direc);
    const metaFin = direc.meta_financeira || catalog?.meta_financeira || 'reducao_custo';
    return {
        ...direc,
        is_catalogo_fixo: !!(direc.slug_catalogo || catalog),
        slug_catalogo: direc.slug_catalogo || catalog?.slug || null,
        icone: direc.icone || catalog?.icone || '🎯',
        meta_label: catalog?.meta_label || (metaFin === 'aumento_receita' ? 'Aumento de Receita' : 'Redução de Custo'),
        meta_financeira: metaFin,
        ordem_catalogo: catalog ? catalog.ordem : 999,
    };
}

function calcularGamificacaoOkr(direcionadores) {
    let totalObj = 0;
    let totalKr = 0;
    let somaPct = 0;
    let countPct = 0;
    let fixosComObj = 0;

    direcionadores.forEach((d) => {
        totalObj += d.objetivos.length;
        if (d.is_catalogo_fixo && d.objetivos.length > 0) fixosComObj += 1;
        d.objetivos.forEach((o) => {
            o.krs.forEach((kr) => {
                totalKr += 1;
                const totalMeta = Math.abs(kr.valor_alvo - kr.valor_inicial);
                const atualProg = Math.abs(kr.valor_atual - kr.valor_inicial);
                const pct = totalMeta > 0 ? Math.min(100, (atualProg / totalMeta) * 100) : 0;
                somaPct += pct;
                countPct += 1;
            });
        });
    });

    const progressoMedio = countPct > 0 ? Math.round(somaPct / countPct) : 0;
    const xp = totalKr * 40 + totalObj * 75 + fixosComObj * 100;
    const nivel = Math.max(1, Math.floor(xp / 400) + 1);
    const xpNoNivel = xp % 400;
    const badges = [];
    if (totalKr >= 1) badges.push({ icon: '🎯', label: 'Primeiro KR', desc: 'Estabeleceu o primeiro resultado-chave.' });
    if (totalObj >= 3) badges.push({ icon: '📐', label: 'Arquiteto TD', desc: 'Três ou mais objetivos de transformação digital.' });
    if (fixosComObj >= 3) badges.push({ icon: '⚡', label: 'Momentum', desc: 'Três pilares MudaEdu com objetivos vinculados.' });
    if (fixosComObj >= 5) badges.push({ icon: '🏆', label: 'Malha Completa', desc: 'Todos os direcionadores fixos com objetivos.' });
    if (progressoMedio >= 50) badges.push({ icon: '🚀', label: 'Meio Caminho', desc: 'Progresso médio dos KRs acima de 50%.' });

    return {
        xp,
        nivel,
        xpNoNivel,
        xpProximo: 400,
        progressoMedio,
        totalObj,
        totalKr,
        fixosComObj,
        totalFixos: 5,
        badges,
    };
}

function calcularProgressoDirecionador(direc) {
    let soma = 0;
    let count = 0;
    direc.objetivos.forEach((o) => {
        o.krs.forEach((kr) => {
            const totalMeta = Math.abs(kr.valor_alvo - kr.valor_inicial);
            const atualProg = Math.abs(kr.valor_atual - kr.valor_inicial);
            soma += totalMeta > 0 ? Math.min(100, (atualProg / totalMeta) * 100) : 0;
            count += 1;
        });
    });
    return count > 0 ? Math.round(soma / count) : 0;
}

/** Readonly só ao inspecionar outro cliente (coach/admin). O próprio gestor com ?id_clie= continua editável. */
function isEstrategiaReadOnly(req, idClieResolved) {
    const q = req.query && req.query.id_clie;
    if (!q) return false;
    const sessionClie =
        req.session.user_id
        || req.session.id_clie
        || (req.session.lead && req.session.lead.id_clie)
        || (req.session.user && req.session.user.id_clie)
        || null;
    if (sessionClie && String(q) === String(sessionClie)) return false;
    if (isSessionAdmin(req)) return true;
    return String(q) !== String(idClieResolved || sessionClie || '');
}


// Rota de Front-End — Matriz OKR Master-Detail (tabela resumo + modal)
app.get('/planejamento-estrategico', async (req, res) => {
    const id_clie = req.query.id_clie
        || req.session.user_id
        || req.session.id_clie
        || (req.session.lead ? req.session.lead.id_clie : null)
        || (req.session.user ? req.session.user.id_clie : null);

    const leadData = req.session.lead || {};
    const userData = req.session.user || req.session.lead || {};

    if (!id_clie) {
        console.error("❌ [SERVER] Tentativa de acesso ao OKR sem id_clie válido.");
        return res.status(403).send("Acesso negado: Sessão inválida ou ID do cliente ausente.");
    }

    attachCoachLocals(req, res, 'estrategia');

    res.render('estrategia-okrs', {
        id_clie: id_clie,
        lead: leadData,
        user: userData,
        readOnly: isEstrategiaReadOnly(req, id_clie),
        pageStylesheet: '/css/estrategia-okrs.css?v=9',
        pageScript: '/js/estrategia-okrs.js?v=9',
        title: "Matriz de Estratégia — OKRs"
    });
});

// Visão gamificada (cockpit por objetivo)
app.get('/planejamento-estrategico/cockpit', async (req, res) => {
    const id_clie = req.query.id_clie
        || req.session.user_id
        || req.session.id_clie
        || (req.session.lead ? req.session.lead.id_clie : null)
        || (req.session.user ? req.session.user.id_clie : null);

    const leadData = req.session.lead || {};
    const userData = req.session.user || req.session.lead || {};

    if (!id_clie) {
        console.error("❌ [SERVER] Tentativa de acesso ao OKR sem id_clie válido.");
        return res.status(403).send("Acesso negado: Sessão inválida ou ID do cliente ausente.");
    }

    try {
        // Log de rastro inequívoco e atualizado
        console.log(`\n>>> [GOVERNANÇA] Carregando árvore estratégica estritamente para o Cliente ID: ${id_clie}`);

        // Consome o endpoint dinâmico passando o ID correto via Query String para o Flask
        const urlFlask = `${BACKEND_URL}/api/okr/consolidado?id_clie=${id_clie}`;
        const response = await axios.get(urlFlask);
        const rows = response.data;

        const direcionadoresMap = {};
        rows.forEach(row => {
            const idDirec = row.id_direc;
            if (!idDirec) return;

            if (!direcionadoresMap[idDirec]) {
                direcionadoresMap[idDirec] = {
                    id_direc: idDirec,
                    nome_direc: row.nome_direc,
                    desc_direc: row.desc_direc,
                    kpi_descricao: row.kpi_descricao || row.direc_kpi || '',
                    meta_receita_alvo: parseFloat(row.meta_receita_alvo) || 0,
                    meta_custo_alvo: parseFloat(row.meta_custo_alvo) || 0,
                    status_direc: row.status_direc,
                    slug_catalogo: row.slug_catalogo || null,
                    meta_financeira: row.meta_financeira || null,
                    icone: row.icone || null,
                    objetivos: {}
                };
            }

            const idObj = row.id_obj_dt;
            if (idObj) {
                if (!direcionadoresMap[idDirec].objetivos[idObj]) {
                    direcionadoresMap[idDirec].objetivos[idObj] = {
                        id_obj_dt: idObj,
                        nome_obj: row.nome_obj,
                        desc_obj: row.desc_obj,
                        kpi_descricao: row.kpi_descricao || row.obj_kpi || '',
                        status_obj: row.status_obj,
                        krs: []
                    };
                }

                if (row.id_kr) {
                    direcionadoresMap[idDirec].objetivos[idObj].krs.push({
                        id_kr: row.id_kr,
                        nome_kr: row.nome_kr,
                        desc_kr: row.desc_kr,
                        kpi_nome: row.kpi_nome || row.kr_kpi || '',
                        valor_inicial: parseFloat(row.valor_inicial) || 0,
                        valor_alvo: parseFloat(row.valor_alvo) || 0,
                        valor_atual: parseFloat(row.valor_atual) || 0,
                        status_kr: row.status_kr
                    });
                }
            }
        });

        let listaDirecionadores = Object.values(direcionadoresMap).map(d => {
            d.objetivos = Object.values(d.objetivos);
            return enrichDirecionadorOkr(d);
        }).map((d) => {
            d.progresso_pct = calcularProgressoDirecionador(d);
            return d;
        }).sort((a, b) => a.ordem_catalogo - b.ordem_catalogo || a.id_direc - b.id_direc);

        const gamificacao = calcularGamificacaoOkr(listaDirecionadores);

        attachCoachLocals(req, res, 'estrategia', { coachData: gamificacao });

        let comentarios = [];
        try {
            const comRes = await axios.get(`${BACKEND_URL}/api/okr/comentarios`, { params: { id_clie } });
            comentarios = comRes.data?.comentarios || [];
        } catch (e) {
            console.warn('Comentários OKR indisponíveis:', e.message);
        }

        const comentariosPorEntidade = {};
        comentarios.forEach((c) => {
            const key = `${c.entidade_tipo}:${c.entidade_id}`;
            if (!comentariosPorEntidade[key]) comentariosPorEntidade[key] = [];
            comentariosPorEntidade[key].push(c);
        });

        res.render('okr', {
            direcionadores: listaDirecionadores,
            gamificacao,
            comentariosPorEntidade,
            id_clie: id_clie,
            lead: leadData,
            user: userData,
            readOnly: isEstrategiaReadOnly(req, id_clie),
            pageStylesheet: '/css/estrategia-okrs.css?v=9',
            title: "Cockpit Estratégico — Planejamento Empresarial"
        });

    } catch (error) {
        console.error("❌ [SERVER ERROR] Falha ao processar e renderizar dados de OKR:", error.message);
        attachCoachLocals(req, res, 'estrategia');
        res.render('okr', {
            direcionadores: [],
            gamificacao: calcularGamificacaoOkr([]),
            comentariosPorEntidade: {},
            id_clie: id_clie,
            lead: leadData,
            user: userData,
            readOnly: isEstrategiaReadOnly(req, id_clie),
            pageStylesheet: '/css/estrategia-okrs.css?v=9',
            title: "Cockpit Estratégico — Planejamento Empresarial"
        });
    }
});


// Rota do Painel de Governança de OKRs (Visão do Administrador)
app.get('/admin/governanca-estrategica', async (req, res) => {
    try {
        // Consome os dados consolidados do motor Python
        const response = await axios.get(`${BACKEND_URL}/api/okr/admin/dashboard`);
        const clientesEstrategia = response.data;

        res.render('okr-admin', {
            clientes: clientesEstrategia,
            title: "Painel de Governança Estratégica - Admin",
            user: req.session.user || { nome: "Administrador" }
        });
    } catch (error) {
        console.error("❌ Erro ao carregar painel admin de OKRs:", error.message);
        res.render('okr-admin', {
            clientes: [],
            title: "Painel de Governança Estratégica - Admin",
            user: req.session.user || { nome: "Administrador" }
        });
    }
});



/////////////////////////// --- INICIALIZAÇÃO --- ////////////////////////////////////////////
// 404 JSON para rotas /bff não mapeadas (evita HTML no fetch do admin CRM)
app.use('/bff', (req, res) => {
    res.status(404).json({
        status: 'error',
        error: `Rota BFF não encontrada: ${req.method} ${req.originalUrl}. Reinicie o servidor Node se acabou de atualizar o código.`
    });
});

// 404 JSON para rotas /api não mapeadas (evita HTML no fetch do frontend)
app.use('/api', (req, res) => {
    res.status(404).json({
        success: false,
        error: `Rota API não encontrada: ${req.method} ${req.originalUrl}`
    });
});

app.listen(PORT, () => {
    console.log(`--------------------------------------------------`);
    console.log(`🚀 SERVIDOR NO AR (Versão Recomposta & Corrigida)`);
    console.log(`📡 Porta Node: ${PORT}`);
    console.log(`🐍 Backend Flask: ${BACKEND_URL}`);
    console.log(`📲 Admin eSIM: http://localhost:${PORT}/admin/esim`);
    console.log(`🏠 Link: http://localhost:${PORT}`);
    console.log(`--------------------------------------------------`);
});