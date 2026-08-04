-- Léxico pedagógico alinhado ao inove4us do professor:
-- EduScrum → Método inove4us | sprint → tarefa | squad → equipe
-- Pré-requisito: 006 (catálogo).

BEGIN;

UPDATE public.school_metodologias_catalogo
SET
    nome = 'Método inove4us',
    descricao = 'Organizar a turma em equipes com aluno facilitador e acompanhar as tarefas na mesa.',
    passos_execucao = $json$[
      {
        "titulo": "Formação de equipes",
        "objetivo": "Criar equipes autogerenciáveis com aluno facilitador.",
        "mecanica_passo_a_passo": "A turma forma equipes e define o aluno facilitador de cada uma.",
        "como_executar_detalhado": "A turma forma equipes e define o aluno facilitador de cada uma (liderança que facilita, não manda).",
        "dica_de_facilitacao": "Deixe claro: o facilitador ajuda o grupo a avançar — não decide sozinho.",
        "duracao_minutos": 8
      },
      {
        "titulo": "Planejamento da tarefa",
        "objetivo": "Escolher, na lista de tarefas do projeto, o que cabe nesta aula.",
        "mecanica_passo_a_passo": "A equipe olha a lista de tarefas do projeto e escolhe o que será feito na aula.",
        "como_executar_detalhado": "A equipe olha a lista de tarefas do projeto e escolhe o que será feito na aula.",
        "dica_de_facilitacao": "Limite a tarefa ao tempo da aula — corte o que não cabe.",
        "duracao_minutos": 10
      },
      {
        "titulo": "Atualização da mesa",
        "objetivo": "Colocar as tarefas em Para Fazer, Fazendo e Pronto.",
        "mecanica_passo_a_passo": "A equipe posiciona as tarefas nas colunas Para Fazer, Fazendo e Pronto.",
        "como_executar_detalhado": "A equipe posiciona as tarefas nas colunas Para Fazer, Fazendo e Pronto.",
        "dica_de_facilitacao": "Só uma tarefa em Fazendo por pessoa — reduz dispersão.",
        "duracao_minutos": 7
      },
      {
        "titulo": "Checagem rápida em pé",
        "objetivo": "Ver o que avançou e o que está travando.",
        "mecanica_passo_a_passo": "No início da aula, cada um responde em poucos segundos: o que fiz, o que farei, o que trava.",
        "como_executar_detalhado": "No início da aula, cada um responde em poucos segundos: o que fiz, o que farei, o que trava.",
        "dica_de_facilitacao": "Cronometre 60 a 90 segundos por pessoa — não vira reunião longa.",
        "duracao_minutos": 10
      },
      {
        "titulo": "Retrospectiva",
        "objetivo": "Avaliar como a equipe trabalhou e melhorar a próxima tarefa.",
        "mecanica_passo_a_passo": "Ao fim do ciclo, a equipe registra o que funcionou e o que precisa melhorar.",
        "como_executar_detalhado": "Ao fim do ciclo, a equipe registra o que funcionou e o que precisa melhorar.",
        "dica_de_facilitacao": "Peça uma ação concreta de melhoria para a próxima tarefa.",
        "duracao_minutos": 10
      }
    ]$json$::jsonb,
    updated_at = CURRENT_TIMESTAMP
WHERE codigo = 'agil_eduscrum'
   OR nome = 'EduScrum';

COMMIT;
