# PRM_009_ADENDO_002 — Fiscalização do retorno

Parecer do analista: aceite permanece NÃO. Revisão estática do REV_009_ADENDO_002 e da implementação local de spider-pay-lookup.js; nenhuma consulta independente ao banco público foi executada pelo analista.

## 1. Classificação REAL ainda insuficiente

classifyOrder marca REAL quando existe mp_payment_id, payment_request_id ou prefixo amount:, desde que não haja sandbox/test_order=true. Esses campos identificam canal/referências; isoladamente não comprovam ambiente real. Uma transação de teste também pode possuir essas referências. Portanto, os nove registros estão identificados na origem operacional conforme relato, mas sua classificação REAL não está independentemente comprovada.

Rastrear como o checkout de produção e suas credenciais/configuração distinguem operação real de teste. Documentar a evidência por registro ou por proveniência confiável aplicável ao conjunto. Não fabricar flags faltantes, não assumir teste nem real por ausência. Se a evidência for inconclusiva, registrar classificação indeterminada em área de revisão segregada e fora dos totais operacionais, conservando vínculo à origem. Não substituir a integração por novos seeds. Operação real também não significa que houve pagamento: preservar PENDING/CANCELLED.

A listagem atualmente filtra classifyOrder depois do LIMIT e calcula nextCursor pelo número de itens filtrados. Garantir que itens excluídos/indeterminados não encerrem prematuramente a leitura e ocultem elegíveis posteriores. Provar página com registros excluídos no início e elegíveis adiante. Documentar exclusões/revisões, em vez de perdê-las silenciosamente.

## 2. Importação permanece por concluir

Prosseguir com V13, binding confirmado lojadepaes, imagens e integração pública dentro da autorização vigente, incorporando a correção acima antes de afirmar que a importação é REAL. Não há motivo para pedir novo login enquanto as dependências publicadas não estiverem prontas. Depois comprovar item a item o percurso e a persistência, sem INSERT direto no Finance.

## 3. Monitor e preservação histórica

Persistência memory demonstra vulnerabilidade a restart, mas não identifica, sozinha, a causa de desaparecimento da execução afm citada. Correlacionar criação, eventos, restart/deploy, engine de destino e filtro de empresa. Registrar causa comprovada ou hipótese pendente, sem converter configuração em prova causal.

Não concluir que retenção durável exige obrigatoriamente novo serviço faturável. Levantar opções já disponíveis, com isolamento, permissões, volume, retenção e custo estimado. Não compartilhar schema de outro produto nem criar recurso sem aprovação. Apresentar recomendação concreta se houver decisão de custo necessária; continuar as demais tarefas independentes.

Para a canônica original, a busca apenas em artefatos versionados não esgota o requisito. Inventariar fontes pertinentes e acessíveis: logs/exportações/arquivos de evidência/backups e stores existentes, com escopo e proteção dos dados. Não prometer que contenham o original. Relatar fontes consultadas e resultado. Se não recuperável, informar perda e lacunas; nenhuma nova execução satisfaz a preservação original sem decisão explícita do proprietário.

Existirem TransactionWorkspace e ExecutionJourney no código não comprova preservação visual/funcional pública. Fazer comparação com a referência anterior, fases expandidas e detalhes, como já exigido. Não reduzir o Monitor nem fabricar eventos.

## Continuidade

Copiar este parecer para documents/reviews e referenciá-lo no relatório. Não declarar aceitos os quatro estados. A autorização para concluir a integração real permanece válida; não abrir PRM_010 nem tratar pendências como dispensa concedida pelo proprietário.
