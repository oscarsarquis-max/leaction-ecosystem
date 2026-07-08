document.addEventListener('DOMContentLoaded', async () => {
    const questionsContainer = document.getElementById('questions-container');
    const form = document.getElementById('evaluationForm');
    const idMatuInput = document.getElementById('id_matu');
    const idMatu = idMatuInput ? idMatuInput.value : (form ? form.getAttribute('data-maturity-id') : null);

    let questionsData = [];

    console.log("🚀 [INÍCIO] Script carregado. ID Maturidade:", idMatu);

    // --- 1. FUNÇÃO DE BUSCA ---
    async function fetchQuestions() {
        console.log("🌐 [FETCH] Chamando API /api/questions_by_dimension...");
        try {
            const response = await fetch('/api/questions_by_dimension');
            if (!response.ok) throw new Error('Falha ao carregar as questões.');
            const data = await response.json();
            console.log("✅ [FETCH] Dados recebidos:", data);
            return data;
        } catch (error) {
            console.error('❌ [FETCH] Erro:', error);
            if (questionsContainer) {
                questionsContainer.innerHTML = `<div class="p-4 bg-red-100 text-red-700">Erro ao carregar questões.</div>`;
            }
            return null;
        }
    }

    // --- 2. FUNÇÃO DE RENDERIZAÇÃO ---
    function renderForm(data) {
        console.log("🎨 [RENDER] Iniciando renderização...");

        // Alvo: Busca 'questions-list' para não apagar o resto do form
        const targetContainer = document.getElementById('questions-list') || questionsContainer;

        if (!targetContainer) {
            console.error("❌ [RENDER] Container não encontrado!");
            return;
        }

        targetContainer.innerHTML = '';

        if (!data || data.length === 0) {
            console.warn("⚠️ [RENDER] Nenhum dado recebido.");
            return;
        }

        data.forEach(dimension => {
            console.log(`🔹 Renderizando Dimensão: ${dimension.name_dime}`);
            const dimensionSection = document.createElement('div');
            dimensionSection.className = 'form-section mb-10 p-6 bg-white rounded-lg shadow-md border-t-4 border-indigo-500';

            dimensionSection.innerHTML = `<h3 class="section-title text-xl font-bold mb-4 text-indigo-800">${dimension.name_dime}</h3>`;

            dimension.dominios.forEach(dominio => {
                const domainSection = document.createElement('div');
                domainSection.className = 'mb-6 ml-2 border-l-2 border-gray-100 pl-4';
                domainSection.innerHTML = `<h4 class="font-semibold text-lg mb-4 text-gray-700">${dominio.name_doma}</h4>`;

                dominio.questoes.forEach(questao => {
                    // LOG PARA VER SE AS RUBRICAS ESTÃO CHEGANDO
                    console.log(`   ❓ Questão ${questao.id_ques}: Rubricas encontradas ->`, questao.rubricas ? questao.rubricas.length : 0);

                    const questionGroup = document.createElement('div');
                    questionGroup.className = 'question-group p-5 bg-gray-50 rounded-xl mb-6 hover:shadow-sm transition-all border border-transparent hover:border-indigo-100';

                    let optionsHTML = '';

                    // Lógica de Rubricas
                    if (questao.rubricas && questao.rubricas.length > 0) {
                        optionsHTML = questao.rubricas.map(rubrica => `
                            <label class="flex items-start p-3 mb-2 bg-white border border-gray-200 rounded-lg cursor-pointer hover:border-indigo-400 hover:bg-indigo-50 transition-all group">
                                <input type="radio" name="question_${questao.id_ques}" value="${rubrica.grad_rubr}" required class="mt-1 form-radio text-indigo-600 h-4 w-4">
                                <div class="ml-3">
                                    <span class="block text-sm font-bold text-gray-800 group-hover:text-indigo-700">
                                        ${rubrica.label_rubr || 'Nível ' + rubrica.grad_rubr}
                                    </span>
                                    <span class="block text-xs text-gray-600 leading-relaxed">
                                        ${rubrica.desc_rubr}
                                    </span>
                                </div>
                            </label>
                        `).join('');
                    } else {
                        optionsHTML = `<div class="flex space-x-4">` +
                            [1, 2, 3, 4, 5].map(v => `
                                <label class="flex flex-col items-center p-2 border rounded-lg cursor-pointer hover:bg-gray-100 w-12">
                                    <input type="radio" name="question_${questao.id_ques}" value="${v}" required class="form-radio text-indigo-600">
                                    <span class="text-sm mt-1">${v}</span>
                                </label>
                            `).join('') + `</div>`;
                    }

                    questionGroup.innerHTML = `
                        <p class="mb-4 text-gray-800 font-bold leading-snug">${questao.desc_ques}</p>
                        <div class="options-container">
                            ${optionsHTML}
                            <label class="flex items-center p-3 mt-3 bg-gray-100 border border-dashed border-gray-300 rounded-lg cursor-pointer opacity-70 hover:opacity-100">
                                <input type="radio" name="question_${questao.id_ques}" value="0" required class="form-radio text-gray-400">
                                <span class="ml-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Não se aplica / Não sei informar</span>
                            </label>
                        </div>
                    `;
                    domainSection.appendChild(questionGroup);
                });
                dimensionSection.appendChild(domainSection);
            });
            targetContainer.appendChild(dimensionSection);
        });
        console.log("🏁 [RENDER] Finalizado com sucesso.");
    }

    // --- 3. EXECUÇÃO ---
    questionsData = await fetchQuestions();
    if (questionsData) {
        renderForm(questionsData);
    }

    // --- 4. ENVIO ---
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            console.log("📤 [SUBMIT] Enviando respostas...");

            const formData = new FormData(form);
            const answers = [];

            const allQuestions = questionsData.flatMap(d => d.dominios.flatMap(dom => dom.questoes.map(q => ({
                id_ques: q.id_ques,
                id_dime: d.id_dime,
                id_doma: dom.id_doma
            }))));

            for (const [name, value] of formData.entries()) {
                if (name.startsWith('question_')) {
                    const idQues = parseInt(name.replace('question_', ''));
                    const relatedQuestion = allQuestions.find(q => q.id_ques === idQues);
                    if (relatedQuestion) {
                        answers.push({
                            ID_MATU: parseInt(idMatu),
                            ID_QUES: relatedQuestion.id_ques,
                            ID_DIME: relatedQuestion.id_dime,
                            ID_DOMA: relatedQuestion.id_doma,
                            GRAD_QUES: parseFloat(value),
                        });
                    }
                }
            }

            try {
                const response = await fetch('/api/ctdi_surv', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(answers)
                });

                if (response.ok) {
                    alert('Avaliação enviada com sucesso!');
                } else {
                    const error = await response.json();
                    alert(`Erro ao enviar: ${error.message}`);
                }
            } catch (error) {
                console.error('Erro:', error);
                alert('Erro de conexão.');
            }
        });
    } else {
        console.error("❌ [ERROR] Formulário #evaluationForm não encontrado.");
    }
});
