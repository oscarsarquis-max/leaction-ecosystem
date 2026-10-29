# ACTIONFINANCE_REV_008 — Encerramento do analista

Data: 01/10/2026.

## Decisão

PRM_008 e corretivos COR_001/COR_002 aprovados e encerrados no recorte de consulta isolada ActionFinance → Spider → borda simulada → Spider → ActionFinance. O bloqueio de recuperação concorrente está encerrado.

Este aceite resulta de revisão estática do código e dos testes, leitura do relatório e dos artefatos de teste existentes, somadas à inspeção das evidências de execução e capturas já revisadas. O analista não reexecutou a suíte.

## Fechamento do residual

O teste recoveringExpiredAttemptDoesNotDiscardNewerStartedAttempt estabelece por barreiras a ordem solicitada: GET lê A → POST inicia B → GET recupera A → B responde. A supressão da recuperação na thread do POST é instrumento explícito do teste para isolar essa disputa. As asserções verificam A recuperada sem aplicação, identidade de B preservada e resposta de B processada como DELIVERED/REFUNDED.

A implementação relê sob lock da operação, encerra apenas tentativas abertas e expiradas e atualiza a operação com predicados de identidade da tentativa, estado e prazo. A conclusão usa o mesmo lock e verifica se a tentativa continua aberta antes de alterar a observação. O teste recoverAndCompleteSameAttemptStayConsistent cobre a disputa entre recuperação e conclusão. Transporte permanece fora da transação.

## Evidências e contagem

O executor relata gate integral mvn verify: 31 Surefire + 53 Failsafe, sem falhas, erros ou skips. ExternalLookupReliabilityIT contém os dez cenários, incluindo as duas disputas.

Na inspeção do analista, a soma de todos os XML presentes em target/surefire-reports foi 52, e em failsafe-reports foi 53, todos sem falhas/erros/skips. A pasta pode conter relatórios de execuções anteriores; essa soma não foi atribuída à execução final nem usada para substituir o total relatado de 84. Preservar o log da execução final como referência do gate e, em futuras entregas, separar artefatos por execução para evitar mistura. Essa diferença de inventário não reabre o residual funcional comprovado.

Permanecem válidas as evidências anteriores de jornada 1280/360, observação preservada na falha, identidade das tentativas e interrupção da Spider com contador do provider inalterado. Frontend, Hub e Spider não precisavam ser reexecutados neste último complemento sem alterações nesses componentes.

## Alcance do aceite

Comprovada a orquestração desta consulta pela Spider com provider simulado. Não comprovados FORWARD contra o Hub real nem sandbox do processador. Nenhuma aprovação de payout, criação de cobrança, baixa automática, idempotência durável de comando ou ativação da integração em produção.

Spider em RAM continua limitação explícita. Panne mantém a gestão do estoque; o conector de compras permanece futuro. As observações de UX sobre cor do aviso e normalização das capturas são melhorias não bloqueantes já registradas.

PRM_007 permanece separado com a invalidação de sessões restauradas pendente. Este aceite não declara publicação, não autoriza recriar RDS e não altera produção.

## Rastreio e sequência

Cursor deve copiar este parecer integral para documents/reviews/ACTIONFINANCE_REV_008_ENCERRAMENTO_ANALISTA.md e atualizar o índice e o estado do REV_008/COR_002 com referência a este aceite, preservando os relatos originais.

PRM_009 não emitido neste encerramento. Próximo recorte recomendado: consulta ao ActionHub Pay real em ambiente controlado, obrigatoriamente pela Spider, com contrato e dados de teste verificados antes da execução. O prompt seguinte será entregue separadamente.
