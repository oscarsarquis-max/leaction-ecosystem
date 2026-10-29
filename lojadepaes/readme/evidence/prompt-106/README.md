# Prompt 106 — auditoria do backoffice

29/10/2026. Diagnóstico e planejamento. Nenhuma implementação, migração, publicação ou alteração de dados operacionais.

## Conclusão

A Loja atual é uma operação de um estabelecimento, com um acesso administrativo configurado, pedido comercial, capacidade de fornada, catálogo e uma cobrança por compra via Hub Pay. Esses componentes são reaproveitáveis. Eles não separam organização, tarefa de parceiro, volume de kit, participação econômica e repasse.

Abrir acesso de parceiro, vender o kit de bruschetta como produção distribuída ou dividir o recebimento exigem decisões de negócio e capacidades que não estão no sistema examinado. A ausência de split não é falha de uma venda atual de pães. É bloqueio da expansão.

Recomendação de piloto, ainda para ratificação: a Loja continua vendedora perante o cliente; um parceiro fornece componentes embalados; a consolidação e a conferência ficam na Loja; o acerto com o parceiro é obrigação registrada, não split do Mercado Pago, até a conta comprovar a modalidade. O desenho do marketplace não está aprovado.

## O que esta fase responde

- Reaproveitar: pedido com snapshots, estados operacionais separados do pagamento, capacidade de fornada, catálogo, sessão administrativa, outbox, reconciliação e alertas financeiros da Loja.
- Melhorar na operação atual: inventário documental defasado; `GET` administrativo que grava a vitrine; imagem da Loja em execução não reinspecionada nesta auditoria.
- Impede parceiro, kit e repasse: uma conta administrativa, sem organização; pedido sem tarefa por produtor; fornada que não é lote sanitário; nenhuma participação econômica nem liquidação de parceiro; split 1:N não comprovado na conta.
- Piloto recomendado: um kit, um parceiro, consolidação na Loja, Loja como vendedora, sem liberar login de parceiro nem repasse automático.
- Decisões externas: proprietário escolhe consolidação, vendedor e política comercial; contador/jurídico escolhem o tratamento fiscal; responsável técnico valida conservação, rótulo e rastreabilidade; Mercado Pago confirma se a conta pode dividir recebimento.
- Próxima etapa, só planejamento: modelo operacional e comercial do kit. Evidências em [decisoes-para-ratificacao.md](decisoes-para-ratificacao.md) e [arquitetura-e-plano-incremental.md](arquitetura-e-plano-incremental.md).

## Escopo examinado

Código local de `C:/Projetos/lojadepaes` e do gateway em `C:/Projetos/leaction-platform`. Documentação `readme/current-state.md` e o relatório em `readme/evidence/prompt-105a/README.md`. Saúde pública da Loja. Hashes dos três arquivos do Hub no disco do servidor, com o processo em execução. Testes já existentes no banco isolado `lojadepaes_test`.

Não houve navegação administrativa, consulta SQL de produção da Loja, abertura de porta, deploy, restart, cobrança, estorno, e-mail, push ou contato com parceiro ou provedor.

## Base e hierarquia de evidência

| Fonte | O que comprova | Limite |
|---|---|---|
| Código local em 29/10/2026 | Comportamento implementado na árvore de trabalho | Pode divergir da imagem publicada |
| `GET https://lojadepaes.com.br/api/v1/health` e `/ready`, 29/10/2026 | Serviço público responde `status=ok`, `service=lojadepaes`. `/ready` executa `SELECT 1` | Não identifica imagem nem revisão Alembic |
| SSH da Loja em `52.15.107.86:22` | Tentativa com a configuração já existente | Tempo esgotado. Abrir a porta seria mudança de permissão e não foi feita. A imagem `lojadepaes:prod-20261028c` permanece a base **informada** pelo relatório de 28/10, não reinspecionada hoje |
| Hub `ubuntu@3.17.19.188`, 29/10/2026 | `amount-checkout.js` `caad9b468514341106d7c2c21dee530ddaa02188be8ea23f5628b01406ae2f4f`; `mp-webhooks.js` `3983720d936e7bbd46d102587d46c8d455efe6016ef79ebd61221e26fbd6ac1d`; `server.js` `2f2ab384625d2d34b2d3fa6dff3ca4f2007758cc2712152c2194a392980a1aaa`. Processo `node .../gateway-api/serve`, pid `591861`, início `Wed Oct 28 17:46:41 2026` | Confere o disco e o processo informado. Não relê extrato nem a habilitação de split da conta |
| `pytest` em `lojadepaes_test`, 29/10/2026, 36 passaram em 100 s | Jornadas C01–C12, pagamentos e o adendo de alerta/capacidade no código local | Prova de teste isolado. Não é carga nem produção |
| `readme/current-state.md` | Abre em 27/10/2026 com imagem `lojadepaes:prod-20261027b` e Alembic `c4d8e1f07a22` | Não descreve `prod-20261028c` nem `d5e9f2a18b33`. Não serve sozinho como inventário da execução |

## Metodologia

Inventário de rotas, modelos, workers e integrações. Cada achado separa implementação e tipo de evidência. Prioridade pelo cenário: P0 só para perda financeira, exposição ou dano operacional demonstrável agora. Ausência de capacidade de marketplace é P1 de expansão, não defeito da venda atual de pães.

## Limitações

Sem sessão administrativa e sem SQL de produção da Loja, não há contagem vigente de pedidos, prova visual das telas publicadas nem confirmação da imagem `prod-20261028c`. Não houve teste de carga, restauração de backup nem consulta à conta Mercado Pago. Volume diário não foi medido; números de crescimento ficam como hipótese.

## Índice

1. [inventario-backoffice.md](inventario-backoffice.md)
2. [matriz-capacidades-riscos.md](matriz-capacidades-riscos.md)
3. [fluxos-kit-e-estados.md](fluxos-kit-e-estados.md)
4. [perfis-permissoes-dados.md](perfis-permissoes-dados.md)
5. [financeiro-conciliacao-repasses.md](financeiro-conciliacao-repasses.md)
6. [logistica-qualidade-parceiros.md](logistica-qualidade-parceiros.md)
7. [avaliacao-ux-e-wireframes.md](avaliacao-ux-e-wireframes.md)
8. [arquitetura-e-plano-incremental.md](arquitetura-e-plano-incremental.md)
9. [matriz-regressoes-e-validacao.md](matriz-regressoes-e-validacao.md)
10. [decisoes-para-ratificacao.md](decisoes-para-ratificacao.md)
