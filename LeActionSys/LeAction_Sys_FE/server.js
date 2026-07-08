const path = require('path');
const axios = require('axios');
const express = require('express');
const expressLayouts = require('express-ejs-layouts');
const session = require('express-session');

// --- DEVOPS: CONFIGURAÇÃO DE AMBIENTE ---
const env = process.env.NODE_ENV || 'development';
require('dotenv').config({ path: `.env.${env}` });

const app = express();
const PORT = process.env.PORT || 3001;

// --- CONFIGURAÇÕES BÁSICAS ---
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, 'public')));

app.use(expressLayouts);
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

// --- CONSTANTES ---
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:5000';
const API_BASE_URL = `${BACKEND_URL}/api`;
const ADMIN_EMAIL = 'sysadmin@leaction.com.br'; // Ajuste conforme seu uso

// --- MIDDLEWARE GLOBAL: VARIÁVEIS PARA AS VIEWS ---
app.use((req, res, next) => {
    res.locals.API_BASE_URL = API_BASE_URL;
    next();
});

// ==================================================================
// 1. GERENCIAMENTO DE SESSÃO (CORRIGIDO E PERMISSIVO)
// ==================================================================
app.use(session({
    secret: 'leaction_segredo_absoluto_2026',
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
// 2. LISTAS DE PERMISSÃO
// ==================================================================
const publicPaths = ['/', '/cadastro', '/login', '/logout', '/termos-de-uso', '/instrucoes-de-uso', '/verificar-email'];
const restrictedPaths = ['/clientes', '/dimensoes', '/fases', '/blocos', '/questoes', '/sprints', '/rodadas', '/maturidades', '/surveys', '/entregaveis', '/movimentos', '/dominios', '/admin', '/teams', '/inteligencia-negocio'];
const leadPaths = ['/avaliacoes', '/diagnostico'];

// ==================================================================
// 3. MIDDLEWARE DE AUTENTICAÇÃO (O PORTEIRO INTELIGENTE)
// ==================================================================
const authMiddleware = (req, res, next) => {
    const currentPath = req.path;

    console.log(`\n[DEBUG ACESSO] ---------------------------------`);
    console.log(`| Rota: ${currentPath}`);
    console.log(`| Sessão ID: ${req.sessionID}`); // <--- CORRIGIDO AQUI
    console.log(`| Lead no Objeto Session: ${req.session.lead ? 'IDENTIFICADO' : 'VAZIO'}`);
    console.log(`| User ID direto: ${req.session.user_id || 'NULO'}`);
    console.log(`------------------------------------------------\n`);

    // A. O "FURA-FILA" (VIP) - Libera estáticos e APIs públicas
    if (publicPaths.includes(currentPath) ||
        currentPath.startsWith('/api/') ||
        currentPath.startsWith('/css/') ||
        currentPath.startsWith('/js/') ||
        currentPath.startsWith('/img/')) {
        return next();
    }

    // B. RECUPERA SESSÃO
    const lead = req.session.lead;
    const isTeam = req.session.isTeam;
    const isLoggedIn = !!(lead || isTeam);
    const isAdmin = isTeam || (lead && lead.email === ADMIN_EMAIL);

    // Injeta no EJS
    res.locals.isLoggedIn = isLoggedIn;
    res.locals.isAdmin = isAdmin;
    //res.locals.lead = lead || (isTeam ? { nome: req.session.user_name || 'Admin' } : null);
    res.locals.user = lead || (isTeam ? { nome: req.session.user_name || 'Admin', role: 'ADMIN' } : null);
    res.locals.lead = res.locals.user; // Mantém o padrão que você já usa

    // C. REGRAS DE BLOQUEIO

    // 1. Visitante
    if (!isLoggedIn) {
        if (req.xhr || req.headers.accept?.indexOf('json') > -1) {
            return res.status(401).json({ error: 'Sessão expirada' });
        }
        return res.redirect('/');
    }

    // 2. Admin (God Mode)
    if (isAdmin) {
        return next();
    }

    // --- AJUSTE AQUI: LIBERAR /teams PARA O LEAD ---
    if (currentPath.startsWith('/teams')) {
        return next(); // Deixa o Lead passar para a página de equipes
    }

    // 3. Cliente em área restrita (Outros caminhos como /admin, /config, etc)
    if (restrictedPaths.some(path => currentPath.startsWith(path))) {
        return res.redirect('/projeto');
    }

    next();
};

app.use(authMiddleware);

// ==================================================================
// NOVAS ROTAS DO PRESURVEY (DEVE FICAR ACIMA DAS ROTAS GENÉRICAS)
// ==================================================================

// Alterado o prefixo de /api/ para /node/ para contornar o desvio do Nginx na AWS
app.post('/node/client/processar-presurvey', async (req, res) => {
    console.log("[SERVER] Tentando processar presurvey para ID:", req.body.id_matu);
    const { id_matu } = req.body;

    try {
        // Usamos o axios para bater no Flask (porta 5000)
        // Certifique-se que BACKEND_URL é 'http://localhost:5000'
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

        res.render('presurvey', {
            lead: flaskResponse.data.lead,
            preData: flaskResponse.data.preData,
            refSetor: flaskResponse.data.refSetor || {},
            insights_ia: flaskResponse.data.insights_ia,
            statusIA: flaskResponse.data.lead.status_ia,
            temProjetoAtivo: false
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
            type: 'LEAD'
        });

        // 2. INSPEÇÃO DOS DADOS (O ponto crítico)
        const data = response.data;
        console.log(">>> [RESPOSTA INTEGRAL DO PYTHON]:", JSON.stringify(data, null, 2));

        // Verificação de segurança: se os IDs não vierem, o redirect vai falhar depois
        if (!data.id_clie || !data.id_matu) {
            console.error("⚠️ [ALERTA] IDs fundamentais ausentes no retorno do Python!");
        }

        const isAdminEmail = (data.email || email) === ADMIN_EMAIL;

        // 3. GRAVAÇÃO NA SESSÃO (Mapeamento explícito)
        req.session.user_id = data.id_clie;
        req.session.user_name = data.nome_clie;
        req.session.id_matu = data.id_matu; // <--- O ID que estava sumindo

        req.session.isTeam = isAdminEmail;
        req.session.role = isAdminEmail ? 'ADMIN' : 'LEAD';
        req.session.isAdmin = isAdminEmail;

        // Armazenamento do papel inicial para governança de rotas internas
        req.session.init_role = data.init_role || 'GENERAL';

        // Objeto consolidado (Lead)
        req.session.lead = {
            id_clie: data.id_clie,
            id_matu: data.id_matu,
            email: data.email || email,
            nome: data.nome_clie,
            hasActiveProject: data.hasActiveProject,
            faseAtual: data.faseAtual,
            role: isAdminEmail ? 'ADMIN' : 'LEAD',
            init_role: data.init_role || 'GENERAL',
            data_geracao_plano: data.data_geracao_plano,
            perfil_lead: data.perfil_lead // Captura o perfil enviado no formulário
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

            let destino = isAdminEmail ? '/admin' : '/projeto';

            // 🎯 O PULO DO GATO: Se for perfil INOVADOR ou papel SOLO, aponta direto para a porta 5000 do Flask
            const papelInicial = String(data.init_role || '').toUpperCase().trim();
            const perfilLead = String(data.perfil_lead || '').toUpperCase().trim();

            if (perfilLead === 'INOVADOR' || papelInicial === 'SOLO') {
                // Despacha o usuário para o Flask passando o id_clie na URL como parâmetro
                destino = `http://localhost:5000/inovador/?id_clie=${data.id_clie}`;
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
app.get('/', (req, res) => {
    // 1. Se já tem sessão, manda pro painel (não perde tempo carregando iframe)
    if (req.session.user_id) {
        if (String(req.session.init_role).toUpperCase() === 'SOLO') {
            return res.redirect('/inovador/dashboard'); // ✨ Redirecionamento persistente recalibrado
        }
        return res.redirect(req.session.isTeam ? '/admin' : '/projeto');
    }

    // 2. Se é visitante, renderiza o index.ejs com a flag de "Deslogado"
    // Isso fará o seu index.ejs show o bloco do Iframe.
    res.render('index', {
        title: 'LeAction - Transformação',
        isLoggedIn: false, // <--- Isso ativa o IF do Iframe no EJS
        isAdmin: false,
        lead: null,
        user: null
    });
});

// PÁGINAS ESTÁTICAS
app.get('/cadastro', (req, res) => res.render('lead-capture', { title: 'Inscrição' }));
app.get('/termos-de-uso', (req, res) => res.render('termos-de-uso', { title: 'Termos de Uso' }));
app.get('/instrucoes-de-uso', (req, res) => res.render('instrucoes-de-uso', { title: 'Guia MVP' }));


// --- ROTA ADMIN (Painel Roxo) ---
app.get('/admin', (req, res) => {
    res.render('index', {
        title: 'Painel Admin',
        isLoggedIn: true,
        isAdmin: true,
        lead: null,
        user: {
            id: req.session.user_id,
            nome: req.session.user_name,
            role: 'ADMIN'
        }
    });
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
            return res.redirect(`http://localhost:5000/inovador/?id_clie=${id_clie}`);
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
            hasProject = journeyData.length > 0;

            console.log(">>> [DB CHECK] Status IA recuperado:", dadosMaturidade.status_ia);
        } else {
            console.log("ℹ️ [INFO] Utilizador sem id_matu (Avaliação Inicial pendente). Ignorando barramento de APIs.");
        }

        // --- UNIFICAÇÃO DE CONTEXTO ---
        const commonContext = {
            ...req.session.lead,
            ...dadosCompletosCliente,
            ...dadosMaturidade,
            id_matu: id_matu,
            id_clie: id_clie,
            nome: req.session.user_name || dadosCompletosCliente.nome_clie,
            role: 'LEAD',
            hasActiveProject: hasProject,
            data_geracao_plano: dadosMaturidade.data_geracao_plano || (hasProject ? (req.session.lead?.data_geracao_plano || true) : null),
            tipo_ensino: dadosCompletosCliente.tipo_ensino || null,
            qtd_alunos: dadosCompletosCliente.qtd_alunos || null,
        };

        // --- ATUALIZAÇÃO DA SESSÃO ---
        req.session.lead = commonContext;

        // ✨ PERSISTÊNCIA SEGURA: Aguarda a gravação física antes de renderizar para evitar colisões no Chrome
        req.session.save((err) => {
            if (err) {
                console.error("❌ Erro ao salvar sessão em /projeto:", err);
            }

            const sprintsAtivas = journeyData.flatMap(onda =>
                (onda.sprints || []).filter(s => s.stat_sprn === 'ativa')
            );

            res.render('index', {
                title: hasProject ? 'Meu Projeto' : 'Diagnóstico',
                isLoggedIn: true,
                isAdmin: false,
                lead: commonContext,
                user: commonContext,
                journey: journeyData,
                sprintsAtivas: sprintsAtivas
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
        res.render('sprint-atual', {
            title: 'Quadro Kanban',
            isLoggedIn: true,
            isAdmin: false,
            lead: req.session.lead,
            user: { nome: req.session.user_name, role: 'LEAD' },
            journey: journeyData // Enviamos a estrutura completa
        });

    } catch (error) {
        console.error("❌ Erro ao carregar Kanban:", error.message);
        res.redirect('/meu-plano');
    }
});

// B. DIAGNÓSTICO (Relatório PDF)
app.get('/diagnostico/:id_matu', async (req, res) => {
    try {
        const response = await axios.get(`${API_BASE_URL}/diagnostico/${req.params.id_matu}`);

        const leadData = req.session.lead || {
            nome: req.session.user_name,
            id_matu: req.params.id_matu
        };

        res.render('diagnosticos', {
            title: 'Diagnóstico',
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
            // Ajustamos o título para o novo padrão
            return res.render('avaliacoes-list', { title: 'Avaliações Iniciais', maturidades: response.data });
        } else if (req.session.lead) {
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
        const questRes = await axios.get(`${API_BASE_URL}/questions_by_dimension`);
        const questions = questRes.data;

        // Modelos contextuais de fallback para novos usuários
        let maturityData = { id_clie: id_clie, status_ia: 'AGUARDANDO CONTEXTO' };
        let savedAnswers = {};

        // 🎯 INTELIGÊNCIA PERMISSIVA: Só batemos nas tabelas ctdi_matu e ctdi_surv se o registro físico já existir no banco!
        if (!ehNovaAvaliacao) {
            const [matuRes, ansRes] = await Promise.all([
                axios.get(`${API_BASE_URL}/ctdi_matu/${id_matu}`),
                axios.get(`${API_BASE_URL}/ctdi_surv/by_maturity/${id_matu}`)
            ]);

            maturityData = matuRes.data || {};
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
const crudPages = ['clientes', 'dimensoes', 'fases', 'blocos', 'questoes', 'sprints', 'rodadas', 'maturidades', 'surveys', 'entregaveis', 'movimentos', 'dominios', 'teams'];
crudPages.forEach(page => {
    app.get(`/${page}`, (req, res) => {
        res.render(page, { title: page.charAt(0).toUpperCase() + page.slice(1) });
    });
});

app.get('/teams', async (req, res) => {
    // 1. Verificação Inteligente: Aceita 'user' (Admin) ou 'lead' (Lead/Consultor)
    const dadosUsuario = req.session.user || req.session.lead;

    if (!dadosUsuario) {
        console.log(">>> [BLOQUEIO] Sessão ausente no Teams.");
        return res.redirect('/');
    }

    try {
        console.log(`>>> [INFO] Buscando projetos para: ${dadosUsuario.email} | Role: ${dadosUsuario.role}`);

        const response = await axios.get(`http://127.0.0.1:5000/api/meus-projetos`, {
            params: {
                role: dadosUsuario.role,
                id_clie: dadosUsuario.id_clie || dadosUsuario.id || null
            }
        });

        // 3. Renderização Unificada: Entrega o que o layout.ejs E a sidebar pedem
        res.render('teams', {
            title: 'Gestão de Time',
            projetos: response.data || [],
            // Unificação para evitar que o clique "morra" no front-end
            user: dadosUsuario,
            lead: dadosUsuario,
            isLoggedIn: true,
            isAdmin: dadosUsuario.role === 'ADMIN',
            API_BASE_URL: process.env.API_BASE_URL || 'http://localhost:3000/api'
        });

    } catch (error) {
        console.error(">>> [ERRO] Falha no backend:", error.message);
        res.render('teams', {
            title: 'Gestão de Time',
            projetos: [],
            user: dadosUsuario,
            lead: dadosUsuario,
            isLoggedIn: true,
            isAdmin: dadosUsuario.role === 'ADMIN'
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
    const agora = new Date().toISOString();

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
            req.session.lead.data_geracao_plano = agora;
            req.session.lead.status_ia = 'PENDENTE'; // <--- Vital para o Loader do EJS
            req.session.lead.hasActiveProject = true;
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
            journey: response.data || [] // Passa os dados das Ondas e Sprints
        });

    } catch (error) {
        console.error("Erro ao carregar a jornada:", error.message);
        // Em caso de erro, volta para o projeto com uma mensagem
        res.render('client_journey', {
            title: 'Meu Plano',
            isLoggedIn: true,
            isAdmin: false,
            lead: req.session.lead,
            user: { nome: req.session.user_name },
            journey: []
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

        // Tente trocar 127.0.0.1 por localhost ou vice-versa para testar a ponte
        const response = await axios.put('http://localhost:5000/api/ctdi_sprn/update-strategic', req.body, {
            timeout: 5000 // Adicionamos um tempo limite de 5 segundos
        });

        res.json(response.data);
    } catch (error) {
        // OSCAR: O erro real do que o Python respondeu vai aparecer aqui no seu terminal do NODE
        if (error.response) {
            console.error("O PYTHON RESPONDEU ERRO:", error.response.data);
            res.status(500).json(error.response.data); // Repassa o erro REAL do Python para a tela
        } else {
            console.error("ERRO DE CONEXÃO COM PYTHON:", error.message);
            res.status(500).json({ error: "O Python está desligado ou inacessível." });
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

// Rota de ponte para os detalhes da Sprint
app.get('/api/sprint_details/:id', async (req, res) => {
    try {
        const id = req.params.id.replace(':', ''); // Limpeza de segurança
        // O Node chama o Python na porta 5000
        const response = await axios.get(`http://127.0.0.1:5000/api/sprint_details/${id}`);
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ error: "Erro ao conectar com o motor Python" });
    }
});

// Rota gravação modal clientes (dados de contexto) - INTEGRADA À MÁQUINA DE ESTADOS
app.post('/api/client/update-context', async (req, res) => {
    try {
        console.log(">>> [NODE] Recebido dados do Lead. Repassando para o Python...");

        // 1. Repassa o payload original recebido da UI para o endpoint do Python
        const response = await axios.post(`${API_BASE_URL}/client/update-context`, req.body);

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
        const response = await axios.get(`http://127.0.0.1:5000/api/cerimonias/${id}`);
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ error: "Erro ao buscar ritos no motor Python" });
    }
});

// Ponte para REGISTRAR uma nova cerimônia
app.post('/api/cerimonias/registrar', async (req, res) => {
    try {
        const response = await axios.post(`http://127.0.0.1:5000/api/cerimonias/registrar`, req.body);
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
        const response = await axios.get(`http://127.0.0.1:5000/api/evidencias/${id_sprn}`);
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
// Ponte para buscar a árvore completa de OKR estruturada do Cliente
app.get('/api/okr/consolidado/:id_clie', async (req, res) => {
    try {
        const id_clie = req.params.id_clie;
        const response = await axios.get(`http://127.0.0.1:5000/api/okr/consolidado?id_clie=${id_clie}`);
        res.json(response.data);
    } catch (error) {
        console.error("❌ Erro na ponte de consolidação OKR:", error.message);
        res.status(500).json({ error: "Erro ao buscar dados de planejamento estratégico no motor Python." });
    }
});

// Ponte para registrar novos Direcionadores (Nível 1)
app.post('/api/okr/direcionadores', async (req, res) => {
    try {
        const response = await axios.post(`http://127.0.0.1:5000/api/okr/direcionadores`, req.body);
        res.status(response.status).json(response.data);
    } catch (error) {
        res.status(500).json({ error: "Erro ao registrar direcionador no motor Python." });
    }
});

// Ponte para registrar novos Objetivos de TD (Nível 2)
app.post('/api/okr/objetivos', async (req, res) => {
    try {
        const response = await axios.post(`http://127.0.0.1:5000/api/okr/objetivos`, req.body);
        res.status(response.status).json(response.data);
    } catch (error) {
        res.status(500).json({ error: "Erro ao vincular objetivo no motor Python." });
    }
});

// Ponte para registrar novos Key Results (Nível 3)
app.post('/api/okr/krs', async (req, res) => {
    try {
        const response = await axios.post(`http://127.0.0.1:5000/api/okr/krs`, req.body);
        res.status(response.status).json(response.data);
    } catch (error) {
        res.status(500).json({ error: "Erro ao estabelecer KR no motor Python." });
    }
});

// Ponte para salvar as Atividades da Sprint (Nível 4)
app.post('/api/okr/atividades', async (req, res) => {
    try {
        const response = await axios.post(`http://127.0.0.1:5000/api/okr/atividades`, req.body);
        res.status(response.status).json(response.data);
    } catch (error) {
        res.status(500).json({ error: "Erro ao registrar atividade de sprint no motor Python." });
    }
});

// Ponte para ATUALIZAR (PUT) qualquer entidade do bloco estratégico (Níveis 1, 2 e 3)
app.put('/api/okr/:entity/:id', async (req, res) => {
    try {
        const { entity, id } = req.params;
        const response = await axios.put(`http://127.0.0.1:5000/api/okr/${entity}/${id}`, req.body);
        res.status(response.status).json(response.data);
    } catch (error) {
        console.error("❌ Erro na ponte PUT de manutenção OKR:", error.message);
        res.status(500).json({ error: "Erro ao atualizar dados no motor Python." });
    }
});

// Ponte para DELETAR (DELETE) qualquer entidade do bloco estratégico em cascata
app.delete('/api/okr/:entity/:id', async (req, res) => {
    try {
        const { entity, id } = req.params;
        const response = await axios.delete(`http://127.0.0.1:5000/api/okr/${entity}/${id}`);
        res.status(response.status).json(response.data);
    } catch (error) {
        console.error("❌ Erro na ponte DELETE de manutenção OKR:", error.message);
        res.status(500).json({ error: "Erro ao deletar dados no motor Python." });
    }
});


// Ponte corrigida para buscar os membros do time filtrados por Squad
app.get('/api/ctdi_team', async (req, res) => {
    try {
        const id_squad = req.query.id_squad || req.query.id_team;

        // Repassa a chamada com o parâmetro exato para o Flask na porta 5000
        const response = await axios.get(`http://127.0.0.1:5000/api/ctdi_team?id_squad=${id_squad}`);
        res.json(response.data);
    } catch (error) {
        console.error("❌ Erro na ponte GET /api/ctdi_team:", error.message);
        res.status(500).json({ error: "Erro ao buscar membros do time no motor Python." });
    }
});

// Rota de Front-End para renderizar a página de Planejamento Estratégico (OKR)
app.get('/planejamento-estrategico', async (req, res) => {
    // GANHO DE PRIORIDADE: Captura o ID da URL (?id_clie=6). Se não existir (cliente comum logado), usa a sessão.
    const id_clie = req.query.id_clie || req.session.id_clie || (req.session.lead ? req.session.lead.id_clie : null) || (req.session.user ? req.session.user.id_clie : null);

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
        const urlFlask = `http://127.0.0.1:5000/api/okr/consolidado?id_clie=${id_clie}`;
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

        const listaDirecionadores = Object.values(direcionadoresMap).map(d => {
            d.objetivos = Object.values(d.objetivos);
            return d;
        });

        res.render('okr', {
            direcionadores: listaDirecionadores,
            id_clie: id_clie,
            lead: leadData,
            user: userData,
            readOnly: req.query.id_clie ? true : false, // Bloqueia edições na tela se for auditoria do Admin
            title: "Estratégia Empresarial - OKR"
        });

    } catch (error) {
        console.error("❌ [SERVER ERROR] Falha ao processar e renderizar dados de OKR:", error.message);
        res.render('okr', { direcionadores: [], id_clie: id_clie, lead: leadData, user: userData, title: "Estratégia Empresarial - OKR" });
    }
});


// Rota do Painel de Governança de OKRs (Visão do Administrador)
app.get('/admin/governanca-estrategica', async (req, res) => {
    try {
        // Consome os dados consolidados do motor Python
        const response = await axios.get('http://127.0.0.1:5000/api/okr/admin/dashboard');
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
app.listen(PORT, () => {
    console.log(`--------------------------------------------------`);
    console.log(`🚀 SERVIDOR NO AR (Versão Recomposta & Corrigida)`);
    console.log(`📡 Porta: ${PORT}`);
    console.log(`🏠 Link: http://localhost:${PORT}`);
    console.log(`--------------------------------------------------`);
});