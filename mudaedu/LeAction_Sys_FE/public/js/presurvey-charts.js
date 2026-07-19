(function () {
    'use strict';

    function readPayload() {
        var el = document.getElementById('presurvey-chart-data');
        if (!el) return null;
        try {
            return JSON.parse(el.textContent || '{}');
        } catch (err) {
            console.error('[presurvey-charts] JSON inválido:', err);
            return null;
        }
    }

    function calcMedia(lista) {
        if (!lista || !lista.length) return 0;
        return lista.reduce(function (a, b) { return a + b; }, 0) / lista.length;
    }

    function buildDominioSeries(rawScores) {
        var mapaNoveDominios = {
            'Dom 1': 'Dom 1: Estratégia Digital',
            'Dom 2': 'Dom 2: Modelo de Negócio Digital',
            'Dom 3': 'Dom 3: Cultura de Inovação',
            'Dom 4': 'Dom 4: Cultura de Dados',
            'Dom 5': 'Dom 5: Cultura de Colaboração',
            'Dom 6': 'Dom 6: Governança Digital',
            'Dom 7': 'Dom 7: Plataformas Digitais',
            'Dom 8': 'Dom 8: Capacidades Digitais',
            'Dom 9': 'Dom 9: Métricas Digitais'
        };
        var acumulador = {};
        Object.keys(mapaNoveDominios).forEach(function (slug) {
            acumulador[slug] = { label: mapaNoveDominios[slug], P: [], F: [], M: [] };
        });

        Object.keys(rawScores || {}).forEach(function (key) {
            var escopoEncontrado = false;
            Object.keys(mapaNoveDominios).forEach(function (slug) {
                var nome = mapaNoveDominios[slug].split(':')[1].trim();
                if (key.indexOf(slug) !== -1 || key.indexOf(nome) !== -1) {
                    if (rawScores[key].P !== undefined) acumulador[slug].P.push(parseFloat(rawScores[key].P) || 0);
                    if (rawScores[key].F !== undefined) acumulador[slug].F.push(parseFloat(rawScores[key].F) || 0);
                    if (rawScores[key].M !== undefined) acumulador[slug].M.push(parseFloat(rawScores[key].M) || 0);
                    escopoEncontrado = true;
                }
            });
            if (!escopoEncontrado) {
                var n = key.replace(/\D/g, '');
                var target = 'Dom ' + n;
                if (n && acumulador[target]) {
                    if (rawScores[key].P !== undefined) acumulador[target].P.push(parseFloat(rawScores[key].P) || 0);
                    if (rawScores[key].F !== undefined) acumulador[target].F.push(parseFloat(rawScores[key].F) || 0);
                    if (rawScores[key].M !== undefined) acumulador[target].M.push(parseFloat(rawScores[key].M) || 0);
                }
            }
        });

        var labels = [];
        var pData = [];
        var fData = [];
        var mData = [];
        Object.keys(acumulador).forEach(function (slug) {
            var item = acumulador[slug];
            labels.push(item.label);
            pData.push(calcMedia(item.P));
            fData.push(calcMedia(item.F));
            mData.push(calcMedia(item.M));
        });
        return { labels: labels, pData: pData, fData: fData, mData: mData };
    }

    function getRadarLib() {
        if (typeof PresurveyRadarChart !== 'undefined') return PresurveyRadarChart;
        if (typeof ChartRadarCommandCenter !== 'undefined') return ChartRadarCommandCenter;
        return null;
    }

    function initPresurveyCharts() {
        var RadarChart = getRadarLib();
        if (typeof Chart === 'undefined' || !RadarChart) {
            return false;
        }

        var payload = readPayload();
        if (!payload) return false;

        var labels = payload.labels || [];
        var pData = payload.pData || [];
        var fData = payload.fData || [];
        var mData = payload.mData || [];

        if (pData.length && labels.length) {
            var maxPIdx = pData.indexOf(Math.max.apply(null, pData));
            var strPilar = document.getElementById('strPilarForte');
            if (strPilar) strPilar.textContent = labels[maxPIdx] || '--';
        }

        var canvasPresurvey = document.getElementById('radarChartPresurvey');
        if (canvasPresurvey && !Chart.getChart(canvasPresurvey)) {
            RadarChart.create(canvasPresurvey, {
                labels: labels,
                datasets: [
                    { label: 'Presente (Realidade)', data: pData, borderColor: '#6c5ce7' },
                    { label: 'Futuro (Ambição)', data: fData, borderColor: '#d97706' },
                    {
                        label: 'Benchmark Mercado',
                        data: mData,
                        borderColor: '#94a3b8',
                        fill: false,
                        borderWidth: 2,
                        borderDash: [6, 4],
                        pointRadius: 0,
                        pointHoverRadius: 0
                    }
                ],
                options: {
                    max: 5,
                    min: 0,
                    labelSize: 12,
                    labelColor: '#334155',
                    legendPosition: 'bottom'
                }
            });
        }

        var doma = buildDominioSeries(payload.dominios || {});
        var canvasDominios = document.getElementById('radarChartDominios');
        if (canvasDominios) {
            if (doma.labels.length > 0 && !Chart.getChart(canvasDominios)) {
                RadarChart.create(canvasDominios, {
                    labels: doma.labels,
                    datasets: [
                        { label: 'Domínio Presente (P)', data: doma.pData, borderColor: '#2563eb' },
                        { label: 'Domínio Futuro (F)', data: doma.fData, borderColor: '#d97706' },
                        {
                            label: 'Domínio Mercado (M)',
                            data: doma.mData,
                            borderColor: '#10b981',
                            fill: false,
                            borderWidth: 2,
                            borderDash: [4, 4],
                            pointRadius: 4
                        }
                    ],
                    options: {
                        max: 5,
                        min: 0,
                        labelSize: 10,
                        labelColor: '#334155',
                        legendPosition: 'bottom'
                    }
                });
            } else if (doma.labels.length === 0) {
                canvasDominios.parentElement.innerHTML =
                    "<p style='text-align:center;color:#94a3b8;font-style:italic;padding:20px;'>" +
                    'Dados de granularidade por Domínio indisponíveis para esta conta institucional.</p>';
            }
        }

        return true;
    }

    function boot() {
        if (initPresurveyCharts()) return;
        var attempts = 0;
        var timer = setInterval(function () {
            attempts += 1;
            if (initPresurveyCharts() || attempts >= 50) clearInterval(timer);
        }, 100);
    }

    window.addEventListener('load', boot);
})();
