# ACTIONFINANCE — Prompt 056 · Consolidação da documentação de estado

## Objetivo
Alinhar os documentos de estado do ActionFinance com a última entrega verificada (055) e a rota real da Spider (REC-001). **Só documentação.**

## Regras
- Alterar só os arquivos listados abaixo e criar só o novo arquivo pedido. Não mexer em código, banco, infraestrutura, na Spider, na Loja nem no Hub.
- Não reescrever o histórico: o que for substituído recebe a marca **Substituído em 09/11/2026 — ver ‹documento›** e continua no arquivo.
- Sem deploy, sem passo 0, sem testes.

## Fontes de verdade
`reviews/ACTIONFINANCE_REV_ESTADO_PUBLICADO_055.md`, `reviews/ACTIONFINANCE_REV_PUBLICACAO_CONTAS_054R1.md`, `integrations/ACTIONFINANCE_DEMANDA_SPIDER_001.md` e o relato `spider/docs/reviews/SPIDER_REV_RECONCILIACAO_ROTA_FINANCE_001.md` (só leitura).

## O que fazer
1. **`ActionFinance/README.md`:** trocar o bloco de estado por: produto 0.2.11, V25, publicado em actionfinance.actionhub.com.br, data de referência 09/11/2026. Mover a história do domínio `finaction.com.br` para uma nota curta de histórico.
2. **`documents/README.md`:** atualizar o "estado vigente" (0.2.11 / V25 / tesouraria entregue até a 054R1) com a data de referência explícita.
3. **`versioning/INDEX.md`:** posição vigente 0.2.11 / V25 / `actionfinance-web:28`; retorno 0.2.10 / `:27`.
4. **`versioning/CHANGELOG.md`:** separar, na seção "Não lançado", três coisas: o software publicado, a carga de dados reais (extrato real ainda não carregado) e o aceite do proprietário (não atribuído).
5. **`operations/ACTIONFINANCE_DEP_001.md`:** marcar como substituídas as referências a `spider-sandbox` e acrescentar um adendo de 09/11 com a rota real: `api.spider.actionhub.com.br` → `spider-runtime-prod` (2 tasks, RDS `spider-prod-canary-pg`) → Pay `LIST_PAYMENT_TRANSACTIONS`, modelo de consulta (pull).
6. **Plano/projeto 023 R1_3:** não editar o corpo. Criar `architecture/ACTIONFINANCE_MATRIZ_ATENDIMENTO_023.md` com uma tabela **Capacidade | Estado (entregue/publicado/pendente) | Evidência (relato)**, cobrindo o que as reviews 049–054R1 entregaram e o que segue pendente (posição pela fonte, conta nos compromissos, fluxo projetado, cenários, análise, conector bancário).

## Entrega
Uma lista dos arquivos alterados e do criado, com uma linha cada sobre o que mudou. Copiar este prompt para `documents/prompts/`.

## Aceite
Os cinco documentos coerentes com 0.2.11/V25, nenhuma menção vigente ao sandbox, histórico preservado e nada fora da lista alterado.
