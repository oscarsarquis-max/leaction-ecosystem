/**
 * Matriz OKR — painel dinâmico por direcionador + criação CRUD
 */
(function () {
    'use strict';

    var page = document.getElementById('estrategia-okrs-page');
    if (!page) return;

    var idClie = page.getAttribute('data-id-clie');
    var readOnly = page.getAttribute('data-read-only') === '1';
    var accordion = document.getElementById('eo-accordion');
    var modalDetalhe = document.getElementById('eo-detalhe-modal');
    var modalDirec = document.getElementById('eo-modal-direc');
    var modalObj = document.getElementById('eo-modal-obj');
    var krsContainer = document.getElementById('eo-krs-container');
    var progressSummary = document.getElementById('eo-modal-progress-summary');
    var toast = document.getElementById('eo-toast');
    var btnSave = document.getElementById('eo-modal-save');

    var painelCache = { direcionadores: [], rows: [], stats: {} };
    var detalheAtual = null;
    var toastTimer = null;
    var expandedIds = {};

    function escapeHtml(s) {
        return String(s || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function showToast(msg, isError) {
        if (!toast) return;
        toast.textContent = msg;
        toast.classList.toggle('is-error', !!isError);
        toast.classList.add('is-visible');
        clearTimeout(toastTimer);
        toastTimer = setTimeout(function () { toast.classList.remove('is-visible'); }, 3200);
    }

    function mascararMoeda(input) {
        var valor = input.value.replace(/\D/g, '');
        valor = (parseInt(valor || '0', 10) / 100).toFixed(2);
        valor = valor.replace('.', ',').replace(/(\d)(?=(\d{3})+(?!\d))/g, '$1.');
        input.value = 'R$ ' + valor;
    }

    function moedaParaFloat(str) {
        if (!str) return 0;
        return parseFloat(String(str).replace('R$ ', '').replace(/\./g, '').replace(',', '.')) || 0;
    }

    function moedaDeFloat(v) {
        return 'R$ ' + parseFloat(v || 0).toFixed(2).replace('.', ',').replace(/(\d)(?=(\d{3})+(?!\d))/g, '$1.');
    }

    function nivelBadgeClass(nivel) {
        var n = (nivel || 'nao_iniciado').toLowerCase();
        if (n === 'em_andamento') return 'eo-nivel__badge--em_andamento';
        if (n === 'avancado') return 'eo-nivel__badge--avancado';
        return 'eo-nivel__badge--nao_iniciado';
    }

    function renderNivelHtml(row) {
        var pct = row.progresso_pct != null ? row.progresso_pct : 0;
        var label = row.nivel_label || 'Não Iniciado';
        return (
            '<div class="eo-nivel eo-nivel--readonly" title="Progresso calculado pelas atividades de sprint">' +
            '<span class="eo-nivel__badge ' + nivelBadgeClass(row.nivel_implementacao) + '">' +
            escapeHtml(label) + '</span>' +
            '<div class="eo-nivel__bar"><div class="eo-nivel__fill" style="width:' + pct + '%"></div></div>' +
            '<span class="eo-nivel__pct">' + pct + '%</span></div>'
        );
    }

    function renderProgressSummary(detalhe) {
        if (!progressSummary || !detalhe) return;
        var pct = detalhe.progresso_pct != null ? detalhe.progresso_pct : 0;
        progressSummary.innerHTML =
            '<div class="eo-nivel eo-nivel--readonly">' +
            '<span class="eo-nivel__badge ' + nivelBadgeClass(detalhe.nivel_implementacao) + '">' +
            escapeHtml(detalhe.nivel_label || 'Não Iniciado') + '</span>' +
            '<div class="eo-nivel__bar"><div class="eo-nivel__fill" style="width:' + pct + '%"></div></div>' +
            '<span class="eo-nivel__pct">' + pct + '%</span></div>';
    }

    function isPanelOpen(id) {
        if (expandedIds[id] === undefined) return true;
        return !!expandedIds[id];
    }

    function togglePanel(idDirec) {
        expandedIds[idDirec] = !isPanelOpen(idDirec);
        var panel = accordion && accordion.querySelector('.eo-panel[data-id-direc="' + idDirec + '"]');
        if (panel) panel.classList.toggle('is-open', expandedIds[idDirec]);
    }

    function renderStats(stats) {
        var s = stats || {};
        var elD = document.getElementById('eo-stat-direc');
        var elO = document.getElementById('eo-stat-obj');
        var elF = document.getElementById('eo-stat-fixos');
        var elP = document.getElementById('eo-stat-progresso');
        if (elD) elD.textContent = s.total_direcionadores != null ? s.total_direcionadores : '—';
        if (elO) elO.textContent = s.total_objetivos != null ? s.total_objetivos : '—';
        if (elF) elF.textContent = (s.pilares_fixos != null ? s.pilares_fixos : '—') + '/5';
        if (elP) elP.textContent = (s.progresso_medio != null ? s.progresso_medio : 0) + '%';
    }

    function renderObjetivosTable(direc) {
        var objs = direc.objetivos || [];
        if (!objs.length) {
            return (
                '<div class="eo-panel-empty">' +
                '<p>Nenhum objetivo vinculado a este direcionador.</p>' +
                (!readOnly
                    ? '<button type="button" class="eo-btn eo-btn--sm eo-btn--primary" data-action="novo-obj" data-id-direc="' + direc.id_direc + '">' +
                      '<i class="fas fa-plus"></i> Adicionar objetivo TD</button>'
                    : '') +
                '</div>'
            );
        }
        var rows = objs.map(function (o) {
            var tipo = o.is_canonico
                ? '<span class="eo-pill eo-pill--canon">Canônico</span>'
                : '<span class="eo-pill eo-pill--custom">Personalizado</span>';
            return (
                '<tr data-id-obj-dt="' + o.id_obj_dt + '" tabindex="0">' +
                '<td class="eo-obj-cell">' + tipo + ' ' + escapeHtml(o.objetivo_titulo) + '</td>' +
                '<td data-col="nivel">' + renderNivelHtml(o) + '</td>' +
                '<td class="eo-td-krs">' + (o.total_krs || 0) + ' KRs</td>' +
                '<td class="eo-actions">' +
                '<button type="button" data-action="detalhe" data-id-obj-dt="' + o.id_obj_dt + '">' +
                (readOnly ? 'Visualizar' : 'Editar metas') + '</button></td></tr>'
            );
        }).join('');
        return (
            '<table class="eo-table eo-table--nested"><thead><tr>' +
            '<th>Objetivo</th><th>Nível de implementação</th><th>KRs</th><th>Ações</th></tr></thead>' +
            '<tbody>' + rows + '</tbody></table>'
        );
    }

    function renderAccordion(direcionadores) {
        if (!accordion) return;
        if (!direcionadores || !direcionadores.length) {
            accordion.innerHTML = '<div class="eo-empty">Nenhum direcionador cadastrado.</div>';
            return;
        }
        accordion.innerHTML = direcionadores.map(function (d) {
            var open = isPanelOpen(d.id_direc);
            var pill = d.is_catalogo_fixo
                ? '<span class="eo-pill eo-pill--fixo">Pilar MudaEdu</span>'
                : '<span class="eo-pill eo-pill--custom">Personalizado</span>';
            var metaPill = d.meta_financeira === 'aumento_receita'
                ? '<span class="eo-pill eo-pill--receita">' + escapeHtml(d.meta_label || 'Receita') + '</span>'
                : '<span class="eo-pill eo-pill--custo">' + escapeHtml(d.meta_label || 'Custo') + '</span>';
            var actions = '';
            if (!readOnly) {
                actions =
                    '<div class="eo-panel-actions">' +
                    '<button type="button" class="eo-btn eo-btn--sm" data-action="novo-obj" data-id-direc="' + d.id_direc + '">' +
                    '<i class="fas fa-plus"></i> Objetivo</button>';
                if (!d.is_catalogo_fixo) {
                    actions +=
                        '<button type="button" class="eo-btn eo-btn--sm eo-btn--ghost" data-action="edit-direc" ' +
                        'data-id-direc="' + d.id_direc + '" data-nome="' + escapeHtml(d.nome_direc) + '" ' +
                        'data-desc="' + escapeHtml(d.desc_direc) + '" data-kpi="' + escapeHtml(d.kpi_descricao) + '" ' +
                        'data-receita="' + d.meta_receita_alvo + '" data-custo="' + d.meta_custo_alvo + '">' +
                        '<i class="fas fa-pencil-alt"></i></button>' +
                        '<button type="button" class="eo-btn eo-btn--sm eo-btn--danger" data-action="del-direc" data-id-direc="' + d.id_direc + '">' +
                        '<i class="fas fa-trash-alt"></i></button>';
                }
                actions += '</div>';
            }
            return (
                '<article class="eo-panel ' + (d.is_catalogo_fixo ? 'eo-panel--fixo' : 'eo-panel--custom') + (open ? ' is-open' : '') + '" data-id-direc="' + d.id_direc + '">' +
                '<header class="eo-panel__head" data-action="toggle" data-id-direc="' + d.id_direc + '">' +
                '<div class="eo-panel__title">' +
                '<span class="eo-panel__icon">' + escapeHtml(d.icone || '🎯') + '</span>' +
                '<div><div class="eo-panel__pills">' + pill + metaPill + '</div>' +
                '<h2 class="eo-panel__name">' + escapeHtml(d.nome_direc) + '</h2>' +
                '<p class="eo-panel__desc">' + escapeHtml(d.desc_direc || '') + '</p>' +
                '<small class="eo-panel__kpi"><strong>KPI:</strong> ' + escapeHtml(d.kpi_descricao || '—') + '</small></div></div>' +
                '<div class="eo-panel__meta">' +
                '<div class="eo-ring" style="--pct:' + (d.progresso_pct || 0) + '%"><span>' + (d.progresso_pct || 0) + '%</span></div>' +
                '<span class="eo-panel__count">' + (d.total_objetivos || 0) + ' obj.</span>' +
                '<i class="fas fa-chevron-down eo-panel__chevron"></i></div></header>' +
                '<div class="eo-panel__body">' + actions + renderObjetivosTable(d) + '</div></article>'
            );
        }).join('');
    }

    async function carregarPainel() {
        try {
            var res = await fetch('/api/estrategia/resumo-okr?id_clie=' + encodeURIComponent(idClie));
            var data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Falha ao carregar painel.');
            painelCache = {
                direcionadores: data.direcionadores || [],
                rows: data.rows || [],
                stats: data.stats || {}
            };
            if (Object.keys(expandedIds).length === 0) {
                painelCache.direcionadores.forEach(function (d) {
                    expandedIds[d.id_direc] = true;
                });
            }
            renderStats(painelCache.stats);
            renderAccordion(painelCache.direcionadores);
        } catch (err) {
            if (accordion) accordion.innerHTML = '<div class="eo-empty">Erro: ' + escapeHtml(err.message) + '</div>';
        }
    }

    function abrirModal(el) {
        if (!el) return;
        el.hidden = false;
        el.classList.add('is-open');
        document.body.style.overflow = 'hidden';
    }

    function fecharModal(el) {
        if (!el) return;
        el.classList.remove('is-open');
        el.hidden = true;
        if (!document.querySelector('.eo-modal.is-open')) {
            document.body.style.overflow = '';
        }
    }

    function renderKrCards(krs) {
        if (!krsContainer) return;
        if (!krs || !krs.length) {
            krsContainer.innerHTML = '<p class="eo-empty">Nenhum Key Result ainda. Adicione o primeiro abaixo.</p>';
            if (!readOnly) {
                krsContainer.innerHTML +=
                    '<button type="button" class="eo-btn eo-btn--gold" id="eo-btn-add-kr" style="margin-top:12px">' +
                    '<i class="fas fa-plus"></i> Adicionar KR</button>';
                bindAddKrButton();
            }
            return;
        }
        krsContainer.innerHTML = krs.map(function (kr, i) {
            var ph = kr.meta_placeholder || 'Meta';
            var krPct = kr.progresso_pct != null ? kr.progresso_pct : 0;
            var concl = kr.atividades_concluidas != null ? kr.atividades_concluidas : 0;
            var total = kr.total_atividades != null ? kr.total_atividades : 0;
            var ativo = kr.ativo !== false;
            var tag = kr.is_canonico
                ? '<span class="eo-kr-tag">Sugestão MudaEdu</span>'
                : '<span class="eo-kr-tag eo-kr-tag--custom">Personalizado</span>';
            if (!ativo) tag += ' <span class="eo-kr-tag eo-kr-tag--off">Suprimido</span>';
            var descVal = kr.descricao || kr.nome_kr || '';
            return (
                '<article class="eo-kr-card' + (ativo ? '' : ' eo-kr-card--suprimido') + '" data-id-kr="' + kr.id_kr + '">' +
                '<div class="eo-kr-card__top">' +
                '<strong>KR ' + (i + 1) + '</strong> ' + tag +
                '</div>' +
                (readOnly
                    ? '<p class="eo-kr-card__desc">' + escapeHtml(descVal) + '</p>'
                    : '<label class="eo-kr-card__hint">Descrição / título do KR' +
                      '<textarea class="eo-kr-desc-input" data-id-kr="' + kr.id_kr + '" rows="2"' +
                      (ativo ? '' : ' disabled') + '>' + escapeHtml(descVal) + '</textarea></label>') +
                '<div class="eo-kr-card__progress">' +
                '<div class="eo-nivel eo-nivel--readonly eo-nivel--sm">' +
                '<div class="eo-nivel__bar"><div class="eo-nivel__fill" style="width:' + krPct + '%"></div></div>' +
                '<span class="eo-nivel__pct">' + krPct + '%</span></div>' +
                '<small class="eo-kr-card__ativ">' + concl + ' / ' + total + ' atividades concluídas</small></div>' +
                '<div class="eo-kr-card__hint">Meta real (placeholder: ' + escapeHtml(ph) + ')</div>' +
                '<input type="text" class="eo-kr-meta-input" data-id-kr="' + kr.id_kr + '" value="' + escapeHtml(kr.meta_cliente || '') + '" ' +
                'placeholder="Ex.: ' + escapeHtml(ph) + '" ' + (readOnly || !ativo ? 'readonly disabled' : '') + ' />' +
                (!readOnly
                    ? '<div class="eo-kr-card__actions">' +
                      (ativo
                          ? '<button type="button" class="eo-btn eo-btn--ghost eo-btn--sm eo-kr-suppress" data-id-kr="' + kr.id_kr + '">Suprimir</button>'
                          : '<button type="button" class="eo-btn eo-btn--gold eo-btn--sm eo-kr-restore" data-id-kr="' + kr.id_kr + '">Reativar</button>') +
                      '</div>'
                    : '') +
                '</article>'
            );
        }).join('');

        if (!readOnly) {
            krsContainer.innerHTML +=
                '<button type="button" class="eo-btn eo-btn--gold" id="eo-btn-add-kr" style="margin-top:14px">' +
                '<i class="fas fa-plus"></i> Adicionar KR</button>';
            bindAddKrButton();
            bindKrLifecycleButtons();
        }
    }

    function bindAddKrButton() {
        var btn = document.getElementById('eo-btn-add-kr');
        if (!btn || btn._bound) return;
        btn._bound = true;
        btn.addEventListener('click', async function () {
            if (!detalheAtual || readOnly) return;
            var texto = window.prompt('Descrição do novo Key Result:');
            if (!texto || !texto.trim()) return;
            try {
                var res = await fetch('/api/okr/krs', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        id_obj_dt: detalheAtual.id_obj_dt,
                        nome_kr: texto.trim(),
                        desc_kr: texto.trim(),
                        kpi_nome: 'Meta personalizada',
                        valor_inicial: 0,
                        valor_alvo: 100,
                        valor_atual: 0
                    })
                });
                var data = await res.json().catch(function () { return {}; });
                if (!res.ok) throw new Error(data.error || 'Falha ao adicionar KR.');
                showToast('KR adicionado.');
                await abrirDetalhe(detalheAtual.id_obj_dt);
                await carregarPainel();
            } catch (err) {
                showToast(err.message, true);
            }
        });
    }

    function bindKrLifecycleButtons() {
        if (!krsContainer) return;
        krsContainer.querySelectorAll('.eo-kr-suppress, .eo-kr-restore').forEach(function (btn) {
            if (btn._bound) return;
            btn._bound = true;
            btn.addEventListener('click', async function () {
                var idKr = parseInt(btn.getAttribute('data-id-kr'), 10);
                var reativar = btn.classList.contains('eo-kr-restore');
                if (!reativar && !window.confirm('Suprimir este KR? Ele sai das sugestões e do vínculo de novas atividades.')) return;
                try {
                    var res = await fetch('/api/estrategia/kr-cliente/' + idKr, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ ativo: reativar })
                    });
                    var data = await res.json().catch(function () { return {}; });
                    if (!res.ok) throw new Error(data.error || 'Falha ao atualizar KR.');
                    showToast(reativar ? 'KR reativado.' : 'KR suprimido.');
                    await abrirDetalhe(detalheAtual.id_obj_dt);
                    await carregarPainel();
                } catch (err) {
                    showToast(err.message, true);
                }
            });
        });
    }

    async function abrirDetalhe(idObjDt) {
        try {
            var res = await fetch('/api/estrategia/objetivo-cliente/' + idObjDt);
            var data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Objetivo não encontrado.');
            detalheAtual = data.data;
            document.getElementById('eo-modal-path').innerHTML =
                'Direcionador: <strong>' + escapeHtml(detalheAtual.direcionador_nome) + '</strong>';
            document.getElementById('eo-modal-title').textContent = detalheAtual.objetivo_titulo || '';
            renderProgressSummary(detalheAtual);
            renderKrCards(detalheAtual.krs || []);
            if (btnSave) {
                btnSave.hidden = readOnly;
                btnSave.disabled = readOnly;
            }
            abrirModal(modalDetalhe);
        } catch (err) {
            showToast(err.message, true);
        }
    }

    async function salvarDetalhe() {
        if (!detalheAtual || readOnly) return;
        btnSave.disabled = true;
        btnSave.textContent = 'Salvando…';
        try {
            var inputs = krsContainer.querySelectorAll('.eo-kr-meta-input');
            var descInputs = krsContainer.querySelectorAll('.eo-kr-desc-input');
            var descById = {};
            Array.prototype.forEach.call(descInputs, function (el) {
                descById[el.getAttribute('data-id-kr')] = el.value.trim();
            });
            var krsPayload = Array.prototype.map.call(inputs, function (input) {
                var idKr = input.getAttribute('data-id-kr');
                var payload = {
                    id_kr: parseInt(idKr, 10),
                    meta_cliente: input.value.trim()
                };
                if (descById[idKr]) {
                    payload.descricao = descById[idKr];
                    payload.nome_kr = descById[idKr];
                    payload.desc_kr = descById[idKr];
                }
                return payload;
            });
            // Inclui KRs só com descrição editada (sem meta input ativo — ex.: suprimidos não)
            Array.prototype.forEach.call(descInputs, function (el) {
                var idKr = el.getAttribute('data-id-kr');
                if (!inputs.length || !Array.prototype.some.call(inputs, function (i) { return i.getAttribute('data-id-kr') === idKr; })) {
                    if (!el.disabled && el.value.trim()) {
                        krsPayload.push({
                            id_kr: parseInt(idKr, 10),
                            descricao: el.value.trim(),
                            nome_kr: el.value.trim(),
                            desc_kr: el.value.trim()
                        });
                    }
                }
            });
            var resObj = await fetch('/api/estrategia/objetivo-cliente/' + detalheAtual.id_obj_dt, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ krs: krsPayload })
            });
            var dataObj = await resObj.json();
            if (!resObj.ok) throw new Error(dataObj.error || 'Erro ao salvar metas.');
            showToast('Metas dos KRs atualizadas.');
            fecharModal(modalDetalhe);
            await carregarPainel();
        } catch (err) {
            showToast(err.message, true);
        } finally {
            btnSave.disabled = false;
            btnSave.textContent = 'Salvar alterações';
        }
    }

    function abrirModalDirec(editData) {
        if (!modalDirec) return;
        document.getElementById('eo-direc-id-edit').value = editData ? editData.id : '';
        document.getElementById('eo-direc-nome').value = editData ? editData.nome : '';
        document.getElementById('eo-direc-desc').value = editData ? editData.desc : '';
        document.getElementById('eo-direc-kpi').value = editData ? editData.kpi : '';
        document.getElementById('eo-direc-receita').value = moedaDeFloat(editData ? editData.receita : 0);
        document.getElementById('eo-direc-custo').value = moedaDeFloat(editData ? editData.custo : 0);
        document.getElementById('eo-direc-titulo').innerHTML = editData
            ? '<i class="fas fa-bullseye"></i> Editar direcionador'
            : '<i class="fas fa-bullseye"></i> Novo direcionador personalizado';
        abrirModal(modalDirec);
    }

    async function salvarDirecionador(e) {
        e.preventDefault();
        var idEdit = document.getElementById('eo-direc-id-edit').value;
        var payload = {
            id_clie: parseInt(idClie, 10),
            nome_direc: document.getElementById('eo-direc-nome').value.trim(),
            desc_direc: document.getElementById('eo-direc-desc').value.trim(),
            kpi_descricao: document.getElementById('eo-direc-kpi').value.trim(),
            meta_receita_alvo: moedaParaFloat(document.getElementById('eo-direc-receita').value),
            meta_custo_alvo: moedaParaFloat(document.getElementById('eo-direc-custo').value),
            status_direc: 'Ativo'
        };
        var url = idEdit ? '/api/okr/direcionadores/' + idEdit : '/api/okr/direcionadores';
        var method = idEdit ? 'PUT' : 'POST';
        try {
            var res = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            var data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Erro ao salvar direcionador.');
            showToast(idEdit ? 'Direcionador atualizado.' : 'Direcionador criado com sucesso!');
            fecharModal(modalDirec);
            await carregarPainel();
        } catch (err) {
            showToast(err.message, true);
        }
    }

    function abrirModalObj(idDirec) {
        if (!modalObj) return;
        document.getElementById('eo-obj-id-direc').value = idDirec;
        document.getElementById('eo-obj-nome').value = '';
        document.getElementById('eo-obj-desc').value = '';
        document.getElementById('eo-obj-kpi').value = '';
        abrirModal(modalObj);
    }

    async function salvarObjetivo(e) {
        e.preventDefault();
        var payload = {
            id_direc: parseInt(document.getElementById('eo-obj-id-direc').value, 10),
            nome_obj: document.getElementById('eo-obj-nome').value.trim(),
            desc_obj: document.getElementById('eo-obj-desc').value.trim(),
            kpi_descricao: document.getElementById('eo-obj-kpi').value.trim(),
            status_obj: 'Ativo'
        };
        try {
            var res = await fetch('/api/okr/objetivos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            var data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Erro ao criar objetivo.');
            showToast('Objetivo vinculado ao direcionador.');
            fecharModal(modalObj);
            expandedIds[payload.id_direc] = true;
            await carregarPainel();
        } catch (err) {
            showToast(err.message, true);
        }
    }

    async function excluirDirecionador(idDirec) {
        if (!confirm('Excluir este direcionador personalizado e seus vínculos?')) return;
        try {
            var res = await fetch('/api/okr/direcionadores/' + idDirec, { method: 'DELETE' });
            var data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Não foi possível excluir.');
            showToast('Direcionador removido.');
            delete expandedIds[idDirec];
            await carregarPainel();
        } catch (err) {
            showToast(err.message, true);
        }
    }

    // Eventos
    var btnNovoDirec = document.getElementById('eo-btn-novo-direc');
    if (btnNovoDirec) btnNovoDirec.addEventListener('click', function () { abrirModalDirec(null); });

    var formDirec = document.getElementById('eo-form-direc');
    if (formDirec) formDirec.addEventListener('submit', salvarDirecionador);

    var formObj = document.getElementById('eo-form-obj');
    if (formObj) formObj.addEventListener('submit', salvarObjetivo);

    document.querySelectorAll('[data-moeda]').forEach(function (inp) {
        inp.addEventListener('input', function () { mascararMoeda(inp); });
    });

    document.querySelectorAll('[data-close-modal]').forEach(function (b) {
        b.addEventListener('click', function () { fecharModal(modalDetalhe); });
    });
    document.querySelectorAll('[data-close-direc]').forEach(function (b) {
        b.addEventListener('click', function () { fecharModal(modalDirec); });
    });
    document.querySelectorAll('[data-close-obj]').forEach(function (b) {
        b.addEventListener('click', function () { fecharModal(modalObj); });
    });

    if (btnSave) btnSave.addEventListener('click', salvarDetalhe);

    if (accordion) {
        accordion.addEventListener('click', function (e) {
            if (e.target.closest('button[data-action]')) {
                var btn = e.target.closest('button[data-action]');
                var action = btn.getAttribute('data-action');
                var idDirec = parseInt(btn.getAttribute('data-id-direc'), 10);
                var idObj = parseInt(btn.getAttribute('data-id-obj-dt'), 10);

                if (action === 'detalhe' && idObj) { abrirDetalhe(idObj); return; }
                if (action === 'novo-obj' && idDirec) { abrirModalObj(idDirec); return; }
                if (action === 'edit-direc') {
                    abrirModalDirec({
                        id: idDirec,
                        nome: btn.getAttribute('data-nome'),
                        desc: btn.getAttribute('data-desc'),
                        kpi: btn.getAttribute('data-kpi'),
                        receita: btn.getAttribute('data-receita'),
                        custo: btn.getAttribute('data-custo')
                    });
                    return;
                }
                if (action === 'del-direc' && idDirec) { excluirDirecionador(idDirec); }
                return;
            }

            var head = e.target.closest('.eo-panel__head[data-action="toggle"]');
            if (head) {
                var idToggle = parseInt(head.getAttribute('data-id-direc'), 10);
                if (idToggle) togglePanel(idToggle);
            }
        });

        accordion.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                var tr = e.target.closest('tr[data-id-obj-dt]');
                if (tr) abrirDetalhe(parseInt(tr.getAttribute('data-id-obj-dt'), 10));
            }
        });

        accordion.addEventListener('click', function (e) {
            var tr = e.target.closest('tr[data-id-obj-dt]');
            if (tr && !e.target.closest('button')) {
                abrirDetalhe(parseInt(tr.getAttribute('data-id-obj-dt'), 10));
            }
        });
    }

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            [modalDetalhe, modalDirec, modalObj].forEach(fecharModal);
        }
    });

    [modalDetalhe, modalDirec, modalObj].forEach(function (m) {
        if (!m) return;
        m.addEventListener('click', function (e) {
            if (e.target === m) fecharModal(m);
        });
    });

    if (!idClie) {
        if (accordion) accordion.innerHTML = '<div class="eo-empty">Cliente não identificado na sessão.</div>';
        return;
    }
    carregarPainel();
})();
