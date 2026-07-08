/**
 * IA Master — assessment conversacional gamificado.
 */
(function () {
    const LOCAL_OPENING = {
        reply: 'Olá! Sou o Consultor LeAction Master, seu consultor estratégico nesta jornada. ' +
            'Vamos mapear sua escola com precisão, em poucas rodadas inteligentes — ' +
            'cada resposta sua alimenta dezenas de indicadores automaticamente. ' +
            'Para começarmos: qual é o porte da sua instituição (número aproximado de alunos) ' +
            'e qual a principal dor operacional hoje?',
        microcopy_badge: 'Partida iniciada',
    };

    function boot() {
        const page = document.getElementById('evaluation-page');
        const form = document.getElementById('evaluationForm');
        const chatRoot = document.getElementById('ia-master-chat');
        if (!page || !chatRoot) return;

        const chatLocked = chatRoot.dataset.chatLocked === 'true';

        const maturityId = form?.dataset?.maturityId || chatRoot.dataset.maturityId;
        const isMini = (form?.getAttribute('data-restricted') === 'true') ||
            chatRoot.dataset.isMini === 'true';
        if (!maturityId || maturityId === 'undefined') {
            console.error('[IA Master] id_matu ausente');
            return;
        }

        const messagesEl = document.getElementById('ia-master-messages');
        const inputEl = document.getElementById('ia-master-input');
        const sendBtn = document.getElementById('ia-master-send');
        const badgeEl = document.getElementById('ia-master-badge');
        const deductionPanel = document.getElementById('ia-master-deduction');
        const deductionHeadline = document.getElementById('ia-master-deduction-headline');
        const deductionCount = document.getElementById('ia-master-deduction-count');
        const btnConfirm = document.getElementById('ia-master-confirm');
        const btnReject = document.getElementById('ia-master-reject');
        const btnFinalize = document.getElementById('ia-master-finalize');
        const modeToggle = document.getElementById('assessment-mode-toggle');
        const classicPanel = document.getElementById('evaluation-classic-panel');
        const coverageHint = document.getElementById('ia-master-coverage-hint');

        const API_TURN = '/api/assessment/ia-master/turn';
        const API_COVERAGE = `/api/assessment/ia-master/coverage/${maturityId}`;

        let history = [];
        let pendingDeduction = null;
        let isLoading = false;
        let hasShownOpening = false;

        function scrollMessages() {
            if (messagesEl) messagesEl.scrollTop = messagesEl.scrollHeight;
        }

        function appendMessage(role, text, badge) {
            if (!messagesEl || !text) return;
            const wrap = document.createElement('div');
            wrap.className = `ia-master-msg ia-master-msg--${role}`;
            const badgeHtml = badge && role === 'assistant'
                ? `<span class="ia-master-msg__badge">${badge}</span>` : '';
            wrap.innerHTML = `${badgeHtml}<div class="ia-master-msg__bubble">${text.replace(/\n/g, '<br>')}</div>`;
            messagesEl.appendChild(wrap);
            scrollMessages();
        }

        function setLoading(on) {
            isLoading = on;
            if (sendBtn) sendBtn.disabled = on;
            if (inputEl) inputEl.disabled = on;
            if (btnConfirm) btnConfirm.disabled = on;
            if (badgeEl && on) badgeEl.textContent = 'Pensando…';
        }

        function updatePresurveyFinalizeUI(state) {
            if (!isMini || !btnFinalize) return;
            const pre = state || window.panelDxAssessment?.getPresurveyState?.();
            if (!pre) return;
            btnFinalize.disabled = !pre.complete;
            btnFinalize.title = pre.complete
                ? 'Gerar relatório de diagnóstico preliminar'
                : `Complete ${pre.total - pre.answered} questão(ões) na 1ª aba (modo detalhado)`;
            btnFinalize.innerHTML =
                '<i class="fas fa-magic"></i> Gerar diagnóstico preliminar';
        }

        function updateCoverageUI(coverage) {
            if (!coverage) return;
            if (coverageHint) {
                if (isMini) {
                    const pre = window.panelDxAssessment?.getPresurveyState?.();
                    if (pre) {
                        coverageHint.textContent =
                            `${pre.answered} de ${pre.total} questões da 1ª aba respondidas`;
                    } else {
                        coverageHint.textContent =
                            `${coverage.answered} de ${coverage.total} questões mapeadas (${coverage.percent}%)`;
                    }
                } else {
                    coverageHint.textContent =
                        `${coverage.answered} de ${coverage.total} indicadores mapeados (${coverage.percent}%)`;
                }
            }
            if (btnFinalize && !isMini) {
                btnFinalize.disabled = !coverage.can_finalize;
            }
            if (isMini) updatePresurveyFinalizeUI();
            document.dispatchEvent(new CustomEvent('assessment-coverage-changed', { detail: coverage }));
        }

        function showDeductionPanel(pending) {
            if (!deductionPanel) return;
            if (!pending || !pending.answers || !pending.answers.length) {
                deductionPanel.style.display = 'none';
                pendingDeduction = null;
                return;
            }
            pendingDeduction = pending;
            deductionPanel.style.display = 'block';
            if (deductionHeadline) {
                deductionHeadline.textContent = pending.headline || 'Bloco deduzido pelo Consultor LeAction Master';
            }
            if (deductionCount) {
                deductionCount.textContent = `${pending.answers.length} indicadores neste bloco`;
            }
        }

        function showOpeningLocal() {
            if (hasShownOpening) return;
            hasShownOpening = true;
            appendMessage('assistant', LOCAL_OPENING.reply, LOCAL_OPENING.microcopy_badge);
            history.push({ role: 'assistant', content: LOCAL_OPENING.reply });
            if (badgeEl) badgeEl.textContent = LOCAL_OPENING.microcopy_badge;
        }

        async function apiTurn(payload) {
            const res = await fetch(API_TURN, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    id_matu: parseInt(maturityId, 10),
                    is_mini: isMini,
                    ...payload,
                }),
            });
            let data;
            try {
                data = await res.json();
            } catch (e) {
                throw new Error('Resposta inválida do servidor. Verifique se o backend Flask está ativo.');
            }
            if (!res.ok || data.status === 'error') {
                throw new Error(data.message || `Erro ${res.status} na conversa com o Consultor LeAction Master`);
            }
            return data;
        }

        async function loadCoverage() {
            try {
                const res = await fetch(`${API_COVERAGE}?mini=${isMini}`);
                if (!res.ok) return;
                const data = await res.json();
                if (data.coverage) updateCoverageUI(data.coverage);
            } catch (e) {
                console.warn('[IA Master] coverage:', e);
            }
        }

        async function handleTurn(options = {}) {
            setLoading(true);
            try {
                const data = await apiTurn(options);
                if (data.reply) {
                    if (!hasShownOpening || options.action === 'start') {
                        if (messagesEl) messagesEl.innerHTML = '';
                        history = [];
                        hasShownOpening = true;
                    }
                    appendMessage('assistant', data.reply, data.microcopy_badge);
                    history.push({ role: 'assistant', content: data.reply });
                }
                if (badgeEl && data.microcopy_badge) badgeEl.textContent = data.microcopy_badge;
                updateCoverageUI(data.coverage);
                if (data.requires_confirmation && data.pending_deduction) {
                    showDeductionPanel(data.pending_deduction);
                } else {
                    showDeductionPanel(null);
                }
                return data;
            } catch (err) {
                console.error('[IA Master]', err);
                if (!hasShownOpening) showOpeningLocal();
                if (badgeEl) badgeEl.textContent = 'Modo local';
                appendMessage(
                    'assistant',
                    'Estou operando em modo local — o Consultor LeAction pode estar reiniciando. ' +
                    'Pode responder normalmente; suas respostas serão salvas assim que a conexão voltar.',
                    'Conexão'
                );
                throw err;
            } finally {
                setLoading(false);
            }
        }

        async function sendUserMessage() {
            const text = (inputEl?.value || '').trim();
            if (!text || isLoading) return;
            appendMessage('user', text);
            history.push({ role: 'user', content: text });
            inputEl.value = '';
            try {
                await handleTurn({ action: 'message', message: text, history });
            } catch (e) {
                /* opening local já exibido */
            }
        }

        async function confirmDeduction() {
            if (!pendingDeduction || isLoading) return;
            appendMessage('user', 'Acertou! Pode registrar esse bloco.');
            history.push({ role: 'user', content: 'Confirmo o bloco deduzido.' });
            try {
                await handleTurn({
                    action: 'confirm_deduction',
                    message: 'Confirmo — acertou em cheio.',
                    history,
                    pending_answers: pendingDeduction.answers,
                });
            } catch (e) { /* ignore */ }
        }

        function rejectDeduction() {
            if (!pendingDeduction || isLoading) return;
            showDeductionPanel(null);
            appendMessage(
                'assistant',
                'Sem problemas — me conte em uma frase como sua realidade difere desse bloco, que eu recalibro.',
                'Ajuste fino'
            );
            if (inputEl) {
                inputEl.placeholder = 'Descreva como sua realidade difere…';
                inputEl.focus();
            }
        }

        async function startConversation() {
            showOpeningLocal();
            loadCoverage();
            try {
                await handleTurn({ action: 'start', message: '', history: [] });
            } catch (e) {
                /* fallback local já visível */
            }
        }

        function setMode(mode) {
            if (chatLocked && mode === 'chat') return;
            const conversational = mode === 'chat';
            chatRoot.style.display = conversational ? 'flex' : 'none';
            if (classicPanel) classicPanel.style.display = conversational ? 'none' : 'block';
            const lockedPanel = document.getElementById('ia-master-locked-panel');
            if (lockedPanel) lockedPanel.classList.toggle('is-visible', chatLocked && !conversational);
            if (modeToggle) {
                modeToggle.querySelectorAll('[data-mode]').forEach(btn => {
                    btn.classList.toggle('active', btn.dataset.mode === mode);
                });
            }
        }

        if (sendBtn) sendBtn.addEventListener('click', sendUserMessage);
        if (inputEl) {
            inputEl.addEventListener('keydown', e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendUserMessage();
                }
            });
        }
        if (btnConfirm) btnConfirm.addEventListener('click', confirmDeduction);
        if (btnReject) btnReject.addEventListener('click', rejectDeduction);
        if (btnFinalize) {
            btnFinalize.addEventListener('click', () => {
                if (isMini) {
                    if (typeof finalizarEGerarDiagnosticoInicial === 'function') {
                        finalizarEGerarDiagnosticoInicial(maturityId, btnFinalize);
                    }
                    return;
                }
                const classicBtn = document.querySelector('.future-submit-btn') ||
                    document.querySelector('.btn-conversion');
                if (classicBtn) {
                    setMode('classic');
                    classicBtn.scrollIntoView({ behavior: 'smooth' });
                }
            });
        }
        document.addEventListener('assessment-presurvey-changed', e => {
            updatePresurveyFinalizeUI(e.detail);
            if (isMini && coverageHint && e.detail) {
                coverageHint.textContent =
                    `${e.detail.answered} de ${e.detail.total} questões da 1ª aba respondidas`;
            }
        });
        if (modeToggle) {
            modeToggle.addEventListener('click', e => {
                const btn = e.target.closest('[data-mode]');
                if (!btn || btn.disabled || btn.classList.contains('is-locked')) return;
                if (btn.dataset.mode === 'chat' && chatLocked) return;
                if (btn) setMode(btn.dataset.mode);
            });
        }

        if (chatLocked) {
            setMode('classic');
        } else {
            setMode('chat');
            startConversation();
            window.setTimeout(() => updatePresurveyFinalizeUI(), 800);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
