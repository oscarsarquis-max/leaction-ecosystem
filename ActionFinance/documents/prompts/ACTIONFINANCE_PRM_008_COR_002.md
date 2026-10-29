# ACTIONFINANCE_PRM_008_COR_002 — Fechamento da consulta pela Spider

## Mandato e parecer do analista

Executar somente este complemento do PRM_008. Não iniciar PRM_009. O retorno do COR_001 foi recebido, mas o aceite integral permanece pendente.

Este parecer decorre da leitura estática do REV_008_COR_001, ExternalLookupService, JdbcExternalOperationRepository, ExternalLookupRules e do roteiro Playwright. Os números de testes são evidências relatadas pelo executor; o analista não os reexecutou. Preservar as correções já entregues e os limites declarados. Não reabrir a fundação, a marca ou os fluxos financeiros aprovados.

O objetivo continua sendo comprovar a consulta: ActionFinance → Spider → provider → Spider → ActionFinance. Nenhuma chamada direta AF→Pay, criação de cobrança, payout ou baixa automática.

## 1. Identidade e recuperação das tentativas

Problema observado: ExternalLookupService cria attemptId para STARTED, mas grava o resultado com outro UUID. Todas as tentativas da operação compartilham correlationId. O relatório afirma uma linha por tentativa, mas o código produz eventos sem vínculo explícito início/fim. Além disso, o retorno booleano de updateIfVersion é ignorado.

Implementar identidade estável de tentativa. Pode ser uma linha com conclusão ou eventos vinculados por attemptId; documentar a escolha no DAT. Garantir:

- Intenção e início persistidos em transação curta antes do transporte. Nenhuma transação de banco permanece aberta durante HTTP.
- Resultado vinculado ao mesmo attemptId, distinguindo resposta recebida, aplicação à observação e descarte por concorrência/obsolescência. Não registrar aplicação bem-sucedida quando updateIfVersion não atualizou a linha.
- Conclusão da tentativa e alteração da observação em transação curta coerente. Em conflito, reler o estado e aplicar política explícita que preserve a observação válida mais recente.
- Interrupção após o início não pode deixar a consulta permanentemente apresentada como em andamento. Recuperação por prazo/estado explícito, sem presumir que houve resposta e sem disparar comando financeiro. Reconsulta manual continua disponível após nova autorização.
- Migração incremental, se necessária: não editar migrations já aplicadas nem apagar dados. Documentar o tratamento dos eventos legados que não permitem pareamento inequívoco; não inventar vínculos.

Provar em PostgreSQL: duas consultas simultâneas têm identidades distintas e resultados rastreáveis; resposta descartada não aparece como aplicada; queda após intenção persistida seguida de reinício permite recuperação; uma observação financeira anterior não é perdida. Usar interrupção controlada no ambiente isolado e conferir o banco após reinício.

## 2. Jornada de UX executada

Subir a fatia local isolada usando os scripts disponíveis, respeitando propriedade de processos e portas. Stack desligada é etapa de preparação, não conclusão da validação. Se surgir impedimento externo concreto, registrar comando, erro e dependência faltante.

Executar navegador real em 1280 e 360 px, com APIs reais da fatia e simulador explicitamente identificado. Usar dados próprios de teste. Cobrir consulta válida, referência inexistente, divergência, indisponibilidade após uma observação válida e recuperação. Para transições de estado, conservar a mesma referência e controlar a resposta na fixture; trocar a referência não prova evolução da mesma operação.

Corrigir o roteiro existente: remover esperas que engolem falhas com catch vazio e asserções que passam só porque o texto estático “Simulador” está visível. Exigir o resultado específico de cada cenário antes da captura.

A interface deve separar “última observação” de “última tentativa”, mostrar a data disponível sem inventar horário do provider e comunicar “não foi possível atualizar” sem apagar o resultado anterior. Não apresentar consulta confirmada como baixa do título. Preservar logos, tamanhos, paleta e acessibilidade aprovados. Verificar foco, ação de tentar novamente e ausência de overflow nas duas larguras.

## 3. Prova da Spider em execução

Registrar correlação e contagem de chamadas nos pontos AF, Spider e borda, sem segredos. Demonstrar seleção da capacidade LOOKUP_ACTIONHUB_PAYMENT pelo registry e retorno ao AF.

Com a borda saudável, interromper somente a Spider isolada e repetir a consulta. Provar que o contador da borda não aumentou, a tentativa ficou indisponível e a observação anterior permaneceu. Religar a Spider e demonstrar recuperação pelo mesmo caminho. Código contendo apenas spiderBaseUrl é evidência arquitetural, mas não substitui esta prova em execução.

Manter EXPERIENCE impedido de EXECUTE_CAPABILITY. Credenciais do Pay continuam fora do AF. Não alterar contratos antigos nem a infraestrutura compartilhada.

## 4. Limites e classificação

SIMULATOR comprova a fatia de orquestração, não integração viva com ActionHub Pay. FORWARD contra código real do Hub local só poderá ser declarado mediante execução e evidência próprias com dados descartáveis; não é sandbox do processador. Não condicionar o fechamento desta consulta simulada à criação de credenciais ou infraestrutura externa.

Spider em RAM permanece uma limitação explícita para futuros comandos. Este complemento não implementa fila durável, cobrança ou motor de pagamentos. Panne continua responsável pelo estoque; integração de compras permanece futura.

PRM_007 segue separado: a invalidação de sessões no restore não foi comprovada antes da limpeza. Não recriar RDS, solicitar login humano nem declarar publicação por este prompt. Não fazer deploy, commit ou push.

## 5. Entrega e parada

Salvar este prompt integral em documents/prompts/ACTIONFINANCE_PRM_008_COR_002.md e o relatório em documents/reviews/ACTIONFINANCE_REV_008_COR_002.md. Atualizar índice e DAT/UX/INT somente onde o comportamento mudou.

Entregar resultados dos testes relevantes de backend e frontend, lint/build, evidências de concorrência/reinício, capturas reais 1280/360 e registro da interrupção/recuperação da Spider. Rodar regressão Spider/Hub se esses componentes forem alterados. Distinguir executado, inspeção estática e não executado; não reutilizar capturas antigas como prova atual.

Relatar migrations, contagem e vínculo das tentativas, estado final da stack e limitações restantes. Parar para o aceite do analista. Não emitir nem iniciar o prompt seguinte.
