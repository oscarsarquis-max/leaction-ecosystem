/**
 * Panorama Executivo — dados via /api/dashboard/consolidado
 * Separação: API (Flask/PostgreSQL) → normalização → renderização (Chart.js / ApexCharts)
 */
(function () {
    'use strict';

    /** Catálogo fixo — espelha PANORAMA_DIRECIONADORES_FIXOS no Flask */
    var DIRECIONADORES_CATALOGO = [
        {
            slug: 'digitalizacao_organizacional',
            nome: 'Digitalização Organizacional',
            meta_financeira: 'reducao_custo',
            meta_label: 'Redução de Custo',
            icone: '📉'
        },
        {
            slug: 'engajamento_comunidade',
            nome: 'Engajamento da Comunidade',
            meta_financeira: 'aumento_receita',
            meta_label: 'Aumento de Receita',
            icone: '💰'
        },
        {
            slug: 'capacitacao_docente',
            nome: 'Capacitação Docente',
            meta_financeira: 'reducao_custo',
            meta_label: 'Redução de Custo',
            icone: '📉'
        },
        {
            slug: 'prontidao_tecnologica',
            nome: 'Prontidão Tecnológica',
            meta_financeira: 'reducao_custo',
            meta_label: 'Redução de Custo',
            icone: '📉'
        },
        {
            slug: 'novos_modelos_negocio',
            nome: 'Novos Modelos de Negócio',
            meta_financeira: 'aumento_receita',
            meta_label: 'Aumento de Receita',
            icone: '💰'
        }
    ];

    var FALLBACK_FILTROS = {
        anosLetivos: ['2025', '2026'],
        periodos: ['1º Bimestre', '2º Bimestre', '1º Semestre', '2º Semestre'],
        anoAtivo: '2026',
        periodoAtivo: '1º Bimestre'
    };

    var AREAS_ESCOLARES_PADRAO = [
        'Diretoria',
        'Desenvolvimento Humano',
        'Administração e Secretaria',
        'Pedagógico',
        'Tecnologia da Informação'
    ];
    var SPRINTS_PADRAO = ['Sprint 1', 'Sprint 2'];

    var PALETA = {
        cinza: '#94a3b8',
        dourado: '#d97706',
        violeta: '#6c5ce7',
        violetaClaro: '#a78bfa',
        verde: '#16a34a',
        amarelo: '#eab308',
        vermelho: '#ef4444',
        texto: '#1f2937',
        textoSuave: '#6b7280'
    };

    var PALETA_ANEIS_RADIAIS = [
        '#4A2E80',
        '#6c5ce7',
        '#2563eb',
        '#7c3aed',
        '#0ea5e9'
    ];

    var chartDonut = null;
    var chartHeatmap = null;
    var chartsGaugeDirecionadores = [];

    var pluginTextoCentral = {
        id: 'panoramaTextoCentral',
        afterDraw: function (chart) {
            var area = chart.chartArea;
            if (!area) return;
            var total = chart.data.datasets[0].data.reduce(function (a, b) { return a + b; }, 0);
            var cx = (area.left + area.right) / 2;
            var cy = (area.top + area.bottom) / 2;
            var ctx = chart.ctx;
            ctx.save();
            ctx.beginPath();
            ctx.arc(cx, cy, 48, 0, Math.PI * 2);
            ctx.fillStyle = '#ffffff';
            ctx.fill();
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = PALETA.texto;
            ctx.font = '800 36px system-ui, -apple-system, Segoe UI, sans-serif';
            ctx.fillText(String(total), cx, cy - 10);
            ctx.fillStyle = PALETA.textoSuave;
            ctx.font = '700 12px system-ui, sans-serif';
            ctx.fillText('TOTAL', cx, cy + 18);
            ctx.restore();
        }
    };

    function corSemanticaOkr(pct) {
        if (pct >= 75) return PALETA.verde;
        if (pct >= 50) return PALETA.amarelo;
        return PALETA.vermelho;
    }

    function destruirGraficos() {
        if (chartDonut) { chartDonut.destroy(); chartDonut = null; }
        if (chartHeatmap) { chartHeatmap.destroy(); chartHeatmap = null; }
        chartsGaugeDirecionadores.forEach(function (c) {
            if (c) c.destroy();
        });
        chartsGaugeDirecionadores = [];
    }

    function obterIdMatu() {
        var root = document.getElementById('panorama-executivo');
        var raw = root && root.getAttribute('data-id-matu');
        if (!raw || raw === 'null' || raw === 'undefined') return null;
        var n = parseInt(raw, 10);
        return Number.isNaN(n) ? null : n;
    }

    function normalizarPayloadApi(raw) {
        var status = raw.status_sprints || {};
        var direcionadores = (raw.direcionadores && raw.direcionadores.length)
            ? raw.direcionadores
            : DIRECIONADORES_CATALOGO.map(function (d) {
                return Object.assign({}, d, { percentual: 0, sub_okrs: [] });
            });

        return {
            filtros: FALLBACK_FILTROS,
            kpis: {
                sprintsAtivas: (raw.kpis && raw.kpis.sprints_ativas) || status.ativa || 0,
                tarefasAtrasadas: (raw.kpis && raw.kpis.tarefas_atrasadas) || 0,
                entregasNoPrazo: (raw.kpis && raw.kpis.entregas_no_prazo) || 0
            },
            sprintsStatus: {
                planejada: status.planejada || 0,
                ativa: status.ativa || 0,
                concluida: status.concluida || 0,
                inovacao_analise: status.inovacao_analise || 0
            },
            direcionadores: direcionadores,
            percentualMedio: raw.percentual_medio_direcionadores || 0,
            alocacao: raw.heatmap_alocacao || { areas: [], sprints: [], matriz: [] }
        };
    }

    function fetchPanorama(idMatu) {
        var url = '/api/dashboard/consolidado?id_matu=' + encodeURIComponent(idMatu);
        return fetch(url)
            .then(function (res) { return res.json(); })
            .then(function (json) {
                if (!json.success && json.error) {
                    console.warn('[Panorama] API:', json.error);
                }
                return normalizarPayloadApi(json);
            })
            .catch(function (err) {
                console.error('[Panorama] Falha ao carregar:', err);
                return normalizarPayloadApi({});
            });
    }

    function renderizarKpis(kpis) {
        var mapa = {
            'kpi-sprints-ativas': kpis.sprintsAtivas,
            'kpi-tarefas-atrasadas': kpis.tarefasAtrasadas,
            'kpi-entregas-prazo': kpis.entregasNoPrazo
        };
        Object.keys(mapa).forEach(function (id) {
            var el = document.getElementById(id);
            if (el) el.textContent = mapa[id];
        });
    }

    function renderizarDonut(status) {
        var canvas = document.getElementById('chartPanoramaDonut');
        if (!canvas || typeof Chart === 'undefined') return;

        var valores = [
            status.planejada || 0,
            status.ativa || 0,
            status.concluida || 0,
            status.inovacao_analise || 0
        ];

        chartDonut = new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: [
                    'Planejadas',
                    'Em andamento',
                    'Concluídas',
                    'Inovação (Em Análise)'
                ],
                datasets: [{
                    data: valores,
                    backgroundColor: [
                        PALETA.cinza,
                        PALETA.dourado,
                        PALETA.violeta,
                        PALETA.violetaClaro
                    ],
                    borderWidth: 2,
                    borderColor: '#ffffff',
                    borderAlign: 'inner',
                    spacing: 2,
                    hoverOffset: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '68%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { boxWidth: 10, padding: 12, font: { size: 10, weight: '600' } }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (ctx) {
                                var total = ctx.dataset.data.reduce(function (a, b) { return a + b; }, 0);
                                var pct = total ? Math.round((ctx.parsed / total) * 100) : 0;
                                return ctx.label + ': ' + ctx.parsed + ' (' + pct + '%)';
                            }
                        }
                    }
                }
            },
            plugins: [pluginTextoCentral]
        });
    }

    function escapeHtml(texto) {
        if (!texto) return '';
        return String(texto)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function ordenarDirecionadores(lista) {
        if (!lista || !lista.length) {
            return DIRECIONADORES_CATALOGO.map(function (d) {
                return Object.assign({}, d, { percentual: 0, total_objetivos: 0 });
            });
        }

        return lista.map(function (d) {
            var cat = DIRECIONADORES_CATALOGO.find(function (c) {
                return c.slug === d.slug || c.nome === d.nome;
            });
            return Object.assign({}, cat || {}, d, {
                total_objetivos: d.total_objetivos != null ? d.total_objetivos : 0
            });
        });
    }

    function corGaugeDirecionador(pct, idx) {
        if (pct >= 75) return PALETA.verde;
        if (pct >= 50) return PALETA.amarelo;
        if (pct > 0) return PALETA.vermelho;
        return PALETA_ANEIS_RADIAIS[idx % PALETA_ANEIS_RADIAIS.length] || PALETA.violeta;
    }

    function textoObjetivosVinculados(qtd) {
        var n = parseInt(qtd, 10) || 0;
        return n === 1 ? '1 Objetivo vinculado' : n + ' Objetivos vinculados';
    }

    function criarGaugeDirecionador(alvo, pct, cor) {
        if (!alvo || typeof ApexCharts === 'undefined') return null;

        var chart = new ApexCharts(alvo, {
            series: [pct],
            chart: {
                type: 'radialBar',
                height: 150,
                width: 150,
                fontFamily: 'system-ui, -apple-system, Segoe UI, sans-serif',
                toolbar: { show: false },
                animations: { enabled: true, easing: 'easeinout', speed: 700 }
            },
            plotOptions: {
                radialBar: {
                    startAngle: 0,
                    endAngle: 360,
                    hollow: {
                        size: '62%',
                        background: '#ffffff'
                    },
                    track: {
                        background: 'rgba(226, 232, 240, 0.65)',
                        strokeWidth: '100%',
                        margin: 0
                    },
                    dataLabels: {
                        name: { show: false },
                        value: {
                            show: true,
                            fontSize: '22px',
                            fontWeight: 800,
                            color: cor,
                            offsetY: 5,
                            formatter: function (v) { return Math.round(v) + '%'; }
                        }
                    }
                }
            },
            fill: {
                type: 'solid',
                opacity: 1
            },
            colors: [cor],
            labels: [''],
            stroke: { lineCap: 'round' }
        });
        chart.render();
        return chart;
    }

    function renderizarGridDirecionadores(lista, percentualMedio) {
        var grid = document.getElementById('panorama-direcionadores-grid');
        var mediaEl = document.getElementById('panorama-media-direcionadores');
        if (!grid) return;

        grid.innerHTML = '';
        chartsGaugeDirecionadores.forEach(function (c) {
            if (c) c.destroy();
        });
        chartsGaugeDirecionadores = [];

        var dirs = ordenarDirecionadores(lista);
        var media = percentualMedio != null
            ? Math.round(percentualMedio)
            : (dirs.length
                ? Math.round(dirs.reduce(function (s, d) { return s + (d.percentual || 0); }, 0) / dirs.length)
                : 0);

        if (mediaEl) {
            mediaEl.textContent = 'Média geral: ' + media + '%';
        }

        if (!dirs.length) {
            grid.innerHTML = '<p class="panorama-empty">Nenhum direcionador estratégico cadastrado.</p>';
            return;
        }

        dirs.forEach(function (d, idx) {
            var pct = Math.round(d.percentual || 0);
            var cor = corGaugeDirecionador(pct, idx);
            var gaugeId = 'panorama-dir-gauge-' + idx;
            var card = document.createElement('article');
            card.className = 'panorama-dir-card';
            card.setAttribute('role', 'listitem');
            card.setAttribute('aria-label', (d.nome || 'Direcionador') + ' — ' + pct + '%');
            card.innerHTML =
                '<h4 class="panorama-dir-card__titulo">' + escapeHtml(d.nome || 'Direcionador') + '</h4>' +
                '<div class="panorama-dir-card__gauge" id="' + gaugeId + '" role="img" aria-label="' +
                escapeHtml(d.nome || '') + ': ' + pct + '% de implementação"></div>' +
                '<div class="panorama-dir-card__rodape">' +
                escapeHtml(textoObjetivosVinculados(d.total_objetivos)) +
                '<span class="panorama-dir-card__meta">' + escapeHtml((d.icone || '') + ' ' + (d.meta_label || '')) + '</span>' +
                '</div>';
            grid.appendChild(card);

            var gaugeEl = document.getElementById(gaugeId);
            var chart = criarGaugeDirecionador(gaugeEl, pct, cor);
            if (chart) chartsGaugeDirecionadores.push(chart);
        });
    }

    function renderizarDirecionadores(lista, percentualMedio) {
        renderizarGridDirecionadores(lista, percentualMedio);
    }

    function rotulosSprintsCurto(quantidade) {
        var labels = [];
        for (var i = 0; i < quantidade; i++) {
            labels.push('Sprint ' + (i + 1));
        }
        return labels;
    }

    function garantirAlocacaoHeatmap(alocacao) {
        var areas = (alocacao && alocacao.areas) || [];
        var sprintsApi = (alocacao && alocacao.sprints) || [];
        var matriz = (alocacao && alocacao.matriz) || [];
        var numColunas = sprintsApi.length;
        if (!numColunas && matriz.length && matriz[0]) {
            numColunas = matriz[0].length;
        }

        if (areas.length && numColunas) {
            return {
                areas: areas,
                sprints: rotulosSprintsCurto(numColunas),
                matriz: matriz,
                isTemplate: false
            };
        }
        return {
            areas: AREAS_ESCOLARES_PADRAO.slice(),
            sprints: SPRINTS_PADRAO.slice(),
            matriz: AREAS_ESCOLARES_PADRAO.map(function () {
                return SPRINTS_PADRAO.map(function () { return 0; });
            }),
            isTemplate: true
        };
    }

    function atualizarHintHeatmap(isTemplate) {
        var hint = document.getElementById('heatmap-template-hint');
        if (!hint) return;
        hint.style.display = isTemplate ? 'block' : 'none';
    }

    function renderizarHeatmap(alocacao) {
        var alvo = document.getElementById('chartPanoramaHeatmap');
        if (!alvo || typeof ApexCharts === 'undefined') return;

        var dados = garantirAlocacaoHeatmap(alocacao);
        atualizarHintHeatmap(dados.isTemplate);
        alvo.innerHTML = '';

        var series = dados.areas.map(function (area, rowIdx) {
            return {
                name: area,
                data: dados.sprints.map(function (sprint, colIdx) {
                    var val = (dados.matriz[rowIdx] && dados.matriz[rowIdx][colIdx] != null)
                        ? dados.matriz[rowIdx][colIdx]
                        : 0;
                    return { x: sprint, y: val };
                })
            };
        });

        chartHeatmap = new ApexCharts(alvo, {
            series: series,
            chart: {
                type: 'heatmap',
                height: 340,
                fontFamily: 'system-ui, sans-serif',
                toolbar: { show: false }
            },
            dataLabels: {
                enabled: true,
                style: { fontSize: '11px', fontWeight: 700, colors: ['#fff'] },
                formatter: function (val) { return val + '%'; }
            },
            plotOptions: {
                heatmap: {
                    shadeIntensity: 0.45,
                    radius: 6,
                    useFillColorAsStroke: false,
                    colorScale: {
                        ranges: [
                            { from: 0, to: 40, name: 'Aguardando', color: '#cbd5e1' },
                            { from: 41, to: 65, name: 'Atenção', color: '#eab308' },
                            { from: 66, to: 100, name: 'Sobrecarga', color: '#ef4444' }
                        ]
                    }
                }
            },
            xaxis: {
                type: 'category',
                categories: dados.sprints,
                labels: {
                    style: { fontSize: '10px', fontWeight: 600 },
                    rotate: -35,
                    rotateAlways: dados.sprints.length > 4,
                    hideOverlappingLabels: true
                }
            },
            yaxis: {
                labels: { style: { fontSize: '11px', fontWeight: 600 } }
            },
            tooltip: {
                y: {
                    formatter: function (val, opts) {
                        if (dados.isTemplate) {
                            return 'Aguardando alocação (template)';
                        }
                        return val + '% de carga alocada';
                    }
                }
            },
            legend: { show: true, position: 'bottom', fontSize: '11px' }
        });
        chartHeatmap.render();
    }

    function popularFiltros(filtros) {
        var selAno = document.getElementById('panorama-filtro-ano');
        var selPeriodo = document.getElementById('panorama-filtro-periodo');
        if (!selAno || !selPeriodo) return;

        selAno.innerHTML = filtros.anosLetivos.map(function (a) {
            var sel = a === filtros.anoAtivo ? ' selected' : '';
            return '<option value="' + a + '"' + sel + '>' + a + '</option>';
        }).join('');

        selPeriodo.innerHTML = filtros.periodos.map(function (p) {
            var sel = p === filtros.periodoAtivo ? ' selected' : '';
            return '<option value="' + p + '"' + sel + '>' + p + '</option>';
        }).join('');
    }

    function renderizarPanorama(dados) {
        destruirGraficos();
        renderizarKpis(dados.kpis);
        renderizarDonut(dados.sprintsStatus);
        renderizarDirecionadores(dados.direcionadores, dados.percentualMedio);
        renderizarHeatmap(dados.alocacao);
    }

    function iniciarPanoramaExecutivo() {
        var root = document.getElementById('panorama-executivo');
        if (!root) return;

        var idMatu = obterIdMatu();

        function carregarERenderizar() {
            if (!idMatu) {
                renderizarPanorama(normalizarPayloadApi({}));
                return;
            }
            fetchPanorama(idMatu).then(renderizarPanorama);
        }

        popularFiltros(FALLBACK_FILTROS);
        carregarERenderizar();

        var selAno = document.getElementById('panorama-filtro-ano');
        var selPeriodo = document.getElementById('panorama-filtro-periodo');
        function onFiltroChange() {
            // TODO: repassar ano/período à API quando o backend filtrar por período letivo
            carregarERenderizar();
        }
        if (selAno) selAno.addEventListener('change', onFiltroChange);
        if (selPeriodo) selPeriodo.addEventListener('change', onFiltroChange);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', iniciarPanoramaExecutivo);
    } else {
        iniciarPanoramaExecutivo();
    }
})();
