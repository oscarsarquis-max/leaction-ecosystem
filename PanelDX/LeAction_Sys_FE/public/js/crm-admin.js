(function () {
    'use strict';

    var root = document.getElementById('admin-crm-root');
    if (!root) return;

    var BFF = '/bff/admin/crm';

    var planos = [];
    var contratos = [];
    var consultores = [];
    var dashboardData = null;
    var chartMrrPlano = null;
    var catalogoAlterado = false;
    var idsAlterados = {};
    var semPublicacaoAnterior = true;

    var elMetricMrr = document.getElementById('metric-mrr');
    var elMetricAtivos = document.getElementById('metric-contratos-ativos');
    var elChartMrr = document.getElementById('chart-mrr-plano');
    var elChartEmpty = document.getElementById('chart-mrr-empty');
    var tbodyPlanos = document.getElementById('planos-table-body');
    var tbodyContratos = document.getElementById('contratos-table-body');
    var toastEl = document.getElementById('admin-crm-toast');

    var modalPlano = document.getElementById('modal-plano');
    var formPlano = document.getElementById('form-plano');
    var modalContrato = document.getElementById('modal-contrato');
    var formContrato = document.getElementById('form-contrato');
    var modalConsultor = document.getElementById('modal-consultor');
    var formConsultor = document.getElementById('form-consultor');
    var tbodyConsultores = document.getElementById('consultores-table-body');
    var selectConsultorUser = document.getElementById('consultor-user-id');
    var selectConsultorAgencia = document.getElementById('consultor-agencia-pai');
    var selectConsultorTipo = document.getElementById('consultor-tipo');
    var usuariosSemPerfil = [];
    var selectContratoPlano = document.getElementById('contrato-plano');
    var selectContratoOrigem = document.getElementById('contrato-consultor-origem');
    var selectContratoTecnico = document.getElementById('contrato-consultor-tecnico');
    var btnPublicarVitrine = document.getElementById('btn-publicar-vitrine');
    var tbodyAddonsContrato = document.getElementById('contrato-addons-body');
    var selectContratoAddonPlano = document.getElementById('contrato-addon-plano');
    var inputContratoAddonQty = document.getElementById('contrato-addon-qty');
    var btnContratoAddonAdd = document.getElementById('btn-contrato-addon-add');
    var contratoAddonsAtual = [];
    var contratoIdModal = null;
    var modalScrollLock = 0;

    function ancorarModalNoBody(modal) {
        if (modal && modal.parentElement !== document.body) {
            document.body.appendChild(modal);
        }
    }

    function lockPageScroll() {
        modalScrollLock += 1;
        document.body.classList.add('mesa-modal-open');
    }

    function unlockPageScroll() {
        modalScrollLock = Math.max(0, modalScrollLock - 1);
        if (modalScrollLock === 0) {
            document.body.classList.remove('mesa-modal-open');
        }
    }

    function abrirModalOverlay(modal) {
        ancorarModalNoBody(modal);
        modal.scrollTop = 0;
        var scrollArea = modal.querySelector('.admin-crm__modal-scroll');
        if (scrollArea) scrollArea.scrollTop = 0;
        modal.classList.add('is-open');
        modal.setAttribute('aria-hidden', 'false');
        lockPageScroll();
    }

    function fecharModalOverlay(modal) {
        if (document.activeElement && modal.contains(document.activeElement)) {
            document.activeElement.blur();
        }
        modal.classList.remove('is-open');
        modal.setAttribute('aria-hidden', 'true');
        unlockPageScroll();
    }

    ancorarModalNoBody(modalPlano);
    ancorarModalNoBody(modalContrato);
    if (modalConsultor) ancorarModalNoBody(modalConsultor);
    var elPublishStatus = document.getElementById('vitrine-publish-status');

    var STATUS_LABELS = {
        ativo: 'Ativo',
        trial: 'Trial',
        inadimplente: 'Inadimplente',
        cancelado: 'Cancelado'
    };

    function escapeHtml(s) {
        return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function formatBRL(value) {
        var n = Number(value);
        if (!isFinite(n)) return '—';
        return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(n);
    }

    function formatDateBR(iso) {
        if (!iso) return '—';
        var parts = String(iso).slice(0, 10).split('-');
        if (parts.length !== 3) return iso;
        return parts[2] + '/' + parts[1] + '/' + parts[0];
    }

    function toast(msg, tipo) {
        if (!toastEl) return;
        toastEl.textContent = msg;
        toastEl.className = 'admin-crm__toast is-visible ' + (tipo === 'error' ? 'is-error' : 'is-success');
        clearTimeout(window._adminCrmToast);
        window._adminCrmToast = setTimeout(function () {
            toastEl.classList.remove('is-visible');
        }, 3800);
    }

    async function apiFetch(url, opts) {
        var r = await fetch(url, Object.assign({ credentials: 'same-origin' }, opts || {}));
        var data = await r.json().catch(function () { return {}; });
        if (!r.ok) {
            var msg = data.error || data.message || 'Erro na requisição';
            if (r.status === 404) {
                msg = msg + ' — reinicie o backend Flask (porta 5002) para carregar as rotas da vitrine.';
            }
            var err = new Error(msg);
            err.status = r.status;
            err.data = data;
            throw err;
        }
        return data;
    }

    function progressClass(pct) {
        if (pct == null || !isFinite(pct)) return 'admin-crm__progress-fill--ok';
        if (pct >= 90) return 'admin-crm__progress-fill--urgent';
        if (pct >= 71) return 'admin-crm__progress-fill--warn';
        return 'admin-crm__progress-fill--ok';
    }

    function renderProgressBar(pct) {
        if (pct == null || !isFinite(pct)) {
            return (
                '<div class="admin-crm__progress">' +
                '<div class="admin-crm__progress-track"><div class="admin-crm__progress-fill admin-crm__progress-fill--ok" style="width:0%"></div></div>' +
                '<span class="admin-crm__progress-label">—</span></div>'
            );
        }
        var clamped = Math.max(0, Math.min(100, pct));
        var cls = progressClass(clamped);
        return (
            '<div class="admin-crm__progress">' +
            '<div class="admin-crm__progress-track">' +
            '<div class="admin-crm__progress-fill ' + cls + '" style="width:' + clamped + '%"></div>' +
            '</div>' +
            '<span class="admin-crm__progress-label">' + clamped.toFixed(1) + '% do período</span>' +
            '</div>'
        );
    }

    function beneficiosTextoDePlano(p) {
        if (p.descricao_beneficios_texto) return p.descricao_beneficios_texto;
        if (Array.isArray(p.descricao_beneficios)) return p.descricao_beneficios.join('\n');
        return '';
    }

    function planoChave(p) {
        return p.id != null ? String(p.id) : String(p._tempId || '');
    }

    function marcarPlanoAlterado(p) {
        catalogoAlterado = true;
        idsAlterados[planoChave(p)] = true;
        atualizarEstadoPublicacao();
    }

    function atualizarEstadoPublicacao() {
        if (btnPublicarVitrine) {
            btnPublicarVitrine.disabled = !catalogoAlterado && !semPublicacaoAnterior;
        }
        if (!elPublishStatus) return;
        if (catalogoAlterado) {
            elPublishStatus.textContent = 'Alterações pendentes — publique para sincronizar com o ActionHub.';
            elPublishStatus.className = 'admin-crm__publish-status is-pending';
        }
    }

    function renderStatusUltimaPublicacao(pub) {
        if (!elPublishStatus || catalogoAlterado) return;
        if (!pub) {
            elPublishStatus.textContent = 'Nenhuma publicação registrada ainda.';
            elPublishStatus.className = 'admin-crm__publish-status';
            return;
        }
        var quando = pub.hub_received_at || pub.criado_em || '';
        elPublishStatus.textContent =
            'Última publicação confirmada pelo ActionHub: ' +
            (quando ? formatDateBR(quando) + ' ' + String(quando).slice(11, 16) : '—') +
            ' · sync ' + (pub.sync_id || '').slice(0, 8) +
            ' · ' + (pub.planos_count || 0) + ' plano(s)';
        elPublishStatus.className = 'admin-crm__publish-status is-ok';
    }

    async function carregarUltimaPublicacao() {
        try {
            var data = await apiFetch(BFF + '/vitrine/ultima-publicacao');
            semPublicacaoAnterior = !data.publicacao;
            renderStatusUltimaPublicacao(data.publicacao);
            atualizarEstadoPublicacao();
        } catch (e) {
            /* silencioso */
        }
    }

    function planosBase() {
        return planos.filter(function (p) { return (p.tipo_plano || 'base') === 'base'; });
    }

    function planosAddon() {
        return planos.filter(function (p) { return p.tipo_plano === 'addon'; });
    }

    function planoParaPayload(p) {
        return {
            id: p.id || undefined,
            nome: p.nome,
            valor_mensal: Number(p.valor_mensal),
            periodicidade: p.periodicidade || 'Mensal',
            max_usuarios: Number(p.max_usuarios != null ? p.max_usuarios : 5),
            tipo_plano: p.tipo_plano || 'base',
            descricao_beneficios: beneficiosTextoDePlano(p),
            ativo: p.ativo !== false
        };
    }

    async function publicarCatalogoVitrine() {
        if (!planos.length) {
            toast('Cadastre ao menos um plano antes de publicar.', 'error');
            return;
        }
        if (!catalogoAlterado && !semPublicacaoAnterior) return;

        if (btnPublicarVitrine) {
            btnPublicarVitrine.disabled = true;
            btnPublicarVitrine.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Publicando…';
        }

        try {
            var payload = { planos: planos.map(planoParaPayload) };
            var data = await apiFetch(BFF + '/vitrine/publicar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            planos = data.planos || planos;
            catalogoAlterado = false;
            idsAlterados = {};
            semPublicacaoAnterior = false;
            renderTabelaPlanos();
            preencherSelectPlanosContrato();
            await refreshPainelFinanceiro();
            renderStatusUltimaPublicacao(data.publicacao);

            var hub = data.hub || {};
            toast(
                'Catálogo publicado! ActionHub confirmou ' + (hub.planos_count || 0) +
                ' plano(s) · sync ' + (hub.sync_id || '').slice(0, 8),
                'success'
            );
        } catch (err) {
            toast(err.message || 'Falha ao publicar vitrine.', 'error');
            atualizarEstadoPublicacao();
        } finally {
            if (btnPublicarVitrine) {
                btnPublicarVitrine.innerHTML = '<i class="fas fa-cloud-upload-alt"></i> Salvar e publicar vitrine';
                btnPublicarVitrine.disabled = !catalogoAlterado && !semPublicacaoAnterior;
            }
        }
    }

    function renderDashboardMetrics() {
        if (!dashboardData) {
            if (elMetricMrr) elMetricMrr.textContent = '—';
            if (elMetricAtivos) elMetricAtivos.textContent = '—';
            return;
        }
        if (elMetricMrr) elMetricMrr.textContent = formatBRL(dashboardData.mrr_total);
        var qtd = (dashboardData.contratos_ativos || []).length;
        if (elMetricAtivos) elMetricAtivos.textContent = String(qtd);
    }

    function renderChartMrrPlano() {
        if (!elChartMrr) return;

        var series = dashboardData && dashboardData.receita_por_plano ? dashboardData.receita_por_plano : [];
        var comValor = series.filter(function (p) { return Number(p.mrr) > 0; });

        if (chartMrrPlano) {
            chartMrrPlano.destroy();
            chartMrrPlano = null;
        }
        elChartMrr.innerHTML = '';

        if (!comValor.length) {
            if (elChartEmpty) elChartEmpty.hidden = false;
            return;
        }

        if (elChartEmpty) elChartEmpty.hidden = true;

        var labels = comValor.map(function (p) { return p.nome_plano || ('Plano #' + p.id_plano); });
        var values = comValor.map(function (p) { return Number(p.mrr) || 0; });

        if (typeof ApexCharts === 'undefined') {
            elChartMrr.innerHTML = '<p class="admin-crm__chart-empty">ApexCharts não carregado.</p>';
            return;
        }

        var options = {
            series: [{ name: 'MRR', data: values }],
            chart: {
                type: 'bar',
                height: 300,
                fontFamily: 'system-ui, -apple-system, Segoe UI, sans-serif',
                toolbar: { show: false },
                animations: { enabled: true, speed: 500 }
            },
            plotOptions: {
                bar: {
                    borderRadius: 8,
                    columnWidth: '52%',
                    distributed: true
                }
            },
            colors: ['#34d399', '#a78bfa', '#60a5fa', '#fbbf24', '#f472b6', '#94a3b8'],
            dataLabels: {
                enabled: true,
                formatter: function (v) {
                    return formatBRL(v);
                },
                style: { fontSize: '11px', fontWeight: 700 }
            },
            legend: { show: false },
            xaxis: {
                categories: labels,
                labels: { style: { fontSize: '12px', fontWeight: 600 } }
            },
            yaxis: {
                labels: {
                    formatter: function (v) { return formatBRL(v); }
                }
            },
            tooltip: {
                y: { formatter: function (v) { return formatBRL(v); } }
            }
        };

        chartMrrPlano = new ApexCharts(elChartMrr, options);
        chartMrrPlano.render();
    }

    function renderTabelaPlanos() {
        if (!planos.length) {
            tbodyPlanos.innerHTML = '<tr><td colspan="7" class="admin-esim__empty">Nenhum plano cadastrado.</td></tr>';
            return;
        }

        tbodyPlanos.innerHTML = planos.map(function (p) {
            var ativo = !!p.ativo;
            var chave = planoChave(p);
            var dirty = !!idsAlterados[chave];
            var qtdBeneficios = Array.isArray(p.descricao_beneficios)
                ? p.descricao_beneficios.length
                : beneficiosTextoDePlano(p).split(/\n/).filter(Boolean).length;
            var editId = p.id != null ? p.id : chave;
            var maxUsuarios = Number(p.max_usuarios != null ? p.max_usuarios : 5);
            var usuariosLabel = maxUsuarios >= 999 ? 'Ilimitado' : String(maxUsuarios);
            var tipo = (p.tipo_plano || 'base') === 'addon' ? 'Add-on' : 'Base';
            var tipoClass = (p.tipo_plano || 'base') === 'addon' ? 'addon' : 'base';
            return (
                '<tr class="' + (dirty ? 'admin-crm__row-dirty' : '') + '">' +
                '<td><strong>' + escapeHtml(p.nome) + '</strong>' +
                (qtdBeneficios ? '<br><span style="font-size:0.72rem;color:#64748b">' + qtdBeneficios + ' benefício(s)</span>' : '') +
                '</td>' +
                '<td><span class="admin-crm__tipo-plano admin-crm__tipo-plano--' + tipoClass + '">' + tipo + '</span></td>' +
                '<td>' + escapeHtml(formatBRL(p.valor_mensal)) + '</td>' +
                '<td>' + escapeHtml(usuariosLabel) + '</td>' +
                '<td>' + escapeHtml(p.periodicidade || 'Mensal') + '</td>' +
                '<td><span class="admin-crm__plano-status--' + (ativo ? 'ativo' : 'inativo') + '">' +
                (ativo ? 'Ativo' : 'Inativo') + '</span></td>' +
                '<td><div class="admin-crm__row-actions">' +
                '<button type="button" class="admin-crm__icon-btn" data-edit-plano="' + escapeHtml(String(editId)) + '" title="Editar">' +
                '<i class="fas fa-edit"></i></button>' +
                '</div></td>' +
                '</tr>'
            );
        }).join('');
    }

    function renderTabelaContratos() {
        if (!contratos.length) {
            tbodyContratos.innerHTML = '<tr><td colspan="7" class="admin-esim__empty">Nenhum contrato cadastrado.</td></tr>';
            return;
        }

        tbodyContratos.innerHTML = contratos.map(function (c) {
            var status = (c.status || '').toLowerCase();
            var nome = c.nome_clie || ('Cliente #' + c.id_clie);
            var vigencia =
                '<div class="admin-crm__vigencia">' +
                '<div><strong>Início:</strong> ' + escapeHtml(formatDateBR(c.data_inicio)) + '</div>' +
                '<div><strong>Fim:</strong> ' + escapeHtml(formatDateBR(c.data_vencimento)) + '</div>' +
                '</div>';

            return (
                '<tr>' +
                '<td><strong>' + escapeHtml(nome) + '</strong>' +
                (c.mail_clie ? '<br><span style="font-size:0.75rem;color:#64748b">' + escapeHtml(c.mail_clie) + '</span>' : '') +
                '</td>' +
                '<td>' + escapeHtml(c.nome_plano || '—') + '</td>' +
                '<td>' + escapeHtml(formatBRL(c.valor_negociado)) + '</td>' +
                '<td><span class="admin-crm__badge admin-crm__badge--' + escapeHtml(status) + '">' +
                escapeHtml(STATUS_LABELS[status] || status) + '</span></td>' +
                '<td>' + vigencia + '</td>' +
                '<td>' + renderProgressBar(c.percentual_execucao) + '</td>' +
                '<td><div class="admin-crm__row-actions">' +
                '<button type="button" class="admin-crm__icon-btn" data-edit-contrato="' + c.id + '" title="Editar contrato">' +
                '<i class="fas fa-edit"></i></button>' +
                '</div></td>' +
                '</tr>'
            );
        }).join('');
    }

    function preencherSelectPlanosContrato(selectedId) {
        if (!selectContratoPlano) return;
        var base = planosBase();
        selectContratoPlano.innerHTML = base.map(function (p) {
            var sel = String(p.id) === String(selectedId) ? ' selected' : '';
            return '<option value="' + p.id + '"' + sel + '>' + escapeHtml(p.nome) + ' (' + formatBRL(p.valor_mensal) + ')</option>';
        }).join('');
    }

    function preencherSelectAddonsContrato() {
        if (!selectContratoAddonPlano) return;
        var addons = planosAddon().filter(function (p) { return p.ativo !== false && p.id; });
        if (!addons.length) {
            selectContratoAddonPlano.innerHTML = '<option value="">Nenhum pacote add-on cadastrado</option>';
            if (btnContratoAddonAdd) btnContratoAddonAdd.disabled = true;
            return;
        }
        if (btnContratoAddonAdd) btnContratoAddonAdd.disabled = false;
        selectContratoAddonPlano.innerHTML = addons.map(function (p) {
            return '<option value="' + p.id + '">' + escapeHtml(p.nome) + ' (+' + (p.max_usuarios || 0) + ' usuários)</option>';
        }).join('');
    }

    function renderAddonsContrato(addons) {
        if (!tbodyAddonsContrato) return;
        contratoAddonsAtual = addons || [];
        if (!contratoAddonsAtual.length) {
            tbodyAddonsContrato.innerHTML = '<tr><td colspan="6" class="admin-esim__empty">Nenhum pacote adicional vinculado.</td></tr>';
            return;
        }
        tbodyAddonsContrato.innerHTML = contratoAddonsAtual.map(function (a) {
            var status = (a.status || '').toLowerCase();
            var cancelBtn = status === 'ativo'
                ? '<button type="button" class="admin-crm__icon-btn" data-cancel-addon="' + a.id + '" title="Cancelar pacote">' +
                  '<i class="fas fa-ban"></i></button>'
                : '—';
            return (
                '<tr>' +
                '<td><strong>' + escapeHtml(a.nome_addon || 'Pacote') + '</strong></td>' +
                '<td>' + escapeHtml(String(a.quantidade || 1)) + '</td>' +
                '<td>+' + escapeHtml(String(a.usuarios_extra || 0)) + '</td>' +
                '<td>' + escapeHtml(formatBRL(a.mrr_linha || 0)) + '</td>' +
                '<td><span class="admin-crm__badge admin-crm__badge--' + escapeHtml(status) + '">' +
                escapeHtml(status === 'ativo' ? 'Ativo' : 'Cancelado') + '</span></td>' +
                '<td>' + cancelBtn + '</td>' +
                '</tr>'
            );
        }).join('');
    }

    async function carregarAddonsContrato(contratoId) {
        if (!tbodyAddonsContrato || !contratoId) return;
        tbodyAddonsContrato.innerHTML = '<tr><td colspan="6" class="admin-esim__empty">Carregando pacotes…</td></tr>';
        try {
            var data = await apiFetch(BFF + '/contratos/' + contratoId + '/addons');
            renderAddonsContrato(data.addons || []);
        } catch (e) {
            tbodyAddonsContrato.innerHTML = '<tr><td colspan="6" class="admin-esim__empty">Falha ao carregar pacotes.</td></tr>';
        }
    }

    async function carregarDashboard() {
        var data = await apiFetch(BFF + '/dashboard');
        dashboardData = data;
        renderDashboardMetrics();
        renderChartMrrPlano();
    }

    async function carregarPlanos() {
        var data = await apiFetch(BFF + '/planos');
        planos = data.planos || [];
        renderTabelaPlanos();
        preencherSelectPlanosContrato();
        preencherSelectAddonsContrato();
    }

    async function carregarContratos() {
        var data = await apiFetch(BFF + '/contratos');
        contratos = data.contratos || [];
        renderTabelaContratos();
    }

    async function refreshPainelFinanceiro() {
        await Promise.all([carregarDashboard(), carregarContratos()]);
    }

    async function carregarConsultores() {
        var data = await apiFetch(BFF + '/consultores?incluir_inativos=1');
        consultores = data.consultores || [];
        preencherSelectConsultoresContrato();
        renderTabelaConsultores();
    }

    async function carregarUsuariosSemPerfil() {
        var data = await apiFetch(BFF + '/consultores/usuarios-sem-perfil');
        usuariosSemPerfil = data.usuarios || [];
    }

    function tipoConsultorLabel(tipo) {
        return tipo === 'agencia' ? 'Agência' : 'Individual';
    }

    function renderTabelaConsultores() {
        if (!tbodyConsultores) return;
        if (!consultores.length) {
            tbodyConsultores.innerHTML = '<tr><td colspan="8" class="admin-esim__empty">Nenhum consultor cadastrado.</td></tr>';
            return;
        }
        tbodyConsultores.innerHTML = consultores.map(function (c) {
            return '<tr>'
                + '<td>' + escapeHtml(c.nome) + '</td>'
                + '<td>' + escapeHtml(c.email) + '</td>'
                + '<td>' + escapeHtml(tipoConsultorLabel(c.tipo)) + '</td>'
                + '<td>' + escapeHtml(c.nome_agencia_pai || '—') + '</td>'
                + '<td>' + Number(c.taxa_comissao_venda).toFixed(2) + '%</td>'
                + '<td>' + Number(c.taxa_comissao_tecnica).toFixed(2) + '%</td>'
                + '<td>' + (c.ativo ? '<span class="admin-crm__badge admin-crm__badge--ativo">Ativo</span>' : '<span class="admin-crm__badge admin-crm__badge--inativo">Inativo</span>') + '</td>'
                + '<td><button type="button" class="mesa-btn mesa-btn--ghost mesa-btn--sm" data-edit-consultor="' + c.id + '"><i class="fas fa-edit"></i></button></td>'
                + '</tr>';
        }).join('');
    }

    function preencherSelectAgenciasConsultor(selectedId, excludeId) {
        if (!selectConsultorAgencia) return;
        var current = selectedId != null ? String(selectedId) : '';
        selectConsultorAgencia.innerHTML = '<option value="">— Nenhuma —</option>';
        consultores.filter(function (c) {
            return c.tipo === 'agencia' && c.ativo && String(c.id) !== String(excludeId || '');
        }).forEach(function (c) {
            var opt = document.createElement('option');
            opt.value = String(c.id);
            opt.textContent = c.nome;
            selectConsultorAgencia.appendChild(opt);
        });
        selectConsultorAgencia.value = current;
    }

    function preencherSelectUsuariosConsultor(selectedId) {
        if (!selectConsultorUser) return;
        var current = selectedId != null ? String(selectedId) : '';
        selectConsultorUser.innerHTML = '<option value="">— Selecione —</option>';
        usuariosSemPerfil.forEach(function (u) {
            var opt = document.createElement('option');
            opt.value = String(u.id_usuario);
            opt.textContent = (u.nome || u.email) + ' (' + u.email + ')';
            selectConsultorUser.appendChild(opt);
        });
        selectConsultorUser.value = current;
    }

    function atualizarCamposTipoConsultor() {
        var tipo = selectConsultorTipo ? selectConsultorTipo.value : 'individual';
        var fieldAgencia = document.getElementById('field-consultor-agencia-pai');
        if (fieldAgencia) {
            fieldAgencia.hidden = tipo === 'agencia';
        }
        if (tipo === 'agencia' && selectConsultorAgencia) {
            selectConsultorAgencia.value = '';
        }
    }

    async function abrirModalConsultor(edicao) {
        var title = document.getElementById('modal-consultor-title');
        var fieldUsuario = document.getElementById('field-consultor-usuario');
        var fieldAtivo = document.getElementById('field-consultor-ativo');
        var inputId = document.getElementById('consultor-id');
        var inputVenda = document.getElementById('consultor-taxa-venda');
        var inputTecnica = document.getElementById('consultor-taxa-tecnica');
        var selectAtivo = document.getElementById('consultor-ativo');

        await carregarUsuariosSemPerfil();
        preencherSelectAgenciasConsultor();

        if (edicao) {
            title.textContent = 'Editar Consultor';
            if (fieldUsuario) fieldUsuario.hidden = true;
            if (fieldAtivo) fieldAtivo.hidden = false;
            if (selectConsultorUser) selectConsultorUser.removeAttribute('required');
            inputId.value = String(edicao.id);
            if (selectConsultorTipo) selectConsultorTipo.value = edicao.tipo || 'individual';
            preencherSelectAgenciasConsultor(edicao.id_agencia_pai, edicao.id);
            if (inputVenda) inputVenda.value = edicao.taxa_comissao_venda;
            if (inputTecnica) inputTecnica.value = edicao.taxa_comissao_tecnica;
            if (selectAtivo) selectAtivo.value = edicao.ativo ? 'true' : 'false';
        } else {
            title.textContent = 'Novo Consultor';
            if (fieldUsuario) fieldUsuario.hidden = false;
            if (fieldAtivo) fieldAtivo.hidden = true;
            if (selectConsultorUser) selectConsultorUser.setAttribute('required', 'required');
            inputId.value = '';
            if (selectConsultorTipo) selectConsultorTipo.value = 'individual';
            preencherSelectUsuariosConsultor();
            if (inputVenda) inputVenda.value = '10';
            if (inputTecnica) inputTecnica.value = '15';
            if (selectAtivo) selectAtivo.value = 'true';
        }
        atualizarCamposTipoConsultor();
        abrirModalOverlay(modalConsultor);
    }

    function fecharModalConsultor() {
        if (modalConsultor) fecharModalOverlay(modalConsultor);
    }

    function preencherSelectConsultoresContrato(origemId, tecnicoId) {
        [selectContratoOrigem, selectContratoTecnico].forEach(function (sel) {
            if (!sel) return;
            var current = sel === selectContratoOrigem
                ? (origemId != null ? String(origemId) : '')
                : (tecnicoId != null ? String(tecnicoId) : '');
            sel.innerHTML = '<option value="">— Nenhum —</option>';
            consultores.filter(function (c) { return c.ativo !== false; }).forEach(function (c) {
                var opt = document.createElement('option');
                opt.value = String(c.id);
                opt.textContent = c.label || c.nome;
                sel.appendChild(opt);
            });
            sel.value = current;
        });
    }

    async function init() {
        try {
            await Promise.all([
                carregarDashboard(),
                carregarPlanos(),
                carregarContratos(),
                carregarUltimaPublicacao(),
                carregarConsultores()
            ]);
        } catch (e) {
            toast(e.message || 'Falha ao carregar CRM.', 'error');
        }
    }

    function ativarAbaPlano(tabId) {
        var tabs = modalPlano.querySelectorAll('[data-plano-tab]');
        var panels = {
            basico: document.getElementById('plano-panel-basico'),
            vitrine: document.getElementById('plano-panel-vitrine')
        };
        tabs.forEach(function (btn) {
            var active = btn.getAttribute('data-plano-tab') === tabId;
            btn.classList.toggle('is-active', active);
            btn.setAttribute('aria-selected', active ? 'true' : 'false');
        });
        Object.keys(panels).forEach(function (key) {
            var panel = panels[key];
            if (!panel) return;
            var active = key === tabId;
            panel.classList.toggle('is-active', active);
            panel.hidden = !active;
        });
    }

    function abrirModalPlano(edicao) {
        var title = document.getElementById('modal-plano-title');
        var fieldAtivo = document.getElementById('field-plano-ativo');
        var btnSubmit = document.getElementById('btn-submit-plano');

        ativarAbaPlano('basico');

        if (edicao) {
            title.textContent = 'Editar Plano';
            fieldAtivo.hidden = false;
            btnSubmit.innerHTML = '<i class="fas fa-check"></i> Aplicar alterações';
        } else {
            title.textContent = 'Novo Plano';
            fieldAtivo.hidden = true;
            btnSubmit.innerHTML = '<i class="fas fa-check"></i> Aplicar alterações';
            formPlano.reset();
            document.getElementById('plano-id').value = '';
            document.getElementById('plano-max-usuarios').value = '5';
            document.getElementById('plano-tipo').value = 'base';
        }

        abrirModalOverlay(modalPlano);
    }

    function fecharModalPlano() {
        fecharModalOverlay(modalPlano);
    }

    function abrirModalContrato(contrato) {
        contratoIdModal = contrato.id;
        document.getElementById('contrato-id').value = contrato.id;
        document.getElementById('modal-contrato-cliente').textContent =
            (contrato.nome_clie || 'Cliente') + (contrato.mail_clie ? ' · ' + contrato.mail_clie : '');

        preencherSelectPlanosContrato(contrato.id_plano);
        preencherSelectAddonsContrato();
        if (inputContratoAddonQty) inputContratoAddonQty.value = '1';
        document.getElementById('contrato-valor').value = contrato.valor_negociado;
        document.getElementById('contrato-status').value = contrato.status || 'ativo';
        document.getElementById('contrato-inicio').value = String(contrato.data_inicio || '').slice(0, 10);
        document.getElementById('contrato-vencimento').value = String(contrato.data_vencimento || '').slice(0, 10);
        preencherSelectConsultoresContrato(contrato.id_consultor_origem, contrato.id_consultor_tecnico);

        void carregarAddonsContrato(contrato.id);

        abrirModalOverlay(modalContrato);
    }

    function fecharModalContrato() {
        contratoIdModal = null;
        contratoAddonsAtual = [];
        fecharModalOverlay(modalContrato);
    }

    document.getElementById('btn-novo-plano').addEventListener('click', function () {
        abrirModalPlano(false);
    });

    if (btnPublicarVitrine) {
        btnPublicarVitrine.addEventListener('click', function () {
            void publicarCatalogoVitrine();
        });
    }

    modalPlano.querySelectorAll('[data-plano-tab]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            ativarAbaPlano(btn.getAttribute('data-plano-tab'));
        });
    });

    document.getElementById('btn-cancelar-plano').addEventListener('click', fecharModalPlano);
    document.getElementById('btn-cancelar-contrato').addEventListener('click', fecharModalContrato);

    modalPlano.addEventListener('click', function (e) {
        if (e.target === modalPlano) fecharModalPlano();
    });
    modalContrato.addEventListener('click', function (e) {
        if (e.target === modalContrato) fecharModalContrato();
    });

    tbodyPlanos.addEventListener('click', function (e) {
        var btn = e.target.closest('[data-edit-plano]');
        if (!btn) return;
        var rawId = btn.getAttribute('data-edit-plano');
        var p = planos.find(function (x) {
            return String(x.id) === String(rawId) || String(x._tempId) === String(rawId);
        });
        if (!p) return;
        abrirModalPlano(true);
        document.getElementById('plano-id').value = p.id != null ? p.id : '';
        document.getElementById('plano-nome').value = p.nome || '';
        document.getElementById('plano-valor').value = p.valor_mensal;
        document.getElementById('plano-periodicidade').value = p.periodicidade || 'Mensal';
        document.getElementById('plano-max-usuarios').value = p.max_usuarios != null ? p.max_usuarios : 5;
        document.getElementById('plano-tipo').value = p.tipo_plano || 'base';
        document.getElementById('plano-beneficios').value = beneficiosTextoDePlano(p);
        document.getElementById('plano-ativo').value = p.ativo ? 'true' : 'false';
        if (!p.id) {
            formPlano.dataset.tempId = p._tempId || '';
        } else {
            delete formPlano.dataset.tempId;
        }
    });

    tbodyContratos.addEventListener('click', function (e) {
        var btn = e.target.closest('[data-edit-contrato]');
        if (!btn) return;
        var id = parseInt(btn.getAttribute('data-edit-contrato'), 10);
        var c = contratos.find(function (x) { return x.id === id; });
        if (!c) return;
        abrirModalContrato(c);
    });

    formPlano.addEventListener('submit', async function (e) {
        e.preventDefault();
        var idRaw = document.getElementById('plano-id').value;
        var tempId = formPlano.dataset.tempId || '';
        var beneficiosText = document.getElementById('plano-beneficios').value;
        var payload = {
            nome: document.getElementById('plano-nome').value.trim(),
            valor_mensal: parseFloat(document.getElementById('plano-valor').value),
            periodicidade: document.getElementById('plano-periodicidade').value,
            max_usuarios: parseInt(document.getElementById('plano-max-usuarios').value, 10),
            tipo_plano: document.getElementById('plano-tipo').value || 'base',
            descricao_beneficios_texto: beneficiosText,
            descricao_beneficios: beneficiosText.split(/\n|;/).map(function (s) { return s.trim(); }).filter(Boolean),
            ativo: idRaw ? document.getElementById('plano-ativo').value === 'true' : true
        };

        if (!payload.nome) {
            toast('Nome do plano é obrigatório.', 'error');
            return;
        }
        if (!isFinite(payload.valor_mensal)) {
            toast('Valor mensal inválido.', 'error');
            return;
        }
        if (!isFinite(payload.max_usuarios) || payload.max_usuarios < 1) {
            toast('Limite máximo de usuários inválido.', 'error');
            return;
        }

        var btnSubmit = document.getElementById('btn-submit-plano');
        if (btnSubmit) {
            btnSubmit.disabled = true;
        }

        try {
            if (idRaw) {
                var apiPayload = planoParaPayload(Object.assign({}, payload, { id: parseInt(idRaw, 10) }));
                var saved = await apiFetch(BFF + '/planos/' + idRaw, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(apiPayload)
                });
                var planoSalvo = saved.plano || apiPayload;
                var idx = planos.findIndex(function (x) { return String(x.id) === String(idRaw); });
                if (idx >= 0) {
                    planos[idx] = Object.assign({}, planos[idx], planoSalvo, payload, { id: parseInt(idRaw, 10) });
                }
                marcarPlanoAlterado(planos[idx]);
            } else if (tempId) {
                var idxTemp = planos.findIndex(function (x) { return x._tempId === tempId; });
                if (idxTemp >= 0) {
                    planos[idxTemp] = Object.assign({}, planos[idxTemp], payload);
                    marcarPlanoAlterado(planos[idxTemp]);
                }
            } else {
                var novoPayload = planoParaPayload(payload);
                var created = await apiFetch(BFF + '/planos', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(novoPayload)
                });
                var novoPlano = created.plano || Object.assign({}, payload, { id: created.plano && created.plano.id });
                if (!novoPlano.id) {
                    throw new Error('Falha ao criar plano.');
                }
                planos.push(novoPlano);
                marcarPlanoAlterado(novoPlano);
            }

            renderTabelaPlanos();
            preencherSelectPlanosContrato();
            preencherSelectAddonsContrato();
            fecharModalPlano();
            toast(
                'Plano salvo no PanelDX. Clique em "Salvar e publicar vitrine" para replicar no ActionHub.',
                'success'
            );
        } catch (err) {
            toast(err.message || 'Falha ao salvar plano.', 'error');
        } finally {
            if (btnSubmit) btnSubmit.disabled = false;
        }
    });

    formContrato.addEventListener('submit', async function (e) {
        e.preventDefault();
        var id = document.getElementById('contrato-id').value;
        var inicio = document.getElementById('contrato-inicio').value;
        var fim = document.getElementById('contrato-vencimento').value;

        if (fim < inicio) {
            toast('A data de vencimento deve ser posterior ao início.', 'error');
            return;
        }

        var payload = {
            id_plano: parseInt(document.getElementById('contrato-plano').value, 10),
            valor_negociado: parseFloat(document.getElementById('contrato-valor').value),
            status: document.getElementById('contrato-status').value,
            data_inicio: inicio,
            data_vencimento: fim,
            id_consultor_origem: selectContratoOrigem && selectContratoOrigem.value
                ? parseInt(selectContratoOrigem.value, 10) : null,
            id_consultor_tecnico: selectContratoTecnico && selectContratoTecnico.value
                ? parseInt(selectContratoTecnico.value, 10) : null
        };

        try {
            await apiFetch(BFF + '/contratos/' + id, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            toast('Contrato atualizado. MRR e acesso do cliente atualizados.', 'success');
            fecharModalContrato();
            await refreshPainelFinanceiro();
        } catch (err) {
            toast(err.message, 'error');
        }
    });

    if (tbodyAddonsContrato) {
        tbodyAddonsContrato.addEventListener('click', function (e) {
            var btn = e.target.closest('[data-cancel-addon]');
            if (!btn || !contratoIdModal) return;
            var addonId = parseInt(btn.getAttribute('data-cancel-addon'), 10);
            if (!addonId) return;
            if (!window.confirm('Cancelar este pacote add-on? O limite de usuários do cliente será reduzido.')) return;
            void (async function () {
                try {
                    await apiFetch(BFF + '/contratos/' + contratoIdModal + '/addons/' + addonId, {
                        method: 'DELETE'
                    });
                    toast('Pacote add-on cancelado.', 'success');
                    await carregarAddonsContrato(contratoIdModal);
                    await refreshPainelFinanceiro();
                } catch (err) {
                    toast(err.message || 'Falha ao cancelar pacote.', 'error');
                }
            })();
        });
    }

    if (btnContratoAddonAdd) {
        btnContratoAddonAdd.addEventListener('click', function () {
            if (!contratoIdModal) return;
            var idPlano = selectContratoAddonPlano ? parseInt(selectContratoAddonPlano.value, 10) : NaN;
            var qty = inputContratoAddonQty ? parseInt(inputContratoAddonQty.value, 10) : 1;
            if (!idPlano) {
                toast('Selecione um pacote add-on.', 'error');
                return;
            }
            if (!isFinite(qty) || qty < 1) {
                toast('Quantidade inválida.', 'error');
                return;
            }
            void (async function () {
                btnContratoAddonAdd.disabled = true;
                try {
                    await apiFetch(BFF + '/contratos/' + contratoIdModal + '/addons', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ id_plano_addon: idPlano, quantidade: qty })
                    });
                    toast('Pacote add-on incluído no contrato.', 'success');
                    if (inputContratoAddonQty) inputContratoAddonQty.value = '1';
                    await carregarAddonsContrato(contratoIdModal);
                    await refreshPainelFinanceiro();
                } catch (err) {
                    toast(err.message || 'Falha ao incluir pacote.', 'error');
                } finally {
                    btnContratoAddonAdd.disabled = false;
                }
            })();
        });
    }

    if (tbodyConsultores) {
        tbodyConsultores.addEventListener('click', function (e) {
            var btn = e.target.closest('[data-edit-consultor]');
            if (!btn) return;
            var id = parseInt(btn.getAttribute('data-edit-consultor'), 10);
            var edicao = consultores.find(function (c) { return c.id === id; });
            if (edicao) void abrirModalConsultor(edicao);
        });
    }

    var btnNovoConsultor = document.getElementById('btn-novo-consultor');
    if (btnNovoConsultor) {
        btnNovoConsultor.addEventListener('click', function () { void abrirModalConsultor(null); });
    }

    var btnCancelarConsultor = document.getElementById('btn-cancelar-consultor');
    if (btnCancelarConsultor) {
        btnCancelarConsultor.addEventListener('click', fecharModalConsultor);
    }

    if (selectConsultorTipo) {
        selectConsultorTipo.addEventListener('change', atualizarCamposTipoConsultor);
    }

    if (formConsultor) {
        formConsultor.addEventListener('submit', async function (e) {
            e.preventDefault();
            var id = document.getElementById('consultor-id').value;
            var payload = {
                tipo: selectConsultorTipo ? selectConsultorTipo.value : 'individual',
                taxa_comissao_venda: parseFloat(document.getElementById('consultor-taxa-venda').value),
                taxa_comissao_tecnica: parseFloat(document.getElementById('consultor-taxa-tecnica').value)
            };
            var agenciaPai = selectConsultorAgencia ? selectConsultorAgencia.value : '';
            payload.id_agencia_pai = agenciaPai ? parseInt(agenciaPai, 10) : null;
            if (payload.tipo === 'agencia') {
                payload.id_agencia_pai = null;
            }
            try {
                if (id) {
                    var selectAtivo = document.getElementById('consultor-ativo');
                    if (selectAtivo) payload.ativo = selectAtivo.value === 'true';
                    await apiFetch(BFF + '/consultores/' + id, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                    toast('Consultor atualizado.', 'success');
                } else {
                    payload.user_id = parseInt(selectConsultorUser.value, 10);
                    if (!payload.user_id) {
                        toast('Selecione o usuário vinculado.', 'error');
                        return;
                    }
                    await apiFetch(BFF + '/consultores', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                    toast('Consultor cadastrado.', 'success');
                }
                fecharModalConsultor();
                await carregarConsultores();
            } catch (err) {
                toast(err.message || 'Falha ao salvar consultor.', 'error');
            }
        });
    }

    init();
})();
