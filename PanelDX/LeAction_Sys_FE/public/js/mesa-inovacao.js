(function () {
    'use strict';

    const root = document.getElementById('mesa-org-root');
    if (!root) return;

    const idMatu = parseInt(root.dataset.idMatu, 10) || null;
    const idClie = parseInt(root.dataset.idClie, 10) || null;
    const blocoPrefill = root.dataset.blocoPrefill || '';
    const FILA_KEY = 'paneldx_mesa_fila_blocos';
    const STORAGE_KEY = idMatu ? ('paneldx_mesa_org_notas_' + idMatu) : null;

    let topGaps = [];
    try {
        topGaps = JSON.parse(document.getElementById('mesa-top-gaps-json').textContent || '[]');
    } catch (e) {
        console.warn('Gaps não carregados:', e);
    }

    const ORDEM_PILARES = ['contencao', 'implementacao', 'prevencao', 'sustentacao'];
    const PILARES_FIXOS = {
        contencao: { label: 'Contenção do Problema', prioridade: 'Critica', esforco: 5 },
        implementacao: { label: 'Implementação da Solução', prioridade: 'Alta', esforco: 8 },
        prevencao: { label: 'Prevenção de Recorrência', prioridade: 'Media', esforco: 3 },
        sustentacao: { label: 'Sustentação', prioridade: 'Baixa', esforco: 2 }
    };

    let notasLocais = [];
    let listaSubtasksLocais = [];
    let gapAtivo = null;
    let ideiaConsolidada = false;
    let persistenciaApi = !!(idClie && idMatu);
    let backlogEsim = [];

    const elMural = document.getElementById('mesa-mural');
    const elContador = document.getElementById('mesa-contador-notas');
    const elEmpty = document.getElementById('mesa-consultor-empty');
    const elResult = document.getElementById('mesa-consultor-result');
    const elBtnSprint = document.getElementById('mesa-btn-transformar-sprint');
    const elToast = document.getElementById('mesa-toast');
    const elEsimList = document.getElementById('mesa-esim-list');
    const elEsimContador = document.getElementById('mesa-esim-contador');

    function rotuloPilar(key) {
        return (PILARES_FIXOS[key] && PILARES_FIXOS[key].label) || key;
    }

    function mostrarToast(msg, cor) {
        if (!elToast) return;
        elToast.textContent = msg;
        elToast.style.background = cor || '#059669';
        elToast.classList.add('is-visible');
        setTimeout(function () { elToast.classList.remove('is-visible'); }, 3200);
    }

    function getTexto(el) {
        return el ? (el.innerText || el.textContent || '').trim() : '';
    }

    function escapeHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function normalizarNome(str) {
        return String(str || '').trim().toLowerCase();
    }

    function blocoKey(bloco) {
        return normalizarNome(bloco && (bloco.id_bloc || bloco.nome));
    }

    function extrairHipoteseTelemetria(conteudo) {
        if (!conteudo) return '';
        var match = conteudo.match(/\[ALERTA TELEMETRIA[^\]]*\]\s*([\s\S]*?)(?:\n\nDomínio:|$)/);
        return match ? match[1].trim() : conteudo;
    }

    function notaFromApi(row) {
        var origem = row.origem || 'mesa_org';
        var isTelemetria = origem === 'telemetria' || !!row.is_alerta;
        return {
            id: String(row.id_nota),
            id_nota: row.id_nota,
            conteudo: row.conteudo || '',
            contexto: row.contexto || 'Ideação livre',
            status: row.status || 'Pendente',
            origemGap: row.origem_gap || null,
            origem: origem,
            isAlerta: !!(row.is_alerta || origem === 'telemetria'),
            hipoteseNegocio: row.hipotese_negocio || (isTelemetria ? extrairHipoteseTelemetria(row.conteudo) : ''),
            subtasks: Array.isArray(row.subtasks) ? row.subtasks : [],
            statusAnomalia: row.status_anomalia || null,
            idItemBacklog: row.id_item_backlog || null,
            dominioAssociado: row.dominio_associado || null,
            blocoAssociado: row.bloco_associado || null,
            codigoEventoPadrao: row.codigo_evento_padrao || null
        };
    }

    function salvarNotasLocalStorage() {
        if (!STORAGE_KEY) return;
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(notasLocais));
        } catch (e) {
            console.warn('localStorage indisponível:', e);
        }
    }

    function carregarNotasLocalStorage() {
        if (!STORAGE_KEY) return [];
        try {
            var raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) return [];
            var parsed = JSON.parse(raw);
            return Array.isArray(parsed) ? parsed : [];
        } catch (e) {
            return [];
        }
    }

    async function parseJsonResponse(response) {
        const raw = await response.text();
        const trimmed = raw.trim();
        if (trimmed.charAt(0) === '{' || trimmed.charAt(0) === '[') {
            try {
                return JSON.parse(trimmed);
            } catch (e) {
                throw new Error('Resposta JSON inválida do servidor.');
            }
        }
        const ct = (response.headers.get('content-type') || '').toLowerCase();
        if (ct.includes('application/json') && trimmed) {
            try {
                return JSON.parse(trimmed);
            } catch (e) {
                throw new Error('Resposta JSON inválida do servidor.');
            }
        }
        throw new Error(
            response.status === 404
                ? 'Rota da Mesa não encontrada no servidor (404). Aguarde o deploy do backend.'
                : 'Resposta inválida do servidor (esperado JSON).'
        );
    }

    async function carregarNotas() {
        if (persistenciaApi) {
            try {
                const response = await fetch(
                    '/api/mesa-inovacao/notas?id_clie=' + encodeURIComponent(idClie) +
                    '&id_matu=' + encodeURIComponent(idMatu),
                    { credentials: 'same-origin' }
                );
                const data = await parseJsonResponse(response);
                if (data.status === 'success' && Array.isArray(data.data)) {
                    notasLocais = data.data.map(notaFromApi);
                    salvarNotasLocalStorage();
                    return;
                }
            } catch (e) {
                console.warn('API de notas indisponível, usando cache local:', e);
            }
        }
        notasLocais = carregarNotasLocalStorage();
    }

    async function persistirNota(nota) {
        if (persistenciaApi) {
            try {
                const response = await fetch('/api/mesa-inovacao/notas', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'same-origin',
                    body: JSON.stringify({
                        id_clie: idClie,
                        id_matu: idMatu,
                        conteudo: nota.conteudo,
                        contexto: nota.contexto,
                        origem_gap: nota.origemGap
                    })
                });
                const data = await parseJsonResponse(response);
                if (data.status === 'success' && data.data) {
                    return notaFromApi(data.data);
                }
            } catch (e) {
                console.warn('Falha ao gravar post-it na API:', e);
            }
        }
        nota.id = nota.id || ('local_' + Date.now());
        return nota;
    }

    async function removerNota(idNota) {
        const idNum = parseInt(idNota, 10);
        if (persistenciaApi && !isNaN(idNum)) {
            try {
                await fetch('/api/mesa-inovacao/notas?id_nota=' + encodeURIComponent(idNum), {
                    method: 'DELETE',
                    credentials: 'same-origin'
                });
            } catch (e) {
                console.warn('Falha ao remover post-it na API:', e);
            }
        }
        notasLocais = notasLocais.filter(function (n) { return n.id !== idNota; });
        salvarNotasLocalStorage();
        renderizarMural();
    }

    async function consumirBacklogEsim(opts) {
        if (!persistenciaApi) return;
        var body = {};
        if (opts && opts.idItemBacklog) body.id_item = opts.idItemBacklog;
        if (opts && (opts.idNota || opts.id_nota)) body.id_nota = opts.idNota || opts.id_nota;
        if (!body.id_item && !body.id_nota) return;
        try {
            await fetch('/api/esim/mesa-backlog/consumir', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify(body)
            });
        } catch (e) {
            console.warn('Falha ao consumir backlog eSIM:', e);
        }
        await carregarBacklogEsim();
    }

    async function consumirBacklogDasNotas(notas) {
        if (!notas || !notas.length) return;
        var vistos = {};
        for (var i = 0; i < notas.length; i++) {
            var n = notas[i];
            var chave = (n.idItemBacklog || '') + ':' + (n.id_nota || n.id);
            if (vistos[chave]) continue;
            vistos[chave] = true;
            await consumirBacklogEsim({
                idItemBacklog: n.idItemBacklog,
                idNota: n.id_nota || n.id
            });
        }
    }

    function itemBacklogFromApi(row) {
        return {
            idItem: row.id_item,
            idNotaMesa: row.id_nota_mesa,
            hipotese: row.hipotese_negocio || '',
            subtasks: Array.isArray(row.subtasks) ? row.subtasks : [],
            dominio: row.dominio_associado || null,
            bloco: row.bloco_associado || null,
            codigoEvento: row.codigo_evento_padrao || null,
            criadoEm: row.criado_em || null
        };
    }

    function renderizarBacklogEsim() {
        if (!elEsimList) return;
        if (elEsimContador) {
            elEsimContador.textContent = backlogEsim.length + ' pendente' + (backlogEsim.length === 1 ? '' : 's');
        }
        if (backlogEsim.length === 0) {
            elEsimList.innerHTML = '<p class="mesa-empty-hint" id="mesa-esim-empty">Nenhum alerta eSIM pendente no backlog preditivo.</p>';
            return;
        }
        elEsimList.innerHTML = backlogEsim.map(function (item) {
            var titulo = item.codigoEvento
                ? item.codigoEvento.replace(/_/g, ' ')
                : 'Alerta telemetria';
            var tags = '';
            if (item.dominio) {
                tags += '<span class="mesa-esim-item__tag">' + escapeHtml(item.dominio) + '</span>';
            }
            if (item.bloco) {
                tags += '<span class="mesa-esim-item__tag mesa-esim-item__tag--bloco">' + escapeHtml(item.bloco) + '</span>';
            }
            return (
                '<article class="mesa-esim-item" data-id-item="' + item.idItem + '"' +
                (item.idNotaMesa ? ' data-id-nota="' + item.idNotaMesa + '"' : '') + '>' +
                '<h3 class="mesa-esim-item__titulo">🚨 ' + escapeHtml(titulo) + '</h3>' +
                '<p class="mesa-esim-item__hipotese">' + escapeHtml(item.hipotese || 'Hipótese em processamento…') + '</p>' +
                (tags ? '<div class="mesa-esim-item__tags">' + tags + '</div>' : '') +
                '</article>'
            );
        }).join('');
    }

    async function carregarBacklogEsim() {
        if (!persistenciaApi || !elEsimList) return;
        try {
            var response = await fetch(
                '/api/esim/mesa-backlog?id_clie=' + encodeURIComponent(idClie) +
                '&id_matu=' + encodeURIComponent(idMatu),
                { credentials: 'same-origin' }
            );
            var data = await parseJsonResponse(response);
            if (data.status === 'success' && Array.isArray(data.data)) {
                backlogEsim = data.data.map(itemBacklogFromApi);
                renderizarBacklogEsim();
                return;
            }
        } catch (e) {
            console.warn('Backlog eSIM indisponível:', e);
        }
        if (elEsimList) {
            elEsimList.innerHTML = '<p class="mesa-empty-hint">Backlog eSIM indisponível (backend offline ou sem permissão).</p>';
        }
    }

    function destacarNotaNoMural(idNota) {
        if (!idNota) return;
        document.querySelectorAll('.mesa-esim-item').forEach(function (el) { el.classList.remove('is-active'); });
        var card = document.querySelector('[data-nota-id="' + idNota + '"]');
        if (card) {
            card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            card.classList.add('is-active');
            setTimeout(function () { card.classList.remove('is-active'); }, 1800);
        }
    }

    async function incubarNotasApi(ids) {
        const idsNum = ids.map(function (id) { return parseInt(id, 10); }).filter(function (n) { return !isNaN(n); });
        if (!persistenciaApi || idsNum.length === 0) return;
        try {
            await fetch('/api/mesa-inovacao/notas/incubar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({ ids_notas: idsNum })
            });
        } catch (e) {
            console.warn('Falha ao incubar post-its na API:', e);
        }
        await carregarBacklogEsim();
    }

    function notaJaExisteParaBloco(bloco) {
        const key = blocoKey(bloco);
        if (!key) return false;
        return notasLocais.some(function (n) {
            if (n.origemGap && blocoKey(n.origemGap) === key) return true;
            return normalizarNome(n.contexto).indexOf(normalizarNome(bloco.nome)) >= 0;
        });
    }

    function lerFilaBlocos() {
        var fila = [];
        try {
            var raw = sessionStorage.getItem(FILA_KEY);
            if (raw) {
                var parsed = JSON.parse(raw);
                if (Array.isArray(parsed)) fila = parsed;
            }
        } catch (e) { /* ignore */ }

        try {
            var rawPrior = sessionStorage.getItem('paneldx_sprint_prioridade');
            if (rawPrior) {
                var prior = JSON.parse(rawPrior);
                if (prior && prior.nome && !fila.some(function (b) { return blocoKey(b) === blocoKey(prior); })) {
                    fila.push(prior);
                }
            }
        } catch (e) { /* ignore */ }

        if (blocoPrefill) {
            var jaNaFila = fila.some(function (b) { return normalizarNome(b.nome) === normalizarNome(blocoPrefill); });
            if (!jaNaFila) {
                fila.push({ nome: blocoPrefill, origem: 'url-mesa' });
            }
        }

        return fila;
    }

    function gravarFilaBlocos(fila) {
        try {
            sessionStorage.setItem(FILA_KEY, JSON.stringify(fila));
        } catch (e) {
            console.warn('Não foi possível gravar fila de blocos:', e);
        }
    }

    function removerBlocoDaFila(bloco) {
        const key = blocoKey(bloco);
        const fila = lerFilaBlocos().filter(function (b) { return blocoKey(b) !== key; });
        gravarFilaBlocos(fila);
    }

    async function criarNota(conteudo, contexto, origemGap) {
        const nota = {
            conteudo: conteudo.trim(),
            contexto: contexto || 'Ideação livre',
            status: 'Pendente',
            origemGap: origemGap || null
        };
        const salva = await persistirNota(nota);
        const idx = notasLocais.findIndex(function (n) { return n.id === salva.id; });
        if (idx >= 0) {
            notasLocais[idx] = salva;
        } else {
            notasLocais.push(salva);
        }
        salvarNotasLocalStorage();
        renderizarMural();
        return salva;
    }

    function renderPostitManual(n, idx) {
        var cls = 'mesa-postit';
        if (n.origemGap) cls += ' mesa-postit--gap';
        if (n.status === 'Incubada') cls += ' mesa-postit--incubada';
        var rot = idx % 2 === 0 ? 'rotate(1deg)' : 'rotate(-1deg)';

        return (
            '<div class="' + cls + '" data-nota-id="' + n.id + '" style="transform:' + rot + '">' +
            '<div class="mesa-postit__actions">' +
            (n.status === 'Pendente'
                ? '<button type="button" data-action="del" data-id="' + n.id + '" title="Remover"><i class="fas fa-trash"></i></button>'
                : '') +
            '<input type="checkbox" class="mesa-chk-nota" value="' + n.id + '"' +
            (n.status !== 'Pendente' ? ' disabled' : '') + '>' +
            '</div>' +
            '<span class="mesa-postit__ctx">' + escapeHtml(n.contexto) + '</span>' +
            '<p class="mesa-postit__text">' + escapeHtml(n.conteudo) + '</p>' +
            '</div>'
        );
    }

    function renderPostitTelemetria(n) {
        var cls = 'mesa-postit post-it-telemetria';
        if (n.status === 'Incubada') cls += ' mesa-postit--incubada';
        var titulo = '🚨 ' + (n.contexto || 'Alerta de telemetria');
        if (n.statusAnomalia) {
            titulo += ' · ' + n.statusAnomalia.replace(/_/g, ' ');
        }
        var hipotese = n.hipoteseNegocio || extrairHipoteseTelemetria(n.conteudo);
        var sprintDisabled = n.status !== 'Pendente' ? ' disabled' : '';
        var metaBloco = '';
        if (n.dominioAssociado || n.blocoAssociado) {
            metaBloco = '<div class="post-it-telemetria__meta">' +
                (n.dominioAssociado ? '<span class="mesa-tag">' + escapeHtml(n.dominioAssociado) + '</span> ' : '') +
                (n.blocoAssociado ? '<span class="mesa-tag">' + escapeHtml(n.blocoAssociado) + '</span>' : '') +
                '</div>';
        }

        return (
            '<article class="' + cls + '" data-nota-id="' + n.id + '" data-origem="telemetria"' +
            (n.idItemBacklog ? ' data-id-item-backlog="' + n.idItemBacklog + '"' : '') + '>' +
            '<div class="mesa-postit__actions">' +
            (n.status === 'Pendente'
                ? '<button type="button" data-action="del" data-id="' + n.id + '" title="Remover"><i class="fas fa-trash"></i></button>'
                : '') +
            '<input type="checkbox" class="mesa-chk-nota" value="' + n.id + '"' +
            (n.status !== 'Pendente' ? ' disabled' : '') + '>' +
            '</div>' +
            '<header class="post-it-telemetria__titulo">' + escapeHtml(titulo) + '</header>' +
            metaBloco +
            '<p class="post-it-telemetria__hipotese">' + escapeHtml(hipotese) + '</p>' +
            '<footer class="post-it-telemetria__footer">' +
            '<button type="button" class="mesa-btn mesa-btn--sprint post-it-telemetria__cta"' +
            ' data-action="sprint-telemetria" data-id="' + n.id + '"' + sprintDisabled + '>' +
            '<i class="fas fa-rocket"></i> Transformar em Sprint' +
            '</button>' +
            '</footer>' +
            '</article>'
        );
    }

    function renderizarMural() {
        elContador.textContent = String(notasLocais.length);
        var elEmpty = document.getElementById('mesa-mural-empty');
        if (notasLocais.length === 0) {
            elMural.innerHTML = '<p class="mesa-empty-hint" id="mesa-mural-empty" style="grid-column:1/-1;">Selecione um gap ou adicione notas manualmente.</p>';
            return;
        }

        elMural.innerHTML = notasLocais.map(function (n, idx) {
            if (n.origem === 'telemetria' || n.isAlerta) {
                return renderPostitTelemetria(n);
            }
            return renderPostitManual(n, idx);
        }).join('');
    }

    function getNotasSelecionadas() {
        return Array.from(document.querySelectorAll('.mesa-chk-nota:checked')).map(function (cb) {
            return notasLocais.find(function (n) { return n.id === cb.value; });
        }).filter(Boolean);
    }

    function obterDirecionadorSelecionado() {
        const sel = document.getElementById('mesa-select-direcionador');
        if (!sel || !sel.value) return null;
        const opt = sel.options[sel.selectedIndex];
        return {
            id_direc: sel.value,
            nome: opt.getAttribute('data-nome') || opt.textContent.trim(),
            desc: opt.getAttribute('data-desc') || '',
            slug: opt.getAttribute('data-slug') || ''
        };
    }

    function resetPainelConsultor(mensagem) {
        elEmpty.style.display = 'none';
        elResult.classList.add('is-visible');
        document.getElementById('mesa-res-titulo').textContent = mensagem || 'Processando…';
        document.getElementById('mesa-res-hipotese').textContent = '';
        document.getElementById('mesa-res-justificativa').textContent = '';
        document.getElementById('mesa-res-impacto').textContent = '';
        document.getElementById('mesa-res-composicao').innerHTML = '';
        listaSubtasksLocais = [];
        renderizarSubtasks();
        ideiaConsolidada = false;
        elBtnSprint.disabled = true;
    }

    async function exibirResultadoConsultor(rascunho, notasSelecionadas) {
        const pilares = rascunho.pilares || {};
        document.getElementById('mesa-res-titulo').textContent = rascunho.nome_acao || 'Iniciativa organizacional';
        document.getElementById('mesa-res-justificativa').textContent = rascunho.justificativa_pedagogica || rascunho.justificativa_estrategica || '';
        document.getElementById('mesa-res-impacto').textContent = rascunho.impacto_negocio || '';

        const hipoteseSugerida = rascunho.hipotese_estrategica
            || ('Se implementarmos "' + (rascunho.nome_acao || 'esta iniciativa') + '", a lacuna de maturidade identificada reduzirá em até 90 dias.');
        document.getElementById('mesa-res-hipotese').textContent = hipoteseSugerida;

        let html = '';
        ORDEM_PILARES.forEach(function (k) {
            html += '<div class="mesa-pilar"><strong>' + rotuloPilar(k) + '</strong>' +
                '<span class="mesa-pilar-editavel" contenteditable="true" data-key="' + k + '">' +
                escapeHtml(pilares[k] || '') + '</span></div>';
        });
        document.getElementById('mesa-res-composicao').innerHTML = html;

        document.getElementById('mesa-hdn-id-ideia').value = 'mesa_org_' + Date.now();
        ideiaConsolidada = true;
        elBtnSprint.disabled = false;

        const idsIncubar = (notasSelecionadas || []).map(function (n) { return n.id; });
        await incubarNotasApi(idsIncubar);
        await consumirBacklogDasNotas(notasSelecionadas || []);
        (notasSelecionadas || []).forEach(function (n) { n.status = 'Incubada'; });
        salvarNotasLocalStorage();
        renderizarMural();
    }

    function renderizarSubtasks() {
        const container = document.getElementById('mesa-lista-subtasks');
        if (!container) return;
        if (listaSubtasksLocais.length === 0) {
            container.innerHTML = '<p class="mesa-empty-hint" style="padding: 8px 0;">Nenhuma subtask vinculada.</p>';
            return;
        }
        container.innerHTML = listaSubtasksLocais.map(function (st, idx) {
            return (
                '<div class="mesa-subtask-item">' +
                '<span><strong style="color:#d97706;">[' + rotuloPilar(st.pilar_subtask) + ']</strong> ' + escapeHtml(st.desc_subtask) + '</span>' +
                '<button type="button" class="mesa-btn mesa-btn--ghost" data-rm-subtask="' + idx + '" style="padding:4px 8px;font-size:0.65rem;">×</button>' +
                '</div>'
            );
        }).join('');
    }

    function montarPayloadUniversal() {
        const idMesa = document.getElementById('mesa-hdn-id-ideia').value || ('mesa_org_' + Date.now());
        const nomeSprint = getTexto(document.getElementById('mesa-res-titulo')) || 'Sprint Organizacional';
        const justificativa = getTexto(document.getElementById('mesa-res-justificativa'));
        const impacto = getTexto(document.getElementById('mesa-res-impacto'));
        const hipotese = getTexto(document.getElementById('mesa-res-hipotese'));
        const direcionador = obterDirecionadorSelecionado();

        var blocoOrigem = gapAtivo;
        if (!blocoOrigem) {
            try {
                var rawPrior = sessionStorage.getItem('paneldx_sprint_prioridade');
                if (rawPrior) blocoOrigem = JSON.parse(rawPrior);
            } catch (e) { /* ignore */ }
        }

        const labelsMap = {};
        const prioridadesMap = {};
        const esforceMap = {};
        ORDEM_PILARES.forEach(function (k) {
            labelsMap[k] = PILARES_FIXOS[k].label;
            prioridadesMap[k] = PILARES_FIXOS[k].prioridade;
            esforceMap[k] = PILARES_FIXOS[k].esforco;
        });

        const backlogItens = [];
        document.querySelectorAll('.mesa-pilar-editavel').forEach(function (el) {
            const key = el.getAttribute('data-key');
            const texto = getTexto(el);
            if (!texto) return;

            const subtasksDestePilar = listaSubtasksLocais
                .filter(function (st) { return st.pilar_subtask === key; })
                .map(function (st) { return { subtask_title: st.desc_subtask }; });

            backlogItens.push({
                id_item: 'st_' + idMesa + '_' + key,
                pilar_original: key,
                titulo: 'Fase: ' + (labelsMap[key] || key),
                descricao: texto,
                pontos_esforco_scrum: esforceMap[key] || 5,
                prioridade: prioridadesMap[key] || 'Media',
                status_inicial: 'To Do',
                subtasks: subtasksDestePilar
            });
        });

        return {
            metadados: {
                origem: 'Mesa de Inovação - PanelDX',
                schema_versao: '1.0.0',
                tipo_mesa: 'organizacional',
                gerado_em: new Date().toISOString(),
                id_matu: idMatu,
                id_direc: direcionador ? direcionador.id_direc : null,
                direcionador_estrategico: direcionador,
                bloco_origem: blocoOrigem
            },
            sprint_exportada: {
                id_origem_mesa: idMesa,
                nome_sprint: nomeSprint,
                meta_da_sprint: 'Hipótese: ' + hipotese + ' | Justificativa: ' + justificativa + ' | Impacto: ' + impacto,
                duracao_sugerida_semanas: 2,
                backlog_itens: backlogItens,
                hipotese_estrategica: hipotese,
                id_direc: direcionador ? direcionador.id_direc : null,
                direcionador_estrategico: direcionador
            }
        };
    }

    async function transformarEmSprint() {
        if (!ideiaConsolidada) {
            alert('Lapide a ideia com o Consultor LeAction antes de transformar em sprint.');
            return;
        }

        const payload = montarPayloadUniversal();
        if (!payload.sprint_exportada.backlog_itens.length) {
            alert('Preencha ao menos um pilar de execução antes de enviar ao Kanban.');
            return;
        }

        elBtnSprint.disabled = true;
        elBtnSprint.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Criando sprint…';
        await enviarSprintParaKanban(payload, elBtnSprint);
    }

    function montarPayloadTelemetria(nota) {
        const direcionador = obterDirecionadorSelecionado();
        const idMesa = 'telemetria_' + (nota.id_nota || nota.id);
        const hipotese = nota.hipoteseNegocio || extrairHipoteseTelemetria(nota.conteudo);
        const subtasks = (nota.subtasks && nota.subtasks.length)
            ? nota.subtasks
            : ['Validar conectividade eSIM', 'Correlacionar incidentes de rede', 'Plano de contenção 24h'];
        const nomeSprint = '🚨 ' + (nota.contexto || 'Alerta Telemetria eSIM');

        const labelsMap = {};
        const prioridadesMap = {};
        const esforceMap = {};
        ORDEM_PILARES.forEach(function (k) {
            labelsMap[k] = PILARES_FIXOS[k].label;
            prioridadesMap[k] = PILARES_FIXOS[k].prioridade;
            esforceMap[k] = PILARES_FIXOS[k].esforco;
        });

        const backlogItens = ORDEM_PILARES.map(function (key, idx) {
            const descricao = subtasks[idx] || ('Investigação ' + rotuloPilar(key) + ' — alerta telemetria');
            return {
                id_item: 'st_' + idMesa + '_' + key,
                pilar_original: key,
                titulo: 'Fase: ' + (labelsMap[key] || key),
                descricao: descricao,
                pontos_esforco_scrum: esforceMap[key] || 5,
                prioridade: idx === 0 ? 'Alta' : (prioridadesMap[key] || 'Media'),
                status_inicial: 'To Do',
                subtasks: [{ subtask_title: descricao }]
            };
        });

        return {
            metadados: {
                origem: 'Telemetria Base Mobile - PanelDX',
                schema_versao: '1.0.0',
                tipo_mesa: 'organizacional',
                gerado_em: new Date().toISOString(),
                id_matu: idMatu,
                id_direc: direcionador ? direcionador.id_direc : null,
                direcionador_estrategico: direcionador,
                bloco_origem: null,
                telemetria: {
                    id_nota: nota.id_nota || nota.id,
                    status_anomalia: nota.statusAnomalia,
                    origem: 'telemetria'
                }
            },
            sprint_exportada: {
                id_origem_mesa: idMesa,
                nome_sprint: nomeSprint,
                meta_da_sprint: 'Hipótese (IA Master): ' + hipotese,
                duracao_sugerida_semanas: 1,
                backlog_itens: backlogItens,
                hipotese_estrategica: hipotese,
                id_direc: direcionador ? direcionador.id_direc : null,
                direcionador_estrategico: direcionador
            }
        };
    }

    async function enviarSprintParaKanban(payload, btnRef) {
        const elBtn = btnRef || elBtnSprint;
        const body = {
            id_clie: idClie || 0,
            payload_sprint: payload
        };

        try {
            sessionStorage.setItem('paneldx_mesa_org_sprint', JSON.stringify(body));
        } catch (e) {
            console.warn('sessionStorage indisponível:', e);
        }

        try {
            const response = await fetch('/api/sprints/importar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            const result = await parseJsonResponse(response);

            if (response.ok && (result.success || result.status === 'success')) {
                sessionStorage.removeItem('paneldx_mesa_org_sprint');
                try {
                    sessionStorage.removeItem('paneldx_sprint_prioridade');
                    sessionStorage.removeItem(FILA_KEY);
                } catch (e) { /* ignore */ }
                mostrarToast('Sprint criada! Redirecionando ao Kanban…');
                setTimeout(function () {
                    window.location.href = '/projeto/sprint-atual?origem=mesa-org&criada=1';
                }, 900);
                return true;
            } else {
                throw new Error(result.error || result.message || 'Falha na importação');
            }
        } catch (err) {
            console.error(err);
            alert('Erro ao criar sprint: ' + err.message + '\nO payload foi salvo na sessão — tente abrir o Kanban.');
            if (elBtn) {
                elBtn.disabled = false;
                elBtn.innerHTML = '<i class="fas fa-rocket"></i> Transformar em Sprint';
            }
            return false;
        }
    }

    async function transformarEmSprintTelemetria(nota) {
        if (!nota || nota.status !== 'Pendente') {
            alert('Este alerta já foi processado ou não está disponível.');
            return;
        }

        const direcionador = obterDirecionadorSelecionado();
        if (!direcionador || !direcionador.id_direc) {
            alert('Selecione um direcionador estratégico antes de transformar em sprint.');
            return;
        }

        const btn = document.querySelector('[data-action="sprint-telemetria"][data-id="' + nota.id + '"]');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Enviando…';
        }

        const payload = montarPayloadTelemetria(nota);
        const ok = await enviarSprintParaKanban(payload, btn);

        if (ok && (nota.id_nota || nota.id)) {
            await incubarNotasApi([nota.id_nota || nota.id]);
            await consumirBacklogEsim({
                idItemBacklog: nota.idItemBacklog,
                idNota: nota.id_nota || nota.id
            });
            nota.status = 'Incubada';
            salvarNotasLocalStorage();
            renderizarMural();
        }
    }

    function exportarJson() {
        const formato = document.getElementById('mesa-combo-formato').value;
        let nomeArquivo = document.getElementById('mesa-txt-nome-arquivo').value.trim() || 'sprint_organizacional';
        if (!nomeArquivo.toLowerCase().endsWith('.json')) nomeArquivo += '.json';

        let payload;
        if (formato === 'Universal') {
            payload = montarPayloadUniversal();
        } else {
            alert('Exportação ' + formato + ' disponível em breve. Use Universal para o Kanban PanelDX.');
            return;
        }

        const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(payload, null, 2));
        const a = document.createElement('a');
        a.href = dataStr;
        a.download = nomeArquivo;
        document.body.appendChild(a);
        a.click();
        a.remove();
        mostrarToast('JSON exportado com sucesso.');
    }

    async function chamarGerarPreview(payload) {
        const body = Object.assign({ tipo_mesa: 'organizacional' }, payload || {});
        const response = await fetch('/api/mesa-inovacao/gerar-preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify(body)
        });
        const resData = await parseJsonResponse(response);
        if (!response.ok) {
            throw new Error(resData.message || ('HTTP ' + response.status));
        }
        return resData;
    }

    async function lapidarComConsultor() {
        const selecionadas = getNotasSelecionadas();
        if (selecionadas.length === 0) {
            alert('Selecione post-its pendentes no mural para lapidar.');
            return;
        }

        const direcionador = obterDirecionadorSelecionado();
        if (!direcionador || !direcionador.id_direc) {
            alert('Selecione um direcionador estratégico antes de lapidar.');
            return;
        }

        const btn = document.getElementById('mesa-btn-incubar');
        btn.disabled = true;
        resetPainelConsultor('O Consultor LeAction está consolidando a iniciativa organizacional…');

        const notasTexto = selecionadas.map(function (n) { return n.conteudo; });
        const idsNotas = selecionadas
            .map(function (n) { return parseInt(n.id_nota || n.id, 10); })
            .filter(function (n) { return !isNaN(n); });

        const payload = {
            tipo_mesa: 'organizacional',
            id_direc: direcionador.id_direc,
            direcionador_estrategico: direcionador,
            notas_texto: notasTexto,
            ids_notas: idsNotas,
            id_matu: idMatu,
            gap_context: gapAtivo || (selecionadas[0] && selecionadas[0].origemGap) || null,
            gaps_maturidade: topGaps
        };

        try {
            const resData = await chamarGerarPreview(payload);
            if (resData.status === 'success' && resData.rascunho) {
                await exibirResultadoConsultor(resData.rascunho, selecionadas);
                if (resData.fallback) {
                    mostrarToast(resData.message || 'Rascunho local gerado (Consultor LeAction remoto indisponível).', '#d97706');
                }
            } else {
                throw new Error(resData.message || 'Não foi possível gerar a inovação agora.');
            }
        } catch (err) {
            console.error(err);
            alert(err.message || 'Falha de comunicação com o Consultor LeAction.');
            elResult.classList.remove('is-visible');
            elEmpty.style.display = 'flex';
        } finally {
            btn.disabled = false;
        }
    }

    async function vincularGap(item) {
        document.querySelectorAll('.mesa-gap-item').forEach(function (el) { el.classList.remove('is-active'); });
        item.classList.add('is-active');

        const idx = parseInt(item.dataset.gapIndex, 10);
        const gap = topGaps[idx] || {
            nome: item.dataset.blocoNome,
            desc: item.dataset.desc || '',
            dominio: item.dataset.dominio,
            gap: parseFloat(item.dataset.gap) || 0,
            id_bloc: item.dataset.idBloc || null
        };

        gapAtivo = {
            nome: gap.nome,
            desc: gap.desc || '',
            dominio: gap.dominio || '',
            gap: parseFloat(gap.gap) || 0,
            id_bloc: gap.id_bloc || null
        };

        const texto = 'Lacuna em "' + gapAtivo.nome + '" (' + gapAtivo.dominio + ', Δ ' + gapAtivo.gap + '): ' + gapAtivo.desc;
        await criarNota(texto, 'Gap · ' + gapAtivo.nome, gapAtivo);
        mostrarToast('Post-it criado a partir do gap prioritário.');
    }

    function initEventos() {
        document.getElementById('mesa-gap-list').addEventListener('click', function (e) {
            const item = e.target.closest('.mesa-gap-item');
            if (item) vincularGap(item);
        });

        document.getElementById('mesa-btn-add-nota').addEventListener('click', async function () {
            const txt = document.getElementById('mesa-txt-nota');
            const val = txt.value.trim();
            if (!val) return alert('Escreva algo no post-it antes de adicionar.');
            await criarNota(val, gapAtivo ? ('Gap · ' + gapAtivo.nome) : 'Ideação livre', gapAtivo);
            txt.value = '';
        });

        elMural.addEventListener('click', function (e) {
            if (e.target.closest('[data-action="sprint-telemetria"]')) {
                e.stopPropagation();
                var btn = e.target.closest('[data-action="sprint-telemetria"]');
                var nota = notasLocais.find(function (n) { return n.id === btn.dataset.id; });
                if (nota) transformarEmSprintTelemetria(nota);
                return;
            }
            if (e.target.closest('[data-action="del"]')) {
                const id = e.target.closest('[data-action="del"]').dataset.id;
                removerNota(id);
                return;
            }
            if (e.target.closest('.post-it-telemetria__footer')) return;
            if (e.target.type === 'checkbox') return;
            const card = e.target.closest('[data-nota-id]');
            if (!card) return;
            const chk = card.querySelector('.mesa-chk-nota');
            if (chk && !chk.disabled) chk.checked = !chk.checked;
        });

        document.getElementById('mesa-btn-add-subtask').addEventListener('click', function () {
            if (listaSubtasksLocais.length >= 4) return alert('Máximo de 4 subtasks.');
            const txt = getTexto(document.getElementById('mesa-txt-nova-subtask'));
            if (!txt) return alert('Descreva a subtask.');
            const pilar = document.querySelector('input[name="mesa-rd-pilar"]:checked').value;
            listaSubtasksLocais.push({ pilar_subtask: pilar, desc_subtask: txt });
            document.getElementById('mesa-txt-nova-subtask').textContent = '';
            renderizarSubtasks();
        });

        document.getElementById('mesa-lista-subtasks').addEventListener('click', function (e) {
            const btn = e.target.closest('[data-rm-subtask]');
            if (!btn) return;
            listaSubtasksLocais.splice(parseInt(btn.dataset.rmSubtask, 10), 1);
            renderizarSubtasks();
        });

        document.getElementById('mesa-btn-incubar').addEventListener('click', lapidarComConsultor);
        document.getElementById('mesa-btn-transformar-sprint').addEventListener('click', transformarEmSprint);
        document.getElementById('mesa-btn-exportar-json').addEventListener('click', exportarJson);

        document.getElementById('btn-ajuda-consultor').addEventListener('click', function () {
            document.getElementById('mesa-modal-ajuda').classList.add('is-open');
        });
        document.getElementById('mesa-btn-fechar-ajuda').addEventListener('click', function () {
            document.getElementById('mesa-modal-ajuda').classList.remove('is-open');
        });
        document.getElementById('mesa-modal-ajuda').addEventListener('click', function (e) {
            if (e.target === this) this.classList.remove('is-open');
        });

        var btnEsimRefresh = document.getElementById('mesa-esim-refresh');
        if (btnEsimRefresh) {
            btnEsimRefresh.addEventListener('click', async function () {
                btnEsimRefresh.disabled = true;
                btnEsimRefresh.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                await carregarBacklogEsim();
                btnEsimRefresh.disabled = false;
                btnEsimRefresh.innerHTML = '<i class="fas fa-sync-alt"></i>';
                mostrarToast('Backlog eSIM atualizado.');
            });
        }

        if (elEsimList) {
            elEsimList.addEventListener('click', function (e) {
                var item = e.target.closest('.mesa-esim-item');
                if (!item) return;
                document.querySelectorAll('.mesa-esim-item').forEach(function (el) { el.classList.remove('is-active'); });
                item.classList.add('is-active');
                var idNota = item.dataset.idNota;
                if (idNota) destacarNotaNoMural(idNota);
            });
        }
    }

    async function criarPostitFromBloco(bloco) {
        if (!bloco || !bloco.nome) return false;
        if (notaJaExisteParaBloco(bloco)) {
            removerBlocoDaFila(bloco);
            return false;
        }

        gapAtivo = {
            nome: bloco.nome,
            desc: bloco.desc || '',
            dominio: bloco.dominio || '',
            gap: parseFloat(bloco.gap) || 0,
            id_bloc: bloco.id_bloc || null,
            id_doma: bloco.id_doma || null
        };
        var prefixoGap = gapAtivo.gap ? ' (Δ ' + gapAtivo.gap + ')' : '';
        var texto = gapAtivo.desc
            ? 'Lacuna em "' + gapAtivo.nome + '"' + prefixoGap + ': ' + gapAtivo.desc
            : 'Prioridade do Relatório de Contexto: ' + gapAtivo.nome;
        await criarNota(texto, 'Relatório · ' + gapAtivo.nome, gapAtivo);
        removerBlocoDaFila(bloco);
        mostrarToast('Post-it criado: ' + gapAtivo.nome);
        return true;
    }

    async function processarFilaRelatorio() {
        const fila = lerFilaBlocos();
        if (!fila.length) return;

        let criados = 0;
        for (let i = 0; i < fila.length; i++) {
            const bloco = fila[i];
            if (notaJaExisteParaBloco(bloco)) {
                removerBlocoDaFila(bloco);
                continue;
            }

            const itemGap = Array.from(document.querySelectorAll('.mesa-gap-item')).find(function (el) {
                return normalizarNome(el.dataset.blocoNome) === normalizarNome(bloco.nome);
            });
            if (itemGap && criados === 0) {
                await vincularGap(itemGap);
            } else {
                await criarPostitFromBloco(bloco);
            }
            criados++;
        }

        if (criados > 0) {
            mostrarToast(criados + ' bloco(s) do relatório adicionados ao mural.');
        }
    }

    async function iniciar() {
        initEventos();
        await Promise.all([carregarNotas(), carregarBacklogEsim()]);
        renderizarMural();
        await processarFilaRelatorio();
        renderizarMural();
    }

    iniciar();
})();
