# PRM_009_INC_002 — Retomada do Monitor após perda de foco

Data: 02/10/2026. Complemento do incidente existente; sem novo ciclo funcional.

## Fatos e limites da evidência

O proprietário observa falha no Monitor depois de perder foco por um instante. Investigar esse comportamento separadamente do INVALID_PAYLOAD do contrato 1.4 já corrigido conforme relato do executor.

A prova VPC AF → Spider → Hub com READY e nove reviews comprova essa chamada; não comprova persistência pelo serviço AF, sessão no navegador ou deep link no Monitor.

Na leitura estática do analista, MonitorShell.jsx agenda nova consulta dos eventos selecionados após sucesso não terminal, mas seu catch apenas registra o erro: uma falha transitória pode interromper esse acompanhamento até seleção/refresh. Não há retomada explícita por visibility/focus nesse componente. useExecutionPolling também encerra após cinco falhas e reinicia estado ao mudar suas dependências. Essas observações são pontos de investigação, não prova de que perder foco seja a causa raiz pública.

## Diagnóstico e correção

Reproduzir em navegador a perda/retorno de foco e troca de aba, mantendo execução selecionada. Registrar horário, visibilidade, sessão HTTP, resposta da API, cancelamento e ciclo de polling, sem cookies/tokens. Distinguir suspensão/throttling do browser, AbortError deliberado, falha de rede, 401, 403, 404 e expiração real do evento.

Corrigir o ciclo de atualização para retomar após erro transitório e retorno à aba, com timeout, backoff limitado e sem requisições sobrepostas. Não acumular listeners/timers nem produzir rajada ao voltar. Abort por desmontagem/cancelamento esperado não deve aparecer como falha de negócio.

Preservar execução selecionada, filtros, busca, fases expandidas e última observação válida durante falha transitória. Mostrar que os dados estão desatualizados e a última atualização efetiva, sem anunciar “Ao vivo” como se a consulta tivesse sucesso. Não transformar falha em lista vazia nem fabricar estados.

Pausa manual deve ser respeitada: retornar ao foco não a cancela. Sessão expirada deve oferecer reautenticação clara preservando destino seguro, sem loop de refresh e sem apagar estado temporário de login por chamadas de API. Revogação/acesso negado não autoriza continuar exibindo conteúdo sensível em cache; aplicar política de autorização correspondente. Não alterar cookies ou concessões para mascarar falha de polling.

Não repetir consulta de detalhe terminal sem necessidade; garantir nova seleção e atualização manual coerentes. Manter formato anterior do Monitor, fluxo canônico e fases reais do Finance.

## Provas

Testar unidade/componentes para falha transitória→recuperação, AbortError, retorno visível, pausa manual, resposta atrasada, ausência de duplicação de polling e sessão expirada. Executar navegador real alternando abas, minimizando/restaurando e interrompendo brevemente apenas a rede do navegador de teste. Não derrubar engine pública compartilhada.

Confirmar no público, após publicação do candidato testado: mesma execução e fases permanecem selecionadas, atualização retoma, não surge falso vazio, deep link continua resolvendo. Não aceitar apenas disparo sintético de evento focus como prova do comportamento real do browser.

## Contrato PRODUCTION e fechamento

Preservar o teste que reproduz INVALID_PAYLOAD por PRODUCTION e executar regressão dos ambientes anteriores e bindings não autorizados. Aceitar o novo valor no schema não deve ampliar acesso a qualquer app/empresa. Separar falha de contrato, provider e transporte no diagnóstico interno do AF.

Concluir a importação autenticada da Loja e o Monitor da mesma execução. Se a sessão humana for indispensável, solicitar somente essa intervenção quando os pré-requisitos estiverem verificados; não usar a necessidade de login para deixar o defeito de foco sem correção.

Salvar este complemento em documents/prompts e acrescentar evidências ao REV_009_INC_002. Registrar causa comprovada, mudanças, testes e versões. Não declarar teste de importação só porque a chamada direta do satélite retornou READY. Autorização de reparo vigente; aceite permanece NÃO; sem PRM_010, dados inventados, APPLY histórico ou nova cobrança.
