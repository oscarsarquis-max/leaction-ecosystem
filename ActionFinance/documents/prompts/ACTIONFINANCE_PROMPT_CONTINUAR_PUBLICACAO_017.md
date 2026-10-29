# Continuar a publicação autorizada dos cadastros

Documento independente para o Cursor. ACTIONFINANCE_PROMPT_CONTINUAR_PUBLICACAO_017. Data 05/10/2026.

## A autorização vigente

O proprietário já instruiu: “por favor providencie, mas quero isso em producao logo”. O Prompt 016 traduziu essa instrução em execução da cópia protegida, ensaio, migração e publicação desta fatia após verificações satisfatórias.

O relatório 015 e o pedido de cópia foram escritos sob a restrição anterior. Sua afirmação de que “falta um sim do proprietário” não deve continuar sendo tratada como bloqueio de autorização genérica. Preserve o histórico, mas registre no novo relatório a instrução posterior. Não peça ao proprietário novamente o mesmo sim.

Execute como agente responsável pela tarefa, pelos mecanismos operacionais existentes. Não confunda autorização com disponibilidade de acesso: se não houver papel de leitura, credencial operacional ou destino protegido, identifique exatamente esse impedimento. Não peça segredos pelo chat nem contorne controles.

## O que aproveitar do ciclo 015

O relatório registra identificação da imagem anterior por digest e JAR, execução contra V19 e preservação de documento/claim após edição. Use essa evidência de rollback, sem reiniciar o ensaio se os artefatos e pressupostos não mudaram. Preserve o aviso real de Flyway. A opção de recuperação continua sendo a versão web anterior testada, sem desfazer schema ou apagar escritas posteriores.

O ensaio sintético do procedimento não substitui a cópia real. O manifesto de 25 arquivos é ponto de partida; antes do build, confira se cobre as dependências e configurações relevantes. O working tree mistura mudanças alheias: não as inclua silenciosamente na imagem. Produza artefatos reproduzíveis da candidata de cadastros, preservando o trabalho alheio, e registre digest e vínculo com o manifesto.

## Executar o restante e publicar

1. Obter dump consistente, somente leitura, do schema actionfinance no RDS actionfinance, conta 253137917703, us-east-2. Usar o canal operacional existente. Não exportar outros bancos ou dados desnecessários.
2. Restaurar em Postgres isolado de ensaio, distinto de produção e do volume de desenvolvimento. O destino deve estar sob controle do operador autorizado e ter armazenamento protegido. Não interpretar “Docker local” como autorização para enviar dados a qualquer computador pessoal. Verificar a identidade real do destino antes de escrever. Sem infraestrutura paga nova.
3. Aplicar V14–V19 na cópia com os artefatos candidatos. Comparar IDs, vínculos, valores, contagens, permissões e integridade dos documentos. Não publicar se houver conflito não resolvido ou perda de dados. Manter dump e evidências sensíveis fora de repositório, chat e screenshots; registrar hashes e resultados agregados. Aplicar a retenção mínima necessária ao ensaio e recuperação, com destino e prazo registrados.
4. Com o ensaio satisfatório, concluir build e verificações pertinentes, backup final e publicação pelo canal vigente. Revalidar o estado efetivo do origin antes da migração. A última referência relatada é V13 e actionfinance-web:11, não uma garantia de estado atual.
5. Aplicar a migração pelo papel apropriado e publicar os componentes compatíveis desta candidata. Aguardar estabilidade e conferir schema, imagem, frontend servido e invariantes. Executar a prova autenticada possível no host público sem inserir fornecedor fictício ou confirmar CSV sintético na empresa produtiva.

Não encerrar entre as etapas para pedir autorização já concedida. Não transformar a entrega em outra rodada de planejamento. Se surgir bloqueio material, concluir o restante independente, informar a causa verificável e apresentar a menor ação necessária para resolvê-lo.

## Limites e entrega

Esta autorização não abrange restore sobre produção, perda de escritas posteriores, importação produtiva em massa, APPLY histórico de pagamentos, movimentação financeira, novas integrações ou alterações de Pay, Spider, Panne e Cognito.

Criar ACTIONFINANCE_REV_CONTINUIDADE_PUBLICACAO_017. Informar execução da cópia, identidade dos artefatos, migrations, rollout, verificações públicas e recuperação disponível. Distinguir publicado de apenas construído ou enviado ao registro. O aceite integral do produto permanece separado; isso não suspende a publicação já solicitada.

Se faltar somente autenticação humana para uma verificação pública, preparar a aba e pedir apenas o login, sem senha/MFA/cookies por mensagem. Relatar o que já está efetivamente em produção e o alcance exato da prova pendente.
