# ACTIONFINANCE_REV_003 — Revalidação do analista

Data: 29/09/2026. Resultado: **correções substancialmente confirmadas; aceite final pendente de R3 residual**. Sem PRM_004.

## Evidência examinada

Relatório v0.2, TitleService, sessão/API/frontend, referências aos testes de domínio e XML locais, capturas mobile de contas a pagar/formulário e desktop de detalhe. Revisão estática e visual; não executei novas operações financeiras nem testes no navegador. Os XML das suítes confirmam 7 testes unitários e 25 de integração, sem falhas/erros/skips. Um XML adicional de TitleOperationsIT aparece no diretório target; não foi contado novamente. Vitest 11/11 e auditorias npm são resultados informados pelo Cursor.

## Revalidação dos pontos anteriores

| Item | Parecer |
| --- | --- |
| R1 | Correção identificada: hash de update inclui ID; replay usa TitleView armazenado após autorização. Testes específicos acrescentados. |
| R2 | Correção identificada: atualização de rascunho com register confirma atomicamente e grava CONFIRMED. |
| R3 | Parcial: sessão notifica React e geração é validada após leitura do corpo. Escrita congelada existe, mas nem toda perda de resposta preserva a chave; ver abaixo. |
| R4 | Problema visual anterior corrigido nas capturas inspecionadas: mobile usa cartões, campos cabem na largura e não há corte lateral aparente. Medição 360=360 atribuída ao relatório. |
| R5 | Melhorias visíveis em datas, moeda, filtro, busca e diálogos. Não equivalem a certificação completa de acessibilidade; não há novo bloqueio visual nas telas inspecionadas. |
| R6 | REPEATABLE_READ identificado no serviço de listagem, com teste adicional de consistência. |

## R3 residual — perda de conexão ainda pode duplicar criação

Em frontend/src/api.ts, request só converte AbortError em erro com timeout=true. Uma rejeição de fetch por conexão interrompida é relançada como erro comum. No formulário, App.tsx/TitleFormPage.submit preserva pending apenas para timeout ou STALE; no else limpa pending.current. Confirmar/cancelar também descartam sua operação pendente quando o erro não tem essas classificações.

Cenário: POST chega ao servidor e é confirmado no banco; a resposta se perde por queda da conexão; fetch rejeita. A interface descarta a chave e uma nova tentativa gera outra. A idempotência do servidor não consegue reconhecer a repetição com chave diferente, podendo criar outro título. É uma conclusão do caminho de código, não um incidente observado no runtime.

**Correção necessária no mesmo PRM_003:** distinguir falha definitiva de negócio de resultado de escrita desconhecido. Em erro de transporte, perda da resposta, resposta inválida ou erro de servidor que não garanta rollback, preservar chave, rota, corpo e contexto da operação. A interface deve oferecer repetição segura, sem reclassificar resultado desconhecido como rejeição. Não reenviar operação de contexto anterior ao trocar empresa/usuário. Não basta capturar apenas AbortError.

Provar com teste em que a primeira escrita é efetivada, mas a resposta é simuladamente perdida como falha de transporte: repetir usa a mesma chave/corpo e termina com um único título/evento de criação. Cobrir também preservação em confirmar/cancelar. Erro de validação definitivo deve permitir correção dos campos, sem bloquear o usuário em pedido inválido.

Reexecutar testes afetados e gates existentes após a alteração. Não refazer o produto, migrations ou itens já resolvidos apenas para este ajuste. Entregar adendo no relatório com evidência e parar para aceite; não iniciar PRM_004.

## Ajuste de UX sem bloqueio de integridade

As referências compactas das duas contas exibidas na captura mobile são ambas PAG-11111111. Compactação apenas pelo prefixo não distingue estes registros. Mostrar prefixo e trecho final ou outro rótulo compacto distinguível, preservando copiar/ver a referência completa. Não alterar os IDs persistidos para resolver apresentação.

## Deliberação

A estrutura de dados e o fluxo funcional são aproveitados. O bloqueio restante desta revisão é específico: recuperação segura de escrita após perda de resposta. O parecer anterior permanece histórico; este documento registra o avanço e não reabre os seis itens integralmente. O relato de start/stop com metadados completos é aceito como evidência do executor, sem afirmar reexecução independente pelo analista.
