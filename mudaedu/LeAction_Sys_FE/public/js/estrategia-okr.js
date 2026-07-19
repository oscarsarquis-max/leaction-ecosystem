/**
 * Hierarquia OKR canônica — Direcionador → Objetivo → KRs
 */
(function (global) {
    'use strict';

    function escapeHtml(s) {
        return String(s || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }

    function renderEstrategiaOkrHierarchy(container, estrategia, opts) {
        if (!container) return;
        opts = opts || {};
        if (!estrategia || !estrategia.direcionador_nome) {
            container.innerHTML = opts.emptyHtml || '';
            container.hidden = true;
            return;
        }
        container.hidden = false;
        var krs = estrategia.krs || [];
        var krsHtml = krs.length
            ? '<ul class="estrategia-okr-hierarchy__krs">' + krs.map(function (kr) {
                return '<li><span class="estrategia-okr-hierarchy__kr-meta">' +
                    escapeHtml(kr.metrica_alvo_placeholder || 'KR') +
                    '</span> ' + escapeHtml(kr.descricao) + '</li>';
            }).join('') + '</ul>'
            : '';

        container.innerHTML =
            '<div class="estrategia-okr-hierarchy" role="group" aria-label="Vínculo estratégico OKR">' +
            '<div class="estrategia-okr-hierarchy__label">Alinhamento estratégico</div>' +
            '<div class="estrategia-okr-hierarchy__path">' +
            '<span class="estrategia-okr-hierarchy__direc">' + escapeHtml(estrategia.direcionador_nome) + '</span>' +
            '<i class="fas fa-chevron-right estrategia-okr-hierarchy__sep" aria-hidden="true"></i>' +
            '<span class="estrategia-okr-hierarchy__obj">' + escapeHtml(estrategia.objetivo_titulo) + '</span>' +
            '</div>' +
            (opts.showKrs !== false ? krsHtml : '') +
            '</div>';
    }

    function findObjetivoNaMatriz(matriz, objetivoId) {
        if (!matriz || !objetivoId) return null;
        var oid = parseInt(objetivoId, 10);
        for (var i = 0; i < matriz.length; i++) {
            var d = matriz[i];
            var objs = d.objetivos || [];
            for (var j = 0; j < objs.length; j++) {
                if (parseInt(objs[j].id, 10) === oid) {
                    return {
                        direcionador_nome: d.nome,
                        direcionador_id: d.id,
                        objetivo_titulo: objs[j].titulo,
                        objetivo_id: objs[j].id,
                        krs: objs[j].krs || []
                    };
                }
            }
        }
        return null;
    }

    global.PanelDxEstrategiaOkr = {
        renderEstrategiaOkrHierarchy: renderEstrategiaOkrHierarchy,
        findObjetivoNaMatriz: findObjetivoNaMatriz
    };
})(typeof window !== 'undefined' ? window : this);
