/**
 * Monitoramento da Gênese IA — barra de progresso + diretrizes contextuais.
 * Poll em /api/client/genese-status até plano_pronto (CONCLUIDO + sprints).
 */
(function () {
    const DIRETRIZES_EXECUTIVAS = [
        'Seletividade estratégica: não criar ações para todos os gaps.',
        'Cada sprint deve citar gap real, insight da Bússola e contexto da unidade.',
        'Roadmap estratégico: no máximo 10 blocos mais críticos.',
        'Plano tático: exatamente 3 sprints ligadas ao problema declarado.',
        'Usar somente blocos existentes no catálogo — sem IDs inventados.',
        'Relatório de inteligência cobrindo os 9 domínios com densidade.',
        'Personalização estrita: correlacionar gaps com mercado e etnografia local.'
    ];

    const STATUS_LABELS = {
        PENDENTE: 'Na fila — preparando o Consultor LeAction...',
        PROCESSANDO: 'Consultor LeAction Master analisando gaps, Bússola e contexto institucional...',
        CONCLUIDO: 'Plano estratégico gerado com sucesso!'
    };

    let pollTimer = null;
    let progressTimer = null;
    let startTime = null;

    function getOverlayEls() {
        return {
            overlay: document.getElementById('progress-overlay'),
            bar: document.getElementById('myBar'),
            percent: document.getElementById('percent-text'),
            status: document.getElementById('status-ia-text'),
            subtitle: document.getElementById('genese-subtitle'),
            diretrizesBox: document.getElementById('genese-diretrizes-list')
        };
    }

    function buildDiretrizesFromLead(lead) {
        if (!lead || typeof lead !== 'object') return [];
        const items = [];
        const tipo = lead.tipo_ensino || '';
        const segmentos = {
            'K12': 'Educação Básica (K12) — BNCC, PNED e segurança digital.',
            'Superior': 'Ensino Superior — LMS, retenção e empregabilidade.',
            'Tecnico': 'Ensino Técnico — laboratórios virtuais e simulações.',
            'Idiomas/Cursos Livres': 'Idiomas/Cursos Livres — UX e conversão digital.',
            'Educação Corporativa': 'Educação Corporativa — microlearning e SKAs.'
        };
        if (segmentos[tipo]) items.push('Segmento: ' + segmentos[tipo]);
        if (lead.localizacao_sede) items.push('Localização: ' + lead.localizacao_sede);
        if (lead.bairro_clie || lead.cidade_clie) {
            items.push('Bairro/Cidade: ' + (lead.bairro_clie || '—') + ' / ' + (lead.cidade_clie || '—'));
        }
        if (lead.qtd_alunos) items.push('Porte: ' + lead.qtd_alunos + ' alunos.');
        return items;
    }

    function renderDiretrizes(contexto, executivas) {
        const box = document.getElementById('genese-diretrizes-list');
        if (!box) return;

        const ctxItems = Array.isArray(contexto) ? contexto : [];
        const execItems = Array.isArray(executivas) ? executivas : DIRETRIZES_EXECUTIVAS;

        let html = '<div class="genese-diretrizes__section"><h4>Contexto da sua instituição</h4><ul>';
        if (ctxItems.length === 0) {
            html += '<li>Perfil institucional carregado do questionário e do contexto validado.</li>';
        } else {
            ctxItems.forEach(function (item) {
                html += '<li>' + escapeHtml(item) + '</li>';
            });
        }
        html += '</ul></div>';
        html += '<div class="genese-diretrizes__section"><h4>Diretrizes de priorização (Consultor LeAction Master)</h4><ul>';
        execItems.forEach(function (item) {
            html += '<li>' + escapeHtml(item) + '</li>';
        });
        html += '</ul></div>';
        box.innerHTML = html;
    }

    function escapeHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function setProgress(pct) {
        const els = getOverlayEls();
        const v = Math.min(100, Math.max(0, Math.round(pct)));
        if (els.bar) els.bar.style.width = v + '%';
        if (els.percent) els.percent.textContent = v + '%';
    }

    function stopTimers() {
        if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
        if (progressTimer) { clearInterval(progressTimer); progressTimer = null; }
    }

    function showOverlay() {
        const els = getOverlayEls();
        if (els.overlay) els.overlay.style.display = 'flex';
    }

    function hideOverlay() {
        const els = getOverlayEls();
        if (els.overlay) els.overlay.style.display = 'none';
        stopTimers();
    }

    function updateStatusLabel(statusIa, faseAtual) {
        const els = getOverlayEls();
        const key = (statusIa || '').toUpperCase();
        let msg = STATUS_LABELS[key] || 'Processando seu plano de transformação...';
        if (faseAtual && key !== 'CONCLUIDO') {
            msg += ' (' + faseAtual + ')';
        }
        if (els.status) els.status.textContent = msg;
    }

    function startProgressAnimation() {
        startTime = Date.now();
        if (progressTimer) clearInterval(progressTimer);
        progressTimer = setInterval(function () {
            const elapsed = (Date.now() - startTime) / 1000;
            // Avanço suave até ~88% enquanto aguarda o backend (sem tempo fixo de 2 min)
            const target = Math.min(88, 12 + elapsed * 1.8);
            setProgress(target);
        }, 400);
    }

    async function pollStatus(idMatu) {
        try {
            const res = await fetch('/api/client/genese-status/' + idMatu);
            if (!res.ok) return null;
            return await res.json();
        } catch (e) {
            console.warn('[Gênese] Poll falhou:', e);
            return null;
        }
    }

    async function iniciarMonitoramentoGenese(idMatu, diretrizesContexto) {
        if (!idMatu) {
            alert('ID de maturidade não encontrado.');
            return;
        }

        stopTimers();
        renderDiretrizes(
            diretrizesContexto || window.geneseDiretrizesContexto || buildDiretrizesFromLead(window._leadData)
        );
        showOverlay();
        setProgress(8);
        updateStatusLabel('PENDENTE', '');

        const els = getOverlayEls();
        if (els.subtitle) {
            els.subtitle.textContent = 'Aguardando conclusão real do processamento. As diretrizes ao lado orientam o Consultor LeAction Master.';
        }

        startProgressAnimation();

        const check = async function () {
            const data = await pollStatus(idMatu);
            if (!data) return;

            updateStatusLabel(data.status_ia, data.fase_atual);

            if (data.erro) {
                stopTimers();
                hideOverlay();
                alert('O Consultor LeAction encontrou um erro ao gerar o plano. Tente novamente ou contate o suporte.');
                window.location.reload();
                return;
            }

            if (data.plano_pronto) {
                stopTimers();
                setProgress(100);
                updateStatusLabel('CONCLUIDO', '');
                if (els.subtitle) els.subtitle.textContent = 'Redirecionando para o Plano Geral...';
                setTimeout(function () {
                    window.location.href = '/projeto';
                }, 900);
            }
        };

        await check();
        pollTimer = setInterval(check, 2500);
    }

    async function executarGeneseEstrategica() {
        if (!confirm('Deseja iniciar a Gênese com o Consultor LeAction e gerar seu Plano de Transformação Digital?')) return;

        const ponte = document.getElementById('dados-index-ponte');
        const idMatu = ponte ? ponte.getAttribute('data-id-matu') : (window._leadData && window._leadData.id_matu) || '';

        try {
            const res = await fetch('/client/generate-ai-plan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id_matu: idMatu })
            });
            const data = await res.json().catch(function () { return {}; });
            if (!res.ok || !data.success) {
                throw new Error(data.error || 'Falha ao iniciar a geração do plano.');
            }
            iniciarMonitoramentoGenese(
                idMatu,
                window.geneseDiretrizesContexto || buildDiretrizesFromLead(window._leadData)
            );
        } catch (err) {
            console.error('[Gênese]', err);
            alert('Erro ao iniciar: ' + err.message);
        }
    }

    window.iniciarMonitoramentoGenese = iniciarMonitoramentoGenese;
    window.executarGeneseEstrategica = executarGeneseEstrategica;
})();
