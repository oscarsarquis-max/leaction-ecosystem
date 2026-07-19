(function () {
    'use strict';

    var root = document.getElementById('admin-usuarios-root');
    if (!root) return;

    var tbody = document.getElementById('usuarios-table-body');
    var modal = document.getElementById('modal-usuario');
    var form = document.getElementById('form-usuario');
    var toastEl = document.getElementById('admin-usuarios-toast');
    var inputBusca = document.getElementById('usuarios-busca');
    var selectRole = document.getElementById('usuarios-filtro-role');
    var selectEmpresa = document.getElementById('usuarios-filtro-empresa');
    var chkInativos = document.getElementById('usuarios-incluir-inativos');
    var resultCountEl = document.getElementById('usuarios-result-count');
    var btnLimparBusca = document.getElementById('btn-limpar-busca');

    var usuarios = [];
    var buscaAtual = '';
    var debounceTimer = null;

    var ROLE_LABELS = {
        sysadmin: 'SysAdmin',
        led: 'GESTOR',
        consultor: 'Consultor',
        executor: 'Executor'
    };

    function escapeHtml(s) {
        return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function escapeRegExp(s) {
        return String(s || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    function highlightText(text, term) {
        var safe = escapeHtml(text);
        var q = (term || '').trim();
        if (!q || q.length < 2) return safe;
        try {
            var re = new RegExp('(' + escapeRegExp(q) + ')', 'ig');
            return safe.replace(re, '<mark class="admin-usuarios__highlight">$1</mark>');
        } catch (e) {
            return safe;
        }
    }

    function toast(msg, tipo) {
        if (!toastEl) return;
        toastEl.textContent = msg;
        toastEl.className = 'admin-usuarios__toast is-visible ' + (tipo === 'error' ? 'is-error' : 'is-success');
        clearTimeout(window._adminUsuariosToast);
        window._adminUsuariosToast = setTimeout(function () {
            toastEl.classList.remove('is-visible');
        }, 3800);
    }

    async function apiFetch(url, opts) {
        var r = await fetch(url, Object.assign({ credentials: 'same-origin' }, opts || {}));
        var data = await r.json().catch(function () { return {}; });
        if (!r.ok) {
            var err = new Error(data.error || data.message || 'Erro na requisição');
            err.status = r.status;
            err.data = data;
            throw err;
        }
        return data;
    }

    var COLSPAN = 6;

    function renderEmpresaCell(u) {
        var label = (u.empresa_grupo || '').trim();
        if (!label) {
            return '<span class="admin-usuarios__empresa-cell admin-usuarios__empresa-cell--empty">—</span>';
        }
        var extra = '';
        if (u.is_holding && u.id_rede) {
            extra = '<span class="admin-usuarios__empresa-tag">Holding</span>';
        } else if (u.id_rede) {
            extra = '<span class="admin-usuarios__empresa-tag">Rede ' + escapeHtml(u.id_rede) + '</span>';
        }
        return (
            '<div class="admin-usuarios__empresa-cell">' +
            highlightText(label, buscaAtual) +
            (extra ? '<br>' + extra : '') +
            '</div>'
        );
    }

    function atualizarContador(total) {
        if (!resultCountEl) return;
        var n = typeof total === 'number' ? total : usuarios.length;
        var partes = [n + (n === 1 ? ' usuário' : ' usuários')];
        if (buscaAtual) partes.push('para "' + buscaAtual + '"');
        if (selectEmpresa && selectEmpresa.value) {
            var opt = selectEmpresa.options[selectEmpresa.selectedIndex];
            if (opt && opt.text) partes.push('· ' + opt.text.trim());
        }
        resultCountEl.textContent = partes.join(' ');
    }

    function atualizarBotaoLimpar() {
        if (!btnLimparBusca || !inputBusca) return;
        btnLimparBusca.hidden = !inputBusca.value.trim();
    }

    function renderTabela() {
        if (!usuarios.length) {
            var msg = buscaAtual
                ? 'Nenhum usuário encontrado para esta busca.'
                : 'Nenhum usuário cadastrado.';
            tbody.innerHTML = '<tr><td colspan="' + COLSPAN + '" class="admin-usuarios__empty">' + escapeHtml(msg) + '</td></tr>';
            atualizarContador(0);
            return;
        }

        tbody.innerHTML = usuarios.map(function (u) {
            var role = (u.system_role || '').toLowerCase();
            return (
                '<tr>' +
                '<td><strong>' + highlightText(u.nome, buscaAtual) + '</strong></td>' +
                '<td>' + highlightText(u.email, buscaAtual) + '</td>' +
                '<td>' + renderEmpresaCell(u) + '</td>' +
                '<td><span class="admin-usuarios__badge admin-usuarios__badge--' + escapeHtml(role) + '">' +
                escapeHtml(ROLE_LABELS[role] || role) + '</span></td>' +
                '<td><span class="admin-usuarios__status--' + (u.ativo ? 'ativo' : 'inativo') + '">' +
                (u.ativo ? 'Ativo' : 'Inativo') + '</span></td>' +
                '<td><div class="admin-usuarios__row-actions">' +
                '<button type="button" class="admin-usuarios__icon-btn admin-usuarios__icon-btn--edit" data-edit="' + u.id_usuario + '" title="Editar"><i class="fas fa-edit"></i></button>' +
                (u.ativo
                    ? '<button type="button" class="admin-usuarios__icon-btn admin-usuarios__icon-btn--off" data-off="' + u.id_usuario + '" title="Desativar"><i class="fas fa-user-slash"></i></button>'
                    : '') +
                '</div></td>' +
                '</tr>'
            );
        }).join('');
        atualizarContador(usuarios.length);
    }

    function montarQueryBusca() {
        var params = new URLSearchParams();
        var q = (inputBusca && inputBusca.value || '').trim();
        var role = (selectRole && selectRole.value || '').trim();
        var empresaGrupo = (selectEmpresa && selectEmpresa.value || '').trim();
        var incluirInativos = chkInativos ? chkInativos.checked : true;

        if (q) params.set('q', q);
        if (role) params.set('system_role', role);
        if (empresaGrupo.indexOf('clie:') === 0) {
            params.set('id_clie', empresaGrupo.slice(5));
        } else if (empresaGrupo.indexOf('rede:') === 0) {
            params.set('id_rede', empresaGrupo.slice(5));
        }
        params.set('incluir_inativos', incluirInativos ? '1' : '0');

        buscaAtual = q;
        atualizarBotaoLimpar();
        return params.toString();
    }

    async function carregarUsuarios() {
        tbody.innerHTML = '<tr><td colspan="' + COLSPAN + '" class="admin-usuarios__empty">Carregando usuários…</td></tr>';
        var qs = montarQueryBusca();
        var url = '/bff/admin/usuarios' + (qs ? '?' + qs : '');
        var data = await apiFetch(url);
        usuarios = data.data || [];
        renderTabela();
    }

    function agendarBusca() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(function () {
            carregarUsuarios().catch(function (e) {
                tbody.innerHTML = '<tr><td colspan="' + COLSPAN + '" class="admin-usuarios__empty" style="color:#dc2626;">' + escapeHtml(e.message) + '</td></tr>';
            });
        }, 320);
    }

    function abrirModal(modoEdicao) {
        document.getElementById('modal-usuario-title').textContent = modoEdicao ? 'Editar Usuário' : 'Novo Usuário';
        document.getElementById('senha-opcional').textContent = modoEdicao ? '' : '*';
        document.getElementById('usuario-senha').required = !modoEdicao;
        document.getElementById('field-ativo').hidden = !modoEdicao;
        document.getElementById('field-codigo-lead').hidden = true;
        document.getElementById('field-senha-atual').hidden = true;
        var codigoInput = document.getElementById('usuario-codigo-acesso');
        var senhaAtualInput = document.getElementById('usuario-senha-atual');
        if (window.MudaEduPasswordToggle) {
            if (codigoInput) window.MudaEduPasswordToggle.clearMasked(codigoInput);
            if (senhaAtualInput) window.MudaEduPasswordToggle.clearMasked(senhaAtualInput);
        }
        document.getElementById('usuario-senha').value = '';
        var hintSenha = document.getElementById('senha-hint');
        if (hintSenha) {
            hintSenha.textContent = modoEdicao
                ? 'Deixe em branco para manter a senha atual. Use o olho para conferir ao digitar.'
                : 'Obrigatória na criação. Use o olho para conferir ao digitar.';
        }
        var btnSubmit = document.getElementById('btn-submit-usuario');
        if (btnSubmit) {
            btnSubmit.innerHTML = modoEdicao
                ? '<i class="fas fa-save"></i> Salvar alterações'
                : '<i class="fas fa-plus"></i> Incluir usuário';
        }
        if (!modoEdicao) {
            form.reset();
            document.getElementById('usuario-id').value = '';
        }
        modal.classList.add('is-open');
        modal.setAttribute('aria-hidden', 'false');
        if (window.MudaEduPasswordToggle) {
            window.MudaEduPasswordToggle.init(modal);
        }
    }

    function fecharModal() {
        modal.classList.remove('is-open');
        modal.setAttribute('aria-hidden', 'true');
    }

    async function carregarCredenciaisAcesso(idUsuario) {
        var fieldCodigo = document.getElementById('field-codigo-lead');
        var codigoInput = document.getElementById('usuario-codigo-acesso');
        var fieldSenhaAtual = document.getElementById('field-senha-atual');
        var senhaAtualInput = document.getElementById('usuario-senha-atual');
        var hintSenha = document.getElementById('senha-hint');

        try {
            var resp = await apiFetch('/bff/admin/usuarios/' + idUsuario + '/acesso');
            var info = resp.data || {};

            if (fieldCodigo) fieldCodigo.hidden = true;
            if (fieldSenhaAtual) fieldSenhaAtual.hidden = true;

            if (info.tipo_credencial === 'codigo_lead' && info.credencial_visivel && codigoInput) {
                fieldCodigo.hidden = false;
                if (window.MudaEduPasswordToggle) {
                    window.MudaEduPasswordToggle.setMaskedValue(codigoInput, info.credencial_visivel);
                } else {
                    codigoInput.value = info.credencial_visivel;
                }
            } else if (info.credencial_visivel && senhaAtualInput && fieldSenhaAtual) {
                fieldSenhaAtual.hidden = false;
                if (window.MudaEduPasswordToggle) {
                    window.MudaEduPasswordToggle.setMaskedValue(senhaAtualInput, info.credencial_visivel);
                } else {
                    senhaAtualInput.value = info.credencial_visivel;
                }
            }

            if (hintSenha) {
                if (info.tipo_credencial === 'codigo_lead') {
                    hintSenha.textContent = 'Código LA-* acima. Para definir senha global, use o campo abaixo.';
                } else if (info.credencial_visivel) {
                    hintSenha.textContent = 'Senha/credencial acima (ambiente local). Para alterar, defina nova senha abaixo.';
                } else if (info.tem_senha) {
                    hintSenha.textContent = 'Senha criptografada no banco. Digite uma nova abaixo e use o olho para conferir.';
                } else {
                    hintSenha.textContent = 'Defina a senha de acesso. Use o olho para conferir ao digitar.';
                }
            }
        } catch (e) {
            if (fieldCodigo) fieldCodigo.hidden = true;
            if (fieldSenhaAtual) fieldSenhaAtual.hidden = true;
            if (hintSenha) {
                hintSenha.textContent = 'Não foi possível carregar credenciais. Defina ou altere a senha no campo abaixo.';
            }
        }
    }

    function editarUsuario(id) {
        var u = usuarios.find(function (x) { return x.id_usuario === id; });
        if (!u) return;
        abrirModal(true);
        document.getElementById('usuario-id').value = u.id_usuario;
        document.getElementById('usuario-nome').value = u.nome || '';
        document.getElementById('usuario-email').value = u.email || '';
        document.getElementById('usuario-role').value = u.system_role || '';
        document.getElementById('usuario-ativo').value = u.ativo ? 'true' : 'false';
        document.getElementById('usuario-senha').value = '';
        carregarCredenciaisAcesso(id);
    }

    async function desativarUsuario(id) {
        if (!confirm('Desativar este usuário? Ele não poderá mais autenticar.')) return;
        try {
            await apiFetch('/bff/admin/usuarios/' + id, { method: 'DELETE' });
            toast('Usuário desativado.', 'success');
            await carregarUsuarios();
        } catch (e) {
            toast(e.message, 'error');
        }
    }

    document.getElementById('btn-novo-usuario').addEventListener('click', function () {
        abrirModal(false);
    });
    document.getElementById('btn-cancelar-modal').addEventListener('click', fecharModal);
    modal.addEventListener('click', function (ev) {
        if (ev.target === modal) fecharModal();
    });

    if (inputBusca) {
        inputBusca.addEventListener('input', agendarBusca);
        inputBusca.addEventListener('keydown', function (ev) {
            if (ev.key === 'Escape') {
                inputBusca.value = '';
                agendarBusca();
            }
        });
    }

    if (btnLimparBusca) {
        btnLimparBusca.addEventListener('click', function () {
            if (inputBusca) inputBusca.value = '';
            agendarBusca();
            if (inputBusca) inputBusca.focus();
        });
    }

    async function carregarOpcoesEmpresa() {
        if (!selectEmpresa) return;
        var valorAtual = selectEmpresa.value;
        var data = await apiFetch('/bff/admin/usuarios/opcoes-empresa');
        var html = '<option value="">Todas empresas / grupos</option>';

        var grupos = data.grupos || [];
        if (grupos.length) {
            html += '<optgroup label="Grupos / Redes">';
            grupos.forEach(function (g) {
                var rede = (g.id_rede || '').trim();
                if (!rede) return;
                var label = g.label || ('Rede ' + rede);
                var qtd = g.qtd_usuarios != null ? ' (' + g.qtd_usuarios + ')' : '';
                html += '<option value="rede:' + rede.replace(/"/g, '') + '">' + escapeHtml(label + qtd) + '</option>';
            });
            html += '</optgroup>';
        }

        var empresas = data.empresas || [];
        if (empresas.length) {
            html += '<optgroup label="Empresas">';
            empresas.forEach(function (e) {
                var label = e.label || e.empresa_clie || e.nome_clie || ('Cliente #' + e.id_clie);
                var qtd = e.qtd_usuarios != null ? ' (' + e.qtd_usuarios + ')' : '';
                html += '<option value="clie:' + e.id_clie + '">' + escapeHtml(label + qtd) + '</option>';
            });
            html += '</optgroup>';
        }

        selectEmpresa.innerHTML = html;
        if (valorAtual) selectEmpresa.value = valorAtual;
    }

    if (selectEmpresa) {
        selectEmpresa.addEventListener('change', agendarBusca);
    }

    if (selectRole) {
        selectRole.addEventListener('change', agendarBusca);
    }

    if (chkInativos) {
        chkInativos.addEventListener('change', agendarBusca);
    }

    tbody.addEventListener('click', function (ev) {
        var editBtn = ev.target.closest('[data-edit]');
        var offBtn = ev.target.closest('[data-off]');
        if (editBtn) editarUsuario(parseInt(editBtn.getAttribute('data-edit'), 10));
        if (offBtn) desativarUsuario(parseInt(offBtn.getAttribute('data-off'), 10));
    });

    form.addEventListener('submit', async function (ev) {
        ev.preventDefault();
        var id = document.getElementById('usuario-id').value;
        var payload = {
            nome: document.getElementById('usuario-nome').value.trim(),
            email: document.getElementById('usuario-email').value.trim(),
            system_role: document.getElementById('usuario-role').value
        };
        var senha = document.getElementById('usuario-senha').value;
        if (senha) payload.senha = senha;
        if (id) payload.ativo = document.getElementById('usuario-ativo').value === 'true';

        try {
            if (id) {
                await apiFetch('/bff/admin/usuarios/' + id, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                toast('Usuário atualizado.', 'success');
            } else {
                if (!senha) {
                    toast('Senha é obrigatória para novo usuário.', 'error');
                    return;
                }
                await apiFetch('/bff/admin/usuarios', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                toast('Usuário criado com sucesso.', 'success');
            }
            fecharModal();
            await carregarUsuarios();
        } catch (e) {
            toast(e.message, 'error');
        }
    });

    Promise.all([
        carregarOpcoesEmpresa().catch(function () { /* dropdown opcional */ }),
        carregarUsuarios()
    ]).catch(function (e) {
        tbody.innerHTML = '<tr><td colspan="' + COLSPAN + '" class="admin-usuarios__empty" style="color:#dc2626;">' + escapeHtml(e.message) + '</td></tr>';
    });
})();
