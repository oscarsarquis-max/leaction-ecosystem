(function () {
    'use strict';

    var root = document.getElementById('admin-esim-root');
    if (!root) return;

    var catalogBody = document.getElementById('catalog-table-body');
    var provedoresBody = document.getElementById('provedores-table-body');
    var toastEl = document.getElementById('admin-esim-toast');

    var catalogItems = [];
    var provedorItems = [];
    var frameworkDims = [];
    var frameworkDoms = [];
    var blocosSelecionados = [];
    var blocoBuscaTimer = null;
    var disparandoMesaId = null;
    var ESIM_DISPARO_CLIENTE_LABEL = 'sistema@paneldx.com.br';

    function escapeHtml(str) {
        return String(str || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    async function parseJsonResponse(response) {
        var text = await response.text();
        try {
            return JSON.parse(text);
        } catch (e) {
            throw new Error(text || 'Resposta inválida do servidor.');
        }
    }

    function mostrarToast(msg, cor) {
        if (!toastEl) return;
        toastEl.textContent = msg;
        toastEl.style.background = cor || '#4A2E80';
        toastEl.classList.add('is-visible');
        setTimeout(function () {
            toastEl.classList.remove('is-visible');
        }, 3200);
    }

    async function apiFetch(url, options) {
        var opts = options || {};
        opts.credentials = 'same-origin';
        opts.headers = opts.headers || {};
        if (opts.body && typeof opts.body === 'object' && !(opts.body instanceof FormData)) {
            opts.headers['Content-Type'] = 'application/json';
            opts.body = JSON.stringify(opts.body);
        }
        var response = await fetch(url, opts);
        var data = await parseJsonResponse(response);
        if (!response.ok || data.status === 'error') {
            throw new Error(data.message || data.error || 'Falha na operação.');
        }
        return data;
    }

    function ativarTab(tabId) {
        document.querySelectorAll('.admin-esim__tab').forEach(function (btn) {
            var ativo = btn.getAttribute('data-tab') === tabId;
            btn.classList.toggle('is-active', ativo);
            btn.setAttribute('aria-selected', ativo ? 'true' : 'false');
        });
        document.querySelectorAll('.admin-esim__panel').forEach(function (panel) {
            panel.classList.toggle('is-active', panel.id === 'panel-' + tabId);
        });
    }

    function abrirModal(id) {
        var modal = document.getElementById(id);
        if (modal) {
            modal.classList.add('is-open');
            modal.setAttribute('aria-hidden', 'false');
        }
    }

    function fecharModal(id) {
        var modal = document.getElementById(id);
        if (modal) {
            modal.classList.remove('is-open');
            modal.setAttribute('aria-hidden', 'true');
        }
    }

    function renderCatalogTable() {
        if (!catalogBody) return;
        if (!catalogItems.length) {
            catalogBody.innerHTML = '<tr><td colspan="5" class="admin-esim__empty">Nenhum evento cadastrado no catálogo.</td></tr>';
            return;
        }
        catalogBody.innerHTML = catalogItems.map(function (item) {
            var blocos = Array.isArray(item.blocos_candidatos) ? item.blocos_candidatos : [];
            var disparando = disparandoMesaId === item.id;
            return (
                '<tr>' +
                '<td><span class="admin-esim__code">' + escapeHtml(item.codigo_evento) + '</span></td>' +
                '<td><strong>' + escapeHtml(item.dimensao_fixada) + '</strong><br><span style="color:var(--wb-muted);font-size:0.75rem;">' + escapeHtml(item.dominio_fixado) + '</span></td>' +
                '<td><span class="mesa-tag">' + blocos.length + ' bloco(s)</span></td>' +
                '<td>' + escapeHtml(item.provedor_nome || '—') + '</td>' +
                '<td><div class="admin-esim__actions">' +
                '<button type="button" class="mesa-btn mesa-btn--gold admin-esim__btn-icon" data-action="disparar-mesa" data-id="' + item.id + '" title="Disparar evento na Mesa de Inovação"' + (disparando ? ' disabled' : '') + '><i class="fas fa-' + (disparando ? 'spinner fa-spin' : 'lightbulb') + '"></i></button>' +
                '<button type="button" class="mesa-btn mesa-btn--ghost admin-esim__btn-icon" data-action="edit-catalog" data-id="' + item.id + '" title="Editar"><i class="fas fa-edit"></i></button>' +
                '<button type="button" class="mesa-btn mesa-btn--ghost admin-esim__btn-icon" data-action="del-catalog" data-id="' + item.id + '" style="color:#b91c1c;" title="Excluir"><i class="fas fa-trash"></i></button>' +
                '</div></td></tr>'
            );
        }).join('');
    }

    function renderProvedoresTable() {
        if (!provedoresBody) return;
        if (!provedorItems.length) {
            provedoresBody.innerHTML = '<tr><td colspan="5" class="admin-esim__empty">Nenhum provedor cadastrado.</td></tr>';
            return;
        }
        provedoresBody.innerHTML = provedorItems.map(function (item) {
            return (
                '<tr>' +
                '<td><strong>' + escapeHtml(item.nome) + '</strong></td>' +
                '<td><code style="font-size:0.75rem;">' + escapeHtml(item.webhook_path || '—') + '</code></td>' +
                '<td style="font-size:0.75rem;max-width:200px;word-break:break-all;">' + escapeHtml(item.upload_endpoint || '—') + '</td>' +
                '<td>' + escapeHtml(item.slug || '—') + '</td>' +
                '<td><div class="admin-esim__actions">' +
                '<button type="button" class="mesa-btn mesa-btn--ghost admin-esim__btn-icon" data-action="edit-provedor" data-id="' + item.id + '"><i class="fas fa-edit"></i></button>' +
                '<button type="button" class="mesa-btn mesa-btn--ghost admin-esim__btn-icon" data-action="del-provedor" data-id="' + item.id + '" style="color:#b91c1c;"><i class="fas fa-trash"></i></button>' +
                '</div></td></tr>'
            );
        }).join('');
    }

    function popularSelectProvedores(selectEl, selectedId) {
        if (!selectEl) return;
        selectEl.innerHTML = '<option value="">Selecione…</option>' +
            provedorItems.map(function (p) {
                var sel = String(p.id) === String(selectedId) ? ' selected' : '';
                return '<option value="' + p.id + '"' + sel + '>' + escapeHtml(p.nome) + '</option>';
            }).join('');
    }

    function popularFrameworkSelects() {
        var selDim = document.getElementById('catalog-dimensao');
        var selDom = document.getElementById('catalog-dominio');
        if (selDim) {
            selDim.innerHTML = '<option value="">Selecione…</option>' +
                frameworkDims.map(function (d) {
                    return '<option value="' + escapeHtml(d.name_dime) + '">' + escapeHtml(d.name_dime) + '</option>';
                }).join('');
        }
        if (selDom) {
            selDom.innerHTML = '<option value="">Selecione…</option>' +
                frameworkDoms.map(function (d) {
                    return '<option value="' + escapeHtml(d.name_doma) + '">' + escapeHtml(d.name_doma) + '</option>';
                }).join('');
        }
    }

    function renderBlocosSelecionados() {
        var container = document.getElementById('catalog-blocos-selecionados');
        if (!container) return;
        if (!blocosSelecionados.length) {
            container.innerHTML = '<span class="admin-esim__field-hint">Nenhum bloco selecionado.</span>';
            return;
        }
        container.innerHTML = blocosSelecionados.map(function (nome, idx) {
            return (
                '<span class="admin-esim__chip">' + escapeHtml(nome) +
                '<button type="button" data-remove-bloco="' + idx + '" title="Remover">&times;</button></span>'
            );
        }).join('');
    }

    async function buscarBlocos(termo) {
        var results = document.getElementById('catalog-bloco-results');
        if (!results) return;
        if ((termo || '').trim().length < 2) {
            results.hidden = true;
            results.innerHTML = '';
            return;
        }
        try {
            var data = await apiFetch('/api/admin/esim/blocos?q=' + encodeURIComponent(termo.trim()));
            var lista = data.data || [];
            if (!lista.length) {
                results.innerHTML = '<div class="admin-esim__empty" style="padding:12px;">Nenhum bloco encontrado.</div>';
            } else {
                results.innerHTML = lista.map(function (b) {
                    return (
                        '<button type="button" class="admin-esim__bloco-item" data-bloco-nome="' + escapeHtml(b.name_bloc) + '">' +
                        '<strong>' + escapeHtml(b.name_bloc) + '</strong>' +
                        '<span>' + escapeHtml(b.name_dime) + ' · ' + escapeHtml(b.name_doma) + '</span></button>'
                    );
                }).join('');
            }
            results.hidden = false;
        } catch (e) {
            results.innerHTML = '<div class="admin-esim__empty" style="padding:12px;color:#b91c1c;">' + escapeHtml(e.message) + '</div>';
            results.hidden = false;
        }
    }

    function abrirFormCatalog(item) {
        document.getElementById('catalog-id').value = item ? item.id : '';
        document.getElementById('modal-catalog-title').textContent = item ? 'Editar evento do catálogo' : 'Novo evento no catálogo';
        document.getElementById('catalog-codigo').value = item ? item.codigo_evento : '';
        document.getElementById('catalog-codigo').disabled = !!item;
        document.getElementById('catalog-descricao').value = item ? item.descricao_tecnica : '';
        popularSelectProvedores(document.getElementById('catalog-provedor'), item ? item.provedor_id : '');
        popularFrameworkSelects();
        if (item) {
            document.getElementById('catalog-dimensao').value = item.dimensao_fixada || '';
            document.getElementById('catalog-dominio').value = item.dominio_fixado || '';
        }
        blocosSelecionados = item && Array.isArray(item.blocos_candidatos) ? item.blocos_candidatos.slice() : [];
        renderBlocosSelecionados();
        document.getElementById('catalog-bloco-busca').value = '';
        document.getElementById('catalog-bloco-results').hidden = true;
        abrirModal('modal-catalog');
    }

    function abrirFormProvedor(item) {
        document.getElementById('provedor-id').value = item ? item.id : '';
        document.getElementById('modal-provedor-title').textContent = item ? 'Editar provedor' : 'Novo provedor eSIM';
        document.getElementById('provedor-nome').value = item ? item.nome : '';
        document.getElementById('provedor-webhook').value = item ? (item.webhook_path || '/api/webhooks/esim') : '/api/webhooks/esim';
        document.getElementById('provedor-upload').value = item ? (item.upload_endpoint || '') : '';
        document.getElementById('provedor-slug').value = item ? (item.slug || '') : '';
        abrirModal('modal-provedor');
    }

    async function dispararEventoMesa(item) {
        if (!item) return;
        var msg = 'Disparar o evento "' + item.codigo_evento + '" para ' + ESIM_DISPARO_CLIENTE_LABEL +
            '?\n\nIsso simula telemetria eSIM e cria o alerta na Mesa de Inovação.';
        if (!confirm(msg)) return;

        disparandoMesaId = item.id;
        renderCatalogTable();
        try {
            var data = await apiFetch('/api/admin/esim/catalog/' + item.id + '/disparar-mesa', {
                method: 'POST',
                body: {}
            });
            var clienteInfo = data.cliente_disparo || {};
            var clienteLabel = clienteInfo.mail_clie || ESIM_DISPARO_CLIENTE_LABEL;
            var nota = data.id_nota_mesa ? (' Post-it #' + data.id_nota_mesa + '.') : '';
            mostrarToast((data.message || 'Evento disparado na Mesa.') + nota, '#059669');
            if (confirm('Evento capturado pela Mesa de Inovação (' + clienteLabel + ').' + nota + '\n\nAbrir a listagem de mesas?')) {
                window.location.href = '/admin/mesas-inovacao';
            }
        } catch (e) {
            mostrarToast(e.message, '#dc2626');
        } finally {
            disparandoMesaId = null;
            renderCatalogTable();
        }
    }

    async function carregarCatalog() {
        var data = await apiFetch('/api/admin/esim/catalog');
        catalogItems = data.data || [];
        renderCatalogTable();
    }

    async function carregarProvedores() {
        var data = await apiFetch('/api/admin/esim/provedores');
        provedorItems = data.data || [];
        renderProvedoresTable();
    }

    async function carregarFrameworkOptions() {
        var data = await apiFetch('/api/admin/esim/framework-options');
        frameworkDims = data.dimensoes || [];
        frameworkDoms = data.dominios || [];
        popularFrameworkSelects();
    }

    async function salvarCatalog(ev) {
        ev.preventDefault();
        var id = document.getElementById('catalog-id').value;
        var payload = {
            codigo_evento: document.getElementById('catalog-codigo').value.trim().toUpperCase(),
            provedor_id: parseInt(document.getElementById('catalog-provedor').value, 10),
            dimensao_fixada: document.getElementById('catalog-dimensao').value,
            dominio_fixado: document.getElementById('catalog-dominio').value,
            descricao_tecnica: document.getElementById('catalog-descricao').value.trim(),
            blocos_candidatos: blocosSelecionados.slice()
        };
        if (id) {
            await apiFetch('/api/admin/esim/catalog/' + id, { method: 'PUT', body: payload });
            mostrarToast('Catálogo atualizado.', '#4A2E80');
        } else {
            await apiFetch('/api/admin/esim/catalog', { method: 'POST', body: payload });
            mostrarToast('Evento cadastrado no catálogo.', '#059669');
        }
        fecharModal('modal-catalog');
        await carregarCatalog();
    }

    async function salvarProvedor(ev) {
        ev.preventDefault();
        var id = document.getElementById('provedor-id').value;
        var payload = {
            nome: document.getElementById('provedor-nome').value.trim(),
            webhook_path: document.getElementById('provedor-webhook').value.trim(),
            upload_endpoint: document.getElementById('provedor-upload').value.trim(),
            slug: document.getElementById('provedor-slug').value.trim()
        };
        if (id) {
            await apiFetch('/api/admin/esim/provedores/' + id, { method: 'PUT', body: payload });
            mostrarToast('Provedor atualizado.', '#4A2E80');
        } else {
            await apiFetch('/api/admin/esim/provedores', { method: 'POST', body: payload });
            mostrarToast('Provedor cadastrado.', '#059669');
        }
        fecharModal('modal-provedor');
        await carregarProvedores();
        await carregarCatalog();
    }

    document.querySelectorAll('.admin-esim__tab').forEach(function (btn) {
        btn.addEventListener('click', function () {
            ativarTab(btn.getAttribute('data-tab'));
        });
    });

    document.getElementById('btn-novo-catalog').addEventListener('click', function () {
        abrirFormCatalog(null);
    });
    document.getElementById('btn-novo-provedor').addEventListener('click', function () {
        abrirFormProvedor(null);
    });
    document.getElementById('btn-cancelar-catalog').addEventListener('click', function () {
        fecharModal('modal-catalog');
    });
    document.getElementById('btn-cancelar-provedor').addEventListener('click', function () {
        fecharModal('modal-provedor');
    });
    document.getElementById('form-catalog').addEventListener('submit', function (ev) {
        salvarCatalog(ev).catch(function (e) {
            mostrarToast(e.message, '#dc2626');
        });
    });
    document.getElementById('form-provedor').addEventListener('submit', function (ev) {
        salvarProvedor(ev).catch(function (e) {
            mostrarToast(e.message, '#dc2626');
        });
    });

    document.getElementById('catalog-bloco-busca').addEventListener('input', function (ev) {
        clearTimeout(blocoBuscaTimer);
        var val = ev.target.value;
        blocoBuscaTimer = setTimeout(function () {
            buscarBlocos(val);
        }, 280);
    });

    document.getElementById('catalog-bloco-results').addEventListener('click', function (ev) {
        var btn = ev.target.closest('[data-bloco-nome]');
        if (!btn) return;
        var nome = btn.getAttribute('data-bloco-nome');
        if (nome && blocosSelecionados.indexOf(nome) === -1) {
            blocosSelecionados.push(nome);
            renderBlocosSelecionados();
        }
        document.getElementById('catalog-bloco-results').hidden = true;
        document.getElementById('catalog-bloco-busca').value = '';
    });

    document.getElementById('catalog-blocos-selecionados').addEventListener('click', function (ev) {
        var btn = ev.target.closest('[data-remove-bloco]');
        if (!btn) return;
        var idx = parseInt(btn.getAttribute('data-remove-bloco'), 10);
        blocosSelecionados.splice(idx, 1);
        renderBlocosSelecionados();
    });

    catalogBody.addEventListener('click', function (ev) {
        var btn = ev.target.closest('[data-action]');
        if (!btn) return;
        var id = parseInt(btn.getAttribute('data-id'), 10);
        var item = catalogItems.find(function (c) { return c.id === id; });
        if (btn.getAttribute('data-action') === 'edit-catalog' && item) {
            abrirFormCatalog(item);
        }
        if (btn.getAttribute('data-action') === 'disparar-mesa' && item) {
            dispararEventoMesa(item).catch(function (e) {
                mostrarToast(e.message, '#dc2626');
            });
        }
        if (btn.getAttribute('data-action') === 'del-catalog') {
            if (!confirm('Remover este evento do catálogo?')) return;
            apiFetch('/api/admin/esim/catalog/' + id, { method: 'DELETE' })
                .then(function () {
                    mostrarToast('Evento removido.', '#4A2E80');
                    return carregarCatalog();
                })
                .catch(function (e) {
                    mostrarToast(e.message, '#dc2626');
                });
        }
    });

    provedoresBody.addEventListener('click', function (ev) {
        var btn = ev.target.closest('[data-action]');
        if (!btn) return;
        var id = parseInt(btn.getAttribute('data-id'), 10);
        var item = provedorItems.find(function (p) { return p.id === id; });
        if (btn.getAttribute('data-action') === 'edit-provedor' && item) {
            abrirFormProvedor(item);
        }
        if (btn.getAttribute('data-action') === 'del-provedor') {
            if (!confirm('Remover este provedor?')) return;
            apiFetch('/api/admin/esim/provedores/' + id, { method: 'DELETE' })
                .then(function () {
                    mostrarToast('Provedor removido.', '#4A2E80');
                    return Promise.all([carregarProvedores(), carregarCatalog()]);
                })
                .catch(function (e) {
                    mostrarToast(e.message, '#dc2626');
                });
        }
    });

    document.querySelectorAll('.mesa-modal').forEach(function (modal) {
        modal.addEventListener('click', function (ev) {
            if (ev.target === modal) {
                fecharModal(modal.id);
            }
        });
    });

    Promise.all([
        carregarProvedores(),
        carregarCatalog(),
        carregarFrameworkOptions()
    ]).catch(function (e) {
        mostrarToast('Erro ao carregar dados: ' + e.message, '#dc2626');
    });
})();
