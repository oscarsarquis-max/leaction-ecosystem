/**

 * Coach Guide — mensagens contextuais do Consultor LeAction (agentes IA)

 */

(function () {

    'use strict';



    var SCRIPTS = {

        estrategia: [

            'Os 5 pilares MudaEdu já estão prontos — vincule objetivos de TD e KRs para alimentar o Panorama Executivo.',

            'Cada KR criado aqui pode ser ligado às atividades das sprints. Quanto mais KRs, mais XP estratégico.',

            'Use os comentários do gestor para registrar decisões de conselho e desbloquear o badge Malha Completa.',

            'Você está no Cockpit Estratégico — seu nível sobe conforme objetivos e KRs evoluem.',

            'Priorize um pilar por vez: objetivo TD → KR → execução na sprint.',

        ],

        assessment: [

            'Sou o Consultor LeAction — minha rede de agentes de IA analisa cada resposta para montar seu diagnóstico.',

            'Responda com honestidade: o relatório usa rubricas de maturidade e horizonte de adoção.',

            'Ao concluir, você desbloqueia insights e o caminho para o planejamento estratégico.',

            'Cada bloco respondido aproxima você do relatório completo de maturidade digital.',

            'Salve o progresso — você pode retomar o assessment quando quiser.',

        ],

        presurvey: [

            'Este é o panorama preliminar — amostra de 28 indicadores. O plano completo expande para 162 questões.',

            'Identifique gaps e fortalezas antes de abrir o planejamento estratégico.',

            'Revise os domínios com menor score — eles indicam onde focar primeiro na estratégia.',

        ],

        execucao: [

            'Modo execução: cada atividade concluída pode refletir no progresso do KR vinculado.',

            'O mapa de calor do Panorama mede volume de atividades OKR por área escolar e sprint.',

            'Priorize entregas da sprint atual — o heatmap e os KPIs reagem às atividades OKR criadas.',

        ],

        consultor: [

            'Conte seu desafio — vou orquestrar os agentes de IA para um mini-plano de ação sob medida.',

            'Quanto mais contexto você der, melhor a sprint sugerida e as tarefas simuladas.',

        ],

    };



    function pickMessage(list, index) {

        if (!list || !list.length) return '';

        return list[index % list.length];

    }



    function dynamicEstrategiaTips(data) {

        if (!data) return [];

        var tips = [];

        if (data.fixosComObj < data.totalFixos) {

            tips.push('Faltam ' + (data.totalFixos - data.fixosComObj) + ' pilares com objetivo TD — comece por Prontidão Tecnológica ou Pedagógico.');

        }

        if (data.totalKr === 0) {

            tips.push('Próximo passo: crie seu primeiro Key Result em qualquer pilar para ganhar o badge Primeiro KR.');

        }

        if (data.nivel && data.nivel > 1) {

            tips.push('Nível ' + data.nivel + ' de Gestor Estratégico — ' + data.xp + ' XP acumulados. Continue!');

        }

        return tips;

    }



    function buildMessagePool(contextKey, coachData) {

        var base = (SCRIPTS[contextKey] || SCRIPTS.estrategia).slice();

        if (contextKey === 'estrategia') {

            base = dynamicEstrategiaTips(coachData).concat(base);

        }

        var seen = {};

        return base.filter(function (msg) {

            if (!msg || seen[msg]) return false;

            seen[msg] = true;

            return true;

        });

    }



    function init() {

        var root = document.getElementById('coach-guide-root');

        if (!root) return;



        var context = root.getAttribute('data-context') || 'estrategia';

        var coachData = {};

        try {

            var dataEl = document.getElementById('coach-guide-data');

            coachData = dataEl ? JSON.parse(dataEl.textContent || '{}') : {};

        } catch (e) { coachData = {}; }



        var bubble = document.getElementById('coach-guide-bubble');

        var textEl = document.getElementById('coach-guide-text');

        var speakerEl = document.getElementById('coach-guide-speaker');

        var ctaBtn = document.getElementById('coach-guide-cta');

        var closeBtn = document.getElementById('coach-guide-close');

        var btnConsultor = document.getElementById('coach-avatar-consultor');



        var msgIndex = 0;



        function updateBubble() {

            if (!textEl || !speakerEl) return;

            var pool = buildMessagePool(context, coachData);

            var msg = pickMessage(pool, msgIndex)

                || 'Siga o fluxo MudaEdu: diagnosticar, planejar e executar.';

            speakerEl.textContent = 'Consultor LeAction · IA';

            textEl.textContent = msg;

            textEl.classList.remove('coach-guide__text--pulse');

            void textEl.offsetWidth;

            textEl.classList.add('coach-guide__text--pulse');

            if (bubble) bubble.classList.remove('is-hidden');

        }



        if (btnConsultor) {

            btnConsultor.addEventListener('click', function () {

                if (bubble && bubble.classList.contains('is-hidden')) {

                    updateBubble();

                }

            });

        }

        if (closeBtn) {

            closeBtn.addEventListener('click', function () {

                if (bubble) bubble.classList.add('is-hidden');

            });

        }

        if (ctaBtn) {

            ctaBtn.addEventListener('click', function () {

                msgIndex += 1;

                updateBubble();

            });

        }



        updateBubble();



        if (bubble) {

            setTimeout(function () { bubble.classList.remove('is-hidden'); }, 400);

        }

    }



    if (document.readyState === 'loading') {

        document.addEventListener('DOMContentLoaded', init);

    } else {

        init();

    }

})();

