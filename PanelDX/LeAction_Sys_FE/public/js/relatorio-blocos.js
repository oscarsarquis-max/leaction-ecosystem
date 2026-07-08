/**
 * Relatório de Contexto — backlog de blocos CTDI
 * Fluxo: Backlog → Mesa de Inovação → Kanban Inovação → Planejada (devolver volta ao backlog)
 */
(function (global) {
    'use strict';

    var diagClickBound = false;

    function blockKey(block) {
        return String((block && (block.id_bloc || block.nome)) || '').trim();
    }

    function escapeHtml(str) {
        return String(str || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function truncateDesc(text, max) {
        if (!text || text.length <= max) return text || '';
        return text.substring(0, max).trim() + '…';
    }

    function gapClass(gap) {
        return (parseFloat(gap) || 0) >= 0.5 ? 'tag--gap-high' : 'tag--gap-mid';
    }

    function statusPlanoLabel(stat) {
        var s = String(stat || '').toLowerCase().trim().replace(/\s+/g, '_');
        if (s === 'em_analise') return 'Em análise no Kanban';
        if (['planejada_backlog', 'planejada', 'planejado', 'pendente', 'agendada', 'agendado'].indexOf(s) >= 0) return 'No plano';
        if (['em_andamento', 'ativa', 'em_progresso', 'executando'].indexOf(s) >= 0) return 'Em andamento';
        return 'No pipeline';
    }

    function groupByDomain(blocks) {
        var map = {};
        blocks.forEach(function (block) {
            var dom = block.dominio || 'Outros';
            if (!map[dom]) map[dom] = { dominio: dom, gap: parseFloat(block.gap) || 0, blocks: [] };
            map[dom].blocks.push(block);
        });
        return Object.keys(map).map(function (k) { return map[k]; }).sort(function (a, b) {
            if (b.gap !== a.gap) return b.gap - a.gap;
            return a.dominio.localeCompare(b.dominio, 'pt-BR');
        });
    }

    function enqueueBlocoMesa(block) {
        var payload = {
            nome: block.nome || '',
            id_bloc: block.id_bloc || null,
            id_doma: block.id_doma || null,
            gap: block.gap != null ? String(block.gap) : null,
            desc: block.desc || '',
            dominio: block.dominio || '',
            dimensao: block.dimensao || '',
            origem: 'relatorio-maturidade',
            criado_em: new Date().toISOString()
        };
        var fila = [];
        try {
            var rawFila = sessionStorage.getItem('paneldx_mesa_fila_blocos');
            if (rawFila) {
                var parsed = JSON.parse(rawFila);
                if (Array.isArray(parsed)) fila = parsed;
            }
        } catch (err) {
            console.warn('Não foi possível ler fila da mesa:', err);
        }
        var key = blockKey(block);
        fila = fila.filter(function (b) { return blockKey(b) !== key; });
        fila.push(payload);
        try {
            sessionStorage.setItem('paneldx_mesa_fila_blocos', JSON.stringify(fila));
            sessionStorage.setItem('paneldx_sprint_prioridade', JSON.stringify(payload));
        } catch (err) {
            console.warn('Não foi possível salvar fila na sessão:', err);
        }
        global.location.href = '/projeto/mesa-inovacao?bloco=' + encodeURIComponent(payload.nome);
    }

    function goToMesa(block) {
        enqueueBlocoMesa(block);
    }

    function devolverAoBacklog(idSprn, btn) {
        if (!idSprn) return Promise.resolve(false);
        var el = btn || null;
        var prevHtml = el ? el.innerHTML : '';
        if (el) {
            el.disabled = true;
            el.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Devolvendo…';
        }
        return fetch('/api/sprints/devolver-relatorio', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ id_sprn: parseInt(idSprn, 10) })
        })
            .then(function (res) { return res.json().then(function (data) { return { ok: res.ok, data: data }; }); })
            .then(function (result) {
                if (result.ok && result.data.success) {
                    global.location.reload();
                    return true;
                }
                if (el) {
                    el.disabled = false;
                    el.innerHTML = prevHtml;
                }
                alert((result.data && result.data.error) || 'Não foi possível devolver ao backlog.');
                return false;
            })
            .catch(function () {
                if (el) {
                    el.disabled = false;
                    el.innerHTML = prevHtml;
                }
                alert('Erro de conexão ao devolver ao backlog.');
                return false;
            });
    }

    function renderBacklogCard(block, pipelineItem) {
        var key = blockKey(block);
        var gap = parseFloat(block.gap) || 0;
        var cta = pipelineItem
            ? '<button type="button" class="backlog-card__cta backlog-card__cta--devolver" data-action="devolver-backlog" data-id-sprn="' + escapeHtml(String(pipelineItem.id_sprn)) + '">' +
                '<i class="fas fa-undo"></i> Devolver ao backlog' +
              '</button>'
            : '<button type="button" class="backlog-card__cta" data-action="mesa-inovacao" data-block-key="' + escapeHtml(key) + '"' +
                ' data-bloco-nome="' + escapeHtml(block.nome) + '"' +
                ' data-id-bloc="' + escapeHtml(String(block.id_bloc || '')) + '"' +
                ' data-id-doma="' + escapeHtml(String(block.id_doma || '')) + '"' +
                ' data-gap="' + escapeHtml(block.gap != null ? String(block.gap) : '') + '">' +
                '<i class="fas fa-lightbulb"></i> Enviar à Mesa de Inovação' +
              '</button>';
        var statusTag = pipelineItem
            ? '<span class="tag tag--plano-status">' + escapeHtml(statusPlanoLabel(pipelineItem.stat_sprn)) + '</span>'
            : '';

        return (
            '<article class="backlog-card' + (pipelineItem ? ' backlog-card--em-plano' : '') + '" data-block-key="' + escapeHtml(key) + '">' +
                '<div class="backlog-card__top">' +
                    '<h6 class="backlog-card__title">' + escapeHtml(block.nome) + '</h6>' +
                    '<span class="tag tag--domain">' + escapeHtml(block.dimensao) + '</span>' +
                    statusTag +
                '</div>' +
                '<p class="backlog-card__desc">' + escapeHtml(truncateDesc(block.desc, 160)) + '</p>' +
                '<div class="backlog-card__footer">' +
                    '<div class="backlog-card__metrics">' +
                        '<span>Realidade: <strong>' + (parseFloat(block.score_pres) || 0).toFixed(2) + '</strong></span>' +
                        '<span>Ambição: <strong>' + (parseFloat(block.score_fut) || 0).toFixed(2) + '</strong></span>' +
                        '<span class="tag ' + gapClass(gap) + '">Lacuna: ' + gap.toFixed(2) + '</span>' +
                    '</div>' +
                    cta +
                '</div>' +
            '</article>'
        );
    }

    function fetchPipelineData(idClie) {
        if (!idClie) return Promise.resolve({ keys: new Set(), map: new Map() });
        return fetch('/api/sprints/blocos-pipeline?id_clie=' + encodeURIComponent(idClie), { credentials: 'same-origin' })
            .then(function (res) { return res.ok ? res.json() : { keys: [], items: [] }; })
            .then(function (data) {
                var items = (data && data.items) || [];
                var keys = (data && data.keys) || [];
                var map = new Map();
                items.forEach(function (item) {
                    var key = String(item.block_key || '').trim();
                    if (key) map.set(key, item);
                });
                keys.forEach(function (k) {
                    var key = String(k).trim();
                    if (key && !map.has(key)) map.set(key, { block_key: key });
                });
                return { keys: new Set(Array.from(map.keys())), map: map };
            })
            .catch(function () { return { keys: new Set(), map: new Map() }; });
    }

    function fetchPipelineKeys(idClie) {
        return fetchPipelineData(idClie).then(function (data) { return data.keys; });
    }

    function applyPlanoStateToTopCards(pipelineMap) {
        document.querySelectorAll('#action-cards-grid .action-card').forEach(function (card) {
            var key = (card.getAttribute('data-block-key') || '').trim();
            var item = key ? pipelineMap.get(key) : null;
            var cta = card.querySelector('[data-action="mesa-inovacao"], [data-action="devolver-backlog"]');
            var tags = card.querySelector('.action-card__tags');
            var oldBadge = card.querySelector('.tag--plano-status');
            if (oldBadge) oldBadge.remove();

            if (item && item.id_sprn && cta) {
                card.classList.add('action-card--em-plano');
                cta.setAttribute('data-action', 'devolver-backlog');
                cta.setAttribute('data-id-sprn', String(item.id_sprn));
                cta.className = 'action-card__cta action-card__cta--devolver';
                cta.innerHTML = '<i class="fas fa-undo"></i> Devolver ao backlog';
                if (tags) {
                    var span = document.createElement('span');
                    span.className = 'tag tag--plano-status';
                    span.textContent = statusPlanoLabel(item.stat_sprn);
                    tags.appendChild(span);
                }
            } else if (cta) {
                card.classList.remove('action-card--em-plano');
                cta.setAttribute('data-action', 'mesa-inovacao');
                cta.removeAttribute('data-id-sprn');
                cta.className = 'action-card__cta action-card__cta--mesa';
                cta.innerHTML = 'Abrir na Mesa de Inovação';
            }
            card.style.display = '';
        });
    }

    function isDiagActionScope(el) {
        return !!(el && el.closest && el.closest('#diagnostico-page, #backlog-modal'));
    }

    function bindDiagnosticoActions(blocksByKey) {
        if (diagClickBound) return;
        diagClickBound = true;

        document.addEventListener('click', function (e) {
            if (!document.getElementById('diagnostico-blocos-data')) return;

            var devolverBtn = e.target.closest('[data-action="devolver-backlog"]');
            if (devolverBtn && isDiagActionScope(devolverBtn)) {
                e.preventDefault();
                e.stopPropagation();
                devolverAoBacklog(devolverBtn.getAttribute('data-id-sprn'), devolverBtn);
                return;
            }

            var mesaBtn = e.target.closest('[data-action="mesa-inovacao"]');
            if (!mesaBtn || !isDiagActionScope(mesaBtn)) return;

            e.preventDefault();
            e.stopPropagation();

            var key = mesaBtn.getAttribute('data-block-key');
            var block = key ? blocksByKey.get(key) : null;
            if (!block) {
                block = {
                    nome: mesaBtn.getAttribute('data-bloco-nome') || '',
                    id_bloc: mesaBtn.getAttribute('data-id-bloc') || null,
                    id_doma: mesaBtn.getAttribute('data-id-doma') || null,
                    gap: mesaBtn.getAttribute('data-gap') || null
                };
            }
            goToMesa(block);
        });
    }

    function initDiagnosticoPage() {
        var dataEl = document.getElementById('diagnostico-blocos-data');
        if (!dataEl) return null;

        var catalog;
        try {
            catalog = JSON.parse(dataEl.textContent || '{}');
        } catch (err) {
            console.warn('Catálogo de blocos inválido:', err);
            return null;
        }

        var idMatu = catalog.id_matu;
        var idClie = catalog.id_clie;
        var pageRoot = document.getElementById('diagnostico-page');
        if (!idClie && pageRoot) idClie = pageRoot.getAttribute('data-id-clie');
        var allBlocks = catalog.blocks || [];
        var topCount = catalog.topCount || 5;
        if (!idMatu || !allBlocks.length) return null;

        var blocksByKey = new Map();
        allBlocks.forEach(function (block) {
            blocksByKey.set(blockKey(block), block);
        });
        var topKeys = new Set(allBlocks.slice(0, topCount).map(blockKey));

        var backlogModal = document.getElementById('backlog-modal');
        var backlogOpenBtn = document.getElementById('backlog-open-btn');
        var backlogBody = document.getElementById('backlog-modal-body');
        var backlogSubtitle = document.getElementById('backlog-modal-subtitle');
        var backlogOpenLabel = document.getElementById('backlog-open-label');
        var pipelineKeys = new Set();
        var pipelineMap = new Map();

        bindDiagnosticoActions(blocksByKey);

        function openBacklog() {
            if (!backlogModal) return;
            if (backlogModal.parentElement !== document.body) {
                document.body.appendChild(backlogModal);
            }
            backlogModal.classList.add('is-open');
            backlogModal.setAttribute('aria-hidden', 'false');
            document.body.classList.add('backlog-modal-open');
        }

        function closeBacklog() {
            if (!backlogModal) return;
            backlogModal.classList.remove('is-open');
            backlogModal.setAttribute('aria-hidden', 'true');
            document.body.classList.remove('backlog-modal-open');
        }

        if (backlogOpenBtn) {
            backlogOpenBtn.addEventListener('click', function (e) {
                e.preventDefault();
                openBacklog();
            });
        }

        if (backlogModal) {
            backlogModal.querySelectorAll('[data-backlog-close]').forEach(function (el) {
                el.addEventListener('click', closeBacklog);
            });
            document.addEventListener('keydown', function (e) {
                if (e.key === 'Escape' && backlogModal.classList.contains('is-open')) closeBacklog();
            });
        }

        function renderBacklog() {
            var backlogBlocks = allBlocks.filter(function (b) {
                return !topKeys.has(blockKey(b));
            });
            var backlogDisponivel = backlogBlocks.filter(function (b) {
                return !pipelineKeys.has(blockKey(b));
            });

            applyPlanoStateToTopCards(pipelineMap);

            if (backlogBody) {
                if (!backlogBlocks.length) {
                    backlogBody.innerHTML = '<p class="backlog-modal__empty">Nenhum bloco adicional no backlog.</p>';
                } else {
                    backlogBody.innerHTML = groupByDomain(backlogBlocks).map(function (group) {
                        return (
                            '<section class="backlog-domain-group">' +
                                '<header class="backlog-domain-group__head">' +
                                    '<h5 class="backlog-domain-group__title">' + escapeHtml(group.dominio) + '</h5>' +
                                    '<div class="backlog-domain-group__meta">' +
                                        '<span class="tag ' + gapClass(group.gap) + '">Lacuna: ' + group.gap.toFixed(2) + '</span>' +
                                        '<span class="backlog-domain-group__count">' + group.blocks.length + ' bloco' + (group.blocks.length > 1 ? 's' : '') + '</span>' +
                                    '</div>' +
                                '</header>' +
                                '<div class="backlog-cards-list">' +
                                    group.blocks.map(function (block) {
                                        return renderBacklogCard(block, pipelineMap.get(blockKey(block)));
                                    }).join('') +
                                '</div>' +
                            '</section>'
                        );
                    }).join('');
                }
            }

            if (backlogSubtitle) {
                backlogSubtitle.textContent = backlogDisponivel.length + ' bloco' + (backlogDisponivel.length === 1 ? '' : 's') +
                    ' livres — os demais no plano podem ser devolvidos com um clique.';
            }
            if (backlogOpenLabel) {
                backlogOpenLabel.textContent = 'Ver demais blocos por lacuna (' + backlogDisponivel.length + ' livres)';
            }
        }

        function refreshPipeline() {
            return fetchPipelineData(idClie).then(function (data) {
                pipelineKeys = data.keys;
                pipelineMap = data.map;
                renderBacklog();
            });
        }

        refreshPipeline();
        return { refresh: refreshPipeline };
    }

    global.PanelRelatorioBlocos = {
        blockKey: blockKey,
        initDiagnosticoPage: initDiagnosticoPage,
        fetchPipelineKeys: fetchPipelineKeys,
        fetchPipelineData: fetchPipelineData,
        devolverAoBacklog: devolverAoBacklog
    };
    global.devolverSprintRelatorio = devolverAoBacklog;
})(window);
