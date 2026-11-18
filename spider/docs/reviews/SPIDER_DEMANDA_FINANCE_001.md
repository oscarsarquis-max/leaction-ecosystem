# Demanda do ActionFinance para a Spider — 001

**Origem:** conversa do ActionFinance, 09/11/2026. **Destino:** conversa da Spider.
**Base:** relato `spider/docs/reviews/SPIDER_REV_RECONCILIACAO_ROTA_FINANCE_001.md` (só leitura).
Este documento diz **o que o Finance precisa**. Como atender fica a critério da conversa da Spider.

## Rota que o Finance usa hoje
O Finance chama `POST api.spider.actionhub.com.br/v1/satellites/interactions` (contrato 1.4, `LIST_EXTERNAL_PAYMENTS`). A chamada passa pelo serviço `spider-runtime-prod` (2 tasks) e segue para `api.actionhub.com.br/.../LIST_PAYMENT_TRANSACTIONS/executions`. O Finance grava o resultado no próprio banco. É a fonte dos recebimentos reais da Loja de Pães.

## Necessidades, por prioridade

1. **Rota de produção reproduzível.** Hoje a ligação de produção dessa rota está em arquivos não commitados (`feat/spider-monitor-persistence-b`), e a imagem em execução não está amarrada a um commit. Um novo deploy a partir do Git pode desligar a rota.
   O Finance precisa de: a rota versionada no Git e a imagem de produção rastreável até um commit.

2. **Isolamento por loja.** Cada loja (empresa) é um cliente separado. O Finance precisa de garantia de que a resposta de uma chamada contém só dados da loja que pediu, inclusive no estado guardado e no Monitor.
   O Finance precisa de: confirmação documentada, ou correção, se houver ponto de mistura.

3. **Repetição sem efeito duplicado.** A idempotência da listagem está em memória por task. Com 2 tasks ou depois de um restart, a mesma chave chama o Pay de novo. Hoje o efeito é baixo, porque a operação é uma listagem e o Finance deduplica do lado dele.
   O Finance precisa de: comportamento previsível na repetição antes de usar a rota com sincronização automática periódica.

4. **Futuro, ainda sem urgência: extrato da conta Mercado Pago de cada loja.** O Finance vai precisar receber automaticamente o extrato ou relatório de liquidação da conta bancária de cada loja (no caso da Loja de Pães, o Mercado Pago), usando credenciais da própria loja e sempre isolado por loja. Hoje esse arquivo entra por upload manual de CSV.
   Será detalhado em demanda própria.

## Fora desta demanda
O Finance não pede mudança de arquitetura da Spider, nem callbacks (`callbacks.` 404 não afeta o modelo atual, em que o Finance consulta).
