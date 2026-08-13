# Proposta — nomes e descrições do catálogo (39 metodologias)

**Status:** só validação — **não aplicado** no banco.  
**Fonte dos “atuais”:** produção School (`school_metodologias_catalogo`), 2026-08-13.  
**Regra:** manter `codigo` estável; alterar só `nome` e `descricao`. Passos (`passos_execucao`) ficam intactos.

## Como validar

Para cada linha, marque na coluna **Decisão**:
- `OK` — aceitar sugestão
- `AJUSTAR` — escrever o texto final na coluna Observação
- `MANTER` — ficar com o atual

Prioridade de revisão humana (se o tempo for curto): linhas com **Prioridade = Alta**.

---

## Tabela proposta

| Prioridade | codigo | categoria | nome atual | nome sugerido | descrição atual (resumo) | descrição sugerida | Decisão | Observação |
|---|---|---|---|---|---|---|---|---|
| Alta | `agil_eduscrum` | Agilidade | Método inove4us | **Método inove4us** *(manter — marca)* | Organizar a turma em equipes… | Organização da turma em equipes com aluno facilitador, quadro de tarefas e ciclos curtos de planejamento–execução–retrospectiva. Substitui o léxico genérico de Scrum por termos do Método inove4us, sem mudar a mecânica da aula. | | |
| Alta | `imersiva_vivencia_multissensorial` | Contextuais | Vivência Metodologia imersiva Multissensorial | **Vivência Multissensorial** | sala — Preparar estímulos… | Aula que usa o espaço físico (som, luz, tato, aroma, objetos) de forma intencional para ancorar o conteúdo. O aluno vive o tema com o corpo e os sentidos e depois traduz a experiência em registro e ligação curricular. | | |
| Alta | `analitica_learning_analytics` | Dedutivas | Metodologia analítica da Aprendizagem | **Análise da Aprendizagem** | sala — Definir que decisão… | Uso ético e leve de dados da própria turma (autoavaliação, tempo, erros comuns) para tomar **uma** decisão pedagógica. Evita dashboard vazio: começa pela pergunta, termina numa intervenção mensurável. | | |
| Alta | `analitica_chatbots` | Dedutivas | Chatbots | **Chatbot como tutor** | sala — Definir a identidade… | A turma desenha e usa um chatbot com papel claro (tutor, personagem ou especialista) para praticar perguntas, feedback e diálogo sobre o conteúdo — com limites éticos e revisão humana. | | |
| Alta | `analitica_rag` | Dedutivas | RAG | **Pesquisa com fontes confiáveis (RAG)** | sala — Separar repositório… | Os alunos consultam um repositório fechado de fontes escolhidas pelo professor e pedem à IA respostas **só** com base nesses materiais. Ensina citação, checagem e distinção entre inventar e recuperar. | | |
| Média | `agil_canvas_mania` | Agilidade | Canvas Mania | Canvas Mania | sala — Escolher o modelo… | A turma escolhe e preenche um canvas visual (negócio, proposta de valor, persona etc.) para organizar ideias complexas em blocos claros, antes de escrever texto longo. | | |
| Média | `agil_elevator_pitch` | Agilidade | Discurso de Elevador | **Pitch de elevador** | sala — Alinhar os 4 pilares… | Treino de comunicação curta e persuasiva: gancho, problema, solução e pedido — em poucos minutos, com feedback da turma. | | |
| Média | `agil_hackathons` | Agilidade | Hackathons | Hackathon | misto — Apresentar problema… | Maratona com problema urgente e prazo estrito. A pressão de tempo faz parte da pedagogia: idear, dividir tarefas e entregar um protótipo apresentável. | | |
| Média | `agil_mapeamento_mental` | Agilidade | Mapeamento mental | **Mapa mental** | sala — Colocar o tema… | Organização visual do conhecimento a partir de um núcleo central, com ramos principais e secundários — útil para estudar, planejar ou sintetizar uma aula. | | |
| Média | `agil_minute_paper` | Agilidade | Minute Paper | Minute Paper | sala — Focar a turma… | Fechamento rápido (1–2 perguntas de alto valor) para capturar o que ficou claro, o que travou e o que o professor precisa retomar na próxima aula. | | |
| Média | `agil_pecha_kucha` | Agilidade | Pecha Kucha | Pecha Kucha | sala — Forçar estrutura… | Formato de apresentação cronometrada (20 slides × 20 segundos) que obriga síntese visual e ritmo — ideal para mostrar projeto sem monólogo longo. | | |
| Média | `agil_pedagogia_extrema` | Agilidade | Pedagogia Extrema | **Programação em dupla (piloto e navegador)** | sala — Um executa… | Dois alunos no mesmo posto: um executa (piloto) e o outro orienta e revisa (navegador), trocando papéis. Reduz erro solitário e torna o raciocínio visível. | | |
| Baixa | `gamificacao_de_conteudo` | Contextuais | Gamificação de Conteúdo | Gamificação de conteúdo | sala — Tornar explícitos… | O próprio conteúdo vira jogo: missões, desafios e “vitória” amarrados ao que se precisa aprender — não só pontos cosméticos. | | |
| Baixa | `gamificacao_estrutural` | Contextuais | Gamificação Estrutural | Gamificação estrutural | sala — Tornar explícitos… | Camada de jogo sobre a rotina da turma (XP, vidas, níveis, ranking ético) para sustentar engajamento ao longo de várias aulas, sem mudar o conteúdo-base. | | |
| Baixa | `imersiva_aprendizagem_jogos` | Contextuais | Aprendizagem Baseada em Jogos | Aprendizagem baseada em jogos | sala — Escolher jogo… | Usa um jogo cuja mecânica já simula o conteúdo (regras, estratégia, cooperação). O jogo é o meio; a reflexão pós-jogo fecha a aprendizagem. | | |
| Baixa | `imersiva_escape_room` | Contextuais | Escape Room | Escape room pedagógico | sala — Engajar a turma… | Missão em que a turma “escapa” resolvendo enigmas do conteúdo em tempo limitado — colaboração e aplicação, não só lembrança. | | |
| Baixa | `imersiva_jogos_serios_3d` | Contextuais | Jogos Sérios com Blocos 3D | Jogos sérios em ambiente 3D | sala — Alinhar objetivo… | Sessão em ambiente 3D / blocos com contrato claro: objetivo de aprendizagem, papéis (piloto, copiloto, analista) e evidência do que conta como sucesso. | | |
| Baixa | `imersiva_roleplaying` | Contextuais | Roleplay | Roleplay (dramatização de papéis) | sala — Distribuir papéis… | Alunos assumem papéis com objetivos claros (às vezes conflitantes) para ensaiar decisão, empatia e argumentação em contexto. | | |
| Baixa | `imersiva_simulacoes` | Contextuais | Simulações | Simulação | sala — Criar ambiente… | Recria um ambiente fictício ou histórico rico o suficiente para os alunos tomarem decisões e verem consequências — ponte entre teoria e prática. | | |
| Média | `analitica_diagnostico_coletivo` | Dedutivas | Diagnóstico Coletivo | Diagnóstico coletivo | sala — Externalizar sintomas… | A turma mapeia sintomas e padrões de um problema comum sem caça a culpados — base para decisão coletiva e próximos passos. | | |
| Média | `analitica_dog_or_cat` | Dedutivas | Dog or Cat: Reconhecimento de Imagens | **Classificação de imagens (treino e teste)** | sala — Reunir fotos… | Introdução prática a reconhecimento de padrões: separar exemplos, “treinar” critérios e testar com imagens novas — analogia viva de como modelos classificam. | | |
| Média | `analitica_extrato_participacao` | Dedutivas | Extrato de Participação | Extrato de participação | sala — Definir atitudes… | Torna visível e negociável o que conta como participação (atitudes, entregas, contribuições), com critérios claros em vez de achismo na nota. | | |
| Baixa | `analitica_ia_generativa` | Dedutivas | Inteligência Artificial Generativa | IA generativa na aula | sala — Ensinar comandos… | Ensina a pedir bem à IA (papel, tarefa, contexto, formato), criticar a resposta e usá-la como rascunho — não como resposta final sem revisão. | | |
| Baixa | `analitica_mapa_calor` | Dedutivas | Mapa de Calor | Mapa de calor | sala — Levantar dados… | Visualiza onde há concentração de atenção, erro ou engajamento (da turma ou do material) para priorizar o que revisar. | | |
| Baixa | `analitica_trilhas_adaptativas` | Dedutivas | Trilhas de Aprendizagem | Trilhas adaptativas | sala — Posicionar cada… | Posiciona alunos/grupos em percursos diferentes conforme o ponto de partida, sem estigma — cada um avança no próximo desafio certo. | | |
| Baixa | `aprendizagem_baseada_em_casos` | Indutivas | Aprendizagem Baseada em Casos | Aprendizagem baseada em casos | sala — Apresentar um caso… | Parte de um caso humano concreto (não abstrato). A turma analisa, discute e decide com base em evidências do caso. | | |
| Baixa | `criativa_abordagem_problematizadora` | Indutivas | Abordagem Problematizadora | Abordagem problematizadora | misto — Conduzir a turma… | Leva a turma a observar um recorte da realidade, nomear o problema e construir caminhos de ação — ensino ancorado no contexto. | | |
| Baixa | `criativa_aprendizagem_equipes` | Indutivas | Aprendizagem Baseada em Equipes | Aprendizagem baseada em equipes (TBL) | sala — Garantir preparo… | Ciclo com preparo individual, garantia de prontidão e aplicação em equipe — a aula rende porque ninguém chega “em branco”. | | |
| Baixa | `criativa_aprendizagem_maker` | Indutivas | Aprendizagem Maker | Aprendizagem maker | sala — Definir o artefato… | Aprender fazendo: a turma define um artefato, esboça, prototipa e testa — o produto concreto carrega o conteúdo. | | |
| Baixa | `criativa_coaching_reverso` | Indutivas | Coaching Reverso | Coaching reverso | sala — Selecionar tema… | Alunos com maior fluência no tema ensinam/orientam os demais (e o professor), invertendo quem “segura o microfone”. | | |
| Baixa | `criativa_design_thinking_express` | Indutivas | Design Thinking | Design Thinking express | sala — Coletar dores… | Ciclo curto de empatia–definição–ideação–protótipo–teste, cabível em uma ou poucas aulas, com dores reais da turma ou da comunidade. | | |
| Baixa | `criativa_mapa_polaridades` | Indutivas | Mapa de Polaridades | Mapa de polaridades | sala — Escolher um conflito… | Torna visível um conflito com duas forças complementares (não um vilão único), para negociar tensões e decisões maduras. | | |
| Média | `criativa_narrativas_transmidia` | Indutivas | Narrativas Transmídia em Rotação por Estações | **Narrativa transmídia (estações)** | misto — Definir o mundo… | A história se espalha por estações/mídias diferentes; a turma rota e completa o mundo narrativo enquanto trabalha o conteúdo. | | |
| Média | `criativa_painel_diversidade` | Indutivas | Painel da Diversidade de Perspectivas | **Painel de perspectivas** | sala — Tornar visíveis… | Torna visíveis os pontos de vista presentes — e os ausentes — na turma, para enriquecer análise e incluir vozes que normalmente não entram. | | |
| Baixa | `criativa_pbl_problemas` | Indutivas | Aprendizagem Baseada em Problemas | Aprendizagem baseada em problemas (PBL) | sala — Apresentar um caso… | Caso complexo sem solução óbvia: a turma formula hipóteses, busca informação e defende um caminho — processo > resposta pronta. | | |
| Baixa | `criativa_pbl_projetos` | Indutivas | Aprendizagem Baseada em Projetos | Aprendizagem baseada em projetos | misto — Apresentar um desafio… | Desafio engajador que exige um produto ou solução final ao longo do tempo, com marcos e entrega pública. | | |
| Baixa | `criativa_sala_invertida` | Indutivas | Sala de Aula Invertida | Sala de aula invertida | misto — Disponibilizar conteúdo… | Conteúdo expositivo antes da aula; o tempo presencial vira prática, dúvidas e aplicação com o professor presente. | | |
| Média | `criativa_veja_pense_pergunte_crie` | Indutivas | Rotina Veja-Pense-Pergunte-Crie | Rotina Veja · Pense · Pergunte · Crie | sala — Listar fatos… | Rotina de pensamento em quatro tempos: observar fatos, interpretar, perguntar e criar — disciplina o olhar antes da opinião. | | |
| Baixa | `criativa_world_cafe` | Indutivas | World Café | World Café | sala — Organizar mesas… | Rodadas em mesas pequenas com registro coletivo; as ideias migram de mesa em mesa e a sala constrói síntese compartilhada. | | |

---

## Resumo das mudanças de nome (só onde muda de verdade)

| codigo | de | para |
|---|---|---|
| `imersiva_vivencia_multissensorial` | Vivência Metodologia imersiva Multissensorial | Vivência Multissensorial |
| `analitica_learning_analytics` | Metodologia analítica da Aprendizagem | Análise da Aprendizagem |
| `analitica_chatbots` | Chatbots | Chatbot como tutor |
| `analitica_rag` | RAG | Pesquisa com fontes confiáveis (RAG) |
| `agil_elevator_pitch` | Discurso de Elevador | Pitch de elevador |
| `agil_hackathons` | Hackathons | Hackathon |
| `agil_mapeamento_mental` | Mapeamento mental | Mapa mental |
| `agil_pedagogia_extrema` | Pedagogia Extrema | Programação em dupla (piloto e navegador) |
| `analitica_dog_or_cat` | Dog or Cat: Reconhecimento de Imagens | Classificação de imagens (treino e teste) |
| `criativa_narrativas_transmidia` | Narrativas Transmídia em Rotação por Estações | Narrativa transmídia (estações) |
| `criativa_painel_diversidade` | Painel da Diversidade de Perspectivas | Painel de perspectivas |
| `agil_eduscrum` | Método inove4us | *(manter)* |

Demais nomes: capitalização / clarificação leve ou manter.

---

## Próximo passo (quando validarem)

1. Vocês devolvem esta tabela com a coluna **Decisão** preenchida.  
2. Só então: migration `UPDATE` por `codigo` + ajuste do seed, **sem** alterar passos.  
3. Deploy School + smoke rápido no Editor (lista abre, nomes novos, passos iguais).

Arquivo local: `C:\Projetos\inove4us-school\docs\PROPOSTA-CATALOGO-39-NOMES-DESCRICOES.md`
