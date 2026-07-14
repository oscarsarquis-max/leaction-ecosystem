(function () {
    'use strict';

    var root = document.getElementById('meu-contrato-root');
    if (!root) return;

    var cfg = window.MEU_CONTRATO_CONFIG || {};
    var elLoading = document.getElementById('mc-loading');
    var elError = document.getElementById('mc-error');
    var elContent = document.getElementById('mc-content');

    function escapeHtml(s) {
        return String(s || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function money(v) {
        var n = Number(v || 0);
        return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    }

    function fmtDate(raw) {
        if (!raw) return '—';
        var d = String(raw).slice(0, 10);
        var parts = d.split('-');
        if (parts.length === 3) return parts[2] + '/' + parts[1] + '/' + parts[0];
        return escapeHtml(raw);
    }

    function checkoutUrlForPlan(planId) {
        var base = cfg.checkoutUpgradeUrl || '';
        if (!base) return '#';
        try {
            var u = new URL(base, window.location.origin);
            if (planId) u.searchParams.set('plan_id', String(planId));
            return u.toString();
        } catch (e) {
            return base + (base.indexOf('?') >= 0 ? '&' : '?') + 'plan_id=' + encodeURIComponent(planId);
        }
    }

    function addonCheckoutUrl(addonId) {
        var tpl = cfg.checkoutAddonUrlTemplate || '';
        if (!tpl || !addonId) return '#';
        return tpl.replace('{addon_id}', String(addonId));
    }

    function movimentoLabel(m) {
        if (m === 'upgrade') return 'Upgrade';
        if (m === 'downgrade') return 'Downgrade';
        if (m === 'atual') return 'Plano atual';
        if (m === 'contratar') return 'Contratar';
        return 'Trocar';
    }

    function renderContrato(data) {
        var c = data.contrato;
        var grid = document.getElementById('mc-contrato-grid');
        var badge = document.getElementById('mc-status-badge');
        var actions = document.getElementById('mc-contrato-actions');

        if (!c) {
            badge.textContent = 'Sem contrato';
            badge.className = 'meu-contrato__badge';
            grid.innerHTML =
                '<div class="meu-contrato__metric"><span>Situação</span><strong>Nenhum contrato CRM ativo</strong></div>' +
                '<div class="meu-contrato__metric"><span>Próximo passo</span><strong>Escolha um plano abaixo</strong></div>';
            actions.innerHTML =
                '<a class="mesa-btn mesa-btn--gold" href="' + escapeHtml(cfg.checkoutUpgradeUrl || '#') + '">' +
                '<i class="fas fa-rocket"></i> Contratar plano</a>';
            return;
        }

        badge.textContent = c.status || '—';
        badge.className = 'meu-contrato__badge meu-contrato__badge--' + String(c.status || '').toLowerCase();
        grid.innerHTML =
            '<div class="meu-contrato__metric"><span>Empresa</span><strong>' + escapeHtml(c.empresa_clie || c.nome_clie || '—') + '</strong></div>' +
            '<div class="meu-contrato__metric"><span>Plano</span><strong>' + escapeHtml(c.nome_plano || '—') + '</strong></div>' +
            '<div class="meu-contrato__metric"><span>Valor negociado</span><strong>' + money(c.valor_negociado) + ' / ' + escapeHtml(c.periodicidade || 'mês') + '</strong></div>' +
            '<div class="meu-contrato__metric"><span>Licenças base</span><strong>' + escapeHtml(c.max_usuarios) + '</strong></div>' +
            '<div class="meu-contrato__metric"><span>Início</span><strong>' + fmtDate(c.data_inicio) + '</strong></div>' +
            '<div class="meu-contrato__metric"><span>Vencimento</span><strong>' + fmtDate(c.data_vencimento) + '</strong></div>';

        actions.innerHTML =
            '<a class="mesa-btn mesa-btn--gold" href="' + escapeHtml(cfg.checkoutUpgradeUrl || '#') + '">' +
            '<i class="fas fa-exchange-alt"></i> Alterar plano</a>';
    }

    function renderCota(cota) {
        var el = document.getElementById('mc-cota');
        if (!cota) {
            el.innerHTML = '<p class="admin-esim__field-hint">Cota indisponível.</p>';
            return;
        }
        var maxLabel = cota.ilimitado ? 'Ilimitado' : String(cota.max_usuarios);
        var pct = cota.ilimitado ? 8 : Math.min(100, Math.round((cota.usado / Math.max(cota.max_usuarios, 1)) * 100));
        el.innerHTML =
            '<div><strong>' + cota.usado + '</strong> de <strong>' + maxLabel + '</strong> licenças em uso' +
            (cota.max_addons_usuarios ? ' (base ' + cota.max_base_usuarios + ' + add-ons ' + cota.max_addons_usuarios + ')' : '') +
            '</div>' +
            '<div class="meu-contrato__bar" aria-hidden="true"><i style="width:' + pct + '%"></i></div>';
    }

    function renderPlanos(planos) {
        var el = document.getElementById('mc-planos');
        if (!planos || !planos.length) {
            el.innerHTML = '<p class="admin-esim__field-hint">Nenhum plano disponível na vitrine.</p>';
            return;
        }
        el.innerHTML = planos.map(function (p) {
            var mov = p.movimento || 'troca';
            var isAtual = !!p.atual;
            var btn = isAtual
                ? '<button type="button" class="mesa-btn mesa-btn--ghost" disabled>Plano atual</button>'
                : '<a class="mesa-btn mesa-btn--gold" href="' + escapeHtml(checkoutUrlForPlan(p.id)) + '">' +
                  '<i class="fas fa-check"></i> ' + (mov === 'upgrade' ? 'Fazer upgrade' : mov === 'downgrade' ? 'Fazer downgrade' : 'Selecionar') + '</a>';
            return (
                '<article class="meu-contrato__plano' + (isAtual ? ' is-atual' : '') + '">' +
                '<span class="meu-contrato__tag meu-contrato__tag--' + mov + '">' + movimentoLabel(mov) + '</span>' +
                '<h3>' + escapeHtml(p.nome) + '</h3>' +
                '<div class="preco">' + money(p.valor_mensal) + '<small style="font-size:0.7rem;font-weight:600;color:#64748b"> / mês</small></div>' +
                '<div class="meta">Até ' + escapeHtml(p.max_usuarios >= 999 ? 'ilimitados' : p.max_usuarios) + ' usuários</div>' +
                (p.descricao_beneficios ? '<div class="meta">' + escapeHtml(String(p.descricao_beneficios).slice(0, 140)) + '</div>' : '') +
                btn +
                '</article>'
            );
        }).join('');
    }

    function renderAddons(data) {
        var el = document.getElementById('mc-addons');
        var addons = data.addons || [];
        var sug = data.addon_sugerido;
        var html = '';

        if (addons.length) {
            html += '<div class="meu-contrato__table-wrap"><table class="admin-esim__table"><thead><tr>' +
                '<th>Pacote</th><th>Qtd</th><th>Usuários extra</th><th>Valor</th><th>Status</th></tr></thead><tbody>';
            html += addons.map(function (a) {
                return '<tr>' +
                    '<td>' + escapeHtml(a.nome_addon) + '</td>' +
                    '<td>' + escapeHtml(a.quantidade) + '</td>' +
                    '<td>+' + escapeHtml(a.usuarios_extra) + '</td>' +
                    '<td>' + money(a.mrr_linha) + '</td>' +
                    '<td>' + escapeHtml(a.status) + '</td></tr>';
            }).join('');
            html += '</tbody></table></div>';
        } else {
            html += '<p class="admin-esim__field-hint">Nenhum pacote adicional ativo.</p>';
        }

        if (sug) {
            html +=
                '<div class="meu-contrato__actions">' +
                '<a class="mesa-btn mesa-btn--gold" href="' + escapeHtml(addonCheckoutUrl(sug.id)) + '">' +
                '<i class="fas fa-user-plus"></i> Comprar ' + escapeHtml(sug.nome) +
                ' (' + money(sug.valor_mensal) + ')</a></div>';
        }
        el.innerHTML = html;
    }

    function renderHistorico(lista) {
        var tbody = document.getElementById('mc-historico-body');
        if (!lista || !lista.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="admin-esim__empty">Sem ativações comerciais registradas.</td></tr>';
            return;
        }
        tbody.innerHTML = lista.map(function (h) {
            return '<tr>' +
                '<td>' + fmtDate(h.data) + '</td>' +
                '<td><strong>' + escapeHtml(h.titulo) + '</strong><br><small>' + escapeHtml(h.descricao || '') + '</small></td>' +
                '<td>' + escapeHtml(h.status || '—') + '</td>' +
                '<td>' + money(h.valor) + '</td>' +
                '<td><code>' + escapeHtml(h.referencia || '—') + '</code></td></tr>';
        }).join('');
    }

    async function carregar() {
        elLoading.hidden = false;
        elError.hidden = true;
        elContent.hidden = true;
        try {
            var url = (cfg.bffUrl || '/bff/led/meu-contrato') +
                (cfg.idClie ? ('?id_clie=' + encodeURIComponent(cfg.idClie)) : '');
            var res = await fetch(url, { headers: { Accept: 'application/json' } });
            var payload = await res.json().catch(function () { return {}; });
            if (!res.ok) throw new Error(payload.error || payload.message || 'Falha ao carregar contrato.');
            var data = payload.data || payload;

            renderContrato(data);
            renderCota(data.cota);
            renderPlanos(data.planos_disponiveis || []);
            renderAddons(data);
            renderHistorico(data.historico_comercial || []);

            var hub = document.getElementById('mc-hub-dashboard');
            if (hub) hub.href = cfg.hubDashboardUrl || '#';

            elContent.hidden = false;
        } catch (err) {
            elError.hidden = false;
            elError.textContent = err.message || 'Erro ao carregar Meu Contrato.';
        } finally {
            elLoading.hidden = true;
        }
    }

    carregar();
})();
