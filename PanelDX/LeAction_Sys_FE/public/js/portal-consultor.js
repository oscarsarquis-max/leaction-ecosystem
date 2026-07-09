(function () {
    'use strict';

    var root = document.getElementById('portal-consultor-root');
    if (!root) return;

    var BFF = '/bff/consultor';
    var dashboardData = null;
    var clientesCache = [];
    var demandasCache = [];
    var financeVisible = true;
    var isAgencia = false;

    var toastEl = document.getElementById('portal-consultor-toast');
    var modalDemanda = document.getElementById('modal-demanda');
    var formDemanda = document.getElementById('form-demanda');
    var selectDemandaCliente = document.getElementById('demanda-cliente');

    function escapeHtml(s) {
        return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function formatBRL(value) {
        var n = Number(value);
        if (!isFinite(n)) return '—';
        return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(n);
    }

    function toast(msg, type) {
        if (!toastEl) return;
        toastEl.textContent = msg;
        toastEl.className = 'admin-crm__toast is-visible' + (type === 'error' ? ' is-error' : '');
        clearTimeout(toast._t);
        toast._t = setTimeout(function () {
            toastEl.classList.remove('is-visible');
        }, 3500);
    }

    async function apiFetch(path, options) {
        var res = await fetch(path, options || {});
        var data = await res.json().catch(function () { return {}; });
        if (!res.ok) {
            throw new Error(data.error || data.message || 'Falha na requisição.');
        }
        return data;
    }

    function ativarTab(tabId) {
        root.querySelectorAll('[data-tab]').forEach(function (btn) {
            var active = btn.getAttribute('data-tab') === tabId;
            btn.classList.toggle('is-active', active);
            btn.setAttribute('aria-selected', active ? 'true' : 'false');
        });
        root.querySelectorAll('.portal-consultor__panel').forEach(function (panel) {
            var active = panel.id === 'panel-' + tabId;
            panel.classList.toggle('is-active', active);
            panel.hidden = !active;
        });
    }

    function setFinanceVisibility(visible) {
        financeVisible = !!visible;
        root.classList.toggle('is-finance-hidden', !financeVisible);
        var banner = document.getElementById('portal-agency-banner');
        if (banner) banner.hidden = financeVisible;
    }

    function renderDashboard(data) {
        dashboardData = data;
        var consultor = data.consultor || {};
        var conc = data.conciliacao || {};
        var totais = conc.totais || {};
        var stats = data.estatisticas || {};

        document.getElementById('portal-consultor-nome').textContent = consultor.nome || 'Consultor';
        var tipoLabel = consultor.tipo === 'agencia' ? 'Agência' : 'Consultor Individual';
        if (consultor.nome_agencia_pai) {
            tipoLabel += ' · ' + consultor.nome_agencia_pai;
        }
        document.getElementById('portal-consultor-tipo').textContent = tipoLabel;

        isAgencia = consultor.tipo === 'agencia';
        renderEquipeAgencia((conc.membros_agencia || data.membros_agencia) || []);

        setFinanceVisibility(conc.consultor ? conc.consultor.financeiro_visivel !== false : true);

        document.getElementById('metric-comissao-total').textContent = formatBRL(totais.comissao_total);
        document.getElementById('metric-comissao-venda').textContent = formatBRL(totais.comissao_venda);
        document.getElementById('metric-comissao-tecnica').textContent = formatBRL(totais.comissao_tecnica);
        document.getElementById('metric-clientes').textContent = stats.clientes_carteira != null ? stats.clientes_carteira : '—';
        document.getElementById('metric-contratos').textContent = stats.contratos_ativos_carteira != null ? stats.contratos_ativos_carteira : '—';
        document.getElementById('metric-sprints').textContent = stats.sprints_ativas != null ? stats.sprints_ativas : '—';
        document.getElementById('metric-demandas').textContent = stats.demandas_abertas != null ? stats.demandas_abertas : '—';

        var tbody = document.getElementById('conciliacao-table-body');
        var linhas = conc.linhas || [];
        if (!linhas.length) {
            tbody.innerHTML = '<tr><td colspan="7" class="admin-esim__empty">Nenhuma linha de comissão no período.</td></tr>';
            return;
        }
        tbody.innerHTML = linhas.map(function (l) {
            var papeis = (l.papeis || []).join(', ') || '—';
            return '<tr>'
                + '<td>' + escapeHtml(l.nome_clie) + '</td>'
                + '<td>' + escapeHtml(l.nome_plano) + '</td>'
                + '<td>' + formatBRL(l.valor_negociado) + '</td>'
                + '<td>' + escapeHtml(papeis) + '</td>'
                + '<td class="portal-col-finance">' + formatBRL(l.comissao_venda) + '</td>'
                + '<td class="portal-col-finance">' + formatBRL(l.comissao_tecnica) + '</td>'
                + '<td class="portal-col-finance"><strong>' + formatBRL(l.comissao_total) + '</strong></td>'
                + '</tr>';
        }).join('');
    }

    function renderEquipeAgencia(membros) {
        var card = document.getElementById('portal-equipe-card');
        var tbody = document.getElementById('equipe-table-body');
        if (!card || !tbody) return;

        if (!isAgencia) {
            card.hidden = true;
            return;
        }

        card.hidden = false;
        if (!membros.length) {
            tbody.innerHTML = '<tr><td colspan="4" class="admin-esim__empty">Nenhum consultor associado à agência.</td></tr>';
            return;
        }

        tbody.innerHTML = membros.map(function (m) {
            return '<tr>'
                + '<td><strong>' + escapeHtml(m.nome) + '</strong></td>'
                + '<td>' + escapeHtml(m.email || '—') + '</td>'
                + '<td>' + Number(m.taxa_comissao_venda || 0).toFixed(2) + '%</td>'
                + '<td>' + Number(m.taxa_comissao_tecnica || 0).toFixed(2) + '%</td>'
                + '</tr>';
        }).join('');
    }

    function papelBadge(papel) {
        var labels = {
            origem: 'Origem',
            tecnico: 'Técnico',
            origem_tecnico: 'Origem + Técnico',
            carteira: 'Carteira'
        };
        var cls = 'portal-consultor__badge--' + (papel || 'carteira');
        return '<span class="portal-consultor__badge ' + cls + '">' + escapeHtml(labels[papel] || papel) + '</span>';
    }

    function renderClientes(rows) {
        clientesCache = rows || [];
        var tbody = document.getElementById('clientes-table-body');
        if (!clientesCache.length) {
            tbody.innerHTML = '<tr><td colspan="6" class="admin-esim__empty">Nenhum cliente na sua carteira.</td></tr>';
            return;
        }
        tbody.innerHTML = clientesCache.map(function (c) {
            var consultores = [
                c.consultor_origem_nome ? ('Origem: ' + c.consultor_origem_nome) : '',
                c.consultor_tecnico_nome ? ('Técnico: ' + c.consultor_tecnico_nome) : ''
            ].filter(Boolean).join(' · ') || '—';
            return '<tr>'
                + '<td><strong>' + escapeHtml(c.nome_clie) + '</strong><br><span class="admin-esim__field-hint">' + escapeHtml(c.mail_clie) + '</span></td>'
                + '<td>' + escapeHtml(c.nome_plano) + '</td>'
                + '<td>' + escapeHtml(c.status_contrato) + '</td>'
                + '<td>' + formatBRL(c.valor_negociado) + '</td>'
                + '<td>' + papelBadge(c.papel_consultor) + '</td>'
                + '<td>' + escapeHtml(consultores) + '</td>'
                + '</tr>';
        }).join('');
        preencherSelectClientesDemanda();
    }

    function renderSprints(rows) {
        var tbody = document.getElementById('sprints-table-body');
        if (!rows || !rows.length) {
            tbody.innerHTML = '<tr><td colspan="4" class="admin-esim__empty">Nenhuma sprint ativa na carteira.</td></tr>';
            return;
        }
        tbody.innerHTML = rows.map(function (s) {
            return '<tr>'
                + '<td>' + escapeHtml(s.nome_clie) + '</td>'
                + '<td><strong>' + escapeHtml(s.name_sprn) + '</strong></td>'
                + '<td>' + escapeHtml(s.stat_sprn) + '</td>'
                + '<td>' + escapeHtml((s.desc_sprn || '').slice(0, 120)) + '</td>'
                + '</tr>';
        }).join('');
    }

    function renderDemandasBoard(rows) {
        demandasCache = rows || [];
        ['aberta', 'em_andamento', 'resolvida'].forEach(function (status) {
            var list = document.getElementById('board-' + status);
            if (!list) return;
            var items = demandasCache.filter(function (d) { return d.status === status; });
            if (!items.length) {
                list.innerHTML = '<p class="admin-esim__field-hint">Nenhuma demanda.</p>';
                return;
            }
            list.innerHTML = items.map(function (d) {
                var actions = '';
                if (status === 'aberta') {
                    actions = '<button type="button" data-demanda-status="' + d.id + '" data-next="em_andamento">Iniciar</button>';
                } else if (status === 'em_andamento') {
                    actions = '<button type="button" data-demanda-status="' + d.id + '" data-next="resolvida">Resolver</button>'
                        + '<button type="button" data-demanda-status="' + d.id + '" data-next="aberta">Reabrir</button>';
                } else {
                    actions = '<button type="button" data-demanda-status="' + d.id + '" data-next="em_andamento">Reativar</button>';
                }
                var consultorBadge = '';
                if (isAgencia && d.consultor_responsavel_nome) {
                    consultorBadge = '<span class="portal-consultor__badge portal-consultor__badge--responsavel" title="Consultor responsável">'
                        + '<i class="fas fa-user-tie"></i> ' + escapeHtml(d.consultor_responsavel_nome)
                        + '</span>';
                }
                return '<article class="portal-consultor__card">'
                    + '<div class="portal-consultor__card-head">'
                    + '<div class="portal-consultor__card-title">' + escapeHtml(d.titulo) + '</div>'
                    + consultorBadge
                    + '</div>'
                    + '<div class="portal-consultor__card-meta">' + escapeHtml(d.nome_clie) + '</div>'
                    + '<p class="admin-esim__field-hint">' + escapeHtml((d.descricao || '').slice(0, 140)) + '</p>'
                    + '<div class="portal-consultor__card-actions">' + actions + '</div>'
                    + '</article>';
            }).join('');
        });
    }

    function preencherSelectClientesDemanda() {
        if (!selectDemandaCliente) return;
        selectDemandaCliente.innerHTML = clientesCache.map(function (c) {
            return '<option value="' + c.id_clie + '">' + escapeHtml(c.nome_clie) + '</option>';
        }).join('');
    }

    async function carregarDashboard() {
        var res = await apiFetch(BFF + '/dashboard');
        renderDashboard(res.data || {});
    }

    async function carregarClientes() {
        var res = await apiFetch(BFF + '/clientes');
        renderClientes(res.data || []);
    }

    async function carregarSprints() {
        var res = await apiFetch(BFF + '/sprints');
        renderSprints(res.data || []);
    }

    async function carregarDemandas() {
        var res = await apiFetch(BFF + '/demandas');
        renderDemandasBoard(res.data || []);
    }

    async function atualizarStatusDemanda(id, status) {
        await apiFetch(BFF + '/demandas/' + id, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: status })
        });
        toast('Demanda atualizada.', 'success');
        await Promise.all([carregarDemandas(), carregarDashboard()]);
    }

    function abrirModalDemanda() {
        if (!clientesCache.length) {
            toast('Carregue a carteira de clientes antes de registrar demandas.', 'error');
            return;
        }
        formDemanda.reset();
        preencherSelectClientesDemanda();
        modalDemanda.classList.add('is-open');
        modalDemanda.setAttribute('aria-hidden', 'false');
    }

    function fecharModalDemanda() {
        modalDemanda.classList.remove('is-open');
        modalDemanda.setAttribute('aria-hidden', 'true');
    }

    root.querySelectorAll('.portal-consultor__tab').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var tab = btn.getAttribute('data-tab');
            ativarTab(tab);
            if (tab === 'clientes') void carregarClientes();
            if (tab === 'sprints') void carregarSprints();
            if (tab === 'demandas') void carregarDemandas();
            if (tab === 'prospeccao') void carregarProspectos();
        });
    });

    document.getElementById('btn-nova-demanda').addEventListener('click', abrirModalDemanda);
    document.getElementById('btn-cancelar-demanda').addEventListener('click', fecharModalDemanda);
    modalDemanda.addEventListener('click', function (e) {
        if (e.target === modalDemanda) fecharModalDemanda();
    });

    formDemanda.addEventListener('submit', async function (e) {
        e.preventDefault();
        try {
            await apiFetch(BFF + '/demandas', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    id_clie: parseInt(selectDemandaCliente.value, 10),
                    titulo: document.getElementById('demanda-titulo').value.trim(),
                    descricao: document.getElementById('demanda-descricao').value.trim(),
                    status: 'aberta'
                })
            });
            toast('Demanda registrada.', 'success');
            fecharModalDemanda();
            await Promise.all([carregarDemandas(), carregarDashboard()]);
            ativarTab('demandas');
        } catch (err) {
            toast(err.message, 'error');
        }
    });

    document.getElementById('demandas-board').addEventListener('click', function (e) {
        var btn = e.target.closest('[data-demanda-status]');
        if (!btn) return;
        var id = parseInt(btn.getAttribute('data-demanda-status'), 10);
        var next = btn.getAttribute('data-next');
        if (!id || !next) return;
        void atualizarStatusDemanda(id, next).catch(function (err) {
            toast(err.message, 'error');
        });
    });

    // --- Prospecção ---
    var STATUS_FUNIL_LABEL = {
        novo_lead: 'Novo lead',
        distribuido: 'Distribuído',
        em_negociacao: 'Em negociação',
        convite_enviado: 'Convite enviado',
        ganho: 'Ganho',
        perdido: 'Perdido'
    };
    var prospectosCache = [];
    var modalVincular = document.getElementById('modal-vincular-matu');
    var formVincular = document.getElementById('form-vincular-matu');
    var modalProspecto = document.getElementById('modal-prospecto');
    var formProspecto = document.getElementById('form-prospecto');

    function inviteUrlFromItem(item) {
        if (item.invite_url) return item.invite_url;
        if (!item.invite_token) return '';
        var ref = item.consultor_ref || '';
        var base = window.location.origin;
        return base + '/cadastro?ref=' + encodeURIComponent(ref)
            + '&invite=' + encodeURIComponent(item.invite_token);
    }

    function renderProspectos(itens) {
        prospectosCache = itens || [];
        var tbody = document.getElementById('prospectos-table-body');
        if (!tbody) return;
        if (!prospectosCache.length) {
            tbody.innerHTML = '<tr><td colspan="6" class="admin-esim__empty">Nenhuma oportunidade ainda.</td></tr>';
            return;
        }
        tbody.innerHTML = prospectosCache.map(function (item) {
            var link = inviteUrlFromItem(item);
            var copyBtn = link
                ? '<button type="button" class="mesa-btn mesa-btn--ghost" data-copy-invite="'
                  + escapeHtml(link) + '"><i class="fas fa-copy"></i> Copiar Link</button>'
                : '—';
            return (
                '<tr>'
                + '<td>' + escapeHtml(item.nome || '—') + '</td>'
                + '<td>' + escapeHtml(item.email || '—') + '</td>'
                + '<td>' + escapeHtml(item.empresa || '—') + '</td>'
                + '<td><span class="portal-consultor__status-pill">'
                + escapeHtml(STATUS_FUNIL_LABEL[item.status_funil] || item.status_funil || '—')
                + '</span></td>'
                + '<td>' + (item.id_matu != null ? item.id_matu : '—') + '</td>'
                + '<td>' + copyBtn + '</td>'
                + '</tr>'
            );
        }).join('');
    }

    async function carregarProspectos() {
        var res = await apiFetch(BFF + '/prospectos');
        var data = (res.data || {}).oportunidades || [];
        renderProspectos(data);
    }

    function abrirModal(modal) {
        if (!modal) return;
        if (modal.parentElement !== document.body) document.body.appendChild(modal);
        modal.classList.add('is-open');
        modal.setAttribute('aria-hidden', 'false');
    }
    function fecharModal(modal) {
        if (!modal) return;
        modal.classList.remove('is-open');
        modal.setAttribute('aria-hidden', 'true');
    }

    var btnVincular = document.getElementById('btn-vincular-matu');
    var btnNovoProspecto = document.getElementById('btn-novo-prospecto');
    if (btnVincular) {
        btnVincular.addEventListener('click', function () {
            document.getElementById('vincular-id-matu').value = '';
            abrirModal(modalVincular);
        });
    }
    if (btnNovoProspecto) {
        btnNovoProspecto.addEventListener('click', function () {
            formProspecto.reset();
            abrirModal(modalProspecto);
        });
    }
    if (document.getElementById('btn-cancelar-vincular')) {
        document.getElementById('btn-cancelar-vincular').addEventListener('click', function () {
            fecharModal(modalVincular);
        });
    }
    if (document.getElementById('btn-cancelar-prospecto')) {
        document.getElementById('btn-cancelar-prospecto').addEventListener('click', function () {
            fecharModal(modalProspecto);
        });
    }
    if (modalVincular) {
        modalVincular.addEventListener('click', function (e) {
            if (e.target === modalVincular) fecharModal(modalVincular);
        });
    }
    if (modalProspecto) {
        modalProspecto.addEventListener('click', function (e) {
            if (e.target === modalProspecto) fecharModal(modalProspecto);
        });
    }

    if (formVincular) {
        formVincular.addEventListener('submit', async function (e) {
            e.preventDefault();
            var btn = document.getElementById('btn-submit-vincular');
            var idMatu = parseInt(document.getElementById('vincular-id-matu').value, 10);
            if (!idMatu) {
                toast('Informe um ID Matu válido.', 'error');
                return;
            }
            if (btn) { btn.disabled = true; btn.textContent = 'Vinculando…'; }
            try {
                await apiFetch(BFF + '/vincular-lead', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id_matu: idMatu })
                });
                toast('Lead vinculado com sucesso.', 'success');
                fecharModal(modalVincular);
                await Promise.all([carregarProspectos(), carregarClientes(), carregarDashboard()]);
            } catch (err) {
                toast(err.message || 'Falha ao vincular lead.', 'error');
            } finally {
                if (btn) { btn.disabled = false; btn.textContent = 'Vincular'; }
            }
        });
    }

    if (formProspecto) {
        formProspecto.addEventListener('submit', async function (e) {
            e.preventDefault();
            var btn = document.getElementById('btn-submit-prospecto');
            if (btn) { btn.disabled = true; btn.textContent = 'Salvando…'; }
            try {
                var res = await apiFetch(BFF + '/prospectos', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        nome: document.getElementById('prospecto-nome').value.trim(),
                        email: document.getElementById('prospecto-email').value.trim(),
                        telefone: document.getElementById('prospecto-telefone').value.trim(),
                        empresa: document.getElementById('prospecto-empresa').value.trim(),
                        public_base_url: window.location.origin
                    })
                });
                var created = res.data || {};
                toast('Prospecto cadastrado.', 'success');
                fecharModal(modalProspecto);
                await carregarProspectos();
                if (created.invite_url && navigator.clipboard) {
                    try {
                        await navigator.clipboard.writeText(created.invite_url);
                        toast('Link de convite copiado.', 'success');
                    } catch (_) { /* ignore */ }
                }
            } catch (err) {
                toast(err.message || 'Falha ao cadastrar prospecto.', 'error');
            } finally {
                if (btn) { btn.disabled = false; btn.textContent = 'Salvar e gerar link'; }
            }
        });
    }

    var prospectosTable = document.getElementById('prospectos-table-body');
    if (prospectosTable) {
        prospectosTable.addEventListener('click', async function (e) {
            var btn = e.target.closest('[data-copy-invite]');
            if (!btn) return;
            var url = btn.getAttribute('data-copy-invite');
            try {
                await navigator.clipboard.writeText(url);
                toast('Link copiado.', 'success');
            } catch (_) {
                window.prompt('Copie o link de convite:', url);
            }
        });
    }

    if (modalDemanda && modalDemanda.parentElement !== document.body) {
        document.body.appendChild(modalDemanda);
    }
    if (modalVincular && modalVincular.parentElement !== document.body) {
        document.body.appendChild(modalVincular);
    }
    if (modalProspecto && modalProspecto.parentElement !== document.body) {
        document.body.appendChild(modalProspecto);
    }

    void (async function init() {
        try {
            await carregarDashboard();
            await carregarClientes();
        } catch (err) {
            toast(err.message || 'Falha ao carregar portal.', 'error');
        }
    })();
})();
