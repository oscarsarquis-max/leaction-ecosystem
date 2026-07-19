/**
 * Widget de Agenda Executiva — mini-calendário + bloco de notas
 * Consome /api/agenda-eventos (proxy Node → Flask)
 */
(function () {
    'use strict';

    var MESES = [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ];
    var DIAS_SEM = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];

    var idMatu = null;
    var viewYear = null;
    var viewMonth = null; // 0-11
    var selectedDate = null; // YYYY-MM-DD
    var eventosMes = [];
    var eventoModal = null;

    function pad2(n) { return n < 10 ? '0' + n : String(n); }

    function hojeISO() {
        var d = new Date();
        return d.getFullYear() + '-' + pad2(d.getMonth() + 1) + '-' + pad2(d.getDate());
    }

    function mesAnoISO(y, m) {
        return y + '-' + pad2(m + 1);
    }

    function dataEventoParaDia(iso) {
        if (!iso) return '';
        return String(iso).slice(0, 10);
    }

    function formatarDataBR(iso) {
        if (!iso) return '—';
        var p = String(iso).slice(0, 10).split('-');
        if (p.length !== 3) return iso;
        return p[2] + '/' + p[1] + '/' + p[0];
    }

    function diasComEventos() {
        var map = {};
        eventosMes.forEach(function (ev) {
            var d = dataEventoParaDia(ev.data_evento);
            if (d) map[d] = true;
        });
        return map;
    }

    function eventosDoDia(diaISO) {
        return eventosMes.filter(function (ev) {
            return dataEventoParaDia(ev.data_evento) === diaISO;
        });
    }

    function getIdMatu() {
        var root = document.getElementById('dashboard-agenda');
        if (!root) return null;
        var v = root.getAttribute('data-id-matu');
        return v ? String(v) : null;
    }

    function fetchJson(url, opts) {
        return fetch(url, opts || {}).then(function (r) {
            return r.json().then(function (data) {
                if (!r.ok) throw new Error((data && data.error) || 'Erro na requisição');
                return data;
            });
        });
    }

    function carregarEventos() {
        if (!idMatu) return Promise.resolve();
        var mes = mesAnoISO(viewYear, viewMonth);
        return fetchJson('/api/agenda-eventos?id_matu=' + encodeURIComponent(idMatu) + '&mes=' + mes)
            .then(function (data) {
                eventosMes = (data && data.eventos) || [];
            })
            .catch(function (err) {
                console.error('Agenda:', err);
                eventosMes = [];
            });
    }

    function renderCalendario() {
        var grid = document.getElementById('agenda-cal-grid');
        var titulo = document.getElementById('agenda-mes-titulo');
        if (!grid || !titulo) return;

        titulo.textContent = MESES[viewMonth] + ' ' + viewYear;
        grid.innerHTML = '';

        DIAS_SEM.forEach(function (nome) {
            var h = document.createElement('div');
            h.className = 'agenda-cal__dow';
            h.textContent = nome;
            grid.appendChild(h);
        });

        var primeiro = new Date(viewYear, viewMonth, 1);
        var offset = primeiro.getDay();
        var diasNoMes = new Date(viewYear, viewMonth + 1, 0).getDate();
        var hoje = hojeISO();
        var comEvento = diasComEventos();

        for (var i = 0; i < offset; i++) {
            var blank = document.createElement('div');
            blank.className = 'agenda-cal__cell agenda-cal__cell--blank';
            grid.appendChild(blank);
        }

        for (var dia = 1; dia <= diasNoMes; dia++) {
            var iso = viewYear + '-' + pad2(viewMonth + 1) + '-' + pad2(dia);
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'agenda-cal__cell';
            btn.setAttribute('data-date', iso);
            btn.setAttribute('aria-label', 'Dia ' + dia);

            if (iso === hoje) btn.classList.add('agenda-cal__cell--hoje');
            if (iso === selectedDate) btn.classList.add('agenda-cal__cell--selected');
            if (comEvento[iso]) btn.classList.add('agenda-cal__cell--evento');

            var num = document.createElement('span');
            num.className = 'agenda-cal__num';
            num.textContent = dia;
            btn.appendChild(num);
            btn.addEventListener('click', function () {
                selecionarDia(this.getAttribute('data-date'));
            });
            grid.appendChild(btn);
        }
    }

    function renderListaEventos() {
        var lista = document.getElementById('agenda-lista-eventos');
        var titulo = document.getElementById('agenda-dia-titulo');
        if (!lista || !titulo) return;

        titulo.textContent = selectedDate
            ? 'Eventos — ' + formatarDataBR(selectedDate)
            : 'Selecione um dia';

        var eventos = selectedDate ? eventosDoDia(selectedDate) : [];
        lista.innerHTML = '';

        if (!selectedDate) {
            lista.innerHTML = '<p class="agenda-lista__vazio">Clique em um dia no calendário.</p>';
            return;
        }
        if (!eventos.length) {
            lista.innerHTML = '<p class="agenda-lista__vazio">Nenhum evento neste dia. Use + para adicionar.</p>';
            return;
        }

        eventos.forEach(function (ev) {
            var item = document.createElement('button');
            item.type = 'button';
            item.className = 'agenda-lista__item';
            item.innerHTML =
                '<span class="agenda-lista__item-titulo">' + escapeHtml(ev.titulo) + '</span>' +
                (ev.nota_texto
                    ? '<span class="agenda-lista__item-preview">' + escapeHtml(ev.nota_texto.slice(0, 80)) + '</span>'
                    : '<span class="agenda-lista__item-preview agenda-lista__item-preview--muted">Sem nota</span>');
            item.addEventListener('click', function () { abrirModal(ev); });
            lista.appendChild(item);
        });
    }

    function escapeHtml(s) {
        if (!s) return '';
        return String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function selecionarDia(iso) {
        selectedDate = iso;
        renderCalendario();
        renderListaEventos();
    }

    function abrirModal(ev) {
        eventoModal = ev || null;
        var overlay = document.getElementById('agenda-modal-overlay');
        var tituloInp = document.getElementById('agenda-modal-titulo');
        var dataInp = document.getElementById('agenda-modal-data');
        var notaInp = document.getElementById('agenda-modal-nota');
        var btnDel = document.getElementById('agenda-modal-excluir');
        if (!overlay || !tituloInp || !notaInp) return;

        if (ev) {
            tituloInp.value = ev.titulo || '';
            dataInp.value = dataEventoParaDia(ev.data_evento);
            notaInp.value = ev.nota_texto || '';
            btnDel.style.display = 'inline-flex';
        } else {
            tituloInp.value = '';
            dataInp.value = selectedDate || hojeISO();
            notaInp.value = '';
            btnDel.style.display = 'none';
        }
        overlay.classList.add('is-open');
        overlay.setAttribute('aria-hidden', 'false');
        tituloInp.focus();
    }

    function fecharModal() {
        var overlay = document.getElementById('agenda-modal-overlay');
        if (!overlay) return;
        overlay.classList.remove('is-open');
        overlay.setAttribute('aria-hidden', 'true');
        eventoModal = null;
    }

    function salvarModal() {
        var tituloInp = document.getElementById('agenda-modal-titulo');
        var dataInp = document.getElementById('agenda-modal-data');
        var notaInp = document.getElementById('agenda-modal-nota');
        var titulo = (tituloInp && tituloInp.value || '').trim();
        var dataEv = dataInp && dataInp.value;
        if (!titulo || !dataEv) {
            alert('Informe título e data.');
            return;
        }

        var payload = {
            titulo: titulo,
            nota_texto: notaInp ? notaInp.value : '',
            data_evento: dataEv + 'T12:00:00'
        };

        var prom;
        if (eventoModal && eventoModal.id_evento) {
            prom = fetchJson('/api/agenda-eventos/' + eventoModal.id_evento, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        } else {
            payload.id_matu = idMatu;
            prom = fetchJson('/api/agenda-eventos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        }

        prom.then(function () {
            fecharModal();
            var d = dataEv.slice(0, 7).split('-');
            viewYear = parseInt(d[0], 10);
            viewMonth = parseInt(d[1], 10) - 1;
            selectedDate = dataEv;
            return carregarEventos();
        }).then(function () {
            renderCalendario();
            renderListaEventos();
        }).catch(function (err) {
            alert(err.message || 'Não foi possível salvar.');
        });
    }

    function excluirModal() {
        if (!eventoModal || !eventoModal.id_evento) return;
        if (!confirm('Excluir este evento?')) return;
        fetchJson('/api/agenda-eventos/' + eventoModal.id_evento, { method: 'DELETE' })
            .then(function () {
                fecharModal();
                return carregarEventos();
            })
            .then(function () {
                renderCalendario();
                renderListaEventos();
            })
            .catch(function (err) {
                alert(err.message || 'Não foi possível excluir.');
            });
    }

    function mudarMes(delta) {
        viewMonth += delta;
        if (viewMonth > 11) { viewMonth = 0; viewYear++; }
        if (viewMonth < 0) { viewMonth = 11; viewYear--; }
        carregarEventos().then(function () {
            renderCalendario();
            renderListaEventos();
        });
    }

    function bindUi() {
        var prev = document.getElementById('agenda-mes-prev');
        var next = document.getElementById('agenda-mes-next');
        var add = document.getElementById('agenda-btn-add');
        var salvar = document.getElementById('agenda-modal-salvar');
        var fechar = document.getElementById('agenda-modal-fechar');
        var cancelar = document.getElementById('agenda-modal-cancelar');
        var excluir = document.getElementById('agenda-modal-excluir');
        var overlay = document.getElementById('agenda-modal-overlay');

        if (prev) prev.addEventListener('click', function () { mudarMes(-1); });
        if (next) next.addEventListener('click', function () { mudarMes(1); });
        if (add) add.addEventListener('click', function () { abrirModal(null); });
        if (salvar) salvar.addEventListener('click', salvarModal);
        if (fechar) fechar.addEventListener('click', fecharModal);
        if (cancelar) cancelar.addEventListener('click', fecharModal);
        if (excluir) excluir.addEventListener('click', excluirModal);
        if (overlay) {
            overlay.addEventListener('click', function (e) {
                if (e.target === overlay) fecharModal();
            });
        }
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') fecharModal();
        });
    }

    function init() {
        var root = document.getElementById('dashboard-agenda');
        if (!root) return;

        idMatu = getIdMatu();
        var now = new Date();
        viewYear = now.getFullYear();
        viewMonth = now.getMonth();
        selectedDate = hojeISO();

        bindUi();
        carregarEventos().then(function () {
            renderCalendario();
            renderListaEventos();
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
