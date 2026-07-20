"""
Banco estático de Metodologias Inov-Ativas do inove4us.

Mecânicas pedagógicas imutáveis e testadas — elimina o custo de gerar
o passo a passo via IA a cada requisição. A IA só fornece
`gancho_adaptacao` (contexto do problema do professor) para plugar nestes cards.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def _card(
    titulo: str,
    objetivo: str,
    mecanica: str,
    dica: str,
    foco: str,
    minutos: int,
) -> dict[str, Any]:
    return {
        "titulo": titulo,
        "titulo_do_card": titulo,
        "objetivo": objetivo,
        "mecanica_passo_a_passo": mecanica,
        "como_executar_detalhado": mecanica,
        "dica_de_facilitacao": dica,
        "foco_da_metodologia_escolhida": foco,
        "duracao_minutos": minutos,
    }


METODOLOGIAS_DB: dict[str, dict[str, Any]] = {
    # ==========================================
    # QUADRANTE: ÁGEIS
    # ==========================================
    "agil_elevator_pitch": {
        "nome": "Elevator Pitch",
        "categoria": "ÁGEIS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Estruturando a Ideia Base",
                "Alinhar os 4 pilares do Pitch: Gancho, Problema, Solução e Pedido.",
                "Distribua uma folha dividida em 4 quadrantes para cada grupo. "
                "Dê 10 minutos para preencherem: 1) O Gancho (frase de impacto/dado); "
                "2) O Problema (a dor real); 3) A Solução (o que criaram); "
                "4) O Pedido (o que precisam da banca). Só tópicos em post-its — sem textos longos.",
                "Proíba slides ou computadores nesta etapa. O foco é o roteiro mental e o papel.",
                "Quadrantes do pitch (gancho–problema–solução–pedido)",
                12,
            ),
            _card(
                "A Regra dos 60 Segundos",
                "Treinar síntese e oratória sob pressão do tempo.",
                "Cada equipe escolhe um Comunicador. Projete um cronômetro de 1 minuto. "
                "Ao sinal, o comunicador vende a ideia aos colegas sem ler. "
                "Se passar de 60s, apite e pare. Os colegas anotam o que ficou confuso; "
                "refazem o teste mais duas vezes.",
                "Seja implacável com o cronômetro. O corte abrupto gera risadas e mostra a necessidade de síntese.",
                "Timebox rígido de 60 segundos",
                15,
            ),
            _card(
                "Arena de Pitches — Rodada Eliminatória",
                "Apresentação oficial com feedback imediato (peer review).",
                "Sala em formato de U. Você (e convidados) no centro como Banca. "
                "Cada grupo faz o pitch de 60 segundos. A turma avalia Clareza, Inovação e Postura "
                "(plaquinhas ou fichas). No fim, debatam quem seria 'financiado'.",
                "A nota dos ouvintes deve compor a avaliação da equipe — evita dispersão.",
                "Peer review com critérios públicos",
                18,
            ),
            _card(
                "Pitch Final + Decisão da Banca",
                "Consolidar a melhor versão e fechar com feedback acionável.",
                "Os 2–3 pitches mais bem avaliados refazem a versão final (ainda em 60s). "
                "A banca entrega um veredicto em 3 bullets: manter, cortar, reforçar. "
                "Cada grupo registra o 'contrato de melhoria' em 1 frase no quadro.",
                "Force 1 frase de melhoria por grupo — evita feedback empático vazio.",
                "Iteração final sob critério da banca",
                10,
            ),
        ],
    },
    "agil_minute_paper": {
        "nome": "Minute Paper",
        "categoria": "ÁGEIS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Pergunta-Gatilho",
                "Focar a turma em 1–2 perguntas de alto valor cognitivo.",
                "Projete duas perguntas no quadro: 1) 'Qual foi a ideia mais importante de hoje?' "
                "2) 'Qual dúvida ainda te impede de aplicar isso?'. "
                "Explique: respostas em 1 minuto, no máximo 3 linhas, sem consulta.",
                "Perguntas vagas geram respostas vagas. Torne-as específicas ao conteúdo da aula.",
                "Perguntas de síntese em tempo curto",
                5,
            ),
            _card(
                "Escrita Relâmpago",
                "Capturar evidência individual de aprendizagem sem pressão de exposição.",
                "Cronômetro de 60–90 segundos. Alunos escrevem em papel ou formulário digital. "
                "Silêncio total. Quem terminar cedo revisa se a resposta é específica (nomeia conceito/exemplo).",
                "Não circule lendo em voz alta durante a escrita — quebra a concentração.",
                "Produção individual cronometrada",
                8,
            ),
            _card(
                "Triagem Rápida do Professor",
                "Identificar padrões de entendimento e lacunas em minutos.",
                "Colete 8–12 papéis aleatórios (ou leia o feed digital). "
                "Classifique mentalmente em 3 pilhas: claro / parcial / confuso. "
                "Anote 2 padrões no quadro sem expor nomes.",
                "Mostre padrões, não 'erros de alunos'. Protege a segurança psicológica.",
                "Leitura amostral para diagnóstico",
                10,
            ),
            _card(
                "Retorno Coletivo",
                "Fechar a lacuna mais frequente com micro-explicação e próxima ação.",
                "Compartilhe 1 insight forte e 1 dúvida recorrente. "
                "Peça a 2 alunos que completem a resposta correta em 20 segundos cada. "
                "Termine com um 'próximo passo' (tarefa de 5 min ou pergunta para a próxima aula).",
                "Se a dúvida for profunda, não improvise aula inteira — marque um mini-clínica depois.",
                "Feedback imediato baseado em evidência",
                12,
            ),
        ],
    },
    "agil_pecha_kucha": {
        "nome": "Pecha Kucha",
        "categoria": "ÁGEIS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Roteiro 20×20",
                "Forçar estrutura visual: 20 slides × 20 segundos cada.",
                "Explique a regra Pecha Kucha: exatamente 20 slides, 20 segundos cada (6m40s). "
                "Cada grupo define o arco: gancho → problema → evidência → proposta → chamada à ação. "
                "Proíba mais de 8 palavras por slide.",
                "Use um template com 20 slots numerados — reduz ansiedade de 'por onde começar'.",
                "Formato 20 slides / 20 segundos",
                12,
            ),
            _card(
                "Montagem Visual Express",
                "Traduzir conteúdo em imagens e palavras-chave.",
                "Grupos produzem os 20 slides (Canva/PPT/papel A5). "
                "Regra: se precisa ler o slide, está errado. "
                "Ensaiem a fala sincronizada com avanço automático ou clique a cada 20s.",
                "Nomeie um 'Guardião do Tempo' por grupo só para o ensaio.",
                "Síntese visual sem texto denso",
                20,
            ),
            _card(
                "Ensaio Cronometrado",
                "Ajustar ritmo e eliminar enrolação.",
                "Cada grupo apresenta para si mesmo 1 vez completa com cronômetro. "
                "Colegas marcam slides 'mortos' (fala vazia) e slides 'ricos'. "
                "Cortam 1 ideia fraca e reforçam 1 metáfora forte.",
                "Grave o ensaio no celular se possível — o aluno se ouve e acelera a correção.",
                "Ensaio sob timing automático",
                12,
            ),
            _card(
                "Apresentação Oficial + Feedback 3×3",
                "Expor a ideia e receber feedback estruturado.",
                "Apresentações oficiais. Audiência usa cartão 3×3: 3 pontos fortes, 3 perguntas, 3 melhorias. "
                "Após cada grupo, 90 segundos de feedback oral do cartão mais claro.",
                "Interrompa aplausos longos — o tempo do Pecha Kucha é o ritual de disciplina.",
                "Apresentação ritualizada + feedback estruturado",
                20,
            ),
        ],
    },
    # ==========================================
    # QUADRANTE: CRI-ATIVAS
    # ==========================================
    "criativa_rotacao_estacoes": {
        "nome": "Rotação por Estações",
        "categoria": "CRI-ATIVAS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Setup do Ecossistema",
                "Preparar o espaço físico para diferentes estímulos de aprendizagem.",
                "Divida a sala em 4 ilhas. Estação 1 (Leitura/Vídeo curto): material teórico. "
                "Estação 2 (Mão na Massa): papel, caneta, massinha para rascunhar. "
                "Estação 3 (Debate): questão polêmica no centro. "
                "Estação 4 (Professor): você para dúvidas pontuais. Conteúdo independente em cada ilha.",
                "Se um grupo não entender a Estação 1, isso não pode impedir a Estação 2.",
                "Ilhas independentes com estímulos distintos",
                10,
            ),
            _card(
                "Giro Rápido (Timebox)",
                "Garantir que todos passem por todas as experiências de forma fluida.",
                "Turma em 4 grupos; cada um começa em uma estação. "
                "Alarme/música a cada 12 minutos + 1 minuto de troca no sentido horário. "
                "Ciclo completo ≈ 50 minutos.",
                "Coloque um líder de tempo em cada grupo para avisar quando faltarem 2 minutos.",
                "Rotação cronometrada entre estações",
                48,
            ),
            _card(
                "Captura por Estação",
                "Registrar evidência mínima em cada ilha sem travar o giro.",
                "Em cada estação, o grupo deixa 1 post-it ou foto: insight, dúvida ou produto parcial. "
                "Quem chega na próxima ilha lê o rastro do grupo anterior (opcional) ou só o próprio portfólio.",
                "Limite a 1 evidência por estação — evita atraso na rotação.",
                "Evidência mínima portátil entre ilhas",
                8,
            ),
            _card(
                "Plenária de Síntese",
                "Conectar as peças e gerar o entregável final.",
                "Volte ao círculo. Cada grupo elege a estação com melhor insight. "
                "Entregável: uma frase no quadro (ou doc compartilhado) que conecte os aprendizados "
                "das 4 estações ao problema principal.",
                "Não pule esta etapa — é onde o movimento ganha propósito pedagógico.",
                "Síntese coletiva pós-rotação",
                12,
            ),
        ],
    },
    "criativa_narrativas_transmidia": {
        "nome": "Narrativas Transmídia",
        "categoria": "CRI-ATIVAS",
        "contexto_execucao": "misto",
        "cards": [
            _card(
                "Universo Narrativo",
                "Definir o mundo da história e o problema central a ser contado.",
                "Em grupos, criem o 'bíblia do universo': personagens, conflito, regra do mundo "
                "e o problema real da turma traduzido em trama. "
                "Entrega: 1 página A3 com mapa do universo.",
                "Exija que o conflito narrativo espelhe o problema pedagógico — senão vira fanfic.",
                "Mundo narrativo ancorado no problema",
                15,
            ),
            _card(
                "Fragmentação por Mídia",
                "Distribuir a história em canais complementares (não repetitivos).",
                "Cada grupo escolhe 3 mídias (ex.: podcast 90s, post Instagram, cartaz, QR com vídeo). "
                "Regra transmídia: cada canal revela uma peça nova; nenhum repete o mesmo texto.",
                "Mostre um exemplo ruim (mesmo texto em 3 mídias) versus um bom (peças complementares).",
                "Canais complementares, não cópias",
                20,
            ),
            _card(
                "Produção das Peças",
                "Materializar os fragmentos com papéis claros na equipe.",
                "Papéis: Roteirista, Designer, Editor de áudio/vídeo, Guardião da coerência. "
                "Produzam as 3 peças mínimas viáveis. Checklist: gancho, evidência do conteúdo, CTA.",
                "Limite o perfeccionismo: MVP em 20 min vale mais que 1 peça perfeita.",
                "Produção multimídia com papéis",
                25,
            ),
            _card(
                "Trilha do Público",
                "Testar se a narrativa guia o público entre as mídias.",
                "Troca entre grupos: cada um consome a trilha do outro na ordem indicada. "
                "Anotam: o que ficou claro, o que faltou, se quiseram ir à próxima mídia. "
                "Autores ajustam 1 transição (ex.: cliffhanger + QR).",
                "Peça feedback sobre a transição entre mídias — o coração da transmídia.",
                "Teste de jornada entre canais",
                15,
            ),
        ],
    },
    "criativa_painel_diversidade": {
        "nome": "Painel de Diversidade",
        "categoria": "CRI-ATIVAS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Mapeamento de Perspectivas",
                "Tornar visíveis os pontos de vista presentes (e ausentes) na turma.",
                "No quadro, colunas: Eu / Minha família / Minha rua / Outro contexto. "
                "Cada aluno cola 1 post-it por coluna sobre o tema. "
                "Leitura silenciosa de 3 minutos para ver padrões e lacunas.",
                "Proíba julgamento na fase de mapeamento — só coleta.",
                "Visibilidade de múltiplas perspectivas",
                12,
            ),
            _card(
                "Constituição do Painel",
                "Montar um painel com vozes deliberadamente diferentes.",
                "Forme painéis de 4: cada membro assume uma lente (ex.: estudante, responsável, "
                "vizinho, gestor público). Em 8 minutos, cada lente escreve 3 argumentos.",
                "Se a turma for homogênea, use cartas de persona para forçar diversidade de olhar.",
                "Lentes/personas no painel",
                15,
            ),
            _card(
                "Rodada de Escuta Ativa",
                "Praticar escuta antes do debate.",
                "Cada lente fala 90 segundos. Os outros só podem anotar perguntas esclarecedoras "
                "(proibido rebater). Depois, 1 pergunta por lente, respondida em 45 segundos.",
                "Use um objeto 'microfone' — só fala quem está com ele.",
                "Protocolo de escuta antes do embate",
                15,
            ),
            _card(
                "Síntese de Decisão Inclusiva",
                "Chegar a uma proposta que incorpore ao menos 2 lentes conflitantes.",
                "O painel escreve uma decisão em 5 linhas: o que fazer, quem ganha, quem precisa "
                "de salvaguarda, e 1 risco ético. Apresentam em 2 minutos para a turma.",
                "Se a proposta ignorar uma lente, devolva o cartão 'perspectiva invisível'.",
                "Decisão que integra tensões",
                12,
            ),
        ],
    },
    "criativa_caso_empatico": {
        "nome": "Caso Empático",
        "categoria": "CRI-ATIVAS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Caso Vivo",
                "Apresentar um caso humano concreto (não abstrato).",
                "Entregue um caso de 1 página: personagem, contexto, tensão ética/prática, "
                "dados incompletos. Leitura individual 5 min + marcação de emoções e fatos.",
                "Casos genéricos matam empatia. Use nomes, idades e detalhes sensoriais.",
                "Caso narrativo com tensão real",
                10,
            ),
            _card(
                "Mapa de Empatia",
                "Separar o que a pessoa diz, faz, pensa e sente.",
                "Em grupos, preencham o mapa: Diz / Faz / Pensa / Sente + dores e ganhos. "
                "Usem só evidências do texto; o que for inferência vai em cor diferente.",
                "Force a distinção evidência vs. inferência — evita 'achar que sabe'.",
                "Mapa Diz/Faz/Pensa/Sente",
                15,
            ),
            _card(
                "Decisão sob Tensão",
                "Tomar uma decisão pedagógica/prática que respeite a pessoa do caso.",
                "O grupo escolhe 1 ação recomendada e lista trade-offs. "
                "Simulam a conversa com a personagem (2 min) e ajustam a proposta.",
                "Peça que digam em voz alta o que a personagem pode sentir ao ouvir a proposta.",
                "Ação alinhada à empatia evidenciada",
                15,
            ),
            _card(
                "Debrief Ético",
                "Generalizar o aprendizado sem perder o humano do caso.",
                "Plenária: 'O que quase ignoramos?' 'Que viés apareceu?' "
                "Cada grupo entrega 1 princípio de ação para o problema da turma.",
                "Feche com princípios, não com 'solução mágica' — o caso é lente, não receita.",
                "Princípios transferíveis do caso",
                10,
            ),
        ],
    },
    "criativa_design_thinking_express": {
        "nome": "Design Thinking Express",
        "categoria": "CRI-ATIVAS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Empatia Relâmpago",
                "Coletar dores reais em tempo curto.",
                "Duplas: 4 min de entrevista (2+2). Perguntas: quando o problema piora? "
                "o que já tentaram? o que importa de verdade? Anotem citações literais.",
                "Proíba soluções nesta fase — só escuta e citações.",
                "Entrevista relâmpago com citações",
                10,
            ),
            _card(
                "Definir o Ponto de Vista",
                "Transformar achados em um POV acionável.",
                "Fórmula no quadro: [Usuário] precisa [necessidade] porque [insight]. "
                "Cada grupo escolhe 1 POV e cola no centro da mesa.",
                "Se o POV couber em qualquer tema, está genérico — peça um detalhe observável.",
                "POV usuário–necessidade–insight",
                10,
            ),
            _card(
                "Ideação Quente",
                "Gerar volume de ideias sem julgamento.",
                "8 minutos de brainstorming silencioso + 4 de cluster. "
                "Meta: 15 ideias mínimas. Depois votam com 3 stickers cada.",
                "Use regra 'sim, e…' se alguém começar a criticar cedo.",
                "Divergência rápida + votação",
                12,
            ),
            _card(
                "Protótipo de Baixa Fidelidade",
                "Tornar a ideia testável em papel.",
                "Em 12 minutos, prototipem com papel, fita, massinha ou storyboard de 6 quadros. "
                "Precisa ser tocável/explicável em 60 segundos.",
                "Protótipo bonito demais é sinal de que não testaram o essencial.",
                "Protótipo rápido testável",
                12,
            ),
            _card(
                "Teste e Ajuste",
                "Validar com outro grupo e iterar 1 mudança.",
                "Troca entre grupos: 3 min de teste, 2 de feedback (gostei / confuso / faltou). "
                "Autores fazem 1 ajuste visível e apresentam o antes/depois em 1 minuto.",
                "Exija exatamente 1 mudança — evita redesign completo sem aprendizado.",
                "Feedback estruturado + micro-iteração",
                12,
            ),
        ],
    },
    # ==========================================
    # QUADRANTE: IMERSIVAS
    # ==========================================
    "imersiva_escape_room": {
        "nome": "Escape Room Educacional",
        "categoria": "IMERSIVAS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "O Enredo Narrativo",
                "Engajar a turma com uma missão em que são protagonistas.",
                "Inicie com clima (música/portas). Apresente o Caso Base e a regra: "
                "'Vocês estão trancados. Para escapar, resolvam 3 enigmas do conteúdo em 40 minutos'.",
                "Você é o Game Master (ou vilão). Teatralize — quebra o gelo.",
                "Missão narrativa com pressão de tempo",
                8,
            ),
            _card(
                "A Caça aos Enigmas",
                "Resolver problemas aplicando conhecimento de forma colaborativa.",
                "Espalhe envelopes pela sala. Resposta do Enigma 1 revela o Enigma 2; "
                "o Enigma 3 revela a senha do cadeado/PDF com o 'antídoto'.",
                "Sistema de 'Dicas Pagas': pedir dica custa 3 minutos no tempo final.",
                "Enigmas encadeados com conteúdo curricular",
                30,
            ),
            _card(
                "Checkpoint do Game Master",
                "Recalibrar grupos travados sem matar a imersão.",
                "Aos 20 minutos, anuncie um 'evento do mundo' (pista coletiva no quadro). "
                "Grupos que já avançaram podem trocar 1 dica com outro grupo (negociação de 60s).",
                "Não entregue a resposta — entregue um caminho de raciocínio.",
                "Intervenção diegética do Game Master",
                8,
            ),
            _card(
                "Debriefing (Descompressão)",
                "Transformar a adrenalina do jogo em consolidação teórica.",
                "Roda final: 'Qual enigma foi mais difícil? Por que a teoria X era a chave?' "
                "Conecte cadeados ao objetivo de aprendizagem do currículo.",
                "Alunos querem falar do tempo; puxe gentilmente para a lógica do conteúdo.",
                "Debrief que amarra jogo → teoria",
                12,
            ),
        ],
    },
    "imersiva_roleplaying": {
        "nome": "Roleplaying",
        "categoria": "IMERSIVAS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Briefing de Papéis",
                "Distribuir papéis com objetivos conflitantes e claros.",
                "Entregue cartas seladas: papel, objetivo secreto, 2 restrições, 1 recurso. "
                "Leitura individual 4 min. Proibido revelar o objetivo secreto ainda.",
                "Papéis sem conflito real geram teatro vazio — desenhe tensões.",
                "Cartas de papel com objetivos ocultos",
                10,
            ),
            _card(
                "Aquecimento em Personagem",
                "Entrar no papel com linguagem e postura.",
                "Em círculo, cada um se apresenta em 20 segundos no personagem. "
                "Depois, 2 minutos de improviso livre em duplas sobre o cenário.",
                "Se alguém sair do personagem, use um sinal combinado (ex.: tocar a mesa).",
                "Entrada corporal/verbal no papel",
                8,
            ),
            _card(
                "Cena Principal",
                "Negociar/decidir sob pressão do cenário.",
                "Rode a cena de 15–20 minutos com um evento detonador no meio "
                "(nova informação, prazo, visita inesperada). "
                "Observadores externos anotam estratégias e vieses.",
                "Um facilitador-relógio anuncia eventos — você não 'julga' a cena durante.",
                "Simulação com evento detonador",
                20,
            ),
            _card(
                "Hot Seat + Debrief",
                "Sair do papel e analisar decisões.",
                "2 personagens vão ao 'hot seat' e respondem perguntas da turma ainda no papel (3 min), "
                "depois fora do papel. Debrief: o que o papel revelou sobre o problema real?",
                "Separe claramente 'no papel' e 'fora do papel' para evitar constrangimento.",
                "Distanciação e análise pós-cena",
                12,
            ),
        ],
    },
    "imersiva_gamificacao": {
        "nome": "Gamificação Estrutural/Conteúdo",
        "categoria": "IMERSIVAS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Regras do Jogo e Missão",
                "Tornar explícitos objetivos, XP, vidas e condições de vitória.",
                "Apresente o tabuleiro/quadro de missões: missões principais (conteúdo), "
                "side-quests (colaboração) e boss final (desafio integrador). "
                "Distribua fichas de XP e explique como se sobe de nível.",
                "Gamificação sem regra clara vira premiinho aleatório — escreva as regras no quadro.",
                "Estrutura de missões + progressão",
                10,
            ),
            _card(
                "Missões em Ciclos Curtos",
                "Executar desafios de conteúdo com feedback imediato de XP.",
                "Ciclos de 8–10 minutos: grupo completa missão → valida com checklist → ganha XP/badge. "
                "Missões falhas podem ser retentadas com custo (perda de 1 vida).",
                "Valide por evidência de aprendizagem, não por 'esforço bonito'.",
                "Ciclos missão–validação–XP",
                25,
            ),
            _card(
                "Boss Challenge",
                "Integrar o conteúdo num desafio final sob regras do jogo.",
                "O boss exige combinar 2–3 habilidades das missões anteriores. "
                "Tempo limitado. Grupos podem gastar XP para 'power-ups' (dica, tempo extra, consulta).",
                "Power-ups caros ensinam priorização — não doe dicas de graça.",
                "Desafio integrador com economia de XP",
                15,
            ),
            _card(
                "Placar e Retrospectiva do Jogador",
                "Refletir o que o jogo ensinou além da pontuação.",
                "Atualize o placar. Cada grupo escreve: 1 skill desbloqueada, 1 falha útil, "
                "1 estratégia para a próxima partida/aula.",
                "Celebre a falha útil — senão a gamificação reforça só vencedores.",
                "Metacognição pós-jogo",
                10,
            ),
        ],
    },
    "imersiva_realidade_aumentada": {
        "nome": "Realidade Aumentada",
        "categoria": "IMERSIVAS",
        "contexto_execucao": "misto",
        "cards": [
            _card(
                "Preparação dos Marcadores",
                "Definir o que será 'aumentado' e com qual intenção pedagógica.",
                "Distribua marcadores (QR/imagens) pela sala ou pátio. "
                "Cada marcador revela camada digital: dado, modelo, pergunta ou pista. "
                "Explique a rota e a regra de captura (foto/nota por marcador).",
                "Teste 1 marcador antes da turma — AR que falha mata o engajamento.",
                "Camadas digitais ancoradas no espaço",
                10,
            ),
            _card(
                "Expedição Aumentada",
                "Coletar evidências misturando espaço físico e camada digital.",
                "Grupos percorrem a rota com celular/tablet. Em cada ponto: observar → "
                "abrir camada → registrar achado no diário de campo (3 linhas).",
                "Um membro só filma/registra; outro só interpreta — evita tela compartilhada bagunçada.",
                "Percurso físico + camada digital",
                25,
            ),
            _card(
                "Montagem do Mapa Híbrido",
                "Sintetizar achados físicos e digitais num artefato único.",
                "No retorno, montem um mapa A3: local físico + o que a AR revelou + implicação "
                "para o problema. Destachem 1 'ponto cego' que a AR não mostrou.",
                "Peça o ponto cego — desenvolve senso crítico sobre a tecnologia.",
                "Síntese híbrida físico-digital",
                15,
            ),
            _card(
                "Demo Guiada",
                "Ensinar o percurso a outro grupo em 3 minutos.",
                "Cada grupo guia visitantes por 2 marcadores-chave e explica a decisão pedagógica "
                "da camada aumentada. Feedback: clareza da camada e utilidade para o aprendizado.",
                "Foque na intenção pedagógica da camada, não no efeito visual.",
                "Mediação peer-to-peer da experiência AR",
                12,
            ),
        ],
    },
    "imersiva_jogos_serios_3d": {
        "nome": "Jogos Sérios 3D",
        "categoria": "IMERSIVAS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Contrato do Jogador",
                "Alinhar objetivo de aprendizagem e regras de uso do ambiente 3D.",
                "Antes de logar: objetivo da sessão, o que conta como evidência, tempo de tela, "
                "e papéis (piloto, copiloto, analista). Combinem sinais de pausa.",
                "Sem contrato, vira só gameplay. Escreva o objetivo no quadro.",
                "Contrato pedagógico pré-jogo",
                8,
            ),
            _card(
                "Missão no Ambiente 3D",
                "Explorar o cenário cumprindo objetivos de conteúdo.",
                "Ciclo de 15–20 min no ambiente (simulador/jogo sério). "
                "Analista anota decisões, erros e descobertas em checklist alinhado ao currículo.",
                "Alterne piloto a cada 5 minutos para não concentrar o controle.",
                "Exploração com registro analítico",
                20,
            ),
            _card(
                "Pausa Metacognitiva",
                "Sair do jogo para explicitar estratégias.",
                "Pause o mundo 3D. Em 5 minutos: o que funcionou, o que foi tentativa cega, "
                "qual conceito escolar explica o resultado. Ajustem a estratégia antes de voltar.",
                "Essa pausa é ouro — não pule para 'mais um nível'.",
                "Pausa para transferir jogo → conceito",
                8,
            ),
            _card(
                "Transferência para o Mundo Real",
                "Traduzir decisões do jogo em plano de ação fora da tela.",
                "Cada grupo entrega um plano de 5 linhas: situação real análoga, decisão recomendada, "
                "risco, evidência observada no jogo. Apresentação de 90 segundos.",
                "Se não houver analogia real, a missão 3D estava desalinhada — anote para redesenhar.",
                "Transferência jogo → ação real",
                12,
            ),
        ],
    },
    # ==========================================
    # QUADRANTE: ANALÍTICAS
    # ==========================================
    "analitica_learning_analytics": {
        "nome": "Learning Analytics",
        "categoria": "ANALÍTICAS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Pergunta Analítica",
                "Definir que decisão pedagógica os dados vão informar.",
                "No quadro: 'Que decisão queremos tomar com evidência?' "
                "Grupos escolhem 1 pergunta mensurável (ex.: quem trava em qual etapa?).",
                "Sem pergunta, dashboard vira distração colorida.",
                "Pergunta antes do dado",
                8,
            ),
            _card(
                "Coleta Ética de Sinais",
                "Levantar dados leves com consentimento e propósito claro.",
                "Coletem sinais: autoavaliação 1–5, tempo por tarefa, erros comuns, "
                "check de saída. Explique o que NÃO será usado para punir.",
                "Diga em voz alta o uso ético — reduz resistência a se expor.",
                "Sinais leves com pacto ético",
                12,
            ),
            _card(
                "Leitura de Padrões",
                "Transformar números/respostas em padrões acionáveis.",
                "Montem um mini-painel (tabela/post-its): distribuição, outliers, gargalos. "
                "Formulem 2 hipóteses ('parece que… porque…').",
                "Force hipóteses falsificáveis — evita achismo disfarçado de dado.",
                "Padrões → hipóteses",
                15,
            ),
            _card(
                "Intervenção Orientada por Dados",
                "Escolher 1 ação pedagógica e um indicador de sucesso.",
                "Cada grupo propõe 1 intervenção para a próxima aula + métrica de sucesso "
                "e plano B se o indicador não melhorar. Compartilham em 2 minutos.",
                "Uma intervenção bem medida vale mais que cinco ideias sem indicador.",
                "Ação + métrica + plano B",
                12,
            ),
        ],
    },
    "analitica_diagnostico_coletivo": {
        "nome": "Diagnóstico Coletivo",
        "categoria": "ANALÍTICAS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Sintomas no Quadro",
                "Externalizar sintomas sem buscar culpados.",
                "Tempestade de sintomas em post-its (1 sintoma por nota). "
                "Agrupem por afinidade. Proibido escrever nomes de pessoas como causa.",
                "Separe sintoma de causa desde o início — senão o diagnóstico vicia.",
                "Inventário coletivo de sintomas",
                10,
            ),
            _card(
                "Cinco Porquês em Grupos",
                "Aprofundar até causas raiz plausíveis.",
                "Cada grupo pega 1 cluster de sintomas e aplica 5 Porquês. "
                "Param quando chegarem a uma causa acionável na escola/turma.",
                "Se o 5º porquê for 'porque os alunos são assim', force um nível sistêmico.",
                "5 Porquês até causa acionável",
                15,
            ),
            _card(
                "Matriz Impacto × Controle",
                "Priorizar o que a turma realmente pode mexer.",
                "Plotem causas em Impacto (baixo/alto) × Controle da turma (baixo/alto). "
                "Escolhem 1 causa do quadrante alto-alto para atacar.",
                "Celebre descartar o que está fora de controle — foca energia.",
                "Priorização impacto × controle",
                12,
            ),
            _card(
                "Hipótese de Intervenção",
                "Converter diagnóstico em hipótese testável.",
                "Fórmula: Se fizermos X por Y tempo, esperamos Z evidência. "
                "Cada grupo cola a hipótese e define 1 sinal de que deu certo/errado.",
                "Exija prazo e evidência — senão vira desejo, não hipótese.",
                "Hipótese testável pós-diagnóstico",
                10,
            ),
        ],
    },
    "analitica_trilhas_adaptativas": {
        "nome": "Trilhas de Aprendizagem Adaptativas",
        "categoria": "ANALÍTICAS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Diagnóstico de Partida",
                "Posicionar cada aluno/grupo em um nível inicial sem estigma.",
                "Quiz curto ou estação de checagem com 3 níveis (A/B/C). "
                "Resultado aponta trilha inicial. Explique: trilhas são caminhos, não rótulos fixos.",
                "Use linguagem de 'rota', nunca de 'fracos/fortes'.",
                "Checagem inicial para roteamento",
                10,
            ),
            _card(
                "Trilhas Paralelas",
                "Oferecer percursos distintos com o mesmo objetivo de chegada.",
                "Monte 3 trilhas: reforço guiado, prática padrão, desafio avançado. "
                "Materiais em mesas/folders coloridos. Alunos trabalham 20 min na trilha.",
                "O objetivo final deve ser o mesmo — muda o andaime, não a ambição.",
                "Percursos diferenciados, mesmo destino",
                20,
            ),
            _card(
                "Checkpoints de Re-roteamento",
                "Permitir mudança de trilha com base em evidência.",
                "Aos 10 e 20 minutos, checkpoint rápido (1 questão ou mostra do produto). "
                "Quem demonstra domínio sobe; quem trava recebe suporte ou desce de andaime.",
                "Normalize a mudança de trilha — é o coração do adaptativo.",
                "Re-roteamento por evidência",
                10,
            ),
            _card(
                "Convergência Final",
                "Reunir todas as trilhas num produto comum.",
                "Todos convergem para a mesma entrega (mapa, pitch, resolução). "
                "Grupos mistos (ex-trilhas diferentes) explicam o que cada rota ensinou.",
                "Misture as trilhas no fim — evita bolhas permanentes.",
                "Produto comum após diferenciação",
                12,
            ),
        ],
    },
}


# Nome oficial (framework) → id do banco
NOME_PARA_ID: dict[str, str] = {
    meta["nome"]: mid for mid, meta in METODOLOGIAS_DB.items()
}

# Aliases comuns do modelo → id
_ALIAS_PARA_ID: dict[str, str] = {
    "elevator pitch": "agil_elevator_pitch",
    "minute paper": "agil_minute_paper",
    "pecha kucha": "agil_pecha_kucha",
    "pecha-kucha": "agil_pecha_kucha",
    "rotação por estações": "criativa_rotacao_estacoes",
    "rotacao por estacoes": "criativa_rotacao_estacoes",
    "narrativas transmídia": "criativa_narrativas_transmidia",
    "narrativas transmidia": "criativa_narrativas_transmidia",
    "painel de diversidade": "criativa_painel_diversidade",
    "caso empático": "criativa_caso_empatico",
    "caso empatico": "criativa_caso_empatico",
    "design thinking express": "criativa_design_thinking_express",
    "design thinking": "criativa_design_thinking_express",
    "escape room educacional": "imersiva_escape_room",
    "escape room": "imersiva_escape_room",
    "roleplaying": "imersiva_roleplaying",
    "role playing": "imersiva_roleplaying",
    "role-playing": "imersiva_roleplaying",
    "gamificação estrutural/conteúdo": "imersiva_gamificacao",
    "gamificacao estrutural/conteudo": "imersiva_gamificacao",
    "gamificação estrutural": "imersiva_gamificacao",
    "gamificacao estrutural": "imersiva_gamificacao",
    "realidade aumentada": "imersiva_realidade_aumentada",
    "jogos sérios 3d": "imersiva_jogos_serios_3d",
    "jogos serios 3d": "imersiva_jogos_serios_3d",
    "learning analytics": "analitica_learning_analytics",
    "diagnóstico coletivo": "analitica_diagnostico_coletivo",
    "diagnostico coletivo": "analitica_diagnostico_coletivo",
    "trilhas de aprendizagem adaptativas": "analitica_trilhas_adaptativas",
}


def get_metodologia(id_metodologia: str) -> dict[str, Any] | None:
    """Busca a estrutura fixa de uma metodologia pelo ID."""
    meta = METODOLOGIAS_DB.get(id_metodologia)
    return deepcopy(meta) if meta else None


def resolve_metodologia_id(nome_ou_id: str | None) -> str | None:
    """Resolve nome do framework, alias ou id interno para a chave do DB."""
    if not nome_ou_id:
        return None
    raw = str(nome_ou_id).strip()
    if raw in METODOLOGIAS_DB:
        return raw
    if raw in NOME_PARA_ID:
        return NOME_PARA_ID[raw]
    low = raw.lower()
    if low in _ALIAS_PARA_ID:
        return _ALIAS_PARA_ID[low]
    for nome, mid in NOME_PARA_ID.items():
        if nome.lower() == low or low in nome.lower() or nome.lower() in low:
            return mid
    return None


def get_metodologia_por_nome(nome: str | None) -> dict[str, Any] | None:
    """Atalho: resolve pelo nome oficial/alias e devolve cópia da metodologia."""
    mid = resolve_metodologia_id(nome)
    return get_metodologia(mid) if mid else None


def aplicar_ganchos(
    metodologia: dict[str, Any],
    ganchos: list[Any] | None,
    *,
    problema: str = "",
    contexto: str = "",
) -> list[dict[str, Any]]:
    """Plugam `gancho_adaptacao` nos cards estáticos e devolvem lista pronta para o plano."""
    cards = deepcopy(metodologia.get("cards") or [])
    ganchos = ganchos or []

    by_index: dict[int, str] = {}
    for i, g in enumerate(ganchos):
        if isinstance(g, dict):
            idx = g.get("indice", g.get("index", i))
            try:
                idx = int(idx)
            except (TypeError, ValueError):
                idx = i
            texto = str(
                g.get("gancho_adaptacao")
                or g.get("gancho")
                or g.get("adaptacao")
                or ""
            ).strip()
            if texto:
                by_index[idx] = texto
        elif isinstance(g, str) and g.strip():
            by_index[i] = g.strip()

    fallback = ""
    if problema:
        trecho = " ".join(str(problema).split())[:120]
        ctx = " ".join(str(contexto or "sala de aula").split())[:60]
        fallback = (
            f"Adapte esta etapa ao desafio «{trecho}» "
            f"(contexto: {ctx}), mantendo a mecânica original."
        )

    out: list[dict[str, Any]] = []
    for i, card in enumerate(cards):
        gancho = by_index.get(i) or fallback
        mecanica = str(
            card.get("mecanica_passo_a_passo")
            or card.get("como_executar_detalhado")
            or ""
        ).strip()
        if gancho:
            card["gancho_adaptacao"] = gancho
            card["como_executar_detalhado"] = (
                f"{mecanica}\n\nAdaptação ao seu problema: {gancho}"
                if mecanica
                else gancho
            )
            card["mecanica_passo_a_passo"] = card["como_executar_detalhado"]
        out.append(card)
    return out


def duracao_total_cards(cards: list[dict[str, Any]]) -> int:
    total = 0
    for c in cards:
        try:
            total += int(c.get("duracao_minutos") or 0)
        except (TypeError, ValueError):
            pass
    return total or 50
