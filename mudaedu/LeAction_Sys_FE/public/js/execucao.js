(function () {
    'use strict';

    var root = document.getElementById('execucao-root');
    if (!root) return;

    var filaEl = document.getElementById('fila-tarefas');
    var notifPanel = document.getElementById('notif-panel');
    var notifBadge = document.getElementById('notif-badge');
    var tarefas = [];

    function escapeHtml(s) {
        return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function badgePosition(position) {
        var p = (position || '').toLowerCase();
        if (p.indexOf('ti') !== -1) {
            return '<span class="execucao__badge execucao__badge--ti">Analista de TI</span>';
        }
        return '<span class="execucao__badge execucao__badge--executor">Analista Executor</span>';
    }

    async function api(url, opts) {
        var r = await fetch(url, Object.assign({ credentials: 'same-origin' }, opts || {}));
        var data = await r.json();
        if (!r.ok) throw new Error(data.message || data.error || 'Erro na requisição');
        return data;
    }

    function renderFila() {
        if (!tarefas.length) {
            filaEl.innerHTML = '<p class="mesa-empty-hint">Nenhuma atribuição pendente no momento.</p>';
            return;
        }
        filaEl.innerHTML = tarefas.map(function (t) {
            return (
                '<article class="execucao__card" data-id="' + t.id_ativ + '">' +
                '<div class="execucao__card-head">' +
                '<strong>' + escapeHtml(t.nome_ativ) + '</strong>' +
                badgePosition(t.executor_position) +
                '</div>' +
                '<p style="margin:0 0 6px;font-size:0.82rem;color:var(--wb-muted);">' +
                escapeHtml(t.name_sprn || 'Sprint') + ' · ' + escapeHtml(t.status_ativ || 'A Fazer') +
                '</p>' +
                '<p style="margin:0;font-size:0.78rem;">' + escapeHtml((t.desc_ativ || '').slice(0, 140)) + '</p>' +
                '</article>'
            );
        }).join('');
    }

    function abrirModal(t) {
        document.getElementById('exec-id-ativ').value = t.id_ativ;
        document.getElementById('exec-id-sprn').value = t.id_sprn || '';
        document.getElementById('exec-nome').textContent = t.nome_ativ || '';
        var sprintLabel = document.getElementById('exec-sprint-label');
        if (sprintLabel) {
            sprintLabel.textContent = t.name_sprn
                ? ('Sprint: ' + t.name_sprn)
                : '';
        }
        document.getElementById('exec-desc').value = t.desc_ativ || '';
        document.getElementById('exec-obs').value = t.obs_encaminhamentos || '';
        document.getElementById('exec-status').value = t.status_ativ || 'A Fazer';
        document.getElementById('modal-execucao').classList.add('is-open');
    }

    function fecharModal() {
        document.getElementById('modal-execucao').classList.remove('is-open');
    }

    async function carregarTarefas() {
        var data = await api('/api/execucao/tarefas');
        tarefas = data.data || [];
        renderFila();
    }

    async function carregarNotificacoes() {
        var data = await api('/api/notificacoes');
        atualizarUiNotificacoes(data);
    }

    function atualizarUiNotificacoes(data) {
        var lista = data.data || [];
        var n = data.nao_lidas || 0;
        if (n > 0) {
            notifBadge.hidden = false;
            notifBadge.textContent = String(n);
        } else {
            notifBadge.hidden = true;
        }
        if (!lista.length) {
            notifPanel.innerHTML = '<div class="execucao__notif-item">Sem notificações.</div>';
            return;
        }
        notifPanel.innerHTML = lista.map(function (n) {
            return (
                '<div class="execucao__notif-item execucao__notif-item--nova" data-id="' + n.id + '">' +
                '<strong>' + escapeHtml(n.tipo) + '</strong><br>' +
                escapeHtml(n.mensagem) +
                '</div>'
            );
        }).join('');
    }

    function pollNotificacoes() {
        fetch('/api/notificacoes', { credentials: 'same-origin' })
            .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
            .then(function (res) {
                if (!res.ok) return;
                atualizarUiNotificacoes(res.data);
            })
            .catch(function () {});
    }

    document.getElementById('btn-notificacoes').addEventListener('click', function () {
        notifPanel.classList.toggle('is-open');
        carregarNotificacoes().catch(function () {});
    });

    filaEl.addEventListener('click', function (ev) {
        var card = ev.target.closest('.execucao__card');
        if (!card) return;
        var id = parseInt(card.getAttribute('data-id'), 10);
        var t = tarefas.find(function (x) { return x.id_ativ === id; });
        if (t) abrirModal(t);
    });

    document.getElementById('btn-fechar-exec').addEventListener('click', fecharModal);
    document.getElementById('modal-execucao').addEventListener('click', function (ev) {
        if (ev.target.id === 'modal-execucao') fecharModal();
    });

    document.getElementById('form-execucao').addEventListener('submit', async function (ev) {
        ev.preventDefault();
        var idAtiv = document.getElementById('exec-id-ativ').value;
        var status = document.getElementById('exec-status').value;
        var obs = (document.getElementById('exec-obs').value || '').trim();
        try {
            await api('/api/okr/atividades/' + idAtiv, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    status_ativ: status,
                    obs_encaminhamentos: obs
                })
            });
            fecharModal();
            await carregarTarefas();
        } catch (e) {
            alert(e.message);
        }
    });

    Promise.all([carregarTarefas(), carregarNotificacoes()]).catch(function (e) {
        filaEl.innerHTML = '<p class="mesa-empty-hint" style="color:#b91c1c;">' + escapeHtml(e.message) + '</p>';
    });

    setInterval(pollNotificacoes, 30000);
})();
