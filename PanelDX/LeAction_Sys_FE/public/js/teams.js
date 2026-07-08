(function () {
    'use strict';

    var root = document.getElementById('teams-root');
    if (!root) return;

    var cfg = window.TEAMS_PAGE_CONFIG || {};
    var API_URL = cfg.apiUrl || '/api/ctdi_team';
    var USER_ROLE = cfg.userRole || 'LEAD';
    var USER_ID_CLIE = cfg.userIdClie ||
        (document.getElementById('id_cliente_hidden') && document.getElementById('id_cliente_hidden').value) ||
        '';

    var squadIdSelecionada = null;
    var idClieAtual = USER_ID_CLIE || null;
    var projetosCache = [];
    var membrosCache = [];
    var buscaAtual = '';
    var emailCapacidadeOk = true;
    var usuariosDisponiveis = [];
    var cotaUsuarios = null;

    var elSeat = {
        panel: document.getElementById('teams-seat-meter'),
        count: document.getElementById('teams-seat-count'),
        planoLabel: document.getElementById('teams-seat-plano-label'),
        barFill: document.getElementById('teams-seat-bar-fill'),
        btnUpgrade: document.getElementById('teams-btn-upgrade'),
        btnAddon: document.getElementById('teams-btn-addon')
    };
    var ROLE_LABELS = { sysadmin: 'SysAdmin', led: 'GESTOR', consultor: 'Consultor', executor: 'Executor' };
    var PERSONA_LABELS = { ADMIN: 'SysAdmin', CONSULTOR: 'Consultor', LEAD: 'GESTOR', CLIENTE: 'Executor' };
    var ROLE_STYLES = { ADMIN: 'admin', CONSULTOR: 'consultor', LEAD: 'lead', CLIENTE: 'cliente' };

    var el = {
        contextLoading: document.getElementById('teams-context-loading'),
        contextBody: document.getElementById('teams-context-body'),
        contextEmpty: document.getElementById('teams-context-empty'),
        switchWrap: document.getElementById('teams-squad-select-panel'),
        squadPicker: document.getElementById('teams-squad-picker'),
        selector: document.getElementById('projeto_selector'),
        squadNome: document.getElementById('teams-squad-nome'),
        projetoLabel: document.getElementById('teams-projeto-label'),
        statMembros: document.getElementById('teams-stat-membros'),
        statSquad: document.getElementById('teams-stat-squad'),
        btnNovo: document.getElementById('btnNovoMembro'),
        btnCadastrar: document.getElementById('btnCadastrarMembro'),
        modalCadastro: document.getElementById('modal-cadastro-membro'),
        filters: document.getElementById('teams-filters'),
        busca: document.getElementById('teams-busca'),
        resultCount: document.getElementById('teams-result-count'),
        tbody: document.getElementById('table-body'),
        modal: document.getElementById('modal-form'),
        modalSquadLabel: document.getElementById('modal-squad-label'),
        toast: document.getElementById('toast-teams')
    };

    function escapeHtml(s) {
        return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function mostrarToast(msg, tipo) {
        if (!el.toast) return;
        el.toast.textContent = msg;
        el.toast.className = 'teams-page__toast is-visible ' + (tipo === 'error' ? 'is-error' : 'is-success');
        clearTimeout(window._toastTeamsTimer);
        window._toastTeamsTimer = setTimeout(function () {
            el.toast.classList.remove('is-visible');
        }, 3800);
    }

    function projetoPorSquad(id) {
        return projetosCache.find(function (p) { return String(p.id_squad) === String(id); });
    }

    function atualizarContextoUI(projeto) {
        if (!projeto) return;
        if (el.squadNome) el.squadNome.textContent = projeto.nome_squad || 'Squad sem nome';
        if (el.projetoLabel) {
            el.projetoLabel.textContent = (projeto.nome_clie || 'Cliente') +
                (projeto.name_ctdi ? ' · ' + projeto.name_ctdi : '');
        }
        if (el.statSquad) el.statSquad.textContent = '#' + projeto.id_squad;
    }

    function setContextState(state) {
        if (el.contextLoading) el.contextLoading.hidden = state !== 'loading';
        if (el.contextBody) el.contextBody.hidden = state !== 'ready';
        if (el.contextEmpty) el.contextEmpty.hidden = state !== 'empty';
    }

    function atualizarContagem() {
        var filtrados = filtrarMembros(membrosCache);
        if (el.statMembros) el.statMembros.textContent = String(membrosCache.length);
        if (el.resultCount) {
            if (!squadIdSelecionada) {
                el.resultCount.textContent = '';
            } else if (buscaAtual.trim()) {
                el.resultCount.textContent = filtrados.length + ' de ' + membrosCache.length + ' membro(s)';
            } else {
                el.resultCount.textContent = membrosCache.length + ' membro(s)';
            }
        }
    }

    function filtrarMembros(lista) {
        var q = (buscaAtual || '').trim().toLowerCase();
        if (!q) return lista;
        return lista.filter(function (m) {
            var blob = [m.nome, m.email, m.position, PERSONA_LABELS[m.role] || m.role].join(' ').toLowerCase();
            return blob.indexOf(q) !== -1;
        });
    }

    async function verificarCapacidadeEmail() {
        var select = document.getElementById('id_usuario');
        var idUsuario = select.value;
        var idMember = document.getElementById('id_member').value;
        emailCapacidadeOk = true;
        select.style.borderColor = '';

        var usuario = usuariosDisponiveis.find(function (u) { return String(u.id_usuario) === String(idUsuario); });
        var email = usuario ? usuario.email : '';
        if (!email || !squadIdSelecionada) return;

        try {
            var qs = new URLSearchParams({ email: email, id_squad: String(squadIdSelecionada) });
            if (idMember) qs.set('id_member', idMember);
            var res = await fetch('/api/rbac/capacidade?' + qs.toString());
            var info = await res.json();
            if (info.bloqueado) {
                emailCapacidadeOk = false;
                select.style.borderColor = '#dc2626';
                mostrarToast(info.error || 'Capacidade máxima: membro já atua em 3 squads.', 'error');
            }
        } catch (err) {
            console.warn('Falha ao verificar capacidade:', err);
        }
    }

    function idClieParaAlocacao() {
        if (USER_ROLE === 'ADMIN') {
            return idClieAtual || USER_ID_CLIE;
        }
        return USER_ID_CLIE || idClieAtual;
    }

    function atualizarInfoUsuario() {
        var select = document.getElementById('id_usuario');
        var info = document.getElementById('usuario-info');
        var usuario = usuariosDisponiveis.find(function (u) { return String(u.id_usuario) === String(select.value); });
        info.textContent = usuario
            ? usuario.email + ' · Papel: ' + (ROLE_LABELS[usuario.system_role] || usuario.system_role)
            : '';
    }

    async function carregarUsuariosDisponiveis(idUsuarioSelecionado) {
        var select = document.getElementById('id_usuario');
        var idClie = idClieParaAlocacao();
        if (!idClie) {
            select.innerHTML = '<option value="">Selecione uma squad da sua empresa</option>';
            return;
        }
        try {
            var res = await fetch('/api/led/usuarios-disponiveis?id_clie=' + encodeURIComponent(idClie));
            var data = await res.json();
            usuariosDisponiveis = data.data || [];
            select.innerHTML = '<option value="">— Selecione um membro da empresa —</option>';
            usuariosDisponiveis.forEach(function (u) {
                var opt = document.createElement('option');
                opt.value = u.id_usuario;
                opt.textContent = u.nome + ' (' + u.email + ') — ' + (ROLE_LABELS[u.system_role] || u.system_role);
                select.appendChild(opt);
            });
            if (idUsuarioSelecionado) select.value = String(idUsuarioSelecionado);
            atualizarInfoUsuario();
        } catch (err) {
            console.error('Erro ao carregar usuários:', err);
            select.innerHTML = '<option value="">Erro ao carregar usuários</option>';
        }
    }

    function labelSquadOption(s) {
        var nome = s.nome_squad || 'Squad sem nome';
        var sprint = s.name_sprn ? ' — ' + s.name_sprn : '';
        var extra = s.name_ctdi ? ' (' + s.name_ctdi + ')' : '';
        return nome + sprint + extra;
    }

    function squadPreferida(dados) {
        if (!dados || !dados.length) return null;
        var ativa = dados.find(function (s) {
            var st = String(s.stat_sprn || '').toLowerCase();
            return st === 'ativa' || st === 'em_andamento';
        });
        return ativa || dados[0];
    }

    function atualizarModalSquadLabel(projeto) {
        if (!el.modalSquadLabel) return;
        if (!projeto) {
            el.modalSquadLabel.hidden = true;
            el.modalSquadLabel.textContent = '';
            return;
        }
        el.modalSquadLabel.hidden = false;
        el.modalSquadLabel.textContent = 'Squad: ' + (projeto.nome_squad || '#' + projeto.id_squad) +
            (projeto.name_sprn ? ' · ' + projeto.name_sprn : '');
    }

    function atualizarSquadPickerAtivo(id) {
        if (!el.squadPicker) return;
        el.squadPicker.querySelectorAll('.teams-page__squad-chip').forEach(function (chip) {
            var ativo = String(chip.getAttribute('data-squad-id')) === String(id);
            chip.classList.toggle('is-active', ativo);
            chip.setAttribute('aria-selected', ativo ? 'true' : 'false');
        });
    }

    function renderizarSquadPicker(dados) {
        if (!el.squadPicker) return;
        if (!dados || !dados.length) {
            el.squadPicker.hidden = true;
            el.squadPicker.innerHTML = '';
            return;
        }
        el.squadPicker.hidden = dados.length < 2;
        if (dados.length < 2) {
            el.squadPicker.innerHTML = '';
            return;
        }
        el.squadPicker.innerHTML = '';
        dados.forEach(function (s) {
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'teams-page__squad-chip';
            btn.setAttribute('data-squad-id', s.id_squad);
            btn.setAttribute('role', 'tab');
            btn.setAttribute('aria-selected', 'false');
            btn.innerHTML =
                '<span class="teams-page__squad-chip-name">' + escapeHtml(s.nome_squad || 'Squad') + '</span>' +
                '<span class="teams-page__squad-chip-meta">#' + escapeHtml(s.id_squad) +
                (s.name_sprn ? ' · ' + escapeHtml(s.name_sprn) : '') + '</span>';
            el.squadPicker.appendChild(btn);
        });
    }

    function toggleSeletorSquads(dados) {
        var has = dados && dados.length > 0;
        if (el.switchWrap) el.switchWrap.hidden = !has;
        if (!has) return;
        preencherSeletorSquads(dados);
        renderizarSquadPicker(dados);
    }

    function preencherSeletorSquads(dados) {
        if (!el.selector) return;
        var selected = squadIdSelecionada || (dados[0] && dados[0].id_squad);
        el.selector.innerHTML = '';
        dados.forEach(function (s) {
            var opt = document.createElement('option');
            opt.value = s.id_squad;
            opt.textContent = labelSquadOption(s);
            el.selector.appendChild(opt);
        });
        el.selector.onchange = function () { selecionarSquad(el.selector.value); };
        if (selected) el.selector.value = String(selected);
    }

    async function carregarSquadsRemoto() {
        var url = cfg.bffSquadsUrl || '/bff/meus-projetos';
        var response = await fetch(url, { credentials: 'same-origin' });
        if (!response.ok) return [];
        return response.json();
    }

    function aplicarCotaUsuariosUI(cota) {
        cotaUsuarios = cota;
        if (!elSeat.panel || !cota) return;

        var usado = Number(cota.usado) || 0;
        var max = Number(cota.max_usuarios) || 5;
        var ilimitado = !!cota.ilimitado;
        var noLimite = !cota.pode_adicionar;

        elSeat.panel.hidden = false;
        if (elSeat.count) {
            elSeat.count.textContent = ilimitado
                ? usado + ' / Ilimitado'
                : usado + ' / ' + max + ' Usuários';
            elSeat.count.classList.toggle('is-warning', !ilimitado && usado >= max * 0.8 && !noLimite);
            elSeat.count.classList.toggle('is-danger', noLimite && !ilimitado);
        }
        if (elSeat.planoLabel) {
            var base = Number(cota.max_base_usuarios) || 0;
            var extras = Number(cota.max_addons_usuarios) || 0;
            var planoTxt = cota.nome_plano
                ? 'Plano ' + cota.nome_plano
                : 'Plano padrão (sem contrato ativo)';
            if (extras > 0) {
                planoTxt += ' · Base ' + base + ' + Add-ons ' + extras;
            }
            elSeat.planoLabel.textContent = planoTxt;
        }
        if (elSeat.barFill) {
            var pct = ilimitado ? Math.min(100, usado > 0 ? 12 : 0) : Math.min(100, Math.round((usado / max) * 100));
            elSeat.barFill.style.width = pct + '%';
            elSeat.barFill.classList.toggle('is-warning', !ilimitado && pct >= 80 && pct < 100);
            elSeat.barFill.classList.toggle('is-danger', noLimite && !ilimitado);
        }
        if (elSeat.btnUpgrade) {
            var upgradeUrl = cfg.checkoutUpgradeUrl || '';
            if (noLimite && upgradeUrl) {
                elSeat.btnUpgrade.href = upgradeUrl;
                elSeat.btnUpgrade.hidden = false;
            } else {
                elSeat.btnUpgrade.hidden = true;
            }
        }
        if (elSeat.btnAddon) {
            var addon = cota.addon_sugerido;
            var addonUrl = '';
            if (addon && addon.id) {
                if (cfg.checkoutAddonUrlTemplate) {
                    addonUrl = cfg.checkoutAddonUrlTemplate.replace('{addon_id}', String(addon.id));
                } else if (cfg.checkoutAddonBaseUrl) {
                    addonUrl = cfg.checkoutAddonBaseUrl + encodeURIComponent(addon.id);
                }
            }
            if (noLimite && addonUrl) {
                var extraUsers = (addon && addon.max_usuarios) ? addon.max_usuarios : 5;
                try {
                    var addonLink = new URL(addonUrl, window.location.href);
                    if (addon.nome) addonLink.searchParams.set('addon_nome', addon.nome);
                    if (addon.valor_mensal != null) {
                        addonLink.searchParams.set('addon_valor', String(addon.valor_mensal));
                    }
                    if (addon.periodicidade) {
                        addonLink.searchParams.set('addon_periodicidade', addon.periodicidade);
                    }
                    if (addon.max_usuarios != null) {
                        addonLink.searchParams.set('addon_max_usuarios', String(addon.max_usuarios));
                    }
                    addonUrl = addonLink.toString();
                } catch (urlErr) {
                    /* mantém template original */
                }
                elSeat.btnAddon.innerHTML =
                    '<i class="fas fa-user-plus"></i> Comprar Pacote de +' + extraUsers + ' Usuários';
                elSeat.btnAddon.href = addonUrl;
                elSeat.btnAddon.hidden = false;
            } else {
                elSeat.btnAddon.hidden = true;
            }
        }
        if (el.btnCadastrar && cfg.canCadastrarMembro) {
            el.btnCadastrar.disabled = noLimite;
            el.btnCadastrar.title = noLimite
                ? 'Limite de usuários do plano atingido. Faça upgrade para adicionar mais membros.'
                : '';
        }
    }

    async function carregarCotaUsuarios() {
        if (!cfg.canCadastrarMembro && USER_ROLE !== 'LEAD') return;
        var url = cfg.bffCotaUrl || '/bff/led/cota-usuarios';
        var params = idClieAtual ? ('?id_clie=' + encodeURIComponent(idClieAtual)) : '';
        try {
            var res = await fetch(url + params, { credentials: 'same-origin' });
            var json = await res.json();
            if (res.ok && json.data) {
                aplicarCotaUsuariosUI(json.data);
            }
        } catch (err) {
            console.warn('Não foi possível carregar cota de usuários:', err);
        }
    }

    async function inicializarTeams() {
        var dados = Array.isArray(cfg.initialSquads) && cfg.initialSquads.length
            ? cfg.initialSquads
            : null;

        if (dados && dados.length) {
            setContextState('ready');
        } else {
            setContextState('loading');
        }

        try {
            if (!dados || !dados.length) {
                dados = await carregarSquadsRemoto();
            }

            if (!dados || dados.length === 0) {
                setContextState('empty');
                el.btnNovo.hidden = true;
                if (el.btnCadastrar) el.btnCadastrar.hidden = true;
                if (el.switchWrap) el.switchWrap.hidden = true;
                el.filters.hidden = true;
                el.tbody.innerHTML = '<tr><td colspan="6" class="teams-page__empty"><i class="fas fa-users-slash"></i>Nenhuma squad ativa disponível.</td></tr>';
                return;
            }
            projetosCache = dados;
            setContextState('ready');
            toggleSeletorSquads(dados);

            var preferida = squadPreferida(dados);
            var squadId = cfg.initialSquadId
                ? String(cfg.initialSquadId)
                : String(preferida.id_squad);
            selecionarSquad(squadId);
            await carregarCotaUsuarios();
        } catch (error) {
            console.error('Erro ao carregar squads:', error);
            setContextState('empty');
            el.tbody.innerHTML = '<tr><td colspan="6" class="teams-page__empty teams-page__empty--error"><i class="fas fa-exclamation-triangle"></i>Erro ao conectar com o servidor.</td></tr>';
        }
    }

    function selecionarSquad(id) {
        if (!id) {
            squadIdSelecionada = null;
            el.btnNovo.hidden = true;
            if (el.btnCadastrar) el.btnCadastrar.hidden = true;
            el.filters.hidden = true;
            el.tbody.innerHTML = '<tr><td colspan="6" class="teams-page__empty">Selecione uma squad.</td></tr>';
            return;
        }
        squadIdSelecionada = id;
        var projeto = projetoPorSquad(id);
        if (USER_ROLE === 'ADMIN') {
            idClieAtual = projeto && projeto.id_clie ? projeto.id_clie : USER_ID_CLIE;
        } else {
            idClieAtual = USER_ID_CLIE || (projeto && projeto.id_clie);
        }
        document.getElementById('id_team_vinc').value = id;
        if (el.selector && el.selector.value !== String(id)) el.selector.value = String(id);
        atualizarContextoUI(projeto);
        atualizarModalSquadLabel(projeto);
        atualizarSquadPickerAtivo(id);
        el.btnNovo.hidden = false;
        if (el.btnCadastrar && cfg.canCadastrarMembro) el.btnCadastrar.hidden = false;
        el.filters.hidden = false;
        carregarMembros();
    }

    async function carregarMembros() {
        if (!squadIdSelecionada) return;
        el.tbody.innerHTML = '<tr><td colspan="6" class="teams-page__empty"><i class="fas fa-circle-notch fa-spin"></i> Carregando membros…</td></tr>';
        try {
            var res = await fetch(API_URL + '?id_squad=' + squadIdSelecionada, { credentials: 'same-origin' });
            if (!res.ok) {
                var errBody = await res.json().catch(function () { return {}; });
                el.tbody.innerHTML = '<tr><td colspan="6" class="teams-page__empty teams-page__empty--error">' +
                    escapeHtml(errBody.error || 'Sem permissão para ver esta squad.') + '</td></tr>';
                return;
            }
            var dados = await res.json();
            membrosCache = Array.isArray(dados) ? dados : [];
            renderizarTabela();
        } catch (error) {
            console.error('Erro ao carregar membros:', error);
            el.tbody.innerHTML = '<tr><td colspan="6" class="teams-page__empty teams-page__empty--error">Falha ao carregar membros.</td></tr>';
        }
    }

    function renderizarTabela() {
        var dados = filtrarMembros(membrosCache);
        atualizarContagem();
        el.tbody.innerHTML = '';
        if (!dados.length) {
            var msg = membrosCache.length
                ? 'Nenhum membro corresponde à busca.'
                : 'Nenhum membro nesta squad ainda. Clique em <strong>Alocar time</strong> para começar.';
            el.tbody.innerHTML = '<tr><td colspan="6" class="teams-page__empty"><i class="fas fa-user-plus"></i> ' + msg + '</td></tr>';
            return;
        }
        dados.forEach(function (item) {
            var tr = document.createElement('tr');
            var roleKey = ROLE_STYLES[item.role] || 'cliente';
            tr.innerHTML =
                '<td class="teams-page__cell-id">#' + escapeHtml(item.id_member) + '</td>' +
                '<td><div class="teams-page__member-name">' + escapeHtml(item.nome) + '</div>' +
                '<div class="teams-page__member-spec"><i class="fas fa-tag"></i> ' + escapeHtml(item.position || 'Geral') + '</div></td>' +
                '<td class="teams-page__cell-email">' + escapeHtml(item.email) + '</td>' +
                '<td><span class="teams-page__badge teams-page__badge--' + roleKey + '">' +
                escapeHtml(PERSONA_LABELS[item.role] || item.role) + '</span></td>' +
                '<td><span class="teams-page__status teams-page__status--' + (item.ativo ? 'ativo' : 'inativo') + '">' +
                '<span class="teams-page__status-dot"></span>' + (item.ativo ? 'Ativo' : 'Inativo') + '</span></td>' +
                '<td><div class="teams-page__row-actions">' +
                '<button type="button" class="teams-page__icon-btn teams-page__icon-btn--edit" data-edit="' + item.id_member + '" title="Editar"><i class="fas fa-edit"></i></button>' +
                '<button type="button" class="teams-page__icon-btn teams-page__icon-btn--delete" data-del="' + item.id_member + '" title="Remover"><i class="fas fa-user-minus"></i></button>' +
                '</div></td>';
            tr.querySelector('[data-edit]').addEventListener('click', function () { editar(item); });
            tr.querySelector('[data-del]').addEventListener('click', function () { deletar(item.id_member); });
            el.tbody.appendChild(tr);
        });
    }

    async function salvarRegistro(e) {
        e.preventDefault();
        if (!emailCapacidadeOk) {
            mostrarToast('Capacidade máxima: membro já atua em 3 squads.', 'error');
            return;
        }
        var id_m = document.getElementById('id_member').value;
        var idUsuario = document.getElementById('id_usuario').value;
        var usuario = usuariosDisponiveis.find(function (u) { return String(u.id_usuario) === String(idUsuario); });
        if (!idUsuario || !usuario) {
            mostrarToast('Selecione um usuário existente.', 'error');
            return;
        }
        var payload = {
            id_usuario: parseInt(idUsuario, 10),
            nome: usuario.nome,
            email: usuario.email,
            position: document.getElementById('position').value,
            ativo: document.getElementById('ativo').value === 'true',
            id_squad: parseInt(squadIdSelecionada, 10)
        };
        if (id_m) payload.id_member = parseInt(id_m, 10);
        var method = id_m ? 'PUT' : 'POST';
        var url = id_m ? API_URL + '/' + id_m : API_URL;
        try {
            var res = await fetch(url, { method: method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            var resultado = await res.json();
            if (res.ok) {
                fecharModal();
                carregarMembros();
                mostrarToast('Membro salvo na squad.', 'success');
            } else if (res.status === 409) {
                mostrarToast(resultado.error || 'Capacidade máxima atingida.', 'error');
            } else if (res.status === 403) {
                mostrarToast(resultado.error || 'Operação não permitida.', 'error');
            } else {
                mostrarToast(resultado.error || 'Falha ao salvar.', 'error');
            }
        } catch (err) {
            console.error('Erro:', err);
            mostrarToast('Erro de comunicação.', 'error');
        }
    }

    function editar(item) {
        abrirModal(false);
        document.getElementById('modal-title').innerText = 'Editar alocação';
        document.getElementById('btn-submit-team').innerHTML = '<i class="fas fa-save"></i> Salvar alterações';
        document.getElementById('id_member').value = item.id_member;
        document.getElementById('position').value = item.position || '';
        document.getElementById('ativo').value = item.ativo ? 'true' : 'false';
        var squadId = item.id_squad || item.id_team;
        document.getElementById('id_team_vinc').value = squadId;
        squadIdSelecionada = squadId;
        carregarUsuariosDisponiveis(item.id_usuario).then(function () {
            var select = document.getElementById('id_usuario');
            if (item.id_usuario && !usuariosDisponiveis.find(function (u) { return String(u.id_usuario) === String(item.id_usuario); })) {
                var opt = document.createElement('option');
                opt.value = item.id_usuario;
                opt.textContent = item.nome + ' (' + item.email + ')';
                select.appendChild(opt);
                select.value = String(item.id_usuario);
            }
            select.disabled = true;
            atualizarInfoUsuario();
        });
    }

    async function deletar(id) {
        if (!confirm('Remover este membro da squad?')) return;
        try {
            var res = await fetch(API_URL + '/' + id, { method: 'DELETE', headers: { 'Content-Type': 'application/json' } });
            if (res.ok) {
                carregarMembros();
                mostrarToast('Membro removido da squad.', 'success');
            } else {
                var err = await res.json();
                mostrarToast(err.error || 'Erro ao excluir.', 'error');
            }
        } catch (err) {
            console.error('Erro na exclusão:', err);
        }
    }

    function abrirModal(limpar) {
        if (limpar !== false) {
            document.getElementById('form-team').reset();
            document.getElementById('id_member').value = '';
            document.getElementById('id_team_vinc').value = squadIdSelecionada;
            document.getElementById('modal-title').innerText = 'Alocar time';
            document.getElementById('btn-submit-team').innerHTML = '<i class="fas fa-user-plus"></i> Incluir no time';
            document.getElementById('id_usuario').disabled = false;
            emailCapacidadeOk = true;
            document.getElementById('id_usuario').style.borderColor = '';
            carregarUsuariosDisponiveis();
        }
        el.modal.classList.add('is-open');
        el.modal.setAttribute('aria-hidden', 'false');
    }

    function fecharModalCadastro() {
        if (!el.modalCadastro) return;
        el.modalCadastro.classList.remove('is-open');
        el.modalCadastro.setAttribute('aria-hidden', 'true');
    }

    function abrirModalCadastro() {
        if (!el.modalCadastro) return;
        if (cotaUsuarios && cotaUsuarios.pode_adicionar === false) {
            mostrarToast('Limite de usuários do plano atingido. Faça upgrade ou compre um pacote extra de usuários.', 'error');
            if (elSeat.btnUpgrade && cfg.checkoutUpgradeUrl) {
                elSeat.btnUpgrade.hidden = false;
                elSeat.btnUpgrade.href = cfg.checkoutUpgradeUrl;
            }
            if (elSeat.btnAddon && cotaUsuarios.addon_sugerido && cfg.checkoutAddonUrlTemplate) {
                var addonUrl = cfg.checkoutAddonUrlTemplate.replace(
                    '{addon_id}',
                    String(cotaUsuarios.addon_sugerido.id)
                );
                elSeat.btnAddon.href = addonUrl;
                elSeat.btnAddon.hidden = false;
            }
            return;
        }
        document.getElementById('form-cadastro-membro').reset();
        el.modalCadastro.classList.add('is-open');
        el.modalCadastro.setAttribute('aria-hidden', 'false');
    }

    async function salvarCadastroMembro(e) {
        e.preventDefault();
        var url = cfg.bffCadastroUrl || '/bff/led/usuarios';
        var payload = {
            nome: document.getElementById('cadastro-nome').value.trim(),
            email: document.getElementById('cadastro-email').value.trim(),
            senha: document.getElementById('cadastro-senha').value,
            system_role: document.getElementById('cadastro-role').value
        };
        try {
            var res = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify(payload)
            });
            var data = await res.json();
            if (!res.ok) {
                if (res.status === 403) {
                    await carregarCotaUsuarios();
                }
                mostrarToast(data.error || 'Falha ao cadastrar membro.', 'error');
                return;
            }
            fecharModalCadastro();
            mostrarToast('Membro cadastrado na sua empresa.', 'success');
            await carregarCotaUsuarios();
            await carregarUsuariosDisponiveis(data.data && data.data.id_usuario);
            if (data.data && data.data.id_usuario) {
                document.getElementById('id_usuario').value = String(data.data.id_usuario);
                atualizarInfoUsuario();
            }
        } catch (err) {
            console.error(err);
            mostrarToast('Erro ao cadastrar membro.', 'error');
        }
    }

    function fecharModal() {
        el.modal.classList.remove('is-open');
        el.modal.setAttribute('aria-hidden', 'true');
        document.getElementById('id_usuario').disabled = false;
    }

    el.btnNovo && el.btnNovo.addEventListener('click', function () { abrirModal(true); });
    el.btnCadastrar && el.btnCadastrar.addEventListener('click', abrirModalCadastro);
    var btnFecharCadastro = document.getElementById('btn-fechar-cadastro');
    btnFecharCadastro && btnFecharCadastro.addEventListener('click', fecharModalCadastro);
    var formCadastro = document.getElementById('form-cadastro-membro');
    formCadastro && formCadastro.addEventListener('submit', salvarCadastroMembro);
    el.modalCadastro && el.modalCadastro.addEventListener('click', function (ev) {
        if (ev.target === el.modalCadastro) fecharModalCadastro();
    });
    if (el.btnCadastrar && !cfg.canCadastrarMembro) {
        el.btnCadastrar.hidden = true;
    }
    var btnFechar = document.getElementById('btn-fechar-modal');
    btnFechar && btnFechar.addEventListener('click', fecharModal);
    var formTeam = document.getElementById('form-team');
    formTeam && formTeam.addEventListener('submit', salvarRegistro);
    el.modal && el.modal.addEventListener('click', function (ev) { if (ev.target === el.modal) fecharModal(); });
    var selUsuario = document.getElementById('id_usuario');
    selUsuario && selUsuario.addEventListener('change', function () {
        atualizarInfoUsuario();
        verificarCapacidadeEmail();
    });
    if (el.squadPicker) {
        el.squadPicker.addEventListener('click', function (ev) {
            var chip = ev.target.closest('.teams-page__squad-chip');
            if (!chip) return;
            selecionarSquad(chip.getAttribute('data-squad-id'));
        });
    }
    if (el.busca) {
        el.busca.addEventListener('input', function () {
            buscaAtual = el.busca.value;
            renderizarTabela();
        });
    }

    inicializarTeams();
})();
