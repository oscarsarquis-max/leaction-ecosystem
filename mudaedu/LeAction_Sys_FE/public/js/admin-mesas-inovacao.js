(function () {
    'use strict';

    var root = document.getElementById('admin-mesas-root');
    if (!root) return;

    var tbody = document.getElementById('mesas-table-body');
    var toastEl = document.getElementById('admin-mesas-toast');
    var mesas = [];

    var STATUS_LABELS = {
        ativa: 'Com pendências',
        disponivel: 'Disponível',
        em_setup: 'Em preparação'
    };

    function escapeHtml(s) {
        return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function toast(msg, cor) {
        if (!toastEl) return;
        toastEl.textContent = msg;
        toastEl.style.background = cor || '#4A2E80';
        toastEl.classList.add('is-visible');
        clearTimeout(window._adminMesasToast);
        window._adminMesasToast = setTimeout(function () {
            toastEl.classList.remove('is-visible');
        }, 3200);
    }

    async function apiFetch(url) {
        var r = await fetch(url, { credentials: 'same-origin' });
        var data = await r.json().catch(function () { return {}; });
        if (!r.ok || data.status === 'error') {
            throw new Error(data.message || data.error || 'Falha ao carregar mesas.');
        }
        return data;
    }

    function urlMesa(item) {
        return '/projeto/mesa-inovacao?id_clie=' + encodeURIComponent(item.id_clie) +
            '&id_matu=' + encodeURIComponent(item.id_matu);
    }

    function renderTabela() {
        if (!mesas.length) {
            tbody.innerHTML = '<tr><td colspan="7" class="admin-mesas__empty">Nenhuma mesa ativa encontrada.</td></tr>';
            return;
        }

        tbody.innerHTML = mesas.map(function (m) {
            var status = m.status_mesa || 'em_setup';
            var pendentes = m.notas_pendentes || 0;
            var alertas = m.alertas_esim || 0;
            return (
                '<tr>' +
                '<td class="admin-mesas__cliente">' +
                '<strong>' + escapeHtml(m.nome_clie) + '</strong>' +
                '<span>#' + escapeHtml(m.id_clie) + (m.mail_clie ? ' · ' + escapeHtml(m.mail_clie) : '') + '</span>' +
                '</td>' +
                '<td><code>#' + escapeHtml(m.id_matu) + '</code></td>' +
                '<td>' + escapeHtml(m.status_ia || '—') + '</td>' +
                '<td><span class="admin-mesas__count' + (pendentes > 0 ? ' admin-mesas__count--alert' : '') + '">' + pendentes + '</span></td>' +
                '<td><span class="admin-mesas__count' + (alertas > 0 ? ' admin-mesas__count--alert' : '') + '">' + alertas + '</span></td>' +
                '<td><span class="admin-mesas__badge admin-mesas__badge--' + escapeHtml(status) + '">' +
                escapeHtml(STATUS_LABELS[status] || status) + '</span></td>' +
                '<td><div class="admin-mesas__actions">' +
                '<a class="mesa-btn mesa-btn--gold admin-esim__btn-icon" href="' + urlMesa(m) + '" title="Abrir Mesa de Inovação">' +
                '<i class="fas fa-external-link-alt"></i> Abrir</a>' +
                '</div></td>' +
                '</tr>'
            );
        }).join('');
    }

    async function carregarMesas() {
        tbody.innerHTML = '<tr><td colspan="7" class="admin-mesas__empty">Carregando mesas…</td></tr>';
        var data = await apiFetch('/api/admin/mesas-inovacao');
        mesas = data.data || [];
        renderTabela();
    }

    document.getElementById('btn-recarregar-mesas').addEventListener('click', function () {
        carregarMesas().catch(function (e) {
            toast(e.message, '#dc2626');
        });
    });

    carregarMesas().catch(function (e) {
        toast(e.message, '#dc2626');
        tbody.innerHTML = '<tr><td colspan="7" class="admin-mesas__empty" style="color:#b91c1c;">' + escapeHtml(e.message) + '</td></tr>';
    });
})();
