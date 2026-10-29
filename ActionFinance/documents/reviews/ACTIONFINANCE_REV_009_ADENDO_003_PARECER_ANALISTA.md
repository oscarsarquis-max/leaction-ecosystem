# PRM_009_ADENDO_003 — Parecer e continuidade obrigatória

Data: 02/10/2026. Aceite NÃO. Base: leitura do relatório do executor; testes não reexecutados pelo analista. Não autorizo APPLY histórico em nome do proprietário.

## 1. Regressão completa não foi concluída

40 testes isolados são evidência útil, mas não cobrem o funcionamento completo solicitado. Contrato/outbox, transições de assinatura, testes AF e Spider permanecem não verificados. A publicação do gateway ocorreu antes de completar esse gate; registrar a sequência corretamente e concluir as provas com prioridade.

Executar os smokes de contract-service e outbox-worker em banco descartável, com destinos controlados e prova de entrega idempotente, retry e isolamento de app. Preparar esse banco faz parte do trabalho autorizado; sua ausência inicial não dispensa o teste. Executar PayReceiptSyncIT, testes afetados da Spider e regressões dos consumidores compartilhados. Rota de preapproval existente não pode ser classificada como NÃO IMPLEMENTADA apenas por não pertencer ao checkout avulso: distinguir recurso existente não testado de recurso inexistente.

Testes de integração externa seguem em sandbox com credenciais legitimamente disponíveis. Sem transação real de teste. Se faltar acesso ao sandbox, especificar essa dependência; continuar os testes independentes. Em regressão crítica comprovada, usar a reversão segura autorizada do componente afetado, preservando dados e segurança.

## 2. Confirmado, autorizado, cobrado e pago

O relatório afirma que approved e authorized viram paid/PAID. Conferir essa equivalência no contrato oficial do provedor e no fluxo de captura realmente usado. Não classificar mera autorização ou transaction_amount de pedido cancelado/pendente como valor efetivamente pago. Preservar valor da transação observado separado de confirmação/captura, com status e fonte.

Valor pago só deve ser apresentado com semântica demonstrada. Provar isso nos testes, inclusive cartão autorizado ainda não capturado e cancelamento quando aplicáveis. Persistir live_mode comprovado não prova pagamento; são dimensões distintas.

## 3. Dry-run histórico ainda precisa de conciliação item a item

Os agregados Hub (7 PAID, 1 PENDING, 1 CANCELLED) e MP consultado (6 approved, 2 cancelled, 1 sem referência) não bastam para aprovar o reparo. Produzir matriz restrita Hub × MP por identidade, método, valor cobrado, valor observado, estado, datas/revisão, live_mode, conta de destino e proposta de campos. Identificar divergências de status explicitamente; não presumir correspondência pelos totais.

Não escrever paid_amount_cents como pago confirmado em linhas cancelled só porque transaction_amount existe. Não esconder contradições mantendo um status sem mostrar a observação divergente. Preservar fatos originais e registrar revisão. Linha sem referência permanece pendente.

Registrar também que o GET de pedido PAID agora pode atualizar a observação: “script não escreveu” não prova ausência de outras escritas concorrentes. Antes do eventual APPLY, reler/precondicionar os valores e a revisão para não sobrescrever atualização legítima posterior ao dry-run.

Manter APPLY histórico parado até apresentação dessa matriz/proposta e autorização do proprietário. Essa parada não bloqueia a importação dos registros existentes para revisão no Finance.

## 4. Autenticidade dos webhooks

A ausência de HMAC exige avaliação concreta. Consulta autenticada ao provedor ajuda a verificar o recurso, mas não demonstra, por si só, autenticidade da notificação nem todos os vínculos de autorização. Verificar a documentação oficial atual e o tipo de notificação usado. Cobrir vinculação de pagamento a pedido, app, conta recebedora e valor, replay e referências não autorizadas.

Se a validação de assinatura aplicável estiver ausente, preparar correção e regressão sem interromper notificações legítimas; não impor regra incompatível sem confirmar o mecanismo real. Não declarar esse item aprovado apenas por ser lacuna pré-existente.

## 5. Concluir as duas frentes já autorizadas

Após gates do candidato, publicar a UI administrativa com Cobrado/Pago e verificar a tela efetiva. API corrigida com frontend antigo não entrega o pedido de valores visíveis.

Concluir V13, binding lojadepaes/PRODUCTION e imagens AF/Spider. Sincronizar os nove registros existentes, ou o inventário atualizado justificado, inclusive área de revisão com valores cobrados e pago ausente quando não comprovado. Sem INSERT direto no Finance e sem depender do reparo histórico. Mostrar a execução real no Monitor público com o formato anterior preservado.

A recomendação de RDS Spider não é autorização de custo nem condição para tarefas independentes. Canônica original permanece não recuperada; nenhuma dispensa foi concedida. Sem PRM_010.

## Entrega

Copiar este parecer para documents/reviews e atualizar relatório/matriz com evidências das execuções. Devolver a jornada concluída ou impedimento externo específico, não outra lista de preparativos já autorizados. Distinguir comprovado, não verificado e bloqueado. O proprietário ainda não concedeu aceite do produto nem autorização para o APPLY histórico.
