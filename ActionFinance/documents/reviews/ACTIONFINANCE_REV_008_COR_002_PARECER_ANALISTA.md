# ACTIONFINANCE_REV_008_COR_002 — Parecer do analista

Data: 30/09/2026. Revisão estática do relatório, serviço, repositório, V11, JSON de interrupção/recuperação e capturas desktop/mobile. Não reexecutei os testes.

## Decisão

Aceite parcial do recorte: comprovada pelas evidências a consulta com orquestração AF → Spider → borda simulada, inclusive indisponibilidade e recuperação sem atalho ao provider. Não equivale a integração viva com ActionHub Pay, prontidão de comandos financeiros ou aprovação de produção.

Aceitos neste complemento: identidade estável da tentativa, correlação por tentativa, transações curtas fora do transporte, V11 incremental sem pareamento inventado do legado, distinção visual entre observação e tentativa, e preservação da observação na indisponibilidade.

A evidência spider-interrupt-recovery.json registra contador da borda 11 → 11 enquanto a Spider estava indisponível e 11 → 12 após sua volta, com capacidade LOOKUP_ACTIONHUB_PAYMENT. A recuperação terminou em divergência/revisão; isso comprova retomada do transporte, não confirmação financeira.

## Único bloqueio de código: recuperação concorrente

ExternalLookupService.recoverStale decide recuperar com base em um ExternalLookupView lido antes da transação. JdbcExternalOperationRepository.markRecovered atualiza por operação e last_attempt_outcome = STARTED, sem conferir last_attempt_id nem o prazo de expiração no UPDATE.

Interleaving possível: GET lê tentativa A antiga; outra consulta inicia B e passa a ser last_attempt_id; o GET recupera A e markRecovered marca B como UNAVAILABLE. A função também avança last_attempt_at para o instante da recuperação. Quando B responde, updateIfVersion pode recusá-la pelo predicado de data. A tentativa nova pode, portanto, ser descartada por uma recuperação destinada à antiga.

O teste de recuperação sequencial relatado não cobre esse caso. Aceite integral pendente somente da correção e comprovação abaixo.

## Instrução ao Cursor — complemento do mesmo COR_002

1. Tornar a recuperação condicional à tentativa efetivamente expirada: conferir identidade, estado e limite temporal no banco, com política de concorrência coerente entre operação e tentativa. Não atualizar uma tentativa nova com base em snapshot antigo.
2. Garantir que recuperação e chegada tardia de resposta tenham resultado consistente: uma tentativa já encerrada como RECOVERED não pode alterar a observação silenciosamente enquanto sua linha de auditoria permanece dizendo que nada foi aplicado. Verificar o resultado da conclusão e adotar transação/lock/predicados adequados, sem manter lock durante HTTP.
3. Acrescentar IT determinístico em PostgreSQL com barreiras: leitura de A expirada → início de B → recuperação de A → resposta de B. B deve continuar rastreável e sua resposta válida deve ser processada pela política normal. Cobrir também disputa entre recuperação e conclusão da mesma tentativa. Não usar sleeps como única sincronização.
4. Executar os ITs afetados. Como V11 e grants mudaram desde o último gate integral, executar uma vez o verify completo do AF no estado final e registrar resultados sem skips. Não repetir Hub, frontend ou Spider se permanecerem inalterados.
5. Acrescentar o resultado ao REV_008_COR_002, preservar evidências anteriores e copiar este parecer para documents/reviews. Parar para aceite; não iniciar PRM_009.

## Observações de UX sem reabertura do layout

As capturas mostram o painel legível e a separação dos estados. O aviso de falha usa fundo verde: em futura alteração desse feedback, usar apresentação de atenção/indisponibilidade, preservando o texto de observação anterior mantida. Não é bloqueio deste recorte.

Os fullPage exibem cabeçalho fixo no meio do documento. Isso não basta para concluir defeito no layout, pois pode decorrer da posição de rolagem na captura. Futuras evidências visuais devem incluir viewport e fullPage normalizado no topo; não alterar o shell por causa dessa imagem isolada.

## Limites preservados

FORWARD/Hub real não exercitado. Spider ainda em RAM. Sem dinheiro real, baixa automática, Panne, deploy, commit ou push. PRM_007 continua separado, com invalidação de sessões no restore pendente. Não recriar RDS nem solicitar login por este complemento.
