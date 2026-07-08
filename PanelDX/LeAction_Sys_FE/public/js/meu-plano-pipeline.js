/**
 * Meu Plano — blocos do Relatório que estão no pipeline (Mesa/Kanban)
 * Renderiza seção visível com botão "Devolver ao backlog".
 */
(function (global) {
    'use strict';

    function statusLabel(stat) {
        var s = String(stat || '').toLowerCase().trim().replace(/\s+/g, '_');
        if (s === 'em_analise') return 'Em análise (Kanban)';
        if (['planejada_backlog', 'planejada', 'planejado', 'pendente'].indexOf(s) >= 0) return 'No plano (Planejada)';
        if (['em_andamento', 'ativa', 'em_progresso'].indexOf(s) >= 0) return 'Em andamento';
        return s || 'No pipeline';
    }

    function tipoMesaLabel(tipo) {
        var t = String(tipo || '').toLowerCase();
        if (t === 'organizacional') return 'Mesa Organizacional';
        if (t === 'pedagogico' || t === 'pedagogica') return 'Mesa Pedagógica';
        return 'Mesa de Inovação';
    }

    function escapeHtml(str) {
        return String(str || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function renderPanel(items) {
        if (!items.length) {
            return (
                '<div class="plano-pipeline-panel plano-pipeline-panel--empty">' +
                    '<div class="plano-pipeline-panel__icon"><i class="fas fa-info-circle"></i></div>' +
                    '<div>' +
                        '<h3 class="plano-pipeline-panel__title">Blocos do Relatório no plano</h3>' +
                        '<p class="plano-pipeline-panel__lead">' +
                            'Nenhum bloco do <strong>Relatório de Contexto</strong> está no plano agora. ' +
                            'Os cards azuis abaixo são sprints da <strong>Gênese IA</strong> — eles não têm botão de devolver ao backlog.' +
                        '</p>' +
                        '<p class="plano-pipeline-panel__steps">' +
                            '<strong>Fluxo:</strong> Relatório → Mesa de Inovação → Kanban (Inovação) → Planejada → ' +
                            '<span class="plano-pipeline-panel__highlight">Devolver ao backlog</span>' +
                        '</p>' +
                    '</div>' +
                '</div>'
            );
        }

        var cards = items.map(function (item) {
            return (
                '<article class="plano-pipeline-card">' +
                    '<div class="plano-pipeline-card__badges">' +
                        '<span class="plano-pipeline-card__badge plano-pipeline-card__badge--dx">DX</span>' +
                        '<span class="plano-pipeline-card__badge plano-pipeline-card__badge--status">' + escapeHtml(statusLabel(item.stat_sprn)) + '</span>' +
                    '</div>' +
                    '<p class="plano-pipeline-card__mesa">' + escapeHtml(tipoMesaLabel(item.tipo_mesa)) + '</p>' +
                    '<h4 class="plano-pipeline-card__title">' + escapeHtml(item.bloco_nome || item.nome || 'Bloco no plano') + '</h4>' +
                    '<p class="plano-pipeline-card__desc">' + escapeHtml(item.desc || 'Sprint originada na Mesa de Inovação.') + '</p>' +
                    '<button type="button" class="plano-pipeline-card__devolver btn-devolver-mesa-plano" data-sprn-id="' + escapeHtml(String(item.id_sprn)) + '">' +
                        '<i class="fas fa-undo"></i> Devolver ao backlog do relatório' +
                    '</button>' +
                '</article>'
            );
        }).join('');

        return (
            '<div class="plano-pipeline-panel plano-pipeline-panel--active">' +
                '<header class="plano-pipeline-panel__head">' +
                    '<h3 class="plano-pipeline-panel__title"><i class="fas fa-layer-group"></i> Blocos do Relatório no plano</h3>' +
                    '<p class="plano-pipeline-panel__lead">Clique no botão vermelho abaixo para devolver ao backlog.</p>' +
                '</header>' +
                '<div class="plano-pipeline-cards">' + cards + '</div>' +
            '</div>'
        );
    }

    function bindDevolverButtons(root) {
        root.querySelectorAll('.btn-devolver-mesa-plano').forEach(function (btn) {
            if (btn.dataset.bound) return;
            btn.dataset.bound = '1';
            btn.addEventListener('click', function () {
                var id = btn.getAttribute('data-sprn-id');
                if (global.devolverSprintRelatorio) {
                    global.devolverSprintRelatorio(id, btn);
                } else if (global.PanelRelatorioBlocos && global.PanelRelatorioBlocos.devolverAoBacklog) {
                    global.PanelRelatorioBlocos.devolverAoBacklog(id, btn);
                }
            });
        });
    }

    function init() {
        var root = document.getElementById('plano-relatorio-pipeline');
        if (!root) return;

        var page = document.getElementById('meu-plano-page');
        var idClie = (page && page.getAttribute('data-id-clie')) || root.getAttribute('data-id-clie');
        if (!idClie) {
            root.innerHTML = renderPanel([]);
            return;
        }

        fetch('/api/sprints/blocos-pipeline?id_clie=' + encodeURIComponent(idClie), { credentials: 'same-origin' })
            .then(function (res) { return res.ok ? res.json() : { items: [] }; })
            .then(function (data) {
                var items = (data && data.items) || [];
                root.innerHTML = renderPanel(items);
                bindDevolverButtons(root);
            })
            .catch(function () {
                root.innerHTML = renderPanel([]);
            });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    global.PanelMeuPlanoPipeline = { init: init };
})(window);
