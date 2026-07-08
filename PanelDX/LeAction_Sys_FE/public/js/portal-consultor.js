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

    if (modalDemanda && modalDemanda.parentElement !== document.body) {
        document.body.appendChild(modalDemanda);
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
