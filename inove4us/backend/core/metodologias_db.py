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
        "origem_card": "catalogo",
        "editado": False,
    }


METODOLOGIAS_DB: dict[str, dict[str, Any]] = {
    # ==========================================
    # QUADRANTE: ÁGEIS
    # ==========================================
    "agil_elevator_pitch": {
        "nome": "Pitch de elevador",
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
        "nome": "Narrativa transmídia (estações)",
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
        "nome": "Painel de perspectivas diversas",
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
        "nome": "Design Thinking express",
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
        "nome": "Escape room pedagógico",
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
        "nome": "Roleplay (dramatização de papéis)",
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
        "nome": "Jogos sérios em ambiente 3D",
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
        "nome": "Análise da Aprendizagem",
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
        "nome": "Diagnóstico coletivo",
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
        "nome": "Trilhas adaptativas",
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
    # ==========================================
    # EXPANSÃO DIA A DIA — 24 mecânicas faltantes
    # ==========================================
    "criativa_abordagem_problematizadora": {
        "nome": "Abordagem problematizadora",
        "categoria": "CRIATIVAS",
        "contexto_execucao": "misto",
        "cards": [
            _card(
                "Observação da Realidade",
                "Conduzir a turma a observar um recorte da realidade e identificar um problema.",
                "O professor conduz a turma a observar um recorte da realidade e identificar "
                "um problema social, ambiental ou técnico.",
                "Escolha um recorte concreto e próximo da turma — evite problemas abstratos demais.",
                "Problema real observado no contexto",
                10,
            ),
            _card(
                "Levantamento de Pontos-Chave",
                "Filtrar as variáveis principais que causam o problema.",
                "Os alunos debatem e filtram as variáveis principais que causam esse problema.",
                "Peça evidência para cada variável — corte opiniões sem lastro.",
                "Causas-chave do problema",
                10,
            ),
            _card(
                "Teorização",
                "Buscar fundamentação teórica para entender o problema a fundo.",
                "Os alunos buscam fundamentação teórica (pesquisa em livros, internet, entrevistas) "
                "para entender o problema a fundo.",
                "Defina fontes mínimas e tempo de pesquisa — evita deriva infinita.",
                "Fundamentação teórica do problema",
                12,
            ),
            _card(
                "Hipóteses de Solução",
                "Criar alternativas viáveis para resolver ou mitigar o problema.",
                "Criação de alternativas viáveis para resolver ou mitigar o problema encontrado.",
                "Exija critérios de viabilidade (tempo, custo, alcance) em cada hipótese.",
                "Alternativas viáveis de intervenção",
                10,
            ),
            _card(
                "Aplicação à Realidade",
                "Executar uma intervenção real para modificar a realidade observada.",
                "Execução de uma intervenção real (campanha, ofício, protótipo) "
                "para modificar a realidade observada.",
                "Prefira intervenções pequenas e entregáveis na aula ou no ciclo curto.",
                "Intervenção real no contexto",
                12,
            ),
        ],
    },
    "criativa_aprendizagem_equipes": {
        "nome": "Aprendizagem baseada em equipes (TBL)",
        "categoria": "CRIATIVAS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Estudo Prévio",
                "Garantir preparo individual antes da aula.",
                "Os alunos recebem e estudam o material base antes da aula.",
                "Envie material curto e objetivo — o TBL falha se o pré-estudo for inviável.",
                "Preparação individual pré-aula",
                0,
            ),
            _card(
                "Teste Individual (iRAT)",
                "Verificar o preparo individual com questionário rápido.",
                "Aplicação de um questionário rápido de múltipla escolha "
                "para verificar o preparo individual.",
                "Mantenha 5–10 itens; o foco é diagnóstico, não punição.",
                "Checagem individual de preparo",
                8,
            ),
            _card(
                "Teste em Equipe (tRAT)",
                "Chegar a consenso em equipe sobre as mesmas questões.",
                "Os alunos se reúnem em grupos e respondem ao mesmo questionário, "
                "debatendo até chegar a um consenso.",
                "Force consenso explícito — um porta-voz justifica a resposta do grupo.",
                "Consenso coletivo no mesmo teste",
                12,
            ),
            _card(
                "Apelação",
                "Contestar respostas com fundamentação na literatura.",
                "Os grupos podem contestar respostas consideradas incorretas, "
                "fundamentando a defesa com a literatura.",
                "Só aceite apelação com citação/fonte — evita reclamação vazia.",
                "Contestação fundamentada",
                8,
            ),
            _card(
                "Aplicação Prática",
                "Usar a teoria consolidada em um caso complexo.",
                "O professor lança um caso complexo e os grupos usam a teoria consolidada "
                "para propor uma solução simultaneamente.",
                "Peça entrega simultânea (mesmo prazo) para comparar estratégias.",
                "Caso complexo com solução em equipe",
                15,
            ),
        ],
    },
    "criativa_pbl_problemas": {
        "nome": "Aprendizagem baseada em problemas (PBL)",
        "categoria": "CRIATIVAS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Apresentação do Cenário",
                "Apresentar um caso complexo sem solução óbvia.",
                "O professor apresenta um caso ou problema complexo e sem solução óbvia.",
                "Não entregue a resposta — o problema precisa gerar lacuna real de conhecimento.",
                "Cenário-problema aberto",
                8,
            ),
            _card(
                "Tempestade de Ideias",
                "Listar o que já se sabe e o que ainda falta descobrir.",
                "Os alunos listam o que já sabem sobre o caso e o que ainda precisam descobrir.",
                "Separe em duas colunas no quadro: 'Sabemos' × 'Precisamos saber'.",
                "Mapa de saberes e lacunas",
                10,
            ),
            _card(
                "Estudo Autônomo",
                "Pesquisar independentemente as lacunas de conhecimento.",
                "Os alunos dividem tarefas e pesquisam independentemente "
                "as lacunas de conhecimento.",
                "Defina tempo e produto mínimo por lacuna (3 bullets + fonte).",
                "Pesquisa das lacunas",
                12,
            ),
            _card(
                "Socialização",
                "Compartilhar achados e debater no grupo.",
                "O grupo se reúne novamente para compartilhar o que aprendeu "
                "e debater os achados.",
                "Cada membro fala só da sua lacuna — evita monopolização.",
                "Compartilhamento dos achados",
                10,
            ),
            _card(
                "Síntese e Resolução",
                "Resolver o problema inicial com os novos conhecimentos.",
                "Aplicação dos novos conhecimentos para resolver o problema inicial "
                "e apresentar a conclusão.",
                "Exija conclusão explícita ligada às lacunas pesquisadas.",
                "Resolução fundamentada do caso",
                12,
            ),
        ],
    },
    "criativa_pbl_projetos": {
        "nome": "Aprendizagem baseada em projetos (PjBL)",
        "categoria": "CRIATIVAS",
        "contexto_execucao": "misto",
        "cards": [
            _card(
                "Questão Motriz",
                "Apresentar um desafio engajador que exige produto ou solução final.",
                "Apresentação de um desafio engajador que exige a criação "
                "de um produto ou solução final.",
                "A questão motriz deve ser aberta e pública — não um exercício fechado.",
                "Desafio com produto final",
                8,
            ),
            _card(
                "Planejamento",
                "Definir escopo, papéis e cronograma do projeto.",
                "Os alunos definem o escopo do projeto, dividem papéis e criam um cronograma.",
                "Limite o escopo ao tempo real disponível — corte ambição sem entrega.",
                "Escopo, papéis e cronograma",
                10,
            ),
            _card(
                "Investigação e Desenvolvimento",
                "Pesquisar e construir as primeiras versões do projeto.",
                "Fase de \"mão na massa\", pesquisa profunda e construção "
                "das primeiras versões do projeto.",
                "Peça evidência de progresso a cada bloco de tempo (foto, rascunho, log).",
                "Construção mão na massa",
                15,
            ),
            _card(
                "Crítica e Revisão",
                "Receber feedback de pares e professor sobre rascunho/protótipo.",
                "Apresentação de um rascunho/protótipo para receber feedback "
                "dos pares e do professor.",
                "Use critérios públicos (clareza, viabilidade, impacto) — evita opinião vaga.",
                "Feedback sobre protótipo",
                10,
            ),
            _card(
                "Exibição Pública",
                "Apresentar o produto final a uma audiência real.",
                "Apresentação do produto final validado para uma audiência real "
                "(comunidade, outros professores, pais).",
                "Mesmo uma audiência pequena (outra turma) eleva a qualidade da entrega.",
                "Apresentação a audiência real",
                12,
            ),
        ],
    },
    "criativa_aprendizagem_maker": {
        "nome": "Aprendizagem maker",
        "categoria": "CRIATIVAS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Identificação do Desafio",
                "Definir o artefato a construir e sua finalidade.",
                "Definição de um objeto, mecanismo ou artefato que precisa ser construído "
                "para uma finalidade específica.",
                "Amarre a finalidade a um usuário real (quem usa? para quê?).",
                "Artefato com finalidade clara",
                8,
            ),
            _card(
                "Design e Esboço",
                "Desenhar como o projeto funcionará.",
                "Desenho da planta, diagrama ou rascunho visual de como o projeto funcionará.",
                "Não libere materiais antes do esboço aprovado em 2 minutos de checagem.",
                "Planta/diagrama do artefato",
                10,
            ),
            _card(
                "Prototipagem",
                "Construir o protótipo físico ou digital.",
                "Construção física ou digital utilizando sucatas, impressoras 3D, "
                "marcenaria ou softwares.",
                "Priorize materiais baratos e rápidos na primeira versão.",
                "Construção do protótipo",
                15,
            ),
            _card(
                "Testes de Estresse",
                "Colocar o protótipo à prova para ver onde falha.",
                "Colocar o protótipo à prova para ver onde ele falha ou quebra.",
                "Peça registro do ponto de falha — falha sem registro não ensina.",
                "Teste até o ponto de falha",
                10,
            ),
            _card(
                "Iteração",
                "Corrigir erros do teste e finalizar o artefato.",
                "Correção dos erros encontrados no teste e finalização do artefato.",
                "Limite a 1–2 correções críticas — evita perfeccionismo sem entrega.",
                "Correção e finalização",
                10,
            ),
        ],
    },
    "criativa_coaching_reverso": {
        "nome": "Coaching reverso",
        "categoria": "CRIATIVAS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Inversão de Papéis",
                "Selecionar tema em que os alunos têm maior fluência.",
                "O professor seleciona um tema onde os alunos possuem maior fluência "
                "(ex: tendências de redes sociais, novos aplicativos).",
                "Escolha tema real de domínio dos alunos — senão a inversão é teatral.",
                "Tema de fluência dos alunos",
                5,
            ),
            _card(
                "Preparação do Mentor",
                "Estruturar como ensinar o conceito a um adulto.",
                "Os alunos estruturam como vão ensinar esse conceito para um adulto "
                "(professor ou membro da gestão).",
                "Peça roteiro de 3 passos + 1 demonstração prática.",
                "Roteiro de mentoria do aluno",
                10,
            ),
            _card(
                "Sessão de Tutoria",
                "Aluno conduz; professor assume postura de aprendiz.",
                "O aluno conduz a aula/mentoria, enquanto o professor assume a postura "
                "de aprendiz, fazendo perguntas.",
                "Faça perguntas genuínas de iniciante — não \"teste\" o aluno.",
                "Mentoria aluno → professor",
                15,
            ),
            _card(
                "Aplicação Conjunta",
                "Professor-aprendiz executa tarefa com a ferramenta ensinada.",
                "O professor-aprendiz tenta executar uma tarefa usando a ferramenta "
                "recém-ensinada pelo aluno.",
                "Peça ao aluno que observe e corrija a execução em tempo real.",
                "Prática supervisionada pelo aluno",
                12,
            ),
            _card(
                "Feedback Mútuo",
                "Refletir o que o professor aprendeu e como o aluno liderou.",
                "Reflexão sobre a experiência: o que o professor aprendeu e como "
                "o aluno se sentiu no papel de liderança.",
                "Registre 1 aprendizado de cada lado no quadro.",
                "Reflexão mútua da inversão",
                8,
            ),
        ],
    },
    "criativa_mapa_polaridades": {
        "nome": "Mapa de polaridades",
        "categoria": "CRIATIVAS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Identificação do Dilema",
                "Escolher um conflito com duas forças complementares.",
                "Escolha de um conflito que não tem resposta única, mas duas forças "
                "complementares (ex: Tradição vs. Inovação; Liberdade vs. Disciplina).",
                "Evite dilemas do tipo \"certo × errado\" — precisa ser polaridade real.",
                "Dilema em duas forças",
                8,
            ),
            _card(
                "Mapeamento dos Lados Positivos",
                "Listar benefícios de focar no Polo A e no Polo B.",
                "A turma lista os benefícios de focar exclusivamente no Polo A e, "
                "em seguida, no Polo B.",
                "Use post-its por polo — facilita mover e comparar depois.",
                "Benefícios de cada polo",
                10,
            ),
            _card(
                "Mapeamento dos Lados Negativos",
                "Listar prejuízos e excessos de cada polo.",
                "A turma lista os prejuízos e excessos que ocorrem quando se foca "
                "demais no Polo A ou no Polo B.",
                "Peça exemplos concretos da escola/turma — evita generalidade.",
                "Excessos de cada polo",
                10,
            ),
            _card(
                "Sinais de Alerta",
                "Definir indicadores de queda para o lado negativo.",
                "Definição de indicadores de que a situação está caindo "
                "para o lado negativo de uma das polaridades.",
                "Transforme sinais em observáveis (o que se vê/ouve na sala).",
                "Indicadores de desequilíbrio",
                10,
            ),
            _card(
                "Plano de Equilíbrio",
                "Criar estratégias para obter benefícios dos dois polos.",
                "Criação de estratégias práticas para obter os benefícios "
                "de ambos os polos simultaneamente.",
                "Cada estratégia deve dizer quem faz o quê e quando.",
                "Estratégias de equilíbrio",
                12,
            ),
        ],
    },
    "criativa_veja_pense_pergunte_crie": {
        "nome": "Rotina Veja · Pense · Pergunte · Crie",
        "categoria": "CRIATIVAS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Veja",
                "Listar fatos literais do estímulo, sem julgamentos.",
                "Exposição de um estímulo visual (obra de arte, gráfico, vídeo curto). "
                "O aluno lista apenas fatos literais do que está vendo, sem julgamentos.",
                "Interrompa adjetivos (bonito/feio) — só o que é observável.",
                "Observação literal do estímulo",
                8,
            ),
            _card(
                "Pense",
                "Elaborar hipóteses sobre significado e intenção.",
                "O aluno elabora hipóteses sobre o que a imagem significa, "
                "quem a fez e qual a intenção por trás dela.",
                "Peça \"eu penso que… porque…\" — amarra hipótese à evidência.",
                "Hipóteses sobre o estímulo",
                10,
            ),
            _card(
                "Pergunte",
                "Levantar dúvidas despertadas pela observação.",
                "Levantamento de dúvidas e questionamentos que a observação despertou "
                "(\"O que eu gostaria de saber sobre isso?\").",
                "Selecione 2–3 perguntas poderosas da turma para a etapa Crie.",
                "Perguntas geradas pela observação",
                10,
            ),
            _card(
                "Crie",
                "Elaborar resposta criativa baseada nas três etapas anteriores.",
                "Elaboração de uma resposta criativa (um parágrafo, um desenho, "
                "uma pergunta de pesquisa) baseada nas três etapas anteriores.",
                "A criação deve citar algo do Veja/Pense/Pergunte — senão vira desconectado.",
                "Produção criativa ancorada",
                15,
            ),
        ],
    },
    "criativa_sala_invertida": {
        "nome": "Sala de aula invertida",
        "categoria": "CRIATIVAS",
        "contexto_execucao": "misto",
        "cards": [
            _card(
                "Curadoria",
                "Disponibilizar conteúdo expositivo antes da aula.",
                "O professor disponibiliza o conteúdo expositivo "
                "(vídeo, podcast, texto curto) no ambiente virtual antes da aula.",
                "Limite a 10–15 minutos de consumo — material longo vira abandono.",
                "Material prévio curto e claro",
                0,
            ),
            _card(
                "Consumo Autônomo",
                "Estudar o material no próprio ritmo, anotando dúvidas.",
                "O aluno estuda o material no seu próprio ritmo, em casa, anotando dúvidas.",
                "Peça 1 dúvida escrita como ingresso da aula presencial.",
                "Estudo prévio com dúvidas anotadas",
                0,
            ),
            _card(
                "Checagem de Compreensão",
                "Quiz rápido nos primeiros minutos da aula presencial.",
                "Nos primeiros 5 minutos da aula presencial, aplicação de um quiz rápido "
                "para checar quem absorveu o conceito.",
                "Use o quiz para agrupar quem precisa de reforço imediato.",
                "Quiz de entrada (5 min)",
                5,
            ),
            _card(
                "Atividade de Alto Nível",
                "Usar o tempo da aula para problemas, debates e projetos.",
                "O tempo da aula é usado para resolução de problemas complexos, "
                "debates e projetos com mediação do professor.",
                "Proíba retomar a exposição longa — a aula é para prática mediada.",
                "Prática complexa em sala",
                30,
            ),
            _card(
                "Fechamento",
                "Compilar erros comuns e reforçar conceitos.",
                "O professor compila os erros mais comuns vistos na atividade prática "
                "e reforça os conceitos.",
                "Mostre padrões de erro, não nomes de alunos.",
                "Reforço pelos erros da prática",
                10,
            ),
        ],
    },
    "criativa_world_cafe": {
        "nome": "World Café",
        "categoria": "CRIATIVAS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Preparação do Ambiente",
                "Organizar mesas pequenas com folha grande e canetas.",
                "Organização da sala em pequenos grupos (4 a 5 alunos), como mesas de um café, "
                "cada uma com uma folha grande e canetas.",
                "Ambiente informal ajuda — música baixa e mesas espalhadas funcionam.",
                "Mesas de café prontas",
                5,
            ),
            _card(
                "Primeira Rodada",
                "Debater a pergunta geradora e registrar na folha.",
                "O professor lança uma pergunta geradora e os grupos debatem e "
                "desenham/escrevem suas ideias na folha por 15 minutos.",
                "Uma pergunta clara por rodada — múltiplas perguntas dispersam.",
                "Debate e registro na mesa",
                15,
            ),
            _card(
                "Troca de Mesas (Polinização)",
                "Anfitrião fica; demais migram para outras mesas.",
                "Um aluno (o \"anfitrião\") fica na mesa. Os demais mudam para mesas diferentes.",
                "Escolha anfitriões que sintetizam bem — treine o resumo em 1 minuto.",
                "Rotação com anfitrião fixo",
                5,
            ),
            _card(
                "Segunda Rodada",
                "Anfitrião resume e novos membros acrescentam ideias.",
                "O anfitrião resume o que foi falado na rodada anterior e os novos membros "
                "adicionam novas ideias sobrepostas às antigas.",
                "Ideias novas vão em outra cor — mostra a polinização visualmente.",
                "Sobreposição de ideias",
                15,
            ),
            _card(
                "Colheita",
                "Plenária com insights mais poderosos de cada mesa.",
                "Plenária final onde cada anfitrião compartilha os insights "
                "mais poderosos que surgiram em sua mesa.",
                "Limite a 2 insights por mesa — força síntese.",
                "Plenária de insights",
                10,
            ),
        ],
    },
    "agil_canvas_mania": {
        "nome": "Canvas Mania",
        "categoria": "ÁGEIS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Seleção do Framework",
                "Escolher o modelo visual adequado ao objetivo.",
                "Escolha do modelo visual adequado "
                "(Canvas de Projeto, Business Model Canvas, Mapa de Empatia).",
                "Mostre o canvas em branco primeiro e explique cada bloco em 30s.",
                "Canvas certo para o objetivo",
                5,
            ),
            _card(
                "Divisão de Equipes",
                "Agrupar alunos em torno do Canvas impresso ou projetado.",
                "Alunos se agrupam em torno do Canvas impresso em tamanho A3 "
                "ou projetado em quadro branco.",
                "3–5 por canvas — grupos maiores travam o preenchimento.",
                "Equipes no canvas",
                5,
            ),
            _card(
                "Preenchimento Iterativo",
                "Preencher blocos com post-its (uma ideia por post-it).",
                "Uso de post-its para preencher os blocos do Canvas. A regra é: "
                "uma ideia por post-it, para facilitar a mudança.",
                "Proíba textos longos no post-it — só palavras-chave.",
                "Post-its móveis por bloco",
                20,
            ),
            _card(
                "Análise Sistêmica",
                "Analisar conexões entre blocos do canvas.",
                "O professor guia a turma para analisar as conexões "
                "(\"Se mudarmos esse post-it aqui, como afeta o resto do quadro?\").",
                "Faça a pergunta de impacto em voz alta a cada mudança relevante.",
                "Conexões entre blocos",
                12,
            ),
            _card(
                "Defesa do Modelo",
                "Apresentar a estrutura lógica criada pelo grupo.",
                "Apresentação da estrutura lógica criada pelo grupo para a sala.",
                "Peça 90 segundos: problema → solução → evidência no canvas.",
                "Pitch do canvas",
                10,
            ),
        ],
    },
    "agil_eduscrum": {
        "nome": "Método inove4us",
        "categoria": "ÁGEIS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Formação de Equipes",
                "Criar grupos autogerenciáveis com Scrum Master aluno.",
                "Criação de grupos autogerenciáveis, com definição do papel do Scrum Master "
                "(aluno líder facilitador).",
                "Scrum Master facilita — não manda. Deixe isso explícito.",
                "Times com Scrum Master",
                8,
            ),
            _card(
                "Planejamento do Sprint",
                "Selecionar do Backlog o que será feito na aula.",
                "A equipe analisa o Backlog (lista de tarefas do projeto) "
                "e seleciona o que será feito na aula atual.",
                "Limite o sprint ao tempo da aula — corte o que não cabe.",
                "Backlog → compromisso do sprint",
                10,
            ),
            _card(
                "Atualização do Quadro (Kanban)",
                "Posicionar cards em Para Fazer / Fazendo / Feito.",
                "Posicionamento dos post-its ou cards nas colunas: "
                "\"Para Fazer\", \"Fazendo\", \"Feito\".",
                "Só 1 card \"Fazendo\" por pessoa — reduz multitarefa.",
                "Quadro Kanban visível",
                7,
            ),
            _card(
                "Reunião em Pé (Stand-up)",
                "Checagem rápida do progresso e dos bloqueios.",
                "No início da aula, perguntas rápidas: O que fiz ontem? "
                "O que farei hoje? O que está me travando?",
                "Cronometre 60–90s por pessoa — stand-up não é reunião longa.",
                "Stand-up de 3 perguntas",
                10,
            ),
            _card(
                "Retrospectiva",
                "Avaliar o processo de trabalho da equipe.",
                "Ao fim de um ciclo, avaliação do processo de trabalho da equipe "
                "(o que funcionou bem e o que precisa melhorar).",
                "Exija 1 ação de melhoria para o próximo sprint.",
                "Retro com ação concreta",
                10,
            ),
        ],
    },
    "agil_hackathons": {
        "nome": "Hackathon",
        "categoria": "ÁGEIS",
        "contexto_execucao": "misto",
        "cards": [
            _card(
                "Lançamento do Desafio",
                "Apresentar problema urgente com prazo estrito.",
                "Apresentação de um problema urgente da escola ou comunidade, "
                "com prazo estrito (ex: 4 horas ou 2 dias).",
                "O prazo é parte da pedagogia — torne-o visível (cronômetro).",
                "Desafio urgente com deadline",
                10,
            ),
            _card(
                "Ideação",
                "Brainstorm rápido e divisão de tarefas no grupo.",
                "Brainstorming rápido para desenhar a solução base e divisão de tarefas "
                "no grupo (design, pesquisa, apresentação).",
                "Feche a ideação com 1 ideia escolhida — não deixe 5 ideias pela metade.",
                "Ideia única e papéis",
                15,
            ),
            _card(
                "Maratona de Desenvolvimento",
                "Construir o protótipo em foco total.",
                "Tempo de foco total onde os alunos constroem o protótipo "
                "da solução (digital ou físico).",
                "Proíba reabrir o briefing — a maratona é construir, não redesenhar o problema.",
                "Construção sob pressão de tempo",
                90,
            ),
            _card(
                "Mentoria Volante",
                "Professores circulam para destravar ideias técnicas.",
                "Professores atuam como consultores, circulando entre os grupos "
                "para destravar ideias técnicas.",
                "Limite a 3 minutos por mesa — mentoria volante, não aula particular.",
                "Consultoria rápida nas mesas",
                20,
            ),
            _card(
                "Pitch",
                "Apresentar a solução em 3 a 5 minutos para banca.",
                "Apresentação cronometrada (3 a 5 minutos) da solução "
                "para uma banca avaliadora.",
                "Critérios públicos na parede: problema, solução, evidência, próximo passo.",
                "Pitch cronometrado para banca",
                20,
            ),
        ],
    },
    "agil_mapeamento_mental": {
        "nome": "Mapa mental",
        "categoria": "ÁGEIS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Núcleo",
                "Colocar o tema central no meio da página.",
                "Escrever ou desenhar o tema central no exato meio de uma página "
                "em branco (papel ou software).",
                "Tema em 1–3 palavras — núcleo longo vira parágrafo, não mapa.",
                "Tema central no meio",
                5,
            ),
            _card(
                "Ramos Principais",
                "Criar categorias/grandes tópicos a partir do centro.",
                "Puxar linhas grossas a partir do centro para representar as categorias "
                "ou grandes tópicos do assunto.",
                "Comece com 4–6 ramos — demais fragmenta a visão.",
                "Categorias principais",
                10,
            ),
            _card(
                "Ramos Secundários",
                "Detalhar palavras-chave a partir dos ramos principais.",
                "Adicionar linhas mais finas saindo dos ramos principais, "
                "contendo palavras-chave e detalhes específicos.",
                "Só palavras-chave — frase completa mata o mapa.",
                "Detalhes em palavras-chave",
                15,
            ),
            _card(
                "Conexões Visuais",
                "Ligar conceitos com setas, cores e ícones.",
                "Uso de setas, cores e ícones para ligar conceitos que se relacionam "
                "de lados opostos do mapa.",
                "Peça pelo menos 2 conexões cruzadas explícitas.",
                "Ligações entre ramos",
                10,
            ),
            _card(
                "Revisão",
                "Usar o mapa para testar retenção e revisar depois.",
                "Leitura do mapa mental para testar a retenção do conteúdo "
                "e facilitar revisões futuras.",
                "Peça que um colega explique o mapa do outro em 60s.",
                "Retenção via mapa",
                10,
            ),
        ],
    },
    "agil_pedagogia_extrema": {
        "nome": "Dupla piloto e navegador",
        "categoria": "ÁGEIS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Trabalho em Pares",
                "Um executa (piloto) e o outro revisa (navegador).",
                "Dois alunos dividem uma única tarefa, caderno ou computador. "
                "Um executa (\"piloto\") e o outro revisa criticamente (\"navegador\").",
                "Troque piloto/navegador a cada ciclo — evita hierarquia fixa.",
                "Par piloto–navegador",
                8,
            ),
            _card(
                "Teste Primeiro (Test-Driven)",
                "Definir critérios de avaliação antes de executar.",
                "Antes de iniciar a atividade, os alunos definem ou recebem "
                "os critérios exatos de como o trabalho será avaliado.",
                "Critérios visíveis na mesa — sem critério, o ciclo curto não funciona.",
                "Critérios antes da execução",
                7,
            ),
            _card(
                "Ciclos Curtos",
                "Quebrar o trabalho em entregas de 15–20 minutos.",
                "O trabalho é quebrado em entregas muito pequenas "
                "(a cada 15 ou 20 minutos).",
                "Toque o sino/cronômetro — o ritual do ciclo é pedagógico.",
                "Entregas em timebox curto",
                20,
            ),
            _card(
                "Feedback Imediato",
                "Avaliar a entrega curta na hora.",
                "O professor avalia a entrega curta na hora, impedindo que o aluno "
                "acumule erros estruturais.",
                "Feedback em 1 minuto por dupla: manter / cortar / corrigir.",
                "Avaliação imediata da entrega",
                10,
            ),
            _card(
                "Refatoração",
                "Melhorar o trabalho antes do próximo ciclo.",
                "O aluno melhora o trabalho imediatamente baseado no feedback "
                "antes de seguir para o próximo ciclo.",
                "Não avance de ciclo sem a correção mínima aplicada.",
                "Correção imediata pós-feedback",
                10,
            ),
        ],
    },
    "imersiva_aprendizagem_jogos": {
        "nome": "Aprendizagem baseada em jogos",
        "categoria": "IMERSIVAS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Seleção e Alinhamento",
                "Escolher jogo cuja mecânica simule o conteúdo.",
                "O professor escolhe um jogo (tabuleiro, cartas ou digital) "
                "cuja mecânica simule o conteúdo a ser aprendido.",
                "Se a mecânica não espelha o conteúdo, é só recreação — troque o jogo.",
                "Jogo alinhado ao conteúdo",
                5,
            ),
            _card(
                "Explicação das Regras",
                "Deixar claras regras de pontuar, vencer e interagir.",
                "Regras claras de como pontuar, vencer e interagir durante o jogo.",
                "Faça 1 rodada de exemplo em 2 minutos antes do jogo real.",
                "Regras explícitas",
                8,
            ),
            _card(
                "Imersão no Gameplay",
                "Jogar com decisões autônomas e consequências.",
                "Os alunos jogam ativamente, tomando decisões autônomas "
                "e lidando com as consequências dentro do jogo.",
                "Resista a interromper — anote pontos para o debriefing.",
                "Gameplay ativo",
                20,
            ),
            _card(
                "Debriefing (Descompressão)",
                "Pausar para analisar estratégias que funcionaram.",
                "O passo mais importante. Pausa no jogo para perguntar: "
                "\"Quais estratégias funcionaram? Por quê?\".",
                "Sem debriefing, o jogo não vira aprendizagem — proteja este tempo.",
                "Análise das estratégias",
                12,
            ),
            _card(
                "Conexão Teórica",
                "Ligar a experiência do jogo aos conceitos da disciplina.",
                "O professor faz a ponte entre a experiência vivida no jogo "
                "e os conceitos formais da disciplina.",
                "Escreva no quadro: jogada → conceito correspondente.",
                "Ponte jogo → teoria",
                10,
            ),
        ],
    },
    "imersiva_simulacoes": {
        "nome": "Simulação",
        "categoria": "IMERSIVAS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Construção do Cenário",
                "Criar ambiente fictício ou histórico rico em detalhes.",
                "Criação de um ambiente fictício ou histórico rico em detalhes "
                "(ex: Assembleia da ONU, mercado financeiro).",
                "Entregue 1 página de briefing por cenário — demais vira sobrecarga.",
                "Cenário detalhado",
                8,
            ),
            _card(
                "Distribuição de Papéis",
                "Dar a cada aluno personagem com objetivos e limites.",
                "Cada aluno recebe um personagem com objetivos, limites "
                "e interesses específicos.",
                "Objetivos secretos aumentam o realismo — use com cuidado ético.",
                "Papéis com interesses claros",
                7,
            ),
            _card(
                "Interação e Negociação",
                "Agir no papel para alcançar objetivos.",
                "Os alunos agem dentro de seus papéis, interagindo uns com os outros "
                "para alcançar seus objetivos.",
                "Circule e anote decisões-chave para a avaliação crítica.",
                "Negociação em papel",
                20,
            ),
            _card(
                "Fatores Surpresa",
                "Inserir crises que forçam adaptação rápida.",
                "O professor insere \"crises\" ou novas variáveis no meio da simulação "
                "para forçar adaptação rápida.",
                "1–2 surpresas bastam — excesso vira caos sem aprendizagem.",
                "Crises controladas",
                8,
            ),
            _card(
                "Avaliação Crítica",
                "Sair do personagem e analisar decisões à luz da teoria.",
                "Os alunos saem de seus personagens e analisam as decisões tomadas "
                "à luz da teoria da disciplina.",
                "Ritual explícito de \"sair do papel\" antes da análise.",
                "Análise pós-personagem",
                12,
            ),
        ],
    },
    "imersiva_vivencia_multissensorial": {
        "nome": "Vivência Multissensorial",
        "categoria": "IMERSIVAS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Design do Ambiente",
                "Preparar estímulos intencionais no espaço físico.",
                "O professor prepara o espaço físico com estímulos intencionais: "
                "trilha sonora, iluminação, aromas e objetos táteis.",
                "Todo estímulo deve ter intenção pedagógica — corte o decorativo vazio.",
                "Ambiente sensorial intencional",
                5,
            ),
            _card(
                "Quebra de Padrão",
                "Entrar no ambiente com percepção maximizada.",
                "Os alunos entram no ambiente em silêncio ou com os olhos vendados "
                "para maximizar a percepção sensorial.",
                "Combine regras de segurança e consentimento antes de vendas/silêncio.",
                "Entrada com percepção ampliada",
                8,
            ),
            _card(
                "Condução Narrativa",
                "Guiar a experiência por história, leitura ou exploração tátil.",
                "O professor guia a experiência através de contação de histórias, "
                "leitura imersiva ou exploração tátil.",
                "Fale pouco e pause — o ambiente também \"fala\".",
                "Narrativa/condução sensorial",
                15,
            ),
            _card(
                "Registro Sensível",
                "Registrar emoções e sensações provocadas.",
                "O aluno escreve, desenha ou relata as emoções e sensações físicas "
                "que a experiência provocou.",
                "Aceite desenho/áudio — nem todo registro precisa ser texto.",
                "Registro das sensações",
                12,
            ),
            _card(
                "Ancoragem",
                "Ligar o sentido físico ao conteúdo curricular.",
                "Conexão lógica entre o que foi sentido fisicamente "
                "e o conteúdo curricular abordado.",
                "Peça a frase: \"Senti X → isso ilustra o conceito Y\".",
                "Ponte senso → currículo",
                10,
            ),
        ],
    },
    "analitica_chatbots": {
        "nome": "Chatbot pedagógico",
        "categoria": "ANALÍTICAS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Definição de Persona",
                "Definir a identidade do bot.",
                "Os alunos definem a identidade do bot "
                "(ex: Um bot de Machado de Assis, ou um bot de fórmulas matemáticas).",
                "Persona clara evita respostas genéricas depois.",
                "Persona do bot",
                8,
            ),
            _card(
                "Árvore de Decisão",
                "Mapear perguntas prováveis e respostas programadas.",
                "Mapeamento visual das perguntas prováveis dos usuários "
                "e das respostas programadas do bot.",
                "Comece com 8–12 caminhos — árvore gigante não fecha na aula.",
                "Fluxo de perguntas e respostas",
                12,
            ),
            _card(
                "Programação ou Simulação",
                "Construir o bot em No-Code ou simular em papel.",
                "Construção do bot em plataformas No-Code (sem código) "
                "ou simulação do fluxo em papel.",
                "Se não houver ferramenta digital, o fluxo em papel vale como protótipo.",
                "Build do fluxo do bot",
                15,
            ),
            _card(
                "Teste de Estresse (Turing)",
                "Outros grupos tentam achar furos nas respostas.",
                "Alunos de outros grupos tentam usar o bot criado "
                "para encontrar \"furos\" ou respostas erradas.",
                "Peça que os testadores anotem a pergunta que quebrou o bot.",
                "Teste adversarial do bot",
                10,
            ),
            _card(
                "Refinamento",
                "Ajustar a base para cobrir perguntas falhas.",
                "Ajuste da base de conhecimento do bot para cobrir "
                "as perguntas que ele não soube responder.",
                "Refinamento mínimo: 3 furos corrigidos e retestados.",
                "Correção da base de conhecimento",
                10,
            ),
        ],
    },
    "analitica_dog_or_cat": {
        "nome": "Classificação de imagens (treino e teste)",
        "categoria": "ANALÍTICAS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Coleta de Dados",
                "Reunir fotos em duas categorias para treino.",
                "Os alunos reúnem dezenas de fotos divididas em duas categorias "
                "(ex: folhas saudáveis vs. folhas com praga).",
                "Equilibre quantidade por categoria — dataset torto enviesa o modelo.",
                "Dataset em duas categorias",
                10,
            ),
            _card(
                "Treinamento do Modelo",
                "Treinar o algoritmo em plataforma educativa de IA.",
                "Inserção das imagens em uma plataforma de IA educativa "
                "(como Teachable Machine) para treinar o algoritmo.",
                "Demonstre 1 treino completo antes de liberar as equipes.",
                "Treino do classificador",
                12,
            ),
            _card(
                "Teste de Acurácia",
                "Testar com imagens inéditas.",
                "Os alunos apresentam imagens inéditas para a câmera/sistema "
                "para ver se a IA acerta a categoria.",
                "Separe imagens de teste que NÃO entraram no treino.",
                "Validação com imagens novas",
                10,
            ),
            _card(
                "Análise de Viés",
                "Discutir erros da máquina e causas no dataset.",
                "Discussão sobre os erros da máquina "
                "(ex: \"Ela errou porque todas as folhas saudáveis que usamos tinham fundo branco\").",
                "Force a pergunta: o erro é do modelo ou dos dados?",
                "Viés e erros do modelo",
                10,
            ),
            _card(
                "Debate Ético",
                "Refletir sobre decisões algorítmicas na vida real.",
                "Reflexão sobre como algoritmos tomam decisões na vida real "
                "e os perigos de dados enviesados.",
                "Traga 1 caso real curto (crédito, recrutamento, saúde) para ancorar.",
                "Ética de dados e algoritmos",
                10,
            ),
        ],
    },
    "analitica_extrato_participacao": {
        "nome": "Extrato de participação",
        "categoria": "ANALÍTICAS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Estabelecimento da Economia",
                "Definir atitudes que geram pontos/moedas.",
                "Definição clara de quais atitudes (fazer perguntas, ajudar colega, "
                "entregar no prazo) geram \"moedas\" ou \"pontos\".",
                "Publique a tabela de pontuação — economia invisível não engaja.",
                "Regras da economia de participação",
                8,
            ),
            _card(
                "Registro Contínuo",
                "Anotar pontuação durante as aulas de forma visível.",
                "O professor (ou um aluno líder) anota a pontuação durante as aulas "
                "usando planilhas, apps ou um quadro visível.",
                "Registre na hora — pós-aula a memória falha e gera contestação.",
                "Registro visível e contínuo",
                10,
            ),
            _card(
                "Emissão do Extrato",
                "Entregar relatório de ganhos e perdas ao aluno.",
                "Entrega de um relatório quinzenal/mensal para que o aluno veja "
                "onde ganhou e onde perdeu pontos.",
                "Extrato individual privado — ranking público pode humilhar.",
                "Extrato individual",
                8,
            ),
            _card(
                "Feedback Direcionado",
                "Usar o extrato para apontar comportamentos a melhorar.",
                "O professor usa o extrato para mostrar ao aluno exatamente "
                "quais comportamentos precisam melhorar.",
                "1 comportamento prioritário por conversa — evita lista acusatória.",
                "Feedback comportamental baseado em dados",
                12,
            ),
            _card(
                "Recompensas",
                "Trocar pontos por benefícios acadêmicos claros.",
                "Troca dos pontos por benefícios acadêmicos "
                "(dica em prova, prorrogação de prazo, escolha de tema de trabalho).",
                "Recompensas devem ser pedagógicas, não só brindes.",
                "Troca por benefícios acadêmicos",
                8,
            ),
        ],
    },
    "analitica_ia_generativa": {
        "nome": "IA generativa na aula",
        "categoria": "ANALÍTICAS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Estruturação do Prompt",
                "Ensinar comandos detalhados (Papel, Tarefa, Contexto, Formato).",
                "Ensino de como criar comandos detalhados "
                "(Papel, Tarefa, Contexto e Formato) para a IA (ex: ChatGPT).",
                "Modele 1 prompt ruim × 1 bom no quadro antes da prática.",
                "Prompt estruturado",
                10,
            ),
            _card(
                "Geração e Iteração",
                "Gerar e ajustar o comando se o resultado for superficial.",
                "O aluno pede para a IA gerar um texto, código ou imagem "
                "e ajusta o comando se o resultado for superficial.",
                "Exija pelo menos 2 iterações documentadas do mesmo pedido.",
                "Iteração do prompt",
                12,
            ),
            _card(
                "Curadoria Crítica",
                "Marcar alucinações, vieses e clichês no resultado.",
                "O aluno analisa o resultado gerado, marcando alucinações (erros), "
                "vieses ou clichês.",
                "Use destaque colorido: erro / viés / clichê.",
                "Crítica do output da IA",
                10,
            ),
            _card(
                "Edição Humana",
                "Reescrever com voz própria e validar fontes.",
                "O aluno reescreve e melhora o conteúdo gerado, "
                "adicionando voz própria e validando fontes.",
                "Sem edição humana, a entrega não conta como aprendizagem.",
                "Reescrita autoral",
                12,
            ),
            _card(
                "Entrega Transparente",
                "Entregar histórico: prompt, geração e alterações humanas.",
                "Apresentação do trabalho final contendo o histórico: "
                "\"Qual foi o prompt\", \"O que a IA gerou\" e \"Como o aluno alterou\".",
                "Torne a transparência critério de avaliação, não opcional.",
                "Rastreabilidade prompt → edição",
                8,
            ),
        ],
    },
    "analitica_mapa_calor": {
        "nome": "Mapa de calor",
        "categoria": "ANALÍTICAS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Coleta de Indicadores",
                "Levantar dados quantitativos do contexto analisado.",
                "Levantamento de dados quantitativos "
                "(notas em exames, evasão, ocorrências disciplinares em áreas da escola).",
                "Defina 1 pergunta analítica antes de coletar — dado sem pergunta vira ruído.",
                "Dados quantitativos do contexto",
                10,
            ),
            _card(
                "Definição de Escala Cromática",
                "Associar valores a cores (ex.: verde × vermelho).",
                "Associação de valores a cores "
                "(ex: Verde para alto desempenho, Vermelho para zonas críticas).",
                "A escala deve ser compartilhada e fixa antes da plotagem.",
                "Legenda cromática",
                8,
            ),
            _card(
                "Plotagem dos Dados",
                "Aplicar cores sobre o espaço/planilha analisada.",
                "Aplicação das cores sobre o espaço analisado "
                "(pode ser uma planilha de notas ou a planta baixa da escola).",
                "Faça a plotagem em silêncio primeiro — depois interpreta.",
                "Visualização colorida dos dados",
                12,
            ),
            _card(
                "Análise Espacial/Visual",
                "Identificar padrões nas zonas coloridas.",
                "Identificação imediata de padrões: "
                "\"Por que as notas estão todas vermelhas neste tópico específico da matéria?\".",
                "Peça hipóteses escritas antes de discutir — evita opinião precipitada.",
                "Padrões nas zonas críticas",
                12,
            ),
            _card(
                "Intervenção Focada",
                "Direcionar recursos às zonas vermelhas.",
                "Direcionamento de recursos ou aulas de revisão exclusivamente "
                "para as \"zonas vermelhas\" identificadas no mapa.",
                "Feche com 1 ação concreta por zona vermelha.",
                "Ação nas zonas críticas",
                10,
            ),
        ],
    },
    "analitica_rag": {
        "nome": "Pesquisa com fontes confiáveis (RAG)",
        "categoria": "ANALÍTICAS",
        "contexto_execucao": "sala",
        "cards": [
            _card(
                "Construção da Base (Retrieval)",
                "Separar repositório fechado de fontes confiáveis.",
                "O professor ou os alunos separam um repositório fechado de PDFs, "
                "artigos e apostilas confiáveis sobre o tema.",
                "Qualidade da base > quantidade — 3–5 fontes boas bastam na aula.",
                "Base fechada de documentos",
                10,
            ),
            _card(
                "Indexação",
                "Carregar documentos em ferramenta de IA com leitura restrita.",
                "Os documentos são carregados em uma ferramenta de IA "
                "que permite leitura de arquivos fechados.",
                "Confirme que a ferramenta está limitada aos arquivos carregados.",
                "Indexação dos documentos",
                8,
            ),
            _card(
                "Interrogação Restrita",
                "Perguntar à IA só com base nos documentos fornecidos.",
                "Os alunos fazem perguntas complexas para a IA com a regra estrita "
                "de buscar a resposta apenas nos documentos fornecidos.",
                "Se a IA inventar fora da base, marque como falha do processo.",
                "Perguntas restritas à base",
                12,
            ),
            _card(
                "Verificação de Lastro",
                "Cruzar citações com página/parágrafo do PDF original.",
                "O aluno verifica as citações geradas pela IA cruzando "
                "com a página e o parágrafo do PDF original.",
                "Sem lastro verificado, a resposta não entra no relatório final.",
                "Auditoria das citações",
                12,
            ),
            _card(
                "Síntese Autoral",
                "Produzir texto humano com informações validadas pela base RAG.",
                "Produção de um artigo ou relatório humano usando as informações "
                "mastigadas e validadas pela base de conhecimento RAG.",
                "A síntese deve citar documento + página — não só \"a IA disse\".",
                "Relatório autoral com lastro",
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
