/**
 * Chart.js — Radar premium (light mode, neumorfismo suave, grade circular)
 */
(function (global) {
    'use strict';

    var PLUGIN_ID = 'radarCommandCenterFx';
    var BRAND_VIOLET = '#6c5ce7';
    var BRAND_COBALT = '#2563eb';
    var BRAND_CYAN = '#22d3ee';
    var GRID_SILVER = '#E2E8F0';
    var LABEL_SLATE = '#334155';

    function hexToRgba(hex, alpha) {
        var h = (hex || BRAND_VIOLET).replace('#', '');
        if (h.length === 3) {
            h = h.split('').map(function (c) { return c + c; }).join('');
        }
        var r = parseInt(h.slice(0, 2), 16);
        var g = parseInt(h.slice(2, 4), 16);
        var b = parseInt(h.slice(4, 6), 16);
        return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
    }

    function radialFill(chart, borderHex) {
        var ctx = chart.ctx;
        var area = chart.chartArea;
        if (!area) return hexToRgba(borderHex, 0.35);
        var cx = (area.left + area.right) / 2;
        var cy = (area.top + area.bottom) / 2;
        var radius = Math.min(area.right - area.left, area.bottom - area.top) / 2;
        var grad = ctx.createRadialGradient(cx, cy, radius * 0.04, cx, cy, radius);
        grad.addColorStop(0, hexToRgba(BRAND_COBALT, 0.1));
        grad.addColorStop(0.45, hexToRgba(borderHex, 0.38));
        grad.addColorStop(1, hexToRgba(BRAND_CYAN, 0.48));
        return grad;
    }

    function registerPlugins() {
        if (!global.Chart || global.Chart.registry.getPlugin(PLUGIN_ID)) return;

        global.Chart.register({
            id: PLUGIN_ID,
            beforeDatasetDraw: function (chart, args) {
                if (chart.config.type !== 'radar') return;
                var meta = chart.getDatasetMeta(args.index);
                if (!meta || meta.hidden) return;
                var ds = chart.data.datasets[args.index];
                if (!ds || ds.fill === false) return;
                var ctx = chart.ctx;
                ctx.save();
                if (!chart.$radarFxSaved) chart.$radarFxSaved = {};
                chart.$radarFxSaved[args.index] = true;
                ctx.shadowBlur = args.index === 0 ? 32 : 22;
                ctx.shadowColor = hexToRgba(
                    typeof ds.borderColor === 'string' ? ds.borderColor : BRAND_VIOLET,
                    0.2
                );
                ctx.shadowOffsetX = 0;
                ctx.shadowOffsetY = 5;
            },
            afterDatasetDraw: function (chart, args) {
                if (chart.config.type !== 'radar') return;
                if (!chart.$radarFxSaved || !chart.$radarFxSaved[args.index]) return;
                chart.ctx.restore();
                chart.$radarFxSaved[args.index] = false;
            }
        });
    }

    function premiumDataset(opts) {
        opts = opts || {};
        var border = opts.borderColor || BRAND_VIOLET;
        var useFill = opts.fill !== false;
        return {
            label: opts.label || '',
            data: opts.data || [],
            borderColor: border,
            borderWidth: opts.borderWidth != null ? opts.borderWidth : 3,
            tension: opts.tension != null ? opts.tension : 0.4,
            pointBackgroundColor: opts.pointBackgroundColor || '#FFFFFF',
            pointBorderColor: opts.pointBorderColor || border,
            pointBorderWidth: opts.pointBorderWidth != null ? opts.pointBorderWidth : 4,
            pointRadius: function (context) {
                var v = context.dataset.data[context.dataIndex];
                return v > 0 ? (opts.pointRadius != null ? opts.pointRadius : 6) : 0;
            },
            pointHoverRadius: function (context) {
                var v = context.dataset.data[context.dataIndex];
                return v > 0 ? (opts.pointHoverRadius != null ? opts.pointHoverRadius : 8) : 0;
            },
            pointHitRadius: 12,
            fill: useFill,
            borderDash: opts.borderDash || [],
            backgroundColor: useFill
                ? function (context) {
                    return radialFill(context.chart, border);
                }
                : 'transparent'
        };
    }

    function premiumOptions(overrides) {
        overrides = overrides || {};
        var max = overrides.max != null ? overrides.max : 100;
        var min = overrides.min != null ? overrides.min : 0;
        var labelCount = (overrides.labels || []).length;

        return {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 900, easing: 'easeOutQuart' },
            interaction: { mode: 'nearest', intersect: false },
            scales: {
                r: {
                    min: min,
                    max: max,
                    beginAtZero: true,
                    grid: {
                        circular: true,
                        color: overrides.gridColor || GRID_SILVER,
                        lineWidth: 1
                    },
                    angleLines: {
                        color: overrides.angleColor || GRID_SILVER,
                        lineWidth: 1
                    },
                    ticks: {
                        display: overrides.showTicks === true,
                        stepSize: overrides.tickStep,
                        backdropColor: 'transparent',
                        color: '#94a3b8',
                        font: { size: 9, weight: '600' }
                    },
                    pointLabels: {
                        color: overrides.labelColor || LABEL_SLATE,
                        font: {
                            size: overrides.labelSize || (labelCount > 6 ? 10 : 12),
                            weight: '800',
                            family: 'system-ui, -apple-system, Segoe UI, sans-serif'
                        },
                        padding: overrides.labelPadding != null ? overrides.labelPadding : 14,
                        centerPointLabels: true
                    }
                }
            },
            plugins: {
                legend: {
                    position: overrides.legendPosition || 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 16,
                        color: LABEL_SLATE,
                        font: { size: 11, weight: '700' }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(255, 255, 255, 0.98)',
                    titleColor: LABEL_SLATE,
                    bodyColor: '#475569',
                    borderColor: GRID_SILVER,
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 10,
                    displayColors: true,
                    boxPadding: 4
                }
            }
        };
    }

    function create(canvas, config) {
        if (!global.Chart || !canvas) return null;
        registerPlugins();
        var ctx = canvas.getContext('2d');
        var labels = config.labels || [];
        var datasets = (config.datasets || []).map(premiumDataset);
        var options = premiumOptions(Object.assign({ labels: labels }, config.options || {}));
        return new global.Chart(ctx, {
            type: 'radar',
            data: { labels: labels, datasets: datasets },
            options: options,
            plugins: config.plugins || []
        });
    }

    global.ChartRadarCommandCenter = {
        create: create,
        premiumDataset: premiumDataset,
        premiumOptions: premiumOptions,
        registerPlugins: registerPlugins
    };
})(typeof window !== 'undefined' ? window : this);
