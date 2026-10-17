# Agentes da ISA na primeira versão de uso

17/10/2026. Complemento do 004. Cartões continuam reservados ao 005.

A inteligência faz parte da entrega da ISA. A pessoa registra o fato sem escolher categoria; depois a ISA organiza o lançamento e ajuda a interpretar o planejamento. A versão candidata é 0.6.0, baseline 1.3.

## Modelo e execução

O modelo encontrado no PanelDX e no Chamelleon foi us.anthropic.claude-sonnet-4-20250514-v1:0, região us-east-1. Uma chamada real foi recusada pela AWS porque essa versão chegou ao fim de vida. O sucessor us.anthropic.claude-sonnet-4-5-20250929-v1:0 respondeu ao ensaio. A ISA usa esse Claude via Amazon Bedrock, com papel IAM próprio, sem chave de outro produto.

O agente de categorização recebe descrição reduzida e direção. Usa o catálogo da ISA, preserva a correção humana e pede ajuda quando a finalidade não pode ser deduzida. PIX não é categoria. A natureza econômica ainda não identificada precisa de conferência; o agente não transforma aplicação, transferência ou resgate em consumo.

O agente de planejamento recebe os compromissos informados, disponibilidade, reservas e cenários previamente calculados. Explica a situação, propõe um próximo passo e pode destacar uma alternativa existente. Datas e valores da comparação são calculados pelo motor. Custos de adiamento e concordância do credor continuam desconhecidos até informação própria. Escolher um plano não altera vencimento e não realiza pagamento.

A ajuda aparece em Início e Planejar. Inclui pergunta livre curta, avaliação de gasto adicional, fontes, histórico e as ações Ver depois, Não me ajuda e Guardar como plano escolhido. O registro novo deixa de pedir categoria. A edição mantém a possibilidade de corrigir.

## Persistência e recuperação

Schema 4 acrescenta ai_job, índices e o registro de coordenação ai_quota. Jobs registram proprietário, finalidade, fotografia das premissas, hash, estado, início, fim, falha e resultado. Sugestões continuam em suggestion e decisões em suggestion_event, com origem ia-real, modelo, prompt, identificador de execução e uso de tokens.

Um worker da própria aplicação executa a fila persistida. O navegador não é a fila. Trabalho interrompido fica registrado como falha recuperável, sem fingir sucesso. Categorias usam comparação com o estado original antes de gravar; a resposta tardia não substitui a correção humana. Análise desatualizada fica histórica e não pode criar novo plano escolhido. Repetir a escolha é idempotente.

Fila, premissas e histórico entram nas cópias e na exclusão por proprietário. A tarefa da cópia diária deve usar a imagem desta entrega para incluir a tabela nova. Não armazenar credenciais nem raciocínio interno do modelo.

## Limites do piloto

Padrão operacional: até 30 chamadas por pessoa por dia e 100 no serviço por dia, 2.000 tokens de saída por chamada e contexto limitado. Lotes de categoria têm até 12 itens. Esses limites controlam volume, não representam cotação de custo. Falha de IA não desfaz o lançamento. A indisponibilidade fica visível.

O envio ao Bedrock usa apenas os dados necessários, com remoção de e-mails e identificadores longos das descrições. Não envia arquivo original, senha ou token. Registros e perguntas são dados não confiáveis, não instruções do sistema. O servidor valida catálogo, IDs, opções e propriedade.

## Conferência

Os dois agentes foram chamados de verdade no PostgreSQL isolado com registros fictícios. Padaria foi categorizada como Alimentação sem alteração de valor. No planejamento, o motor preservou o ponto mínimo de menos R$ 100,00 antes da renda. A alternativa e o plano escolhido ficaram persistidos, sem alterar o vencimento.

Foram executados 26 testes de motor, HTTP, identidade, persistência e IA. A falha inicial do teste de mensagem foi atualizada para a nova redação; a rodada seguinte passou. Há avisos anteriores de recursos de teste não fechados. O navegador percorreu a análise real e a escolha do plano com identidade sintética; a conferência em 390 px usou emulação.

## Referências de integração

A integração usa a operação Converse e a saída de ferramenta, validada pela aplicação. A permissão necessária é bedrock:InvokeModel, restrita ao perfil e aos modelos associados. Referência: [Converse na documentação da AWS](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html).
